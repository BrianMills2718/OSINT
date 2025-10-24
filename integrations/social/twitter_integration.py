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
        Quick relevance check for Twitter.

        Twitter is useful for: Public discourse, breaking news, leaks, social movements
        Twitter is NOT useful for: Structured data (contracts, jobs, procurement)

        Args:
            research_question: The user's research question

        Returns:
            False if asking about structured data (contracts/jobs), True for social/news queries
        """
        # Quick keyword check for structured data queries where Twitter isn't helpful
        question_lower = research_question.lower()

        # Contract/procurement queries - Twitter rarely has official solicitations
        contract_keywords = ["contract", "solicitation", "rfp", "procurement", "award", "bidding", "idiq", "gwac"]
        if any(keyword in question_lower for keyword in contract_keywords):
            # Check if also asking about discourse/news about contracts (Twitter IS relevant for that)
            discourse_keywords = ["discussion", "news", "announcement", "opinion", "reaction", "controversy"]
            if not any(keyword in question_lower for keyword in discourse_keywords):
                return False

        # Job posting queries - Twitter has job ads but better sources exist (USAJobs, ClearanceJobs)
        job_keywords = ["jobs available", "job openings", "hiring for", "recruiting for"]
        if any(keyword in question_lower for keyword in job_keywords):
            return False

        return True

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
        # Check relevance first
        if not await self.is_relevant(research_question):
            return None

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
        prompt = f"""Generate search parameters for Twitter.

Twitter provides: Real-time social media posts and public discussions.

API Parameters:
- query (string, required):
    Twitter search query. Supports boolean operators:
    OR (alternatives), AND (required terms), NOT (exclusions), quotes for exact phrases
    Example: "JTTF OR counterterrorism" or "FBI AND hiring"

- search_type (enum, required):
    Search filter type. Valid options:
    "Latest" = Most recent tweets
    "Top" = Most popular/engaging tweets
    "Media" = Tweets with images/videos
    "People" = User profiles (for finding accounts, not tweets)

- max_pages (integer, required):
    Number of result pages to fetch. Range: 1-5
    Each page contains approximately 20 tweets.

Research Question: {research_question}

Decide whether Twitter is relevant for this question.

Twitter is useful for:
- Public discourse and opinions on government programs, policies, leaks
- Breaking news, whistleblower revelations, investigative journalism
- Official government accounts and announcements
- Activism, protests, social movements
- Expert commentary from journalists, researchers, former officials
- Real-time reactions to events

Twitter is NOT useful for:
- Structured data like contracts, jobs, procurement
- Historical documents or archives
- Formal government records

If the question involves public discussion, news, leaks, or social/political topics,
Twitter is HIGHLY RELEVANT. Only mark as not relevant if it's purely about
structured government data (contracts, jobs, etc.).

Return JSON:
{{
  "relevant": boolean,
  "query": string,
  "search_type": "Latest" | "Top" | "Media" | "People",
  "max_pages": integer,
  "reasoning": string
}}
"""

        schema = {
            "type": "object",
            "properties": {
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
            "required": ["query", "search_type", "max_pages", "reasoning"],
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

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

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
