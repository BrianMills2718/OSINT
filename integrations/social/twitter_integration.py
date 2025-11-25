#!/usr/bin/env python3
"""
Twitter database integration using RapidAPI twitter-api45.

Provides access to Twitter search for social media intelligence gathering.
"""

import json
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime
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

# Import Twitter API client
from experiments.twitterexplorer_sigint.api_client import execute_api_step

# Set up logger for this module
logger = logging.getLogger(__name__)


class TwitterIntegration(DatabaseIntegration):
    """
    Integration for Twitter using RapidAPI twitter-api45.

    Twitter is a social media platform used for real-time information,
    public discourse, and social intelligence gathering.

    API Features:
    - Requires RapidAPI key
    - 23 endpoints available (search, timelines, followers, replies, etc.)
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

    # Query pattern templates - map high-level intents to endpoints
    QUERY_PATTERNS = {
        "search_tweets": {
            "description": "Search for tweets by keywords or hashtags",
            "endpoint": "search.php",
            "required_params": ["query"],
            "optional_params": ["search_type", "cursor"],
            "use_case": "Finding public discussion, breaking news, trending topics"
        },
        "user_profile": {
            "description": "Get detailed information about a user",
            "endpoint": "screenname.php",
            "required_params": ["screenname"],
            "optional_params": ["rest_id"],
            "use_case": "Identifying key voices, verifying accounts, profile analysis"
        },
        "user_timeline": {
            "description": "Get a user's recent tweets and retweets",
            "endpoint": "timeline.php",
            "required_params": ["screenname"],
            "optional_params": ["rest_id", "cursor"],
            "use_case": "Tracking influencer activity, monitoring key accounts"
        },
        "user_followers": {
            "description": "Get list of users who follow an account",
            "endpoint": "followers.php",
            "required_params": ["screenname"],
            "optional_params": ["cursor"],
            "use_case": "Network analysis, finding related accounts, influence mapping"
        },
        "user_following": {
            "description": "Get list of users an account follows",
            "endpoint": "following.php",
            "required_params": ["screenname"],
            "optional_params": ["cursor"],
            "use_case": "Network analysis, finding communities, identifying interests"
        },
        "tweet_details": {
            "description": "Get full details of a specific tweet",
            "endpoint": "tweet.php",
            "required_params": ["id"],
            "optional_params": [],
            "use_case": "Analyzing specific posts, extracting media, checking engagement"
        },
        "tweet_replies": {
            "description": "Get replies to a specific tweet",
            "endpoint": "latest_replies.php",
            "required_params": ["id"],
            "optional_params": ["cursor"],
            "use_case": "Conversation tracking, community response analysis"
        },
        "tweet_thread": {
            "description": "Get all tweets in a thread",
            "endpoint": "tweet_thread.php",
            "required_params": ["id"],
            "optional_params": ["cursor"],
            "use_case": "Following multi-part statements, context gathering"
        },
        "retweet_users": {
            "description": "Get users who retweeted a specific tweet",
            "endpoint": "retweets.php",
            "required_params": ["id"],
            "optional_params": ["cursor"],
            "use_case": "Amplification analysis, finding supporters/promoters"
        },
        "trending_topics": {
            "description": "Get trending topics by country",
            "endpoint": "trends.php",
            "required_params": ["country"],
            "optional_params": [],
            "use_case": "Identifying emerging narratives, breaking news discovery"
        },
        "user_media": {
            "description": "Get tweets with media (photos/videos) from a user",
            "endpoint": "usermedia.php",
            "required_params": ["screenname"],
            "optional_params": ["rest_id", "cursor"],
            "use_case": "Visual content analysis, multimedia investigations"
        },
        "list_timeline": {
            "description": "Get tweets from a Twitter list",
            "endpoint": "listtimeline.php",
            "required_params": ["list_id"],
            "optional_params": ["cursor"],
            "use_case": "Curated source monitoring, community tracking"
        },
        "user_affiliates": {
            "description": "Get users affiliated with an account",
            "endpoint": "affilates.php",
            "required_params": ["screenname"],
            "optional_params": ["cursor"],
            "use_case": "Finding related accounts, organization mapping, affiliation analysis"
        },
        "check_follow_relationship": {
            "description": "Check if one user follows another",
            "endpoint": "checkfollow.php",
            "required_params": ["user", "follows"],
            "optional_params": [],
            "use_case": "Verify connections, validate network claims, relationship verification"
        },
        "check_retweet_status": {
            "description": "Check if a user retweeted a specific tweet",
            "endpoint": "checkretweet.php",
            "required_params": ["screenname", "tweet_id"],
            "optional_params": [],
            "use_case": "Verify amplification, check engagement, validate sharing behavior"
        },
        "bulk_user_lookup": {
            "description": "Get profiles for multiple users by IDs",
            "endpoint": "screennames.php",
            "required_params": ["rest_ids"],
            "optional_params": [],
            "use_case": "Batch profile retrieval, network analysis at scale, efficient user lookups"
        },
        "list_members": {
            "description": "Get members of a Twitter list",
            "endpoint": "list_members.php",
            "required_params": ["list_id"],
            "optional_params": ["cursor"],
            "use_case": "Curated community analysis, list membership mapping, group identification"
        },
        "list_followers": {
            "description": "Get followers of a Twitter list",
            "endpoint": "list_followers.php",
            "required_params": ["list_id"],
            "optional_params": ["cursor"],
            "use_case": "List audience analysis, community reach assessment, follower tracking"
        },
        "community_timeline": {
            "description": "Get posts from a Twitter Community",
            "endpoint": "community_timeline.php",
            "required_params": ["community_id"],
            "optional_params": ["cursor", "ranking"],
            "use_case": "Community monitoring, closed group analysis, niche discussion tracking"
        },
        "spaces_details": {
            "description": "Get details about a Twitter Spaces audio room",
            "endpoint": "spaces.php",
            "required_params": ["id"],
            "optional_params": [],
            "use_case": "Live audio monitoring, speaker identification, community event tracking"
        }
    }

    # Relationship types - investigative patterns involving multiple entities
    RELATIONSHIP_TYPES = {
        "follower_network": {
            "description": "Map who follows whom to understand influence networks",
            "endpoints": ["followers.php", "following.php"],
            "pattern": "Get followers/following lists to identify communities and influence",
            "example": "Who are the key influencers in the OSINT community?"
        },
        "conversation_tracking": {
            "description": "Track discussion threads and replies",
            "endpoints": ["search.php", "latest_replies.php", "tweet_thread.php"],
            "pattern": "Search for topic → Get replies → Analyze conversation dynamics",
            "example": "How is the intelligence community discussing new FISA reforms?"
        },
        "amplification_analysis": {
            "description": "Understand how content spreads via retweets",
            "endpoints": ["search.php", "retweets.php"],
            "pattern": "Find tweets → Get who retweeted → Analyze amplification patterns",
            "example": "Who is amplifying Russian disinformation narratives?"
        },
        "author_deep_dive": {
            "description": "Comprehensive analysis of specific accounts",
            "endpoints": ["screenname.php", "timeline.php", "followers.php", "following.php"],
            "pattern": "Get profile → Get tweets → Get network → Full context",
            "example": "Profile the account @bellingcat - who are they, what do they post, who follows them?"
        },
        "temporal_tracking": {
            "description": "Monitor how discussion evolves over time",
            "endpoints": ["search.php", "timeline.php"],
            "pattern": "Search by recency (Latest) → Track key accounts → Monitor changes",
            "example": "Track how defense Twitter discusses Ukraine war over past week"
        }
    }

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
        LLM-based relevance check for Twitter.

        Uses LLM to determine if Twitter (public discourse, breaking news, leaks,
        social movements) might have relevant content for the research question.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt
        import json

        prompt = render_prompt(
            "integrations/twitter_relevance.j2",
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
            logger.warning(f"Twitter relevance check failed, defaulting to True: {e}", exc_info=True)
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Twitter query parameters using LLM with endpoint selection.

        Uses LLM to understand the research question and select the most
        appropriate Twitter API endpoint and parameters.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "pattern": "user_timeline",
                "endpoint": "timeline.php",
                "params": {"screenname": "bellingcat"},
                "max_pages": 3,
                "reasoning": "Get recent tweets from @bellingcat"
            }
        """

        # Handle simple keywords from Boolean monitors
        # If research_question is just 1-3 words, treat as keyword search
        if len(research_question.split()) <= 3:
            # Simple keyword, use search endpoint directly without LLM
            return {
                "pattern": "search_tweets",
                "endpoint": "search.php",
                "params": {
                    "query": research_question,
                    "search_type": "Latest"
                },
                "max_pages": 2,
                "reasoning": f"Keyword search for: {research_question}"
            }

        # Full research question - use LLM with endpoint selection
        prompt = render_prompt(
            "integrations/twitter_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "enum": [
                        "search_tweets", "user_profile", "user_timeline",
                        "user_followers", "user_following", "tweet_details",
                        "tweet_replies", "tweet_thread", "retweet_users",
                        "trending_topics", "user_media", "list_timeline",
                        "user_affiliates", "check_follow_relationship", "check_retweet_status",
                        "bulk_user_lookup", "list_members", "list_followers",
                        "community_timeline", "spaces_details"
                    ],
                    "description": "Query pattern to use"
                },
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint to call (e.g., search.php, timeline.php)"
                },
                "params": {
                    "type": "object",
                    "description": "Endpoint-specific parameters",
                    "properties": {
                        "query": {"type": "string"},
                        "search_type": {"type": "string"},
                        "screenname": {"type": "string"},
                        "id": {"type": "string"},
                        "country": {"type": "string"},
                        "list_id": {"type": "string"},
                        "user": {"type": "string"},
                        "follows": {"type": "string"},
                        "tweet_id": {"type": "string"},
                        "rest_ids": {"type": "string"},
                        "community_id": {"type": "string"},
                        "cursor": {"type": "string"},
                        "ranking": {"type": "string"},
                        "rest_id": {"type": "string"}
                    },
                    "additionalProperties": True
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
            "required": ["pattern", "endpoint", "params", "max_pages", "reasoning"],
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

        return {
            "pattern": result["pattern"],
            "endpoint": result["endpoint"],
            "params": result["params"],
            "max_pages": result["max_pages"],
            "reasoning": result["reasoning"]
        }

    def _transform_tweet_to_standard(self, tweet: Dict) -> Dict:
        """
        Transform a tweet object to standardized SIGINT format.

        Args:
            tweet: Tweet object from API

        Returns:
            Standardized result dict
        """
        # Extract user info (can be in different places depending on endpoint)
        user_info = tweet.get('user_info', tweet.get('author', {}))
        screen_name = user_info.get('screen_name', user_info.get('profile', 'unknown'))
        tweet_id = tweet.get('tweet_id', tweet.get('id', ''))
        text = tweet.get('text', tweet.get('display_text', ''))

        return {
            # Common SIGINT fields (for generic display)
            "title": text[:100] + ("..." if len(text) > 100 else ""),
            "url": f"https://twitter.com/{screen_name}/status/{tweet_id}" if tweet_id else "",
            "date": tweet.get("created_at", ""),
            "description": text,

            # Twitter-specific metadata
            "author": screen_name,
            "author_name": user_info.get("name", ""),
            "verified": user_info.get("verified", user_info.get("blue_verified", False)),
            "favorites": tweet.get("favorites", tweet.get("likes", 0)),
            "retweets": tweet.get("retweets", 0),
            "replies": tweet.get("replies", 0),
            "views": tweet.get("views", "0"),
            "tweet_id": tweet_id,
            "conversation_id": tweet.get("conversation_id", ""),
            "lang": tweet.get("lang", ""),
            "engagement_total": tweet.get("favorites", 0) + tweet.get("retweets", 0) + tweet.get("replies", 0)
        }

    def _transform_user_to_standard(self, user: Dict) -> Dict:
        """
        Transform a user profile object to standardized SIGINT format.

        Args:
            user: User object from API

        Returns:
            Standardized result dict
        """
        screen_name = user.get('screen_name', user.get('profile', 'unknown'))

        return {
            # Common SIGINT fields
            "title": f"@{screen_name} - {user.get('name', 'Unknown')}",
            "url": f"https://twitter.com/{screen_name}",
            "date": user.get("created_at", ""),
            "description": user.get("description", user.get("desc", "")),

            # User-specific metadata
            "author": screen_name,
            "author_name": user.get("name", ""),
            "verified": user.get("verified", user.get("blue_verified", False)),
            "followers_count": user.get("followers_count", user.get("sub_count", 0)),
            "following_count": user.get("friends_count", user.get("friends", 0)),
            "tweet_count": user.get("statuses_count", 0),
            "location": user.get("location", ""),
            "user_id": user.get("user_id", user.get("id", user.get("rest_id", "")))
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10,
                           param_hints: Optional[Dict] = None) -> QueryResult:
        """
        Execute Twitter API call with generated parameters.

        Supports multiple endpoints: search, timeline, followers, profiles, etc.

        Args:
            query_params: Parameters from generate_query()
            api_key: RapidAPI key (required)
            limit: Maximum number of results to return
            param_hints: Optional parameter overrides from LLM reformulation

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
            # Extract endpoint and params from new format
            endpoint = query_params.get("endpoint", "search.php")
            params = query_params.get("params", {})
            max_pages = query_params.get("max_pages", 2)
            pattern = query_params.get("pattern", "search_tweets")

            # Apply param_hints overrides if provided
            if param_hints:
                params.update(param_hints)

            # Prepare step plan for api_client
            step_plan = {
                "endpoint": endpoint,
                "params": params,
                "max_pages": max_pages,
                "reason": query_params.get("reasoning", f"Twitter {pattern}")
            }

            # Execute using api_client (synchronous, so wrap in thread)
            result = await asyncio.to_thread(execute_api_step, step_plan, [], api_key)

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Check for errors
            if "error" in result:
                log_request(
                    api_name="Twitter (RapidAPI)",
                    endpoint=endpoint,
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

            # Transform results based on pattern/endpoint type
            data = result.get("data", {})
            standardized_results = []

            # Handle different response types
            if pattern in ["search_tweets", "user_timeline", "tweet_replies", "user_media", "list_timeline"]:
                # These return timeline arrays
                timeline = data.get("timeline", [])
                for tweet in timeline[:limit]:
                    standardized_results.append(self._transform_tweet_to_standard(tweet))

            elif pattern in ["user_followers", "user_following"]:
                # These return user arrays
                users = data.get("followers", data.get("following", []))
                for user in users[:limit]:
                    standardized_results.append(self._transform_user_to_standard(user))

            elif pattern == "user_profile":
                # Returns single user object
                if data:
                    standardized_results.append(self._transform_user_to_standard(data))

            elif pattern in ["tweet_details", "tweet_thread"]:
                # Returns single tweet or thread
                if pattern == "tweet_details" and data:
                    standardized_results.append(self._transform_tweet_to_standard(data))
                elif pattern == "tweet_thread":
                    thread = data.get("thread", [])
                    for tweet in thread[:limit]:
                        standardized_results.append(self._transform_tweet_to_standard(tweet))

            elif pattern == "retweet_users":
                # Returns users who retweeted
                retweeters = data.get("retweets", [])
                for user in retweeters[:limit]:
                    standardized_results.append(self._transform_user_to_standard(user))

            elif pattern == "trending_topics":
                # Returns trending topics
                trends = data.get("trends", [])
                for trend in trends[:limit]:
                    standardized_results.append({
                        "title": trend.get("name", ""),
                        "url": f"https://twitter.com/search?q={trend.get('name', '')}" if trend.get("name") else "",
                        "description": trend.get("description", trend.get("context", "")),
                        "trend_name": trend.get("name", ""),
                        "trend_context": trend.get("context", "")
                    })

            # Log successful request
            log_request(
                api_name="Twitter (RapidAPI)",
                endpoint=endpoint,
                status_code=200,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="Twitter",
                total=len(standardized_results),
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "pattern": pattern,
                    "endpoint": endpoint,
                    "pages_fetched": max_pages,
                    "params_used": params
                }
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"Twitter search failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="Twitter (RapidAPI)",
                endpoint=query_params.get("endpoint", "unknown"),
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
                error=f"Twitter API call failed: {str(e)}",
                query_params=query_params,
                response_time_ms=response_time_ms
            )
