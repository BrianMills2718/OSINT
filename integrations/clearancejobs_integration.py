#!/usr/bin/env python3
"""
ClearanceJobs database integration.

Provides access to U.S. security clearance job listings through the
ClearanceJobs API.
"""

import json
from typing import Dict, Optional
from datetime import datetime
import sys
import os

# Add ClearanceJobs to path - need to go up one level from integrations/
clearance_jobs_path = os.path.join(os.path.dirname(__file__), '..', 'ClearanceJobs')
if clearance_jobs_path not in sys.path:
    sys.path.insert(0, clearance_jobs_path)

from ClearanceJobs import ClearanceJobs
import litellm

from database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from api_request_tracker import log_request


class ClearanceJobsIntegration(DatabaseIntegration):
    """
    Integration for ClearanceJobs - U.S. security clearance job board.

    ClearanceJobs is a specialized job board for positions requiring
    U.S. security clearances (Confidential, Secret, TS/SCI, etc.).

    API Features:
    - No authentication required
    - Search by keywords
    - Filter by clearance level
    - Filter by posting date

    Rate Limits:
    - Unknown (appears generous)
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="ClearanceJobs",
            id="clearancejobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only, API is free
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # Unknown
            description="U.S. security clearance job listings (government contractor positions)"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to jobs?

        We check for job-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about jobs.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about jobs, False otherwise
        """
        job_keywords = [
            "job", "jobs", "career", "careers", "employment", "hiring",
            "position", "positions", "vacancy", "vacancies", "work",
            "contractor", "contracting", "clearance", "cleared"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in job_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate ClearanceJobs query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the ClearanceJobs API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "cybersecurity analyst",
                "clearances": ["TS/SCI", "Top Secret"],
                "posted_days_ago": 30
            }
        """

        prompt = f"""You are a search query generator for ClearanceJobs, a U.S. security clearance job board.

Research Question: {research_question}

Generate search parameters for the ClearanceJobs API:
- keywords: Search terms for job title/description (string)
- clearances: Security clearance levels required (array of strings from: "Unspecified", "Confidential", "Secret", "Top Secret", "TS/SCI", "Q Clearance")
- posted_days_ago: How recent the postings (integer, 0-365, where 0 = any time)

Guidelines:
- keywords: Use specific job-related terms, avoid very long queries
- clearances: Only specify if the question mentions clearance requirements
- posted_days_ago: Only filter by date if recency is mentioned (e.g., "recent", "new", "this week")

If this question is not about jobs or employment, return relevant: false.

Return JSON with these exact fields. Use empty arrays for clearances and 0 for posted_days_ago if not applicable.

Example 1:
Question: "What cybersecurity jobs with TS/SCI are available?"
Response:
{{
  "relevant": true,
  "keywords": "cybersecurity",
  "clearances": ["TS/SCI"],
  "posted_days_ago": 0,
  "reasoning": "Looking for cybersecurity jobs requiring TS/SCI clearance"
}}

Example 2:
Question: "Recent counterterrorism analyst positions?"
Response:
{{
  "relevant": true,
  "keywords": "counterterrorism analyst",
  "clearances": [],
  "posted_days_ago": 30,
  "reasoning": "Recent postings for counterterrorism analyst roles"
}}

Example 3:
Question: "What government contracts are available?"
Response:
{{
  "relevant": false,
  "keywords": "",
  "clearances": [],
  "posted_days_ago": 0,
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
                "clearances": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of clearance levels, empty if not specified"
                },
                "posted_days_ago": {
                    "type": "integer",
                    "description": "Days ago for posting date filter, 0 for any time"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "keywords", "clearances", "posted_days_ago", "reasoning"],
            "additionalProperties": False
        }

        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "clearancejobs_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        if not result["relevant"]:
            return None

        return {
            "keywords": result["keywords"],
            "clearances": result["clearances"],
            "posted_days_ago": result["posted_days_ago"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute ClearanceJobs search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (ClearanceJobs doesn't require auth)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://api.clearancejobs.com/api/v1/jobs/search"

        try:
            cj = ClearanceJobs()

            # Build request body
            body = {
                "pagination": {"page": 1, "size": limit},
                "query": query_params.get("keywords", "")
            }

            # Add clearance filter if specified
            if query_params.get("clearances") and len(query_params["clearances"]) > 0:
                body["filters"] = body.get("filters", {})
                body["filters"]["clearance"] = query_params["clearances"]

            # Add date filter if specified
            if query_params.get("posted_days_ago") and query_params["posted_days_ago"] > 0:
                body.setdefault("filters", {})["posted"] = query_params["posted_days_ago"]

            # Execute API call
            response = cj.post("/jobs/search", body)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()

            # ClearanceJobs returns "data" array and "meta" object
            jobs = data.get("data", [])
            meta = data.get("meta", {})
            pagination = meta.get("pagination", {})
            total = pagination.get("total", len(jobs))

            # Log successful request
            log_request(
                api_name="ClearanceJobs",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=body
            )

            return QueryResult(
                success=True,
                source="ClearanceJobs",
                total=total,
                results=jobs[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "pagination": pagination
                }
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="ClearanceJobs",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="ClearanceJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
