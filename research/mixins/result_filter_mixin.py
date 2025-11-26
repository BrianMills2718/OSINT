#!/usr/bin/env python3
"""
Result filtering mixin for deep research.

Provides result validation and filtering capabilities.
Delegates to ResultFilter service for actual implementation.

This mixin is a thin wrapper that:
- Maintains backward compatibility with existing code
- Wires the service's progress callback to self._emit_progress
- Can be used by classes that inherit from SimpleDeepResearch
"""

import logging
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING

from research.services import ResultFilter

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class ResultFilterMixin:
    """
    Mixin providing result validation and filtering.

    Delegates to ResultFilter service for implementation.

    Requires host class to have:
        - self._emit_progress(event_type: str, message: str, task_id=None, data=None): method
    """

    _result_filter_instance: Optional[ResultFilter] = None

    @property
    def _result_filter(self: "SimpleDeepResearch") -> ResultFilter:
        """Lazily create ResultFilter service with progress callback wired up."""
        if self._result_filter_instance is None:
            # Wire the service's progress callback to emit_progress
            def progress_callback(event_type: str, message: str, data: Optional[Dict] = None):
                self._emit_progress(event_type, message, data=data)

            self._result_filter_instance = ResultFilter(progress_callback=progress_callback)
        return self._result_filter_instance

    async def _validate_result_relevance(
        self: "SimpleDeepResearch",
        task_query: str,
        research_question: str,
        sample_results: List[Dict],
        source_execution_status: Optional[Dict[str, Dict]] = None
    ) -> Tuple[bool, str, List[int], bool, str, Dict]:
        """
        Validate result relevance, filter to best results, and decide if more searching needed.

        Delegates to ResultFilter service.

        Args:
            task_query: Query that generated these results
            research_question: Original research question
            sample_results: All results to evaluate

        Returns:
            Tuple of (should_accept, reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown)
        """
        return await self._result_filter.validate_relevance(
            task_query=task_query,
            research_question=research_question,
            sample_results=sample_results,
            source_execution_status=source_execution_status
        )

    def _validate_result_dates(self: "SimpleDeepResearch", results: List[Dict]) -> List[Dict]:
        """
        Validate and filter results with suspicious dates.

        Delegates to ResultFilter service.

        Args:
            results: List of result dicts

        Returns:
            Filtered list with valid dates, suspicious results flagged
        """
        return self._result_filter.validate_dates(results)
