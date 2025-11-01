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
from core.prompt_loader import render_prompt
# Lazy import - only load Playwright when actually searching
# from integrations.government.clearancejobs_playwright import search_clearancejobs
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
        Generate ClearanceJobs query parameters using LLM.

        NOTE: The Playwright scraper only supports keyword search.
        Clearance levels and recency are extracted from results, not used as filters.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "cybersecurity engineer"
            }
        """

        prompt = render_prompt(
            "integrations/clearancejobs_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                                "keywords": {
                    "type": "string",
                    "description": "Search keywords for job titles and descriptions"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["keywords", "reasoning"],
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

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

        return {
            "keywords": result["keywords"]
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
            # Lazy import - only import Playwright when actually executing
            from integrations.government.clearancejobs_playwright import search_clearancejobs

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
                    total=result.get("total", len(result.get("jobs", []))),
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
