#!/usr/bin/env python3
"""
NewsAPI database integration.

Provides access to news articles from 80,000+ sources globally via NewsAPI.org.
Supports keyword search, date filtering, source filtering, and language selection.
"""

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
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


class NewsAPIIntegration(DatabaseIntegration):
    """
    Integration for NewsAPI - News aggregation from 80,000+ sources worldwide.

    NewsAPI provides access to breaking news headlines and historical articles
    from news sources and blogs across the web.

    API Features:
    - Search across 80,000+ news sources
    - Filter by date, source, language, domain
    - Sort by relevancy, popularity, or publishedAt
    - Advanced search operators (quotes, AND/OR/NOT, +/-)
    - Article metadata (title, description, author, url, image)

    Rate Limits (Free Tier):
    - 100 requests per day
    - Articles up to 1 month old
    - 24-hour delay before articles searchable
    - Development use only

    API Documentation:
    - https://newsapi.org/docs
    - https://newsapi.org/docs/endpoints/everything
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        db_config = config.get_database_config("newsapi")

        return DatabaseMetadata(
            name="NewsAPI",
            id="newsapi",
            category=DatabaseCategory.NEWS,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only (API is free tier)
            typical_response_time=2.0,      # seconds
            rate_limit_daily=db_config.get("rate_limit_daily", 100),  # Free tier limit
            description="News aggregation from 80,000+ sources worldwide with keyword search and filtering"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for NewsAPI.

        Uses LLM to determine if NewsAPI might have relevant news coverage
        for the research question.

        Args:
            research_question: The user's research question

        Returns:
            True if relevant, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv

        load_dotenv()

        prompt = f"""Is NewsAPI relevant for researching this question?

RESEARCH QUESTION:
{research_question}

NEWSAPI CHARACTERISTICS:
Strengths:
- 80,000+ news sources worldwide (major outlets + blogs + trade publications)
- Breaking news and current events
- Media coverage and public perception
- Timeline of news coverage for events
- Multiple perspectives across different sources
- Search by keywords, dates, sources, language
- Good for: What is the media saying? What's the timeline? How is this covered?

Limitations:
- News articles only (not primary documents, government filings, or data)
- Free tier: Articles up to 1 month old only (24-hour delay)
- Not for: Corporate filings (use SEC EDGAR), government contracts (use SAM.gov), job postings, academic research

DECISION CRITERIA:
- Is relevant: If seeking news coverage, media perspective, public discourse, or timeline of events
- NOT relevant: If ONLY seeking primary documents, government data, corporate filings, or academic research

