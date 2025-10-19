#!/usr/bin/env python3
"""
USAJobs database integration.

Provides access to federal government job listings from USAJOBS.gov,
the official job site of the United States federal government.
"""

import json
from typing import Dict, Optional
from datetime import datetime
import requests
from llm_utils import acompletion

from database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from api_request_tracker import log_request


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
        return DatabaseMetadata(
            name="USAJobs",
            id="usajobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # Unknown
            description="Official U.S. federal government job listings across all agencies"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to federal jobs?

        We check for job-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about employment.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about federal jobs, False otherwise
        """
        job_keywords = [
            "job", "jobs", "career", "careers", "employment", "hiring",
            "position", "positions", "vacancy", "vacancies", "work",
            "federal", "government", "usajobs", "civil service",
            "gs", "grade", "agency"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in job_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate USAJobs query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the USAJobs API.

        Args:
            research_question: The user's research question

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

        prompt = f"""You are a search query generator for USAJOBS, the official U.S. federal government job site.

Research Question: {research_question}

Generate search parameters for the USAJOBS API:
- keywords: Search terms for job titles/descriptions (string, keep focused)
- location: Geographic location if specified (string like "Washington, DC" or "California" or null)
- organization: Federal agency/organization (string like "Department of Defense", "FBI", or null)
- pay_grade_low: Minimum GS pay grade if mentioned (integer 1-15, or null)
- pay_grade_high: Maximum GS pay grade if mentioned (integer 1-15, or null)

Guidelines:
- keywords: Use job title or skill terms (e.g., "engineer", "analyst", "scientist")
- location: Format as city-state or just state name, null if not mentioned
- organization: Use full agency names, null if not specified
- pay_grade: GS (General Schedule) grades range 1-15, where:
  * GS-1 to GS-4: Entry-level positions
  * GS-5 to GS-9: Junior professional positions
  * GS-10 to GS-12: Mid-level professional positions
  * GS-13 to GS-15: Senior professional/supervisory positions
  Only specify if the question explicitly mentions pay grade or seniority level

If this question is not about federal government jobs or employment, return relevant: false.

Return JSON with these exact fields. Use null for optional fields.

Example 1:
Question: "What data science jobs are available in the DC area?"
Response:
{{
  "relevant": true,
  "keywords": "data science",
  "location": "Washington, DC",
  "organization": null,
  "pay_grade_low": null,
  "pay_grade_high": null,
  "reasoning": "Federal data science positions in DC area"
}}

Example 2:
Question: "Senior engineer positions at NASA"
Response:
{{
  "relevant": true,
  "keywords": "engineer",
  "location": null,
  "organization": "NASA",
  "pay_grade_low": 13,
  "pay_grade_high": 15,
  "reasoning": "Senior engineering roles at NASA (GS-13 to 15)"
}}

Example 3:
Question: "What cybersecurity jobs with clearances are available?"
Response:
{{
  "relevant": true,
  "keywords": "cybersecurity security clearance",
  "location": null,
  "organization": null,
  "pay_grade_low": null,
  "pay_grade_high": null,
  "reasoning": "Federal cybersecurity positions requiring clearances"
}}

Example 4:
Question: "What government contracts are available?"
Response:
{{
  "relevant": false,
  "keywords": "",
  "location": null,
  "organization": null,
  "pay_grade_low": null,
  "pay_grade_high": null,
  "reasoning": "Question is about contracts, not jobs"
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
                    "description": "Search keywords for job titles and descriptions"
                },
                "location": {
                    "type": ["string", "null"],
                    "description": "Geographic location or null"
                },
                "organization": {
                    "type": ["string", "null"],
                    "description": "Federal agency/organization name or null"
                },
                "pay_grade_low": {
                    "type": ["integer", "null"],
                    "description": "Minimum GS pay grade (1-15) or null"
                },
                "pay_grade_high": {
                    "type": ["integer", "null"],
                    "description": "Maximum GS pay grade (1-15) or null"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "keywords", "location", "organization", "pay_grade_low", "pay_grade_high", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model="gpt-5-mini",
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

        if not result["relevant"]:
            return None

        return {
            "keywords": result["keywords"],
            "location": result["location"],
            "organization": result["organization"],
            "pay_grade_low": result["pay_grade_low"],
            "pay_grade_high": result["pay_grade_high"]
        }

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
                error="API key required for USAJobs"
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
                "User-Agent": "claude-code-research@anthropic.com",  # Required by API
                "Authorization-Key": api_key
            }

            # Execute API call
            response = requests.get(endpoint, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()

            # USAJobs wraps results in SearchResult object
            search_result = data.get("SearchResult", {})
            jobs = search_result.get("SearchResultItems", [])
            total = search_result.get("SearchResultCount", len(jobs))

            # Extract job details from nested structure
            results = []
            for item in jobs[:limit]:
                matched_obj = item.get("MatchedObjectDescriptor", {})
                results.append(matched_obj)

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
                error=f"HTTP {status_code}: {str(e)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
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
                response_time_ms=response_time_ms
            )
