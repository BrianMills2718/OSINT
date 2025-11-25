#!/usr/bin/env python3
"""
Social Media & Web Search MCP Server

This MCP server wraps 4 social media and web search integrations as FastMCP tools:
- Twitter: Social media search via RapidAPI
- Brave Search: Web search for investigative journalism and analysis
- Discord: Community discussions from OSINT servers (local export search)
- Reddit: Reddit search for discussions and news

Design: Thin wrapper layer that reuses existing DatabaseIntegration classes.
Uses shared mcp_utils.execute_mcp_search() to eliminate boilerplate.

Usage:
    # In-memory (CLI/Streamlit)
    from fastmcp import Client
    async with Client(social_mcp.mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_twitter", {...})

    # STDIO (AI assistants like Claude Desktop)
    python -m integrations.mcp.social_mcp
"""

from typing import Dict, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import DatabaseIntegration classes
from integrations.social.twitter_integration import TwitterIntegration
from integrations.social.brave_search_integration import BraveSearchIntegration
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.reddit_integration import RedditIntegration

# Import shared MCP utilities
from integrations.mcp.mcp_utils import execute_mcp_search

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


@mcp.tool
async def search_twitter(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 20,
    param_hints: Optional[Dict] = None
) -> dict:
    """Search Twitter for tweets and social media discussions.

    Twitter provides real-time social media posts and public discussions,
    useful for breaking news, public discourse, whistleblower revelations,
    and expert commentary.

    Args:
        research_question: Natural language query (e.g., "JTTF counterterrorism
            operations" or "NSA whistleblower revelations")
        api_key: RapidAPI key (optional, uses RAPIDAPI_KEY env var if not provided)
        limit: Maximum number of results to return (default: 20, max: 100)
        param_hints: Optional parameter hints to override LLM-generated values
            (e.g., {"search_type": "Top", "max_pages": 2})

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        TwitterIntegration, research_question, "RAPIDAPI_KEY", api_key, limit, param_hints
    )


@mcp.tool
async def search_brave(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 20
) -> dict:
    """Search the web using Brave Search for investigative journalism sources.

    Brave Search provides access to web content including news articles,
    blog posts, leaked documents, investigative journalism, and analysis
    that may not be in specialized databases.

    Args:
        research_question: Natural language query (e.g., "Panama Papers offshore
            shell companies" or "NSO Group Pegasus spyware investigations")
        api_key: Brave API key (optional, uses BRAVE_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        BraveSearchIntegration, research_question, "BRAVE_API_KEY", api_key, limit
    )


@mcp.tool
async def search_discord(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 20
) -> dict:
    """Search Discord exports for OSINT community discussions.

    Searches local exports from Discord OSINT communities including
    Bellingcat, Project OWL, and other investigative journalism servers.
    Contains expert discussions, methodology sharing, and breaking analysis.

    Args:
        research_question: Natural language query (e.g., "satellite imagery
            analysis techniques" or "Russian military unit identification")
        api_key: Not required (searches local exports)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        DiscordIntegration, research_question, "DISCORD_API_KEY", api_key, limit
    )


@mcp.tool
async def search_reddit(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 20
) -> dict:
    """Search Reddit for community discussions and expert commentary.

    Reddit provides access to specialized subreddits covering defense,
    intelligence, cybersecurity, and investigative topics with expert
    commentary and insider perspectives.

    Args:
        research_question: Natural language query (e.g., "defense contractor
            insider perspectives" or "clearance processing times")
        api_key: Not required (uses public Reddit API)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        RedditIntegration, research_question, "REDDIT_API_KEY", api_key, limit
    )


# Run server when executed directly
if __name__ == "__main__":
    mcp.run()
