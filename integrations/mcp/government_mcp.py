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
No duplication - all configuration, error handling, and API logic comes from
the DatabaseIntegration implementations.

Usage:
    # In-memory (CLI/Streamlit)
    from fastmcp import Client
    async with Client(government_mcp.mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_sam", {...})

    # STDIO (AI assistants like Claude Desktop)
    python -m integrations.mcp.government_mcp

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
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration

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


# =============================================================================
# SAM.gov - Federal Contracting Opportunities
# =============================================================================

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

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters for the SAM.gov API. It then executes the
    search and returns structured results.

    Args:
        research_question: Natural language query (e.g., "cybersecurity contracts
            from Department of Defense")
        api_key: SAM.gov API key (optional, uses SAM_GOV_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 1000)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "SAM.gov"
            - total: int (total matching opportunities)
            - results: list of contracting opportunities
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_sam(
        ...     research_question="cybersecurity contracts from FBI",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "SAM.gov",
            "total": 42,
            "results": [
                {
                    "title": "Cybersecurity Assessment Services",
                    "solicitationNumber": "FBI-24-1234",
                    "type": "Solicitation",
                    "organizationName": "Federal Bureau of Investigation",
                    ...
                }
            ],
            "query_params": {
                "keywords": "cybersecurity",
                "organization": "Federal Bureau of Investigation"
            },
            "response_time_ms": 2341.56
        }
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("SAM_GOV_API_KEY")

    # Create integration instance (reuse existing implementation)
    integration = SAMIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        # LLM determined not relevant
        return {
            "success": False,
            "source": "SAM.gov",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for SAM.gov"
        }

    # Execute search using existing DatabaseIntegration logic
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
# DVIDS - Military Media
# =============================================================================

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

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters for the DVIDS API.

    Args:
        research_question: Natural language query (e.g., "F-35 training exercises")
        api_key: DVIDS API key (optional, uses DVIDS_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "DVIDS"
            - total: int (total matching media items)
            - results: list of media items (photos, videos, news)
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_dvids(
        ...     research_question="Navy ship deployments",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "DVIDS",
            "total": 156,
            "results": [
                {
                    "id": "12345",
                    "title": "USS Lincoln Carrier Strike Group Deploys",
                    "type": "news",
                    "branch": "Navy",
                    "date": "2024-03-15",
                    ...
                }
            ],
            "query_params": {
                "keywords": "Navy OR ship OR deployment",
                "media_types": ["image", "video", "news"],
                "branches": ["Navy"]
            },
            "response_time_ms": 1876.32
        }
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("DVIDS_API_KEY")

    # Create integration instance
    integration = DVIDSIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "DVIDS",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for DVIDS"
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
# USAJobs - Federal Government Jobs
# =============================================================================

@mcp.tool
async def search_usajobs(
    research_question: str,
    api_key: Optional[str] = None,
    limit: int = 10
) -> dict:
    """Search USAJobs for federal government job listings.

    USAJobs is the official employment site for the U.S. federal government,
    listing positions across all federal agencies and departments.

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters for the USAJobs API.

    Args:
        research_question: Natural language query (e.g., "intelligence analyst
            jobs in Washington DC")
        api_key: USAJobs API key (optional, uses USAJOBS_API_KEY env var if not provided)
        limit: Maximum number of results to return (default: 10, max: 500)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "USAJobs"
            - total: int (total matching jobs)
            - results: list of job listings
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_usajobs(
        ...     research_question="cybersecurity analyst jobs at FBI",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "USAJobs",
            "total": 12,
            "results": [
                {
                    "PositionTitle": "Cybersecurity Analyst",
                    "OrganizationName": "Federal Bureau of Investigation",
                    "PositionLocation": [{"LocationName": "Washington, DC"}],
                    "JobGrade": [{"Code": "GS"}],
                    ...
                }
            ],
            "query_params": {
                "keywords": "cybersecurity analyst",
                "organization": "FBI",
                "location": "Washington, DC"
            },
            "response_time_ms": 1543.21
        }
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("USAJOBS_API_KEY")

    # Create integration instance
    integration = USAJobsIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "USAJobs",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for USAJobs"
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
# ClearanceJobs - Security Clearance Jobs
# =============================================================================

@mcp.tool
async def search_clearancejobs(
    research_question: str,
    limit: int = 10
) -> dict:
    """Search ClearanceJobs for security clearance job postings.

    ClearanceJobs.com specializes in job postings requiring TS/SCI, Secret,
    Top Secret, and other government security clearances.

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters. Results are obtained via browser automation
    (Playwright) since the official API is broken.

    Args:
        research_question: Natural language query (e.g., "SIGINT analyst with
            TS/SCI clearance")
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "ClearanceJobs"
            - total: int (total matching jobs)
            - results: list of job listings
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_clearancejobs(
        ...     research_question="penetration tester with TS clearance",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "ClearanceJobs",
            "total": 23,
            "results": [
                {
                    "title": "Senior Penetration Tester",
                    "company": "Defense Contractor Inc.",
                    "location": "Fort Meade, MD",
                    "clearance": "TS/SCI",
                    "posted": "2 days ago",
                    ...
                }
            ],
            "query_params": {
                "keywords": "penetration tester OR ethical hacker"
            },
            "response_time_ms": 5432.10
        }

    Note:
        This integration uses Playwright for browser automation, so it's slower
        than API-based integrations (typically 5-8 seconds). Results require
        Playwright dependencies to be installed.
    """
    # Create integration instance
    integration = ClearanceJobsIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "ClearanceJobs",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for ClearanceJobs"
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
# FBI Vault - FOIA Document Releases
# =============================================================================

@mcp.tool
async def search_fbi_vault(
    research_question: str,
    limit: int = 10
) -> dict:
    """Search FBI Vault for FOIA document releases and investigation files.

    FBI Vault is the FBI's FOIA Library containing documents released under
    the Freedom of Information Act, including investigation files, memos,
    reports, and declassified materials.

    This tool uses an LLM to understand your research question and generate
    appropriate search parameters. Results are obtained via browser automation
    (SeleniumBase UC Mode) to bypass Cloudflare protection.

    Args:
        research_question: Natural language query (e.g., "domestic terrorism
            threat assessments")
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict: Search results with structure:
            - success: bool
            - source: "FBI Vault"
            - total: int (total matching documents)
            - results: list of documents
            - query_params: dict (generated search parameters)
            - response_time_ms: float
            - error: str (if success=False)

    Example:
        >>> await search_fbi_vault(
        ...     research_question="organized crime investigations",
        ...     limit=5
        ... )
        {
            "success": True,
            "source": "FBI Vault",
            "total": 15,
            "results": [
                {
                    "title": "Organized Crime Investigation Files",
                    "url": "https://vault.fbi.gov/organized-crime",
                    "snippet": "Investigation files related to organized crime...",
                    "date": "2022-06-15",
                    "document_type": "Folder",
                    ...
                }
            ],
            "query_params": {
                "query": "organized crime"
            },
            "response_time_ms": 3876.54
        }

    Note:
        This integration uses SeleniumBase UC Mode for Cloudflare bypass, so it's
        slower than API-based integrations (typically 3-5 seconds). Requires
        SeleniumBase and Chrome/Chromium to be installed.
    """
    # Create integration instance
    integration = FBIVaultIntegration()

    # Generate query parameters using LLM
    query_params = await integration.generate_query(research_question)

    if query_params is None:
        return {
            "success": False,
            "source": "FBI Vault",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for FBI Vault"
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
# Server Execution
# =============================================================================

if __name__ == "__main__":
    # Run MCP server with STDIO transport (for Claude Desktop, Cursor, etc.)
    mcp.run()

    # Alternative: HTTP transport (for remote clients)
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