Return JSON:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why NewsAPI is/isn't relevant"
}}"""

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default to True on parsing failure

        except Exception as e:
            # Fallback on error - acceptable to default to True
            logger.warning(f"NewsAPI relevance check failed, defaulting to True: {e}", exc_info=True)
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate NewsAPI query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for NewsAPI.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "artificial intelligence military",
                "from_date": "2024-10-01",
                "to_date": "2024-11-01",
                "language": "en",
                "sort_by": "relevancy",
                "limit": 50
            }
        """

        prompt = render_prompt(
            "integrations/newsapi_query.j2",
            research_question=research_question
        )

        schema = {
            "name": "newsapi_query",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {
                        "type": "boolean",
                        "description": "Is this question relevant for NewsAPI?"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why is/isn't this relevant for NewsAPI?"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search keywords (max 500 chars, supports AND/OR/NOT, quotes for exact match)"
                    },
                    "from_date": {
                        "type": ["string", "null"],
                        "description": "Start date in YYYY-MM-DD format (null for oldest available)"
                    },
                    "to_date": {
                        "type": ["string", "null"],
                        "description": "End date in YYYY-MM-DD format (null for most recent)"
                    },
                    "language": {
                        "type": "string",
                        "description": "2-letter language code (en, es, fr, de, etc.)",
                        "enum": ["ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "zh"]
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort order for results",
                        "enum": ["relevancy", "popularity", "publishedAt"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to retrieve (1-100)"
                    }
                },
                "required": ["relevant", "reasoning", "query", "from_date", "to_date", "language", "sort_by", "limit"],
                "additionalProperties": False
            }
        }

        response = await acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": schema}
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        return {
            "query": result.get("query", ""),
            "from_date": result.get("from_date"),
            "to_date": result.get("to_date"),
            "language": result.get("language", "en"),
            "sort_by": result.get("sort_by", "relevancy"),
            "limit": min(result.get("limit", 50), 100)  # Cap at API max
        }

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 50
    ) -> QueryResult:
        """
        Execute NewsAPI search via /v2/everything endpoint.

        Args:
            query_params: Query parameters from generate_query()
            api_key: NewsAPI API key (from .env)
            limit: Maximum results to return

        Returns:
            QueryResult with news articles found
        """
        query = query_params.get("query", "")
        from_date = query_params.get("from_date")
        to_date = query_params.get("to_date")
        language = query_params.get("language", "en")
        sort_by = query_params.get("sort_by", "relevancy")
        limit = min(query_params.get("limit", 50), limit, 100)  # Cap at 100 (API max)

        # Safety net: Enforce free tier's 30-day historical limit
        # This prevents 426 errors when LLM generates dates older than allowed
        from integrations.source_metadata import get_source_metadata
        metadata = get_source_metadata("NewsAPI")
        if metadata and from_date:
            historical_limit_days = metadata.characteristics.get('historical_data_limit_days', 30)
            cutoff_date = (datetime.now() - timedelta(days=historical_limit_days)).strftime("%Y-%m-%d")
            if from_date < cutoff_date:
                from_date = cutoff_date
                # Note: This is transparent to the LLM - we just enforce the constraint

        if not query:
            return QueryResult(
                success=False,
                source="NewsAPI",
                total=0,
                results=[],
                query_params=query_params,
                error="No search query provided"
            )

        # Get API key
        if not api_key:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("NEWSAPI_API_KEY")

        if not api_key:
            return QueryResult(
                success=False,
                source="NewsAPI",
                total=0,
                results=[],
                query_params=query_params,
                error="NewsAPI key not found. Set NEWSAPI_API_KEY in .env file."
            )

        try:
            # Build request
            url = "https://newsapi.org/v2/everything"

            # Build query params
            query_params = {
                "q": query,
                "language": language,
                "sortBy": sort_by,
                "pageSize": limit
            }

            # Add optional date filters
            if from_date:
                query_params["from"] = from_date
            if to_date:
                query_params["to"] = to_date

            # Make request with API key in header
            response = requests.get(
                url,
                params=query_params,
                headers={"X-Api-Key": api_key},
                timeout=15
            )

            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("status") == "error":
                error_code = data.get("code", "unknown")
                error_message = data.get("message", "Unknown error")
                return QueryResult(
                    success=False,
                    source="NewsAPI",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"NewsAPI error ({error_code}): {error_message}"
                )

            # Extract articles
            articles = data.get("articles", [])
            total_results = data.get("totalResults", 0)

            documents = []

            for article in articles:
                # Extract article data
                source_info = article.get("source", {})
                source_name = source_info.get("name", "Unknown")

                # Build document
                doc = {
                    "title": article.get("title", "No title"),
                    "url": article.get("url", ""),
                    "snippet": article.get("description", "")[:500] if article.get("description") else "",
                    "date": article.get("publishedAt", "")[:10] if article.get("publishedAt") else None,  # Extract YYYY-MM-DD
                    "metadata": {
                        "source": source_name,
                        "author": article.get("author"),
                        "published_at": article.get("publishedAt"),
                        "url_to_image": article.get("urlToImage"),
                        "content_preview": article.get("content", "")[:200] if article.get("content") else None
                    }
                }
                documents.append(doc)

            return QueryResult(
                success=True,
                source="NewsAPI",
                total=len(documents),
                results=documents,
                query_params=query_params,
                response_time_ms=int(response.elapsed.total_seconds() * 1000),
                metadata={"total_results_available": total_results}
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"NewsAPI HTTP error: {e}", exc_info=True)
            if e.response.status_code == 429:
                return QueryResult(
                    success=False,
                    source="NewsAPI",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="NewsAPI rate limit exceeded (100 requests/day on free tier)"
                )
            elif e.response.status_code == 401:
                return QueryResult(
                    success=False,
                    source="NewsAPI",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="NewsAPI authentication failed. Check API key in .env"
                )
            else:
                return QueryResult(
                    success=False,
                    source="NewsAPI",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"NewsAPI HTTP error: {str(e)}"
                )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"NewsAPI search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="NewsAPI",
                total=0,
                results=[],
                query_params=query_params,
                error=f"NewsAPI search failed: {str(e)}"
            )
