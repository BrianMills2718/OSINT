#!/usr/bin/env python3
"""
Generic search fallback helper for database integrations.

Provides reusable fallback execution pattern: try search strategies
in order of reliability until one succeeds.

This is NOT integration-specific - ANY integration can use it.
"""

from typing import Dict, Optional, Callable, List, Any, TYPE_CHECKING
import logging
from core.database_integration_base import QueryResult

if TYPE_CHECKING:
    from integrations.source_metadata import SourceMetadata

# Set up logger for this module
logger = logging.getLogger(__name__)


async def execute_with_fallback(
    source_name: str,
    query_params: Dict,
    search_methods: Dict[str, Callable],
    metadata: 'SourceMetadata'
) -> QueryResult:
    """
    Generic fallback executor - tries search strategies in declared order.

    Pattern: Declare strategies in metadata (data layer),
             Execute generically here (code layer).

    This makes fallback a standard capability, not a per-integration carve-out.

    Args:
        source_name: Source name (for logging/errors)
        query_params: Query params from generate_query() containing strategy parameters
        search_methods: Dict mapping strategy names to async search functions
                       e.g., {'cik': self._search_by_cik, 'ticker': self._search_by_ticker}
        metadata: SourceMetadata with search_strategies configuration

    Returns:
        QueryResult from first successful strategy, or error if all fail

    Example metadata configuration:
        'SEC_EDGAR': SourceMetadata(
            characteristics={
                'search_strategies': [
                    {'method': 'cik', 'reliability': 'high', 'param': 'cik'},
                    {'method': 'ticker', 'reliability': 'high', 'param': 'ticker'},
                    {'method': 'name_exact', 'reliability': 'medium', 'param': 'company_name'},
                ],
                'supports_fallback': True
            }
        )

    Example usage in integration:
        search_methods = {
            'cik': self._search_by_cik,
            'ticker': self._search_by_ticker,
            'name_exact': self._search_by_name_exact,
        }
        return await execute_with_fallback(
            "SEC EDGAR", query_params, search_methods, metadata
        )
    """
    # Validation: metadata must be provided
    if not metadata:
        raise ValueError(
            f"{source_name}: No metadata provided. "
            f"Cannot use fallback without metadata configuration."
        )

    # Get declared strategies from metadata
    strategies = metadata.characteristics.get('search_strategies', [])

    if not strategies:
        raise ValueError(
            f"{source_name}: No search_strategies declared in metadata. "
            f"Cannot use fallback without strategy configuration."
        )

    # Track attempts for error reporting
    attempts = []

    # Try strategies in declared order (metadata controls priority)
    for strategy in strategies:
        method_name = strategy['method']
        param_name = strategy['param']
        reliability = strategy.get('reliability', 'unknown')

        # Skip if query params don't include this strategy's parameter
        if param_name not in query_params or not query_params[param_name]:
            attempts.append({
                'method': method_name,
                'skipped': True,
                'reason': f'No {param_name} in query_params'
            })
            continue

        # Skip if search method not provided by integration
        if method_name not in search_methods:
            attempts.append({
                'method': method_name,
                'skipped': True,
                'reason': f'Search method {method_name} not implemented'
            })
            continue

        # Execute this strategy
        search_func = search_methods[method_name]
        param_value = query_params[param_name]

        # Validate search_func is callable
        if not callable(search_func):
            attempts.append({
                'method': method_name,
                'skipped': True,
                'reason': f'Search method {method_name} is not callable'
            })
            continue

        try:
            result = await search_func(param_value)

            # Success criteria: valid result with data
            if result.success and result.total > 0:
                # Add metadata about which strategy succeeded
                if not result.metadata:
                    result.metadata = {}
                result.metadata['fallback_strategy_used'] = method_name
                result.metadata['fallback_strategy_reliability'] = reliability
                result.metadata['fallback_attempts'] = len(attempts) + 1

                return result
            else:
                # Strategy executed but returned no results
                attempts.append({
                    'method': method_name,
                    'param': param_name,
                    'param_value': param_value,
                    'result': 'no_results',
                    'reliability': reliability
                })

        except Exception as e:
            # Strategy failed with error - log and continue to next strategy
            logger.warning(f"Search fallback strategy '{method_name}' failed for {source_name}: {e}", exc_info=True)
            attempts.append({
                'method': method_name,
                'param': param_name,
                'param_value': param_value,
                'error': str(e),
                'reliability': reliability
            })
            continue

    # All strategies failed - return error with attempt details
    return QueryResult(
        success=False,
        source=source_name,
        total=0,
        results=[],
        query_params=query_params,
        error=f"All {len(strategies)} search strategies failed",
        metadata={'fallback_attempts': attempts}
    )
