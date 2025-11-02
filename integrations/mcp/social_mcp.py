#!/usr/bin/env python3
"""
Social Media & Web Search MCP Server

This MCP server wraps 4 social media and web search integrations as FastMCP tools:
- Twitter: Social media search via RapidAPI
- Brave Search: Web search for investigative journalism and analysis
- Discord: Community discussions from OSINT servers (local export search)
- Reddit: Reddit search for discussions and news

Design: Thin wrapper layer that reuses existing DatabaseIntegration classes.
No duplication - all configuration, error handling, and API logic comes from
the DatabaseIntegration implementations.

Usage:
    # In-memory (CLI/Streamlit)
    from fastmcp import Client
    async with Client(social_mcp.mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_twitter", {...})

    # STDIO (AI assistants like Claude Desktop)
    python -m integrations.mcp.social_mcp

    # HTTP (remote clients)
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
"""

import json
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Import DatabaseIntegration classes
from integrations.social.twitter_integration import TwitterIntegration
from integrations.social.brave_search_integration import BraveSearchIntegration
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.reddit_integration import RedditIntegration

# Create MCP server
mcp = FastMCP(
    name="Social Media & Web Search",
    instructions="""
    Access to social media and web search sources for investigative research.

    Available tools:
    - search_twitter: Twitter search for real-time discussions and news
    - search_brave: Web search for investigative journalism, analysis, leaked docs
    - search_discord: OSINT community discussions (Bellingcat, Project OWL)
    - search_reddit: Reddit search for community discussions and expert commentary

    All tools use LLM-powered query generation to understand natural language
    research questions and generate appropriate search parameters.
    """
)


# =============================================================================
# Twitter - Social Media Search
# =============================================================================

