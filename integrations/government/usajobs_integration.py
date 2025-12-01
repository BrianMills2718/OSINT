#!/usr/bin/env python3
"""
USAJobs database integration.

Provides access to federal government job listings from USAJOBS.gov,
the official job site of the United States federal government.
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio
import requests
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.result_builder import SearchResultBuilder
from core.api_request_tracker import log_request
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class USAJobsIntegration(DatabaseIntegration):
    """
    Integration for USAJOBS - Official U.S. Federal Government job board.

    USAJOBS is the official employment site for the U.S. federal government,
    listing positions across all federal agencies and departments.

    API Features:
    - Requires API key (free registration)
    - Requires User-Agent header with email
    - Search by keywords
    - Filter by location (city, state)
    - Filter by organization/agency
    - Filter by pay grade, position type

    Rate Limits:
    - Unknown (appears generous for reasonable use)
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="USAJobs",
            id="usajobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=True,
            api_key_env_var="USAJOBS_API_KEY",
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # Unknown
            description="Official U.S. federal government job listings across all agencies"
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

    async def generate_query(self, research_question: str, param_hints: Optional[Dict] = None) -> Optional[Dict]:
        """
        Generate USAJobs query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the USAJobs API.

        Args:
            research_question: The user's research question
            param_hints: Optional parameter hints to override LLM-generated values
                (e.g., {"keywords": "cybersecurity"} to use broad single keyword)

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "data scientist",
                "location": "Washington, DC",
                "organization": None,
                "pay_grade_low": None,
                "pay_grade_high": None
            }
        """

        prompt = render_prompt(
            "integrations/usajobs_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                                "keywords": {
                    "type": "string",
                    "description": "Search keywords for job titles and descriptions"
                },
                "location": {
                    "type": "string",
                    "description": "Geographic location (optional)"
                },
                "organization": {
                    "type": "string",
                    "description": "Federal agency/organization name (optional)"
                },
                "pay_grade_low": {
                    "type": "integer",
                    "description": "Minimum GS pay grade (1-15) (optional)"
                },
                "pay_grade_high": {
                    "type": "integer",
                    "description": "Maximum GS pay grade (1-15) (optional)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["keywords", "organization", "pay_grade_low", "pay_grade_high", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "usajobs_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

        # Build query params from LLM result
        query_params = {
            "keywords": result["keywords"],
            "location": result["location"],
            "organization": result["organization"],
            "pay_grade_low": result["pay_grade_low"],
            "pay_grade_high": result["pay_grade_high"]
        }

        # Merge param_hints if provided (hints override LLM values)
        if param_hints:
            query_params.update(param_hints)

        return query_params

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute USAJobs search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: USAJobs API key (required)
            limit: Maximum number of results to return (max 500)

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://data.usajobs.gov/api/search"

        if not api_key:
            return QueryResult(
                success=False,
                source="USAJobs",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for USAJobs",
                http_code=None  # Non-HTTP error
            )

        try:
            # Build request parameters
            params = {
                "ResultsPerPage": min(limit, 500)  # USAJobs max is 500
            }

            # Add keywords if specified
            if query_params.get("keywords"):
                params["Keyword"] = query_params["keywords"]

            # Add location
            if query_params.get("location"):
                params["LocationName"] = query_params["location"]

            # Add organization
            if query_params.get("organization"):
                params["Organization"] = query_params["organization"]

            # Add pay grade range
            if query_params.get("pay_grade_low"):
                params["PayGradeLow"] = query_params["pay_grade_low"]

            if query_params.get("pay_grade_high"):
                params["PayGradeHigh"] = query_params["pay_grade_high"]

            # USAJobs requires specific headers
            headers = {
                "Host": "data.usajobs.gov",
                "User-Agent": "brianmills2718@gmail.com",  # Required by API
                "Authorization-Key": api_key
            }

            # Execute API call
            # Run blocking requests in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(endpoint, params=params, headers=headers, timeout=config.get_database_config("usajobs")["timeout"])
            )
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()

            # USAJobs wraps results in SearchResult object
            search_result = data.get("SearchResult", {})
            jobs = search_result.get("SearchResultItems", [])
            total = search_result.get("SearchResultCount", len(jobs))

            # Extract job details from nested structure using defensive builder
            results = []
            for item in jobs[:limit]:
                matched_obj = item.get("MatchedObjectDescriptor", {})

                # Extract URL with fallback chain
                url = matched_obj.get("PositionURI")
                if not url:
                    apply_uri = matched_obj.get("ApplyURI", [])
                    if apply_uri and len(apply_uri) > 0:
                        url = apply_uri[0].get("ApplicationURI")

                normalized = (SearchResultBuilder()
                    .title(matched_obj.get("PositionTitle"), default="Untitled Position")
                    .url(url)
                    .snippet(matched_obj.get("QualificationSummary"), max_length=200)
                    .metadata({
                        **matched_obj,  # Keep all raw fields for specialized consumers
                        "description": SearchResultBuilder.safe_text(
                            matched_obj.get("QualificationSummary"), max_length=500
                        )
                    })
                    .build())

                results.append(normalized)

            # Mask API key in headers for logging
            log_headers = headers.copy()
            log_headers["Authorization-Key"] = f"{api_key[:8]}***{api_key[-4:]}"

            # Log successful request
            log_request(
                api_name="USAJobs",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params={"params": params, "headers": log_headers}
            )

            return QueryResult(
                success=True,
                source="USAJobs",
                total=total,
                results=results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "user_area": search_result.get("UserArea", {})
                }
            )

        except requests.HTTPError as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="USAJobs",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="USAJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e,
                http_code=status_code)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="USAJobs",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="USAJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                http_code=None,  # Non-HTTP error
                response_time_ms=response_time_ms
            )
