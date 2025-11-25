#!/usr/bin/env python3
"""
Government Data Sources MCP Server

This MCP server wraps 5 government data source integrations as FastMCP tools:
- SAM.gov: Federal contracting opportunities
- DVIDS: Military media (photos, videos, news)
- USAJobs: Federal government job listings
- ClearanceJobs: Security clearance job postings
- FBI Vault: FOIA document releases

Design: Thin wrapper layer that reuses existing DatabaseIntegration classes.
Uses shared mcp_utils.execute_mcp_search() to eliminate boilerplate.

Usage:
    # In-memory (CLI/Streamlit)
    from fastmcp import Client
    async with Client(government_mcp.mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_sam", {...})

    # STDIO (AI assistants like Claude Desktop)
    python -m integrations.mcp.government_mcp
"""

from typing import Optional
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import DatabaseIntegration classes
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration

# Import shared MCP utilities
from integrations.mcp.mcp_utils import execute_mcp_search

# Create MCP server
mcp = FastMCP(
    name="Government Data Sources",
    instructions="""
    Access to U.S. government data sources for investigative research.

    Available tools:
    - search_sam: Federal contracting opportunities (SAM.gov)
    - search_dvids: Military media - photos, videos, news (DVIDS)
    - search_usajobs: Federal government job listings (USAJobs)
    - search_clearancejobs: Security clearance job postings
    - search_fbi_vault: FBI FOIA document releases

    All tools use LLM-powered query generation to understand natural language
    research questions and generate appropriate search parameters.
    """
)


@mcp.tool
async def search_sam(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search SAM.gov for federal contracting opportunities and solicitations.

    SAM.gov (System for Award Management) is the official U.S. government system
    for finding federal contracting opportunities including solicitations,
    presolicitations, and sources sought notices.

    Args:
        research_question: Natural language query (e.g., "cybersecurity contracts
            from Department of Defense")
        api_key: SAM.gov API key (optional, uses SAM_GOV_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 1000)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        SAMIntegration, research_question, "SAM_GOV_API_KEY", api_key, limit
    )


@mcp.tool
async def search_dvids(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search DVIDS for U.S. military media including photos, videos, and news.

    DVIDS (Defense Visual Information Distribution Service) is the official
    source for U.S. military media including combat footage, training imagery,
    humanitarian operations, and public affairs content.

    Args:
        research_question: Natural language query (e.g., "F-35 training exercises")
        api_key: DVIDS API key (optional, uses DVIDS_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 100)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        DVIDSIntegration, research_question, "DVIDS_API_KEY", api_key, limit
    )


@mcp.tool
async def search_usajobs(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search USAJobs for federal government job listings.

    USAJobs is the official job site of the U.S. Federal Government, listing
    civilian positions across all federal agencies including DoD, intelligence
    community, and law enforcement.

    Args:
        research_question: Natural language query (e.g., "cybersecurity analyst
            positions at NSA")
        api_key: USAJobs API key (optional, uses USAJOBS_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 500)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        USAJobsIntegration, research_question, "USAJOBS_API_KEY", api_key, limit
    )


@mcp.tool
async def search_clearancejobs(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search ClearanceJobs for security clearance job postings.

    ClearanceJobs is the leading job board for positions requiring security
    clearances, covering defense contractors, intelligence agencies, and
    government positions requiring TS/SCI, Secret, or other clearances.

    Args:
        research_question: Natural language query (e.g., "TS/SCI cyber positions
            at defense contractors")
        api_key: Not required (uses web scraping)
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        ClearanceJobsIntegration, research_question, "CLEARANCEJOBS_API_KEY", api_key, limit
    )


@mcp.tool
async def search_fbi_vault(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search FBI Vault for FOIA document releases.

    The FBI Vault contains over 6,700 declassified documents released under
    FOIA, including files on historical figures, organizations, events,
    and government programs.

    Args:
        research_question: Natural language query (e.g., "COINTELPRO documents"
            or "Hoover files on civil rights leaders")
        api_key: Not required (public access)
        limit: Maximum number of results to return (default: 10, max: 100)

    Returns:
        dict: Search results with success, source, total, results, query_params, error
    """
    return await execute_mcp_search(
        FBIVaultIntegration, research_question, "FBI_VAULT_API_KEY", api_key, limit
    )


# Run server when executed directly
if __name__ == "__main__":
    mcp.run()
