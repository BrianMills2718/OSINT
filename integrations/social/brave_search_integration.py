#!/usr/bin/env python3
"""
Brave Search database integration.

Provides access to open web content via Brave Search API including news,
analysis, leaked documents, court filings, and advocacy reports.
"""

import json
import logging
import re
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


class BraveSearchIntegration(DatabaseIntegration):
    """
    Integration for Brave Search API.

    Brave Search provides access to open web content not available
    in structured government databases:
    - Investigative journalism & analysis
    - Leaked documents & whistleblower reports
    - Court filings & legal documents
    - Advocacy group reports
    - News coverage of government programs

    API Features:
    - API key required (free tier: 2,000 queries/month)
    - Web search with relevance ranking
    - Freshness filters (past day/week/month/year)
    - Country and language filters
    - Pagination support (offset parameter)

    Rate Limits:
    - Free tier: 2,000 queries/month
    - Paid tier: $5 per 1,000 queries
    - 1 request per second recommended

    Limitations:
    - Results per query: 1-20 (default 10)
    - Offset limit: 0-9 (max 200 results via pagination)
    - No exact date filtering (only freshness periods)
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="Brave Search",
            id="brave_search",
            category=DatabaseCategory.WEB_SEARCH,
            requires_api_key=True,
            api_key_env_var="BRAVE_SEARCH_API_KEY",
            cost_per_query_estimate=0.005,  # $5/1000 queries + LLM cost
            typical_response_time=1.0,       # seconds
            rate_limit_daily=None,           # Monthly limit, not daily
            description="Web search for investigative journalism, analysis, leaked docs, and news coverage",

            # Rate Limit Recovery - Brave has 1 req/sec recommendation
            rate_limit_recovery_seconds=120,  # 2 min wait, then retry
            retry_on_rate_limit_within_session=True  # Worth waiting and retrying
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Simplified relevance check per user feedback.

        Always returns True to let LLM in generate_query() make the decision.
        User wants minimal filtering: "I only want it there to clearly exclude
        things which are clearly not relevant."

        Args:
            research_question: The user's research question

        Returns:
            True (always - let LLM decide in generate_query)
        """
        # Simplified per user feedback - let LLM decide in generate_query
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Brave Search query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the Brave Search API.
        Returns None if LLM determines web search is not relevant.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "NSA surveillance programs leaked documents",
                "count": 10,
                "freshness": "pm",  # past month
                "country": "us"
            }
        """

        prompt = render_prompt(
            "integrations/brave_search_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                                "query": {
                    "type": "string",
                    "description": "Search query string for Brave Search"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return (1-20)",
                    "minimum": 1,
                    "maximum": 20
                },
                "freshness": {
                    "type": "string",
                    "description": "Time filter: pd, pw, pm, py (optional)"
                },
                "country": {
                    "type": "string",
                    "description": "Country code (e.g., 'us')"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["query", "count", "country", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "brave_search_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

        # Build query params dict (exclude null freshness)
        query_params = {
            "query": result["query"],
            "count": result["count"],
            "country": result["country"]
        }

        if result["freshness"] is not None:
            query_params["freshness"] = result["freshness"]

        return query_params

    # Rate limit retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 2  # Start with 2 seconds
    MAX_BACKOFF_SECONDS = 60     # Cap at 60 seconds

    async def _make_request_with_retry(
        self,
        endpoint: str,
        params: Dict,
        api_key: str
    ) -> requests.Response:
        """
        Make HTTP request with automatic retry on 429 rate limit errors.

        Uses exponential backoff: 2s, 4s, 8s (capped at 60s).

        Args:
            endpoint: API endpoint URL
            params: Query parameters
            api_key: API key for authentication

        Returns:
            Response object on success

        Raises:
            requests.HTTPError: On non-429 HTTP errors or after max retries
        """
        loop = asyncio.get_event_loop()
        backoff = self.INITIAL_BACKOFF_SECONDS

        for attempt in range(self.MAX_RETRIES + 1):
            response = await loop.run_in_executor(
                None,
                lambda p=params: requests.get(
                    endpoint,
                    params=p,
                    headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                    timeout=15
                )
            )

            # Success - return response
            if response.status_code == 200:
                return response

            # Rate limited - retry with backoff
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(f"Brave Search rate limited (429), waiting {backoff}s before retry {attempt + 1}/{self.MAX_RETRIES}")
                print(f"⏳ Brave Search rate limited, waiting {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.MAX_BACKOFF_SECONDS)
                continue

            # Other error or max retries exceeded - raise
            response.raise_for_status()

        # Should not reach here, but raise if we do
        response.raise_for_status()
        return response  # For type checker

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute Brave Search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Brave Search API key (required)
            limit: Maximum number of results to return (max 20)

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://api.search.brave.com/res/v1/web/search"

        if not api_key:
            return QueryResult(
                success=False,
                source="Brave Search",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for Brave Search",
                response_time_ms=0
            )

        try:
            # Build request parameters
            params = {
                "q": query_params["query"],
                "count": min(query_params.get("count", 10), 20),
                "search_lang": "en",  # English results only per user requirement
            }

            # Add optional parameters
            if query_params.get("freshness"):
                params["freshness"] = query_params["freshness"]

            if query_params.get("country"):
                params["country"] = query_params["country"]

            # Execute API call with automatic retry on rate limit
            response = await self._make_request_with_retry(endpoint, params, api_key)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            web_results = data.get("web", {}).get("results", [])

            # Transform to standardized format using defensive builder
            standardized_results = []
            for item in web_results[:limit]:
                standardized_results.append(SearchResultBuilder()
                    .title(item.get("title"), default="Untitled")
                    .url(item.get("url"))
                    .snippet(item.get("description"))
                    .metadata({
                        "age": item.get("age", ""),
                        "language": item.get("language", "en"),
                        "profile": item.get("profile", {}),
                        "source": "Brave Search"
                    })
                    .build())

            # Log successful request
            log_request(
                api_name="Brave Search",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=params
            )

            return QueryResult(
                success=True,
                source="Brave Search",
                total=len(standardized_results),
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "search_query": params["q"],
                    "freshness": params.get("freshness")
                }
            )

        except requests.HTTPError as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            # Extract status code from response, or parse from error message as fallback
            if e.response is not None:
                status_code = e.response.status_code
            else:
                # Parse status code from error message (e.g., "429 Client Error")
                match = re.search(r'(\d{3})\s+(?:Client|Server)\s+Error', str(e))
                status_code = int(match.group(1)) if match else 0

            # Log failed request
            log_request(
                api_name="Brave Search",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=f"HTTP {status_code}",
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Brave Search",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="Brave Search",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Brave Search",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
