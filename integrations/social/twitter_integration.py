#!/usr/bin/env python3
"""
Twitter database integration using RapidAPI twitter-api45.

Provides access to Twitter search for social media intelligence gathering.
"""

import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from llm_utils import acompletion

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config

# Import Twitter API client
from twitterexplorer_sigint.api_client import execute_api_step


class TwitterIntegration(DatabaseIntegration):
    """
    Integration for Twitter using RapidAPI twitter-api45.

    Twitter is a social media platform used for real-time information,
    public discourse, and social intelligence gathering.

    API Features:
    - Requires RapidAPI key
    - Search tweets by keywords
    - Filter by search type (Latest, Top, Media, People)
    - Cursor-based pagination
    - Rate limiting handled automatically

    Search Types:
    - Latest: Most recent tweets
    - Top: Most popular/relevant tweets
    - Media: Tweets with images/videos
    - People: User profiles matching query

    Rate Limits:
    - Managed by RapidAPI (varies by subscription plan)
    - Exponential backoff for 429 errors built into api_client
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Twitter",
            id="twitter",
            category=DatabaseCategory.SOCIAL_TWITTER,
            requires_api_key=True,
            cost_per_query_estimate=0.01,  # RapidAPI cost + LLM cost
            typical_response_time=3.0,     # seconds (API calls can be slow)
            rate_limit_daily=None,         # Depends on RapidAPI subscription
            description="Twitter search for tweets, users, and social media intelligence"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to social media / Twitter?

        We check for social media-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about social intelligence.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about social media, False otherwise
        """
        social_keywords = [
            "twitter", "tweet", "tweets", "social media", "social", "trending",
            "conversation", "discussion", "public opinion", "sentiment",
            "discourse", "community", "online", "viral", "hashtag",
            # SIGINT-specific keywords
            "jttf", "counterterrorism", "extremism", "radicalization",
            "disinformation", "misinformation", "propaganda",
            "influence operations", "social movements"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in social_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Twitter search parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the Twitter API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "JTTF OR counterterrorism",
                "search_type": "Latest",
                "max_pages": 2,
                "reasoning": "Recent tweets about JTTF and counterterrorism"
            }
        """

        # Handle simple keywords from Boolean monitors
        # If research_question is just 1-3 words, treat as keyword search
        if len(research_question.split()) <= 3:
            # Simple keyword, use directly without LLM
            return {
                "query": research_question,
                "search_type": "Latest",
                "max_pages": 2,
                "reasoning": f"Keyword search for: {research_question}"
            }

        # Full research question - use LLM
        prompt = f"""You are a search query generator for Twitter (via RapidAPI twitter-api45).

Research Question: {research_question}

Generate search parameters for the Twitter API:
- query: Search keywords (use Twitter Boolean operators: OR, AND, NOT, quotes for exact phrases)
- search_type: Search filter type (MUST be one of: "Latest", "Top", "Media", "People")
- max_pages: Number of pages to fetch (integer 1-5, each page ~20 results)
- reasoning: Brief explanation of query strategy

Search Type Guidelines:
- "Latest": Most recent tweets (best for time-sensitive research, breaking news)
- "Top": Most popular/relevant tweets (best for high-engagement content)
- "Media": Tweets with images/videos (best for visual content)
- "People": User profiles (best for finding accounts, NOT for tweets)

Query Syntax Tips:
- Use OR for alternatives: "JTTF OR counterterrorism"
- Use AND to require multiple terms: "cybersecurity AND federal"
- Use quotes for exact phrases: "\\"joint terrorism task force\\""
- Use NOT to exclude: "python NOT snake"
- Keep queries focused (Twitter search has limitations)

Guidelines:
- query: Use Boolean operators for precision
- search_type: "Latest" for time-sensitive, "Top" for popularity
- max_pages: 1-2 for broad queries, 3-5 for focused queries
- reasoning: Explain why these parameters were chosen

IMPORTANT: search_type MUST be exactly one of: "Latest", "Top", "Media", "People"

If this question is not about social media or Twitter, return relevant: false.

Return JSON with these exact fields.

Example 1:
Question: "Recent Twitter discussions about JTTF and counterterrorism operations"
Response:
{{
  "relevant": true,
  "query": "JTTF OR \\"Joint Terrorism Task Force\\" OR counterterrorism",
  "search_type": "Latest",
  "max_pages": 3,
  "reasoning": "Use Latest for recent discussions, OR operator to catch variations, 3 pages for good coverage"
}}

