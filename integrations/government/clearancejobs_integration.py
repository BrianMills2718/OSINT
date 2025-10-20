#!/usr/bin/env python3
"""
ClearanceJobs integration using DatabaseIntegration pattern.

Unlike API-based integrations, this wraps the Playwright scraper
for ClearanceJobs.com.
"""

import json
from typing import Dict, Optional
from datetime import datetime

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from integrations.government.clearancejobs_playwright import search_clearancejobs
from llm_utils import acompletion
from config_loader import config


class ClearanceJobsIntegration(DatabaseIntegration):
    """
    ClearanceJobs integration - wraps Playwright scraper.

    Unlike API-based integrations, this uses browser automation
    to scrape ClearanceJobs.com. The official API is broken
    (returns all 57k jobs regardless of query), so we use Playwright.
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="ClearanceJobs",
            id="clearancejobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=5.0,  # Slower due to Playwright
            rate_limit_daily=None,
            description="Security clearance job postings requiring TS/SCI, Secret, Top Secret, and other clearances"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to cleared jobs?

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about cleared jobs
        """
        job_keywords = [
            "job", "jobs", "position", "positions", "career", "careers",
            "employment", "hire", "hiring", "clearance", "cleared",
            "security clearance", "ts/sci", "ts", "sci", "secret",
            "top secret", "polygraph", "ci poly", "fs poly"
        ]

        question_lower = research_question.lower()
        return any(kw in question_lower for kw in job_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate ClearanceJobs query parameters using LLM.

        Returns keywords + clearance levels + recency filters.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "cybersecurity engineer",
                "clearance_levels": ["TS/SCI"],
                "posted_within_days": 30
            }
        """

        prompt = f"""You are a search query generator for ClearanceJobs.com, a job board for security-cleared positions.

Research Question: {research_question}

Generate search parameters:
- keywords: Search terms for job titles/descriptions (string, keep focused - 2-3 words max)
- clearance_levels: Required clearances (array from: "TS/SCI", "Top Secret", "Secret", "Confidential", "Public Trust", or empty array for all)
- posted_within_days: How recent (integer: 7, 14, 30, 60, or 0 for all time)

Clearance level guidelines:
- "TS/SCI" - Most restrictive, for intelligence/defense/cyber
- "Top Secret" - High-level government work
- "Secret" - Standard cleared positions
- "Confidential" - Entry-level cleared work
- "Public Trust" - Government positions without clearance
- Use empty array if clearance level not specified

Recency guidelines:
- Use 7 for "recent" or "latest"
- Use 30 for "last month" or default
- Use 60 for "past couple months"
- Use 0 for "all jobs" or unspecified timeframe

If this question is not about security-cleared jobs or employment, return relevant: false.

Return JSON with these exact fields."""

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
                "clearance_levels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required clearance levels, empty array for all"
                },
                "posted_within_days": {
                    "type": "integer",
                    "description": "Days back to search, 0 for all time",
                    "minimum": 0
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "keywords", "clearance_levels", "posted_within_days", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
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
            "clearance_levels": result["clearance_levels"],
            "posted_within_days": result["posted_within_days"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute ClearanceJobs search via Playwright scraper.

        Calls the existing search_clearancejobs() function which uses
        browser automation to scrape results.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (no API key needed)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()

        try:
            # Call existing Playwright scraper
            result = await search_clearancejobs(
                keywords=query_params.get("keywords", ""),
                limit=limit,
                headless=True
            )

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            if result.get("success"):
                return QueryResult(
                    success=True,
                    source="ClearanceJobs",
                    total=len(result.get("jobs", [])),
                    results=result.get("jobs", []),
                    query_params=query_params,
                    response_time_ms=response_time_ms,
                    metadata={
                        "scraper": "playwright",
                        "headless": True
                    }
                )
            else:
                return QueryResult(
                    success=False,
                    source="ClearanceJobs",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=result.get("error", "Unknown error from Playwright scraper"),
                    response_time_ms=response_time_ms
                )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=False,
                source="ClearanceJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
