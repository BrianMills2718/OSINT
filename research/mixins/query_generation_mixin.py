#!/usr/bin/env python3
"""
Query generation mixin for deep research.

Provides LLM-based query generation for hypothesis execution.
Delegates to QueryGenerator service for actual implementation.

This mixin is a thin wrapper that:
- Maintains backward compatibility with existing code
- Wires the service's execution logger to self.logger
- Can be used by classes that inherit from SimpleDeepResearch
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from research.services import QueryGenerator

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch, ResearchTask

logger = logging.getLogger(__name__)


class QueryGenerationMixin:
    """
    Mixin providing query generation for hypothesis execution.

    Delegates to QueryGenerator service for implementation.

    Requires host class to have:
        - self.logger: ExecutionLogger instance (optional)
    """

    _query_generator_instance: Optional[QueryGenerator] = None

    @property
    def _query_generator(self: "SimpleDeepResearch") -> QueryGenerator:
        """Lazily create QueryGenerator service with execution logger wired up."""
        if self._query_generator_instance is None:
            # Wire the service's execution logger to self.logger
            self._query_generator_instance = QueryGenerator(
                execution_logger=getattr(self, 'logger', None)
            )
        return self._query_generator_instance

    async def _generate_hypothesis_query(
        self: "SimpleDeepResearch",
        hypothesis: Dict,
        source_tool_name: str,
        research_question: str,
        task_query: str,
        task: 'ResearchTask'
    ) -> Optional[str]:
        """
        Generate source-specific query for hypothesis execution (Phase 3B).

        Delegates to QueryGenerator service.

        Args:
            hypothesis: Hypothesis dict with statement, confidence, search_strategy
            source_tool_name: Integration ID (e.g., "usajobs")
            research_question: Original research question
            task_query: Task query this hypothesis belongs to
            task: ResearchTask object

        Returns:
            Query string optimized for this source, or None on error
        """
        return await self._query_generator.generate_hypothesis_query(
            hypothesis=hypothesis,
            source_tool_name=source_tool_name,
            research_question=research_question,
            task_query=task_query,
            task_id=task.id,
            hypothesis_id=hypothesis.get('id', 0)
        )

    async def _generate_initial_query(
        self: "SimpleDeepResearch",
        hypothesis: Dict[str, Any],
        source_name: str,
        source_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate first query from hypothesis (no query history yet).

        Delegates to QueryGenerator service.

        Args:
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            source_metadata: Metadata about the source

        Returns:
            {"query": str, "reasoning": str}
        """
        return await self._query_generator.generate_initial_query(
            hypothesis=hypothesis,
            source_name=source_name,
            source_metadata=source_metadata
        )

    async def _generate_next_query_or_stop(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        hypothesis: Dict[str, Any],
        source_name: str,
        query_history: List[Dict],
        source_metadata: Dict,
        total_results_accepted: int
    ) -> Dict[str, Any]:
        """
        LLM decides: continue with next query or stop (saturated).

        Delegates to QueryGenerator service.

        Args:
            task: Research task (unused, kept for backward compatibility)
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            query_history: List of previous query attempts
            source_metadata: Metadata about the source
            total_results_accepted: Total results accepted so far

        Returns:
            Dict with decision, reasoning, confidence, strategies_tried, etc.
        """
        return await self._query_generator.generate_next_query_or_stop(
            hypothesis=hypothesis,
            source_name=source_name,
            query_history=query_history,
            source_metadata=source_metadata,
            total_results_accepted=total_results_accepted
        )
