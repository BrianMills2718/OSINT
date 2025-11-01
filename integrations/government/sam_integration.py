#!/usr/bin/env python3
"""
SAM.gov database integration.

Provides access to federal government contracting opportunities from SAM.gov
(System for Award Management).
"""

import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import requests
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config


class SAMIntegration(DatabaseIntegration):
    """
    Integration for SAM.gov - System for Award Management.

    SAM.gov is the official U.S. government system for finding federal
    contracting opportunities including solicitations, presolicitations,
    and sources sought notices.

    API Features:
    - Requires API key
    - Search by keywords
    - Filter by procurement type
    - Filter by set-aside type
    - Filter by agency/organization
    - Filter by NAICS codes
    - REQUIRES date range (max 1 year)

    Rate Limits:
    - Unknown but appears to be strict (429 errors common)
    - Recommendation: 1-2 seconds between requests
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="SAM.gov",
            id="sam",
            category=DatabaseCategory.CONTRACTS,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.5,      # seconds (often slow)
            rate_limit_daily=None,          # Unknown, but strict
            description="U.S. federal government contracting opportunities and solicitations"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - always return True, let generate_query() LLM decide.

        The LLM in generate_query() is smarter at determining relevance and avoids
        false negatives from overly restrictive keyword matching.

        Args:
            research_question: The user's research question

        Returns:
            Always True - relevance determined by generate_query()
        """
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate SAM.gov query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the SAM.gov API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "cybersecurity",
                "procurement_types": ["Solicitation"],
                "set_aside": None,
                "naics_codes": ["541512", "541519"],
                "date_range_days": 60
            }
        """

        prompt = render_prompt(
            "integrations/sam_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                                "keywords": {
                    "type": "string",
                    "description": "Search keywords for opportunity titles and descriptions"
                },
                "procurement_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of procurement types, empty if not specified"
                },
                "set_aside": {
                    "type": ["string", "null"],
                    "description": "Set-aside type code or null"
                },
                "naics_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of NAICS codes, empty if not specified"
                },
                "organization": {
                    "type": ["string", "null"],
                    "description": "Agency/organization name or null"
                },
                "date_range_days": {
                    "type": "integer",
                    "description": "Days back to search, 1-364 (NOT 365 - API limit)",
                    "minimum": 1,
                    "maximum": 364
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["keywords", "procurement_types", "set_aside", "naics_codes", "organization", "date_range_days", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "sam_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

        return {
            "keywords": result["keywords"],
            "procurement_types": result["procurement_types"],
            "set_aside": result["set_aside"],
            "naics_codes": result["naics_codes"],
            "organization": result["organization"],
            "date_range_days": result["date_range_days"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute SAM.gov search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: SAM.gov API key (required)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://api.sam.gov/opportunities/v2/search"

        if not api_key:
            return QueryResult(
                success=False,
                source="SAM.gov",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for SAM.gov"
            )

        try:
            # Calculate date range (required by SAM.gov)
            # CRITICAL: SAM.gov rejects exactly 365 days with "Date range must be null year(s) apart"
            # Maximum allowed is 364 days
            date_range_days = query_params.get("date_range_days", 60)
            date_range_days = min(date_range_days, 364)  # Cap at 364 days (API limit)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=date_range_days)

            # Build request parameters
            params = {
                "api_key": api_key,
                "postedFrom": from_date.strftime("%m/%d/%Y"),
                "postedTo": to_date.strftime("%m/%d/%Y"),
                "limit": min(limit, 1000),  # SAM.gov max is 1000
                "offset": 0
            }

            # Add keywords if specified
            if query_params.get("keywords"):
                params["keywords"] = query_params["keywords"]

            # Add procurement type mapping
            ptype_map = {
                "Solicitation": "o",
                "Presolicitation": "p",
                "Combined Synopsis/Solicitation": "k",
                "Sources Sought": "r"
            }
            if query_params.get("procurement_types") and len(query_params["procurement_types"]) > 0:
                params["ptype"] = ",".join([ptype_map.get(p, p) for p in query_params["procurement_types"]])

            # Add set-aside (only one allowed)
            if query_params.get("set_aside"):
                params["typeOfSetAside"] = query_params["set_aside"]

            # Add NAICS codes
            if query_params.get("naics_codes") and len(query_params["naics_codes"]) > 0:
                params["ncode"] = ",".join(query_params["naics_codes"])

            # Add organization
            if query_params.get("organization"):
                params["organizationName"] = query_params["organization"]

            # Execute API call with retry logic for rate limits
            max_retries = 3
            retry_delays = [2, 4, 8]  # Exponential backoff: 2s, 4s, 8s

            for attempt in range(max_retries):
                response = requests.get(endpoint, params=params,
                                      timeout=config.get_database_config("sam")["timeout"])

                # If HTTP 429 (rate limit), retry with backoff
                if response.status_code == 429:
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        import time
                        delay = retry_delays[attempt]
                        print(f"SAM.gov rate limit hit, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        # Last attempt failed, raise the error
                        response.raise_for_status()

                # Success or non-retryable error
                response.raise_for_status()
                break

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            opportunities = data.get("opportunitiesData", data.get("results", []))
            total = data.get("totalRecords", data.get("total", len(opportunities)))

            # Mask API key in params for logging
            log_params = params.copy()
            if "api_key" in log_params:
                log_params["api_key"] = f"{api_key[:8]}***{api_key[-4:]}"

            # Log successful request
            log_request(
                api_name="SAM.gov",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=log_params
            )

            return QueryResult(
                success=True,
                source="SAM.gov",
                total=total,
                results=opportunities[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "date_range": {
                        "from": from_date.strftime("%Y-%m-%d"),
                        "to": to_date.strftime("%Y-%m-%d")
                    }
                }
            )

        except requests.HTTPError as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request (but don't expose full error with API key)
            log_request(
                api_name="SAM.gov",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=f"HTTP {status_code}",
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="SAM.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="SAM.gov",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="SAM.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