Example 2:
Question: "What are people saying about FBI hiring?"
Response:
{{
  "relevant": true,
  "query": "FBI AND (hiring OR jobs OR careers OR recruitment)",
  "search_type": "Top",
  "max_pages": 2,
  "reasoning": "Top tweets for high-engagement discussions, AND/OR for relevant combinations"
}}

Example 3:
Question: "Federal contracting opportunities in Virginia"
Response:
{{
  "relevant": false,
  "query": "",
  "search_type": "Latest",
  "max_pages": 1,
  "reasoning": "Question is about federal contracts, not social media"
}}
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether this database is relevant to the question"
                },
                "query": {
                    "type": "string",
                    "description": "Twitter search query with Boolean operators"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["Latest", "Top", "Media", "People"],
                    "description": "Search filter type"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Number of pages to fetch (1-5)",
                    "minimum": 1,
                    "maximum": 5
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "query", "search_type", "max_pages", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "twitter_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        if not result["relevant"]:
            return None

        return {
            "query": result["query"],
            "search_type": result["search_type"],
            "max_pages": result["max_pages"],
            "reasoning": result["reasoning"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute Twitter search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: RapidAPI key (required)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()

        if not api_key:
            return QueryResult(
                success=False,
                source="Twitter",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for Twitter (RapidAPI)"
            )

        try:
            # Prepare step plan for api_client
            step_plan = {
                "endpoint": "search.php",
                "params": {
                    "query": query_params.get("query", ""),
                    "search_type": query_params.get("search_type", "Latest")
                },
                "max_pages": query_params.get("max_pages", 2),
                "reason": query_params.get("reasoning", "Twitter search")
            }

            # Execute search using api_client (synchronous, so wrap in thread)
            # This handles async/sync mismatch (Risk #2 from RISKS_SUMMARY.md)
            result = await asyncio.to_thread(execute_api_step, step_plan, [], api_key)

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Check for errors
            if "error" in result:
                # Log failed request
                log_request(
                    api_name="Twitter (RapidAPI)",
                    endpoint="search.php",
                    status_code=result.get('status_code', 0),
                    response_time_ms=response_time_ms,
                    error_message=result["error"],
                    request_params=query_params
                )

                return QueryResult(
                    success=False,
                    source="Twitter",
                    total=0,
                    results=[],
                    error=result["error"],
                    query_params=query_params,
                    response_time_ms=response_time_ms
                )

            # Extract timeline (list of tweets)
            data = result.get("data", {})
            timeline = data.get("timeline", [])

            # Transform Twitter API format to SIGINT common format
            standardized_results = []
            for tweet in timeline[:limit]:  # Respect limit
                user_info = tweet.get('user_info', {})
                screen_name = user_info.get('screen_name', 'unknown')
                tweet_id = tweet.get('tweet_id', '')
                text = tweet.get('text', '')

                standardized_results.append({
                    # Common SIGINT fields (for generic display)
                    "title": text[:100] + ("..." if len(text) > 100 else ""),
                    "url": f"https://twitter.com/{screen_name}/status/{tweet_id}" if tweet_id else "",
                    "date": tweet.get("created_at", ""),
                    "description": text,

                    # Twitter-specific metadata (for advanced features)
                    "author": screen_name,
                    "author_name": user_info.get("name", ""),
                    "verified": user_info.get("verified", False),
                    "favorites": tweet.get("favorites", 0),
                    "retweets": tweet.get("retweets", 0),
                    "replies": tweet.get("replies", 0),
                    "views": tweet.get("views", "0"),
                    "tweet_id": tweet_id,
                    "conversation_id": tweet.get("conversation_id", ""),
                    "lang": tweet.get("lang", ""),

                    # Engagement metadata (for filtering/sorting)
                    "engagement_total": tweet.get("favorites", 0) + tweet.get("retweets", 0) + tweet.get("replies", 0)
                })

            # Log successful request
            log_request(
                api_name="Twitter (RapidAPI)",
                endpoint="search.php",
                status_code=200,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="Twitter",
                total=len(timeline),  # Total from current page(s)
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "search_type": query_params.get("search_type"),
                    "pages_fetched": query_params.get("max_pages"),
                    "query_used": query_params.get("query")
                }
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="Twitter (RapidAPI)",
                endpoint="search.php",
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Twitter",
                total=0,
                results=[],
                error=f"Twitter search failed: {str(e)}",
                query_params=query_params,
                response_time_ms=response_time_ms
            )
