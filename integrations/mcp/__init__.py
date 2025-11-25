"""
MCP (Model Context Protocol) server wrappers for integrations.

This package provides FastMCP server implementations that wrap
DatabaseIntegration classes as MCP tools for use with AI assistants.

Modules:
    mcp_utils: Shared utilities for MCP wrappers
    government_mcp: Government data sources (SAM, DVIDS, USAJobs, etc.)
    social_mcp: Social media sources (Twitter, Reddit, Discord, etc.)
"""

from integrations.mcp.mcp_utils import execute_mcp_search, query_result_to_dict

__all__ = ["execute_mcp_search", "query_result_to_dict"]