@mcp.tool
async def search_twitter(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 20
) -> dict:
    """Search Twitter for tweets and social media discussions.

    Twitter provides real-time social media posts and public discussions,
    useful for breaking news, public discourse, whistleblower revelations,
    and expert commentary.

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters for the Twitter API (via RapidAPI).

    Args:
        research_question: Natural language query (e.g., "JTTF counterterrorism
            operations" or "NSA whistleblower revelations")
        api_key: RapidAPI key (optional, uses RAPIDAPI_KEY env var if not provided)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "Twitter"
            - total: int (total tweets returned)
            - results: list of tweets with metadata
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_twitter(
        ...     research_question="FBI domestic terrorism threat assessment",
        ...     limit=10
        ... )
        {
            "success": True,
            "source": "Twitter",
            "total": 10,
            "results": [
                {
                    "title": "Breaking: FBI releases domestic terrorism...",
                    "url": "https://twitter.com/username/status/123...",
                    "date": "2024-03-15",
                    "author": "username",
                    "verified": True,
                    "favorites": 245,
                    "retweets": 89,
                    ...
                }
            ],
            "query_params": {
                "query": "FBI OR domestic terrorism OR threat assessment",
                "search_type": "Latest"
            },
            "response_time_ms": 3214.56
        }

    Note:
        Requires RapidAPI subscription for twitter-api45 service.
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("RAPIDAPI_KEY")

    # Create integration instance
    integration = TwitterIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "Twitter",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for Twitter"
        }

    # Execute search
    result = await integration.execute_search(query_params, api_key, limit)

    # Convert QueryResult to dict
    return {
        "success": result.success,
        "source": result.source,
        "total": result.total,
        "results": result.results,
        "query_params": result.query_params,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
        "metadata": result.metadata
    }


# =============================================================================
# Brave Search - Web Search
# =============================================================================

@mcp.tool
async def search_brave(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search the web for investigative journalism, analysis, and leaked documents.

    Brave Search provides access to open web content not available in structured
    government databases:
    - Investigative journalism & analysis
    - Leaked documents & whistleblower reports
    - Court filings & legal documents
    - Advocacy group reports
    - News coverage of government programs

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters for the Brave Search API.

    Args:
        research_question: Natural language query (e.g., "NSA surveillance
            programs leaked documents")
        api_key: Brave Search API key (optional, uses BRAVE_SEARCH_API_KEY env var
            if not provided)
        limit: Maximum number of results to return (default: 10, max: 20)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "Brave Search"
            - total: int (total results returned)
            - results: list of web pages with metadata
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_brave(
        ...     research_question="ICE detention facilities human rights violations",
        ...     limit=10
        ... )
        {
            "success": True,
            "source": "Brave Search",
            "total": 10,
            "results": [
                {
                    "title": "Report: Human Rights Violations at ICE Facilities",
                    "url": "https://example.org/ice-report",
                    "description": "Investigation reveals widespread abuse...",
                    "age": "2 weeks ago",
                    "source": "Brave Search"
                }
            ],
            "query_params": {
                "query": "ICE detention violations report",
                "count": 10,
                "freshness": "pm"
            },
            "response_time_ms": 1234.56
        }

    Note:
        Free tier: 2,000 queries/month. Paid tier: $5 per 1,000 queries.
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    # Create integration instance
    integration = BraveSearchIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "Brave Search",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for Brave Search"
        }

    # Execute search
    result = await integration.execute_search(query_params, api_key, limit)

    # Convert QueryResult to dict
    return {
        "success": result.success,
        "source": result.source,
        "total": result.total,
        "results": result.results,
        "query_params": result.query_params,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
        "metadata": result.metadata
    }


# =============================================================================
# Discord - OSINT Community Discussions
# =============================================================================

@mcp.tool
async def search_discord(
    research_question: str,
    limit: int = 10
) -> dict:
    """Search Discord OSINT community discussions for expert analysis and breaking news.

    Discord provides access to community discussions from OSINT servers including:
    - Bellingcat: OSINT investigative journalism community
    - Project OWL: Geopolitical analysis and intelligence discussions
    - Other OSINT and intelligence community servers

    This tool searches local exported Discord message history (no API key required).
    It uses an LLM to extract key search terms from your research question.

    Args:
        research_question: Natural language query (e.g., "ukraine intelligence
            analysis" or "bellingcat geolocation techniques")
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "Discord"
            - total: int (total messages found)
            - results: list of Discord messages with metadata
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_discord(
        ...     research_question="satellite imagery analysis techniques",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "Discord",
            "total": 5,
            "results": [
                {
                    "title": "Discord message from @analyst",
                    "content": "For satellite imagery analysis, I recommend...",
                    "url": "https://discord.com/channels/...",
                    "timestamp": "2024-03-15T10:30:00",
                    "author": "analyst",
                    "server": "Bellingcat",
                    "channel": "geospatial-analysis",
                    "score": 0.75,
                    "matched_keywords": ["satellite", "imagery", "analysis"]
                }
            ],
            "query_params": {
                "keywords": ["satellite", "imagery", "analysis", "geolocation"]
            },
            "response_time_ms": 543.21
        }

    Note:
        Searches local exported Discord message history. No API key required.
        Discord exports must be present in data/exports/ directory.
    """
    # Create integration instance (uses local exports)
    integration = DiscordIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "Discord",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for Discord"
        }

    # Execute search (no API key needed)
    result = await integration.execute_search(query_params, api_key=None, limit=limit)

    # Convert QueryResult to dict
    return {
        "success": result.success,
        "source": result.source,
        "total": result.total,
        "results": result.results,
        "query_params": result.query_params,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
        "metadata": result.metadata
    }


# =============================================================================
# Reddit - Community Discussions
# =============================================================================

@mcp.tool
async def search_reddit(
    research_question: str,
    limit: int = 25,
    param_hints: Optional[Dict] = None
) -> dict:
    """Search Reddit for community discussions, expert commentary, and news reactions.

    Reddit provides access to community discussions organized into topic-specific
    subreddits, including:
    - Intelligence & Security: r/Intelligence, r/natsec, r/NSA, r/CIA, r/FBI
    - OSINT & Journalism: r/OSINT, r/journalism, r/Whistleblowers, r/Leaks
    - Geopolitics: r/geopolitics, r/UkrainianConflict, r/syriancivilwar
    - General News: r/news, r/worldnews, r/neutralnews

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters including relevant subreddits.

    Args:
        research_question: Natural language query (e.g., "NSA surveillance
            program discussions" or "intelligence community whistleblower reactions")
        limit: Maximum number of results to return (default: 25, max: 100)
        param_hints: Optional parameter hints to override LLM-generated values
            (e.g., {"time_filter": "year"} to expand time range)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "Reddit"
            - total: int (total posts returned)
            - results: list of Reddit posts with metadata
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_reddit(
        ...     research_question="FBI domestic extremism classifications",
        ...     limit=10
        ... )
        {
            "success": True,
            "source": "Reddit",
            "total": 10,
            "results": [
                {
                    "title": "New FBI memo on domestic extremism leaked",
                    "url": "https://reddit.com/r/Intelligence/...",
                    "date": "2024-03-15",
                    "description": "The FBI has updated its classifications...",
                    "subreddit": "Intelligence",
                    "author": "throwaway123",
                    "score": 342,
                    "num_comments": 89,
                    ...
                }
            ],
            "query_params": {
                "query": "FBI AND domestic extremism",
                "subreddits": ["Intelligence", "natsec", "FBI"],
                "sort": "relevance",
                "time_filter": "month"
            },
            "response_time_ms": 2154.32
        }

    Note:
        Requires Reddit API credentials configured in config.yaml.
        Credentials: client_id, client_secret, username, password.
    """
    # Create integration instance
    integration = RedditIntegration()

    # Generate query parameters using LLM (with optional hints)
    query_params = await integration.generate_query(research_question, param_hints=param_hints)

    if query_params is None:
        return {
            "success": False,
            "source": "Reddit",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for Reddit"
        }

    # Execute search (credentials from config)
    result = await integration.execute_search(query_params, api_key=None, limit=limit)

    # Convert QueryResult to dict
    return {
        "success": result.success,
        "source": result.source,
        "total": result.total,
        "results": result.results,
        "query_params": result.query_params,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
        "metadata": result.metadata
    }


# =============================================================================
# Server Execution
# =============================================================================

if __name__ == "__main__":
    # Run MCP server with STDIO transport (for Claude Desktop, Cursor, etc.)
    mcp.run()

    # Alternative: HTTP transport (for remote clients)
    # mcp.run(transport="http", host="0.0.0.0", port=8001)
