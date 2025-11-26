#!/usr/bin/env python3
"""
Exa AI semantic search integration.

Provides AI-powered semantic search that understands meaning, not just keywords.
Complements Brave Search for conceptual queries and finding similar content.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import aiohttp

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

logger = logging.getLogger(__name__)


# Query patterns for LLM selection
QUERY_PATTERNS = {
    "semantic_search": {
        "description": "Neural/semantic search - finds content by meaning, not just keywords",
        "endpoint": "/search",
        "use_when": "Conceptual queries, exploratory research, when exact keywords unknown"
    },
    "find_similar": {
        "description": "Find pages similar to a given URL",
        "endpoint": "/findSimilar",
        "use_when": "Given a URL, find related companies, articles, or content"
    }
}


class ExaIntegration(DatabaseIntegration):
    """
    Integration for Exa AI semantic search API.

    Exa provides neural/embedding-based search that finds content by meaning:
    - Semantic search (understands concepts, not just keywords)
    - Find Similar (given a URL, find related pages)
    - Category filtering (company, news, research paper, pdf, github, etc.)
    - Date range filtering (published date)
    - Content retrieval (text, highlights, summaries)

    API Features:
    - Neural search using embeddings
    - Auto mode (combines neural + keyword)
    - Category filtering for targeted results
    - Date range filtering
    - Optional content extraction

    Pricing:
    - $5 per 1000 searches (1-25 results)
    - $0.001 per page for content extraction
    - $10 free credit to start

    Best for:
    - "Find companies similar to X"
    - Conceptual queries ("AI companies working with Pentagon")
    - Discovery (finding non-obvious connections)
    - When you don't know exact keywords to search
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="Exa",
            id="exa",
            category=DatabaseCategory.WEB_SEARCH,
            requires_api_key=True,
            cost_per_query_estimate=0.005,  # $5/1000 queries
            typical_response_time=1.5,
            rate_limit_daily=None,
            description="AI semantic search - finds content by meaning, not just keywords. Best for conceptual queries and finding similar content.",

            # Rate limit recovery
            rate_limit_recovery_seconds=60,
            retry_on_rate_limit_within_session=True
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Exa is relevant for most research questions.

        Let generate_query() decide the search strategy.
        """
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Exa search parameters using LLM.

        LLM decides:
        - Which pattern to use (semantic_search vs find_similar)
        - Query text or URL to search for
        - Category filter (company, news, research paper, etc.)
        - Date range if relevant
        - Number of results

        Returns:
            Dict with query parameters, or None if not relevant
        """
        prompt = render_prompt(
            "integrations/exa_query_generation.j2",
            research_question=research_question,
            query_patterns=QUERY_PATTERNS
        )

        schema = {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "enum": ["semantic_search", "find_similar"],
                    "description": "Which search pattern to use"
                },
                "query": {
                    "type": "string",
                    "description": "Search query text (for semantic_search) or URL (for find_similar)"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-25)",
                    "minimum": 1,
                    "maximum": 25
                },
                "category": {
                    "type": ["string", "null"],
                    "enum": ["company", "research paper", "news", "pdf", "github", "tweet", "personal site", "linkedin profile", "financial report", None],
                    "description": "Optional category filter"
                },
                "start_published_date": {
                    "type": ["string", "null"],
                    "description": "Start date filter (YYYY-MM-DD format) or null"
                },
                "end_published_date": {
                    "type": ["string", "null"],
                    "description": "End date filter (YYYY-MM-DD format) or null"
                },
                "include_text": {
                    "type": ["string", "null"],
                    "description": "Only include results containing this text"
                },
                "exclude_text": {
                    "type": ["string", "null"],
                    "description": "Exclude results containing this text"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the search strategy"
                }
            },
            "required": ["pattern", "query", "num_results", "category", "start_published_date", "end_published_date", "include_text", "exclude_text", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "exa_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Build query params
        query_params = {
            "pattern": result["pattern"],
            "query": result["query"],
            "num_results": result["num_results"]
        }

        # Add optional params if not null
        if result.get("category"):
            query_params["category"] = result["category"]
        if result.get("start_published_date"):
            query_params["start_published_date"] = result["start_published_date"]
        if result.get("end_published_date"):
            query_params["end_published_date"] = result["end_published_date"]
        if result.get("include_text"):
            query_params["include_text"] = result["include_text"]
        if result.get("exclude_text"):
            query_params["exclude_text"] = result["exclude_text"]

        logger.info(f"Exa query strategy: {result['reasoning']}")

        return query_params

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 10
    ) -> QueryResult:
        """
        Execute Exa search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Exa API key (required)
            limit: Maximum results (overridden by query_params if present)

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        pattern = query_params.get("pattern", "semantic_search")

        if pattern == "find_similar":
            endpoint = "https://api.exa.ai/findSimilar"
        else:
            endpoint = "https://api.exa.ai/search"

        if not api_key:
            return QueryResult(
                success=False,
                source="Exa",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for Exa",
                response_time_ms=0
            )

        try:
            # Build request body
            if pattern == "find_similar":
                body = {
                    "url": query_params["query"],
                    "numResults": query_params.get("num_results", limit),
                    "excludeSourceDomain": True  # Don't return pages from same domain
                }
            else:
                body = {
                    "query": query_params["query"],
                    "type": "auto",  # Let Exa decide neural vs keyword
                    "numResults": query_params.get("num_results", limit),
                }

            # Add optional filters
            if query_params.get("category"):
                body["category"] = query_params["category"]
            if query_params.get("start_published_date"):
                body["startPublishedDate"] = query_params["start_published_date"]
            if query_params.get("end_published_date"):
                body["endPublishedDate"] = query_params["end_published_date"]
            if query_params.get("include_text"):
                body["includeText"] = [query_params["include_text"]]
            if query_params.get("exclude_text"):
                body["excludeText"] = [query_params["exclude_text"]]

            # Execute async request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                    if response.status != 200:
                        error_text = await response.text()
                        log_request(
                            api_name="Exa",
                            endpoint=endpoint,
                            status_code=response.status,
                            response_time_ms=response_time_ms,
                            error_message=error_text,
                            request_params=body
                        )
                        return QueryResult(
                            success=False,
                            source="Exa",
                            total=0,
                            results=[],
                            query_params=query_params,
                            error=f"HTTP {response.status}: {error_text}",
                            response_time_ms=response_time_ms
                        )

                    data = await response.json()

            # Parse response
            exa_results = data.get("results", [])

            # Transform to standardized format
            standardized_results = []
            for item in exa_results:
                standardized_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("text", item.get("snippet", "")),
                    "published_date": item.get("publishedDate", ""),
                    "author": item.get("author", ""),
                    "score": item.get("score", 0),
                    "source": "Exa"
                })

            # Log successful request
            log_request(
                api_name="Exa",
                endpoint=endpoint,
                status_code=200,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=body
            )

            return QueryResult(
                success=True,
                source="Exa",
                total=len(standardized_results),
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "pattern": pattern,
                    "search_type": data.get("resolvedSearchType", "auto"),
                    "cost_dollars": data.get("costDollars", {})
                }
            )

        except asyncio.TimeoutError:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_request(
                api_name="Exa",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message="Request timeout",
                request_params=query_params
            )
            return QueryResult(
                success=False,
                source="Exa",
                total=0,
                results=[],
                query_params=query_params,
                error="Request timeout after 30s",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            logger.error(f"Exa search failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_request(
                api_name="Exa",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )
            return QueryResult(
                success=False,
                source="Exa",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
