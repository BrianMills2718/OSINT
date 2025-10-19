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
        Quick relevance check - does question relate to government contracts?

        We check for contract/procurement-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about federal contracting.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about contracts, False otherwise
        """
        contract_keywords = [
            "contract", "contracts", "contracting", "procurement", "solicitation",
            "rfp", "rfq", "rfi", "sources sought", "opportunity", "opportunities",
            "bid", "bids", "bidding", "proposal", "proposals", "federal",
            "government", "agency", "sam.gov", "sam", "award", "awards"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in contract_keywords)

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

        prompt = f"""You are a search query generator for SAM.gov, the U.S. federal government contracting opportunities system.

Research Question: {research_question}

Generate search parameters for the SAM.gov API:
- keywords: Search terms for opportunity titles/descriptions (string, keep focused)
- procurement_types: Types of procurement (array from: "Solicitation", "Presolicitation", "Combined Synopsis/Solicitation", "Sources Sought")
- set_aside: Small business set-aside type (string from: null, "SBA" (Total Small Business), "8A", "SDVOSBC" (Service-Disabled Veteran), "WOSB" (Women-Owned), "HZC" (HUBZone), or null for none)
- naics_codes: Industry classification codes if relevant (array of strings like ["541512", "541519"], or empty array)
- organization: Specific agency/organization if mentioned (string or null)
- date_range_days: How many days back to search (integer 1-365, default 60)

Guidelines:
- keywords: Use industry/procurement-specific terms
- procurement_types: Include all types unless specifically requested (e.g., "RFPs only" → ["Solicitation"])
- set_aside: Only ONE allowed per query, use null if not specified
- naics_codes: Common codes:
  * 541512 - Computer Systems Design Services
  * 541519 - Other Computer Related Services
  * 541611 - Administrative Management Consulting
  * 541990 - All Other Professional Services
  * 334111 - Electronic Computer Manufacturing
  * 518210 - Data Processing Services
- organization: Only specify if question mentions specific agency (e.g., "DoD", "FBI", "VA")
- date_range_days: Use 30 for "recent", 60 for default, 90 for "past few months"

IMPORTANT: SAM.gov REQUIRES a date range and it cannot exceed 365 days.

If this question is not about government contracts or procurement, return relevant: false.

Return JSON with these exact fields. Use empty arrays for optional list fields and null for optional single fields.

Example 1:
Question: "What cybersecurity contracts are available from DoD?"
Response:
{{
  "relevant": true,
  "keywords": "cybersecurity",
  "procurement_types": [],
  "set_aside": null,
  "naics_codes": ["541512", "541519"],
  "organization": "Department of Defense",
  "date_range_days": 60,
  "reasoning": "DoD cybersecurity contracting opportunities"
}}

Example 2:
Question: "Recent small business IT solicitations"
Response:
{{
  "relevant": true,
  "keywords": "IT information technology",
  "procurement_types": ["Solicitation"],
  "set_aside": "SBA",
  "naics_codes": ["541512", "541519"],
  "organization": null,
  "date_range_days": 30,
  "reasoning": "Recent IT solicitations for small businesses"
}}

Example 3:
Question: "What military jobs require security clearances?"
Response:
{{
  "relevant": false,
  "keywords": "",
  "procurement_types": [],
  "set_aside": null,
  "naics_codes": [],
  "organization": null,
  "date_range_days": 60,
  "reasoning": "Question is about jobs, not contracts"
}}
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether this database is relevant to the question"
                },
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
                    "description": "Days back to search, 1-365",
                    "minimum": 1,
                    "maximum": 365
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "keywords", "procurement_types", "set_aside", "naics_codes", "organization", "date_range_days", "reasoning"],
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

        if not result["relevant"]:
            return None

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
            date_range_days = query_params.get("date_range_days", 60)
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

            # Execute API call
            response = requests.get(endpoint, params=params,
                                  timeout=config.get_database_config("sam")["timeout"])
            response.raise_for_status()
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
