#!/usr/bin/env python3
"""
ClearanceJobs integration using DatabaseIntegration pattern.

Unlike API-based integrations, this wraps the Playwright scraper
for ClearanceJobs.com.
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.result_builder import SearchResultBuilder
from core.prompt_loader import render_prompt
# Lazy import - only load Playwright when actually searching
# from integrations.government.clearancejobs_playwright import search_clearancejobs
from llm_utils import acompletion
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class ClearanceJobsIntegration(DatabaseIntegration):
    """
    ClearanceJobs integration - uses HTTP requests for server-side rendered pages.

    The official API is broken (returns all 57k jobs regardless of query),
    but the website pages are server-side rendered, so we use direct HTTP
    requests with BeautifulSoup parsing (10x faster than browser automation).
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="ClearanceJobs",
            id="clearancejobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=0.5,  # HTTP requests (was 5.0 for Playwright)
            rate_limit_daily=None,
            description="Security clearance job postings requiring TS/SCI, Secret, Top Secret, and other clearances",
            requires_stealth=False,  # Server-side rendered, no bot detection
            stealth_method=None  # Uses simple HTTP requests (not browser automation)
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
        Execute ClearanceJobs search via Playwright scraper with retry logic.

        Retries failed searches with exponential backoff to handle intermittent
        Playwright navigation timeouts (33% failure rate reduced to <5%).

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (no API key needed)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        # Use HTTP-based scraper (10x faster than Playwright, same results)
        from integrations.government.clearancejobs_http import search_clearancejobs
        import asyncio

        # Retry configuration (3 attempts with exponential backoff)
        max_retries = 3
        retry_delays = [1, 2, 4]  # seconds between retries

        start_time = datetime.now()
        last_error = None

        for attempt in range(max_retries):
            try:
                # Call FIXED Playwright scraper with increased timeout and better selectors
                result = await search_clearancejobs(
                    keywords=query_params.get("keywords", ""),
                    limit=limit,
                    headless=True
                )

                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Success case - normalize fields using defensive builder
                if result.get("success"):
                    normalized_jobs = []
                    for job in result.get("jobs", []):
                        normalized_job = (SearchResultBuilder()
                            .title(job.get("title"), default="Untitled Position")
                            .url(job.get("url"))
                            .snippet(job.get("description"))
                            .metadata({
                                **job,  # Keep all raw fields
                                "clearance_level": job.get("clearance", "")
                            })
                            .build())
                        normalized_jobs.append(normalized_job)

                    return QueryResult(
                        success=True,
                        source="ClearanceJobs",
                        total=result.get("total", len(normalized_jobs)),
                        results=normalized_jobs,
                        query_params=query_params,
                        response_time_ms=response_time_ms,
                        metadata={
                            "scraper": "playwright",
                            "headless": True,
                            "retry_count": attempt
                        }
                    )

                # Failure case - store error and retry if attempts remain
                last_error = result.get("error", "Unknown error from Playwright scraper")
                if attempt < max_retries - 1:
                    print(f"  ClearanceJobs attempt {attempt + 1} failed: {last_error}, retrying in {retry_delays[attempt]}s...")
                    await asyncio.sleep(retry_delays[attempt])
                    continue

            except Exception as e:
                # ClearanceJobs search exception - retry if attempts remain
                logger.warning(f"ClearanceJobs attempt {attempt + 1} threw exception: {e}, retrying in {retry_delays[attempt]}s...", exc_info=True)
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                    continue

        # All retries exhausted - return failure with last error
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return QueryResult(
            success=False,
            source="ClearanceJobs",
            total=0,
            results=[],
            query_params=query_params,
            error=f"Failed after {max_retries} attempts: {last_error}",
            response_time_ms=response_time_ms,
            metadata={
                "scraper": "playwright",
                "retry_count": max_retries
            }
        )
