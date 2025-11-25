#!/usr/bin/env python3
"""
Shared utilities for MCP server wrappers.

Provides a generic wrapper function that handles the common pattern:
1. Get API key from environment
2. Create integration instance
3. Generate query parameters using LLM
4. Check relevance
5. Execute search
6. Convert QueryResult to dict

This eliminates ~50 lines of boilerplate per MCP tool.
"""

import os
from typing import Dict, Optional, Type

from core.database_integration_base import DatabaseIntegration, QueryResult


async def execute_mcp_search(
    integration_class: Type[DatabaseIntegration],
    research_question: str,
    api_key_env_var: str,
    api_key: Optional[str] = None,
    limit: int = 10,
    param_hints: Optional[Dict] = None
) -> dict:
    """
    Generic MCP search wrapper for any DatabaseIntegration.

    This function handles the common pattern used by all MCP tools:
    - API key resolution from environment
    - Integration instantiation
    - LLM-powered query generation with relevance checking
    - Search execution
    - Result conversion to dict

    Args:
        integration_class: The DatabaseIntegration class to instantiate
        research_question: Natural language research query
        api_key_env_var: Environment variable name for API key
        api_key: Optional explicit API key (overrides env var)
        limit: Maximum results to return
        param_hints: Optional parameter hints to override LLM-generated values

    Returns:
        dict: Search results with standard structure:
            - success: bool
            - source: str
            - total: int
            - results: list
            - query_params: dict
            - response_time_ms: float
            - error: str (if success=False)
            - metadata: dict (optional)
    """
    # Resolve API key
    if not api_key:
        api_key = os.getenv(api_key_env_var)

    # Create integration instance
    integration = integration_class()
    source_name = integration.metadata.name

    # Generate query parameters using LLM with rejection reasoning
    try:
        enriched = await integration.generate_query_with_reasoning(research_question)
    except AttributeError:
        # Fallback for integrations without generate_query_with_reasoning
        query_params = await integration.generate_query(research_question)
        if query_params is None:
            return {
                "success": False,
                "source": source_name,
                "total": 0,
                "results": [],
                "error": f"Could not generate query for {source_name}"
            }
        enriched = {"relevant": True, "query_params": query_params}

    # Check if LLM determined not relevant
    if not enriched.get("relevant", False):
        return {
            "success": False,
            "source": source_name,
            "total": 0,
            "results": [],
            "error": f"Research question not relevant for {source_name}: {enriched.get('rejection_reason', 'No reason provided')}",
            "metadata": {
                "rejection_reasoning": enriched.get("rejection_reason"),
                "suggested_reformulation": enriched.get("suggested_reformulation")
            }
        }

    # Extract query params
    query_params = enriched.get("query_params")
    if query_params is None:
        return {
            "success": False,
            "source": source_name,
            "total": 0,
            "results": [],
            "error": "Wrapper returned relevant=True but query_params is None"
        }

    # Apply param hints if provided
    if param_hints:
        query_params.update(param_hints)

    # Execute search
    result = await integration.execute_search(query_params, api_key, limit)

    # Convert QueryResult to dict
    return query_result_to_dict(result)


def query_result_to_dict(result: QueryResult) -> dict:
    """Convert a QueryResult to a dictionary for MCP response."""
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
