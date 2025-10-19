#!/usr/bin/env python3
"""
ClearanceJobs database integration.

Provides access to U.S. security clearance job listings through
Puppeteer-based web scraping (the official API is broken).
"""

import json
from typing import Dict, Optional
from datetime import datetime
import sys
import os

from llm_utils import acompletion

from database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from api_request_tracker import log_request
from integrations.clearancejobs_puppeteer import search_clearancejobs, PuppeteerNotAvailableError


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
- keywords: BE SPECIFIC with multi-word job titles (e.g., "cybersecurity engineer" NOT just "cybersecurity", "network administrator" NOT just "network")
  * Use full job titles: "cybersecurity analyst", "intelligence analyst", "software engineer"
  * Avoid single generic words that match too broadly
  * Focus on the actual POSITION, not just the field
- clearances: Only specify if the question mentions clearance requirements
- posted_days_ago: Only filter by date if recency is mentioned (e.g., "recent", "new", "this week")

If this question is not about jobs or employment, return relevant: false.

Return JSON with these exact fields. Use empty arrays for clearances and 0 for posted_days_ago if not applicable.

Example 1:
Question: "What cybersecurity jobs with TS/SCI are available?"
Response:
{{
  "relevant": true,
  "keywords": "cybersecurity analyst",
  "clearances": ["TS/SCI"],
  "posted_days_ago": 0,
  "reasoning": "Looking for cybersecurity analyst positions requiring TS/SCI clearance"
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

        response = await acompletion(
            model="gpt-5-mini",
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
        Execute ClearanceJobs search using Puppeteer web scraping.

        NOTE: The official ClearanceJobs Python library API is broken - it
        returns all 57k+ jobs regardless of search query. This implementation
        uses Puppeteer to interact with the actual website search form.

        This method should be called with Puppeteer MCP tools available in the
        environment. If running from Claude Code, this will work automatically.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (ClearanceJobs doesn't require auth)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://www.clearancejobs.com/jobs"

        error_msg = (
            "ClearanceJobs integration requires Puppeteer MCP server. "
            "The Python API library is broken (returns irrelevant results). "
            "Please run this search from Claude Code with Puppeteer MCP configured, "
            "or manually search at https://www.clearancejobs.com/jobs"
        )

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        log_request(
            api_name="ClearanceJobs",
            endpoint=endpoint,
            status_code=0,
            response_time_ms=response_time_ms,
            error_message=error_msg,
            request_params=query_params
        )

        return QueryResult(
            success=False,
            source="ClearanceJobs",
            total=0,
            results=[],
            query_params=query_params,
            error=error_msg,
            response_time_ms=response_time_ms,
            metadata={
                "method": "puppeteer_required",
                "manual_url": f"https://www.clearancejobs.com/jobs?keywords={query_params.get('keywords', '').replace(' ', '+')}"
            }
        )
