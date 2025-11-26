#!/usr/bin/env python3
"""
Reddit database integration using PRAW (Python Reddit API Wrapper).

Provides access to Reddit search for social media intelligence gathering.
"""

import json
import asyncio
import logging
import os
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
import praw

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config
from llm_utils import acompletion
from core.prompt_loader import render_prompt

# Load environment variables
load_dotenv()

# Set up logger for this module
logger = logging.getLogger(__name__)


class RedditIntegration(DatabaseIntegration):
    """
    Integration for Reddit using PRAW API.

    Reddit is a social media platform organized into communities (subreddits)
    used for discussions, news sharing, and community intelligence gathering.

    API Features:
    - Requires Reddit API credentials (client_id, client_secret, username, password)
    - Search across multiple subreddits
    - Filter by time range (hour, day, week, month, year, all)
    - Sort by relevance, hot, top, new, comments
    - Rate limits handled by PRAW automatically

    Search Capabilities:
    - Keyword search across post titles and content
    - Boolean operators supported (with limitations - see query syntax guide)
    - Subreddit-specific or multi-subreddit search
    - Time-filtered results

    Query Syntax (Empirically Tested 2025-10-25):
    - BEST: Unquoted keywords with AND (e.g., "threat intelligence AND contract") - 43% accuracy
    - AVOID: Quoted phrases with Boolean (e.g., "threat intelligence" AND contract) - 0% accuracy
    - AVOID: Parentheses for grouping (e.g., (contract OR procurement)) - breaks queries
    - See docs/INTEGRATION_QUERY_GUIDES.md for detailed test results

    Rate Limits:
    - Reddit API: 60 requests per minute
    - PRAW handles rate limiting automatically
    """

    def __init__(self) -> None:
        """Initialize Reddit client with lazy loading."""
        self._reddit_client = None

    def _get_reddit_client(self) -> Optional[object]:
        """Lazy initialize Reddit client on first use."""
        if self._reddit_client is None:
            # Get credentials from environment variables (loaded from .env)
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            username = os.getenv("REDDIT_USERNAME")
            password = os.getenv("REDDIT_PASSWORD")
            user_agent = "SIGINT_Platform/1.0"

            if not all([client_id, client_secret, username, password]):
                raise ValueError("Reddit credentials not found in environment variables (.env file)")

            self._reddit_client = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                user_agent=user_agent
            )

        return self._reddit_client

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="Reddit",
            id="reddit",
            category=DatabaseCategory.SOCIAL_REDDIT,
            requires_api_key=False,  # Loads credentials from .env internally via _get_reddit_client()
            cost_per_query_estimate=0.01,  # LLM cost for query generation
            typical_response_time=2.0,     # seconds
            rate_limit_daily=None,         # 100 req/min (post-2023), handled by PRAW
            description="Reddit search for discussions, news, and community intelligence",

            # Rate Limit Recovery - Reddit has 100 requests/minute (post-2023 API changes)
            # Source: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
            # PRAW handles rate limiting automatically (waits up to 600s internally)
            rate_limit_recovery_seconds=60,  # If PRAW fails, wait 1 min
            retry_on_rate_limit_within_session=True  # Worth retrying - per-minute limit
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for Reddit.

        Uses LLM to determine if Reddit communities might have valuable information
        for the research question, considering Reddit's strengths and limitations.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt

        prompt = render_prompt(
            "integrations/reddit_relevance.j2",
            research_question=research_question
        )

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)

        except Exception as e:
            logger.warning(f"Reddit relevance check failed, defaulting to True: {e}", exc_info=True)
            return True

    async def generate_query(self, research_question: str, param_hints: Optional[Dict] = None) -> Optional[Dict]:
        """
        Generate Reddit search parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the Reddit API.

        Args:
            research_question: The user's research question
            param_hints: Optional parameter hints to override LLM-generated values
                (e.g., {"time_filter": "year"} to expand time range)

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "JTTF OR counterterrorism",
                "subreddits": ["Intelligence", "natsec", "FBI"],
                "sort": "relevance",
                "time_filter": "month",
                "reasoning": "Searching intelligence/security subreddits for JTTF discussions"
            }
        """

        # Handle simple keywords from Boolean monitors
        # If research_question is just 1-3 words, treat as keyword search
        if len(research_question.split()) <= 3:
            # Simple keyword, use directly without LLM
            query_params = {
                "query": research_question,
                "subreddits": ["Intelligence", "natsec", "OSINT"],  # Default intelligence subreddits
                "sort": "relevance",
                "time_filter": "month",
                "reasoning": f"Keyword search for: {research_question}"
            }
            # Merge param_hints if provided (hints override defaults)
            if param_hints:
                query_params.update(param_hints)
            return query_params

        # Full research question - use LLM
        prompt = render_prompt(
            "integrations/reddit_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reddit search query using UNQUOTED keywords with AND (best accuracy). AVOID quoted phrases with Boolean."
                },
                "subreddits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of subreddit names to search (without r/ prefix)",
                    "minItems": 1,
                    "maxItems": 5
                },
                "sort": {
                    "type": "string",
                    "enum": ["relevance", "hot", "top", "new", "comments"],
                    "description": "Sort order for results"
                },
                "time_filter": {
                    "type": "string",
                    "enum": ["hour", "day", "week", "month", "year", "all"],
                    "description": "Time range to search"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["query", "subreddits", "sort", "time_filter", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "reddit_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Build query params from LLM result
        query_params = {
            "query": result["query"],
            "subreddits": result["subreddits"],
            "sort": result["sort"],
            "time_filter": result["time_filter"],
            "reasoning": result["reasoning"]
        }

        # Merge param_hints if provided (hints override LLM values)
        if param_hints:
            query_params.update(param_hints)

        return query_params

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 25) -> QueryResult:
        """
        Execute Reddit search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (credentials from config)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()

        try:
            # Get Reddit client
            reddit = self._get_reddit_client()

            # Build subreddit string (e.g., "Intelligence+natsec+OSINT")
            subreddit_list = query_params.get("subreddits", ["all"])
            subreddit_string = "+".join(subreddit_list)
            subreddit = reddit.subreddit(subreddit_string)

            # Execute search (sync operation, wrap in thread)
            query = query_params.get("query", "")
            sort = query_params.get("sort", "relevance")
            time_filter = query_params.get("time_filter", "month")

            # PRAW search is synchronous, run in thread pool
            search_results = await asyncio.to_thread(
                lambda: list(subreddit.search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                ))
            )

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Transform Reddit API format to SIGINT common format
            standardized_results = []
            for submission in search_results:
                # Extract post data
                author_name = submission.author.name if submission.author else "[deleted]"
                created_dt = datetime.fromtimestamp(submission.created_utc)

                standardized_results.append({
                    # Common SIGINT fields (for generic display)
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "date": created_dt.strftime("%Y-%m-%d"),
                    "description": submission.selftext[:500] if submission.selftext else "",

                    # Reddit-specific metadata
                    "subreddit": submission.subreddit.display_name,
                    "author": author_name,
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "post_id": submission.id,
                    "is_self": submission.is_self,
                    "link_flair_text": submission.link_flair_text,

                    # Engagement metadata (for filtering/sorting)
                    "engagement_total": submission.score + submission.num_comments
                })

            # Log successful request
            log_request(
                api_name="Reddit (PRAW)",
                endpoint="search",
                status_code=200,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="Reddit",
                total=len(standardized_results),
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "subreddits_searched": subreddit_list,
                    "sort": sort,
                    "time_filter": time_filter,
                    "query_used": query
                }
            )

        except ValueError as e:
            # Configuration error
            logger.error(f"Reddit configuration error: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            log_request(
                api_name="Reddit (PRAW)",
                endpoint="search",
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Reddit",
                total=0,
                results=[],
                error=f"Reddit configuration error: {str(e)}",
                query_params=query_params,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Catch-all for unexpected errors at integration boundary
            # This is acceptable - return error instead of crashing
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log the error with full stack trace
            logger.error(f"Reddit search failed: {e}", exc_info=True)

            # Log failed request
            log_request(
                api_name="Reddit (PRAW)",
                endpoint="search",
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Reddit",
                total=0,
                results=[],
                error=f"Reddit search failed: {str(e)}",
                query_params=query_params,
                response_time_ms=response_time_ms
            )
