#!/usr/bin/env python3
"""
Brave Search database integration.

Provides access to open web content via Brave Search API including news,
analysis, leaked documents, court filings, and advocacy reports.
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
                    "type": ["string", "null"],
                    "description": "Time filter: pd, pw, pm, py, or null"
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
            "required": ["query", "count", "freshness", "country", "reasoning"],
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

            # Execute API call
            # Run blocking requests in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    endpoint,
                    params=params,
                    headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                    timeout=15
                )
            )
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            web_results = data.get("web", {}).get("results", [])

            # Transform to standardized format
            standardized_results = []
            for item in web_results[:limit]:
                standardized_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "age": item.get("age", ""),  # "X days ago" or date
                    "language": item.get("language", "en"),
                    "profile": item.get("profile", {}),  # Site info
                    "source": "Brave Search"
                })

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
            status_code = e.response.status_code if e.response else 0

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
