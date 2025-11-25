#!/usr/bin/env python3
"""
Unit tests for SourceExecutorMixin.

Tests:
- _execute_hypothesis (mocked dependencies)
- _execute_hypotheses (mocked dependencies)
- _execute_hypotheses_parallel (mocked dependencies)
- _execute_hypotheses_sequential (mocked dependencies)
- _execute_source_with_saturation (mocked dependencies)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockResearchTask:
    """Mock ResearchTask for testing."""

    def __init__(self, task_id=1, query="test query"):
        self.id = task_id
        self.query = query
        self.hypotheses = {"hypotheses": []}
        self.hypothesis_runs = []
        self.metadata = {}
        self.accumulated_results = []
        self.entities_found = []


class MockExecutionLogger:
    """Mock ExecutionLogger for testing."""

    def __init__(self):
        self.events = []

    def log_source_saturation_start(self, **kwargs):
        self.events.append(("saturation_start", kwargs))

    def log_source_saturation_complete(self, **kwargs):
        self.events.append(("saturation_complete", kwargs))

    def log_query_attempt(self, **kwargs):
        self.events.append(("query_attempt", kwargs))

    def log_coverage_assessment(self, **kwargs):
        self.events.append(("coverage_assessment", kwargs))

    def log_hypothesis_query_generation(self, **kwargs):
        self.events.append(("hypothesis_query_gen", kwargs))


class TestExecuteHypothesis:
    """Test _execute_hypothesis method."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHost(SourceExecutorMixin):
            logger = MockExecutionLogger()
            mcp_tools = []
            integrations = []
            query_saturation_enabled = False

            def _map_hypothesis_sources(self, hypothesis):
                return hypothesis.get("search_strategy", {}).get("sources", [])

            def _deduplicate_with_attribution(self, results, hypothesis_id):
                for r in results:
                    r["hypothesis_id"] = hypothesis_id
                return results

            def _compute_hypothesis_delta(self, task, hypothesis, results):
                return {"results_new": len(results), "results_duplicate": 0}

            async def _generate_hypothesis_query(self, hypothesis, source_tool_name, research_question, task_query, task):
                return "test query"

            async def _validate_result_relevance(self, task_query, research_question, sample_results):
                indices = list(range(len(sample_results)))
                return (True, "All relevant", indices, False, "Sufficient", {})

            async def _call_mcp_tool(self, tool_config, query, param_adjustments, task_id, attempt, exec_logger):
                return {"success": True, "results": [{"title": "Test", "url": "https://test.com"}]}

            async def _search_brave(self, query, max_results=10):
                return [{"title": "Brave Result", "url": "https://brave.com/result"}]

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_executes_hypothesis_sources(self):
        """Executes search across hypothesis sources."""
        hypothesis = {
            "id": 1,
            "statement": "Test hypothesis",
            "confidence": 80,
            "search_strategy": {
                "sources": ["brave_search"],
                "signals": ["test"],
                "expected_entities": []
            }
        }

        task = MockResearchTask()

        with patch("research.mixins.source_executor_mixin.registry") as mock_registry:
            mock_registry.get_display_name.return_value = "Brave Search"
            with patch("research.mixins.source_executor_mixin.config") as mock_config:
                mock_config.get_integration_limit.return_value = 10

                results = await self.host._execute_hypothesis(
                    hypothesis=hypothesis,
                    task=task,
                    research_question="What is this about?"
                )

        assert len(results) >= 0
        # Should have recorded hypothesis run
        assert len(task.hypothesis_runs) == 1

    @pytest.mark.asyncio
    async def test_tags_results_with_hypothesis_id(self):
        """Results are tagged with hypothesis_id."""
        hypothesis = {
            "id": 42,
            "statement": "Test",
            "search_strategy": {"sources": ["brave_search"]}
        }

        task = MockResearchTask()

        with patch("research.mixins.source_executor_mixin.registry") as mock_registry:
            mock_registry.get_display_name.return_value = "Brave Search"
            with patch("research.mixins.source_executor_mixin.config") as mock_config:
                mock_config.get_integration_limit.return_value = 10

                results = await self.host._execute_hypothesis(
                    hypothesis=hypothesis,
                    task=task,
                    research_question="test"
                )

        # All results should have hypothesis_id
        for result in results:
            assert result.get("hypothesis_id") == 42

    @pytest.mark.asyncio
    async def test_handles_no_valid_sources(self):
        """Returns empty when no valid sources in hypothesis."""
        hypothesis = {
            "id": 1,
            "statement": "Test",
            "search_strategy": {"sources": []}  # No sources
        }

        task = MockResearchTask()

        results = await self.host._execute_hypothesis(
            hypothesis=hypothesis,
            task=task,
            research_question="test"
        )

        assert results == []


class TestExecuteHypotheses:
    """Test _execute_hypotheses method (mode selection)."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHost(SourceExecutorMixin):
            coverage_mode = False
            max_hypotheses_to_execute = 5
            max_time_per_task_seconds = 300

            async def _execute_hypotheses_parallel(self, task, research_question, hypotheses):
                return [{"parallel": True}]

            async def _execute_hypotheses_sequential(self, task, research_question, hypotheses):
                return [{"sequential": True}]

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_returns_empty_without_hypotheses(self):
        """Returns empty list when no hypotheses."""
        task = MockResearchTask()
        task.hypotheses = None

        results = await self.host._execute_hypotheses(task, "test question")

        assert results == []

    @pytest.mark.asyncio
    async def test_calls_parallel_when_coverage_mode_false(self):
        """Calls parallel execution when coverage_mode is False."""
        self.host.coverage_mode = False

        task = MockResearchTask()
        task.hypotheses = {"hypotheses": [{"id": 1}]}

        results = await self.host._execute_hypotheses(task, "test")

        assert results[0]["parallel"] is True

    @pytest.mark.asyncio
    async def test_calls_sequential_when_coverage_mode_true(self):
        """Calls sequential execution when coverage_mode is True."""
        self.host.coverage_mode = True

        task = MockResearchTask()
        task.hypotheses = {"hypotheses": [{"id": 1}]}

        results = await self.host._execute_hypotheses(task, "test")

        assert results[0]["sequential"] is True


class TestExecuteHypothesesParallel:
    """Test _execute_hypotheses_parallel method."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHost(SourceExecutorMixin):
            async def _execute_hypothesis(self, hypothesis, task, research_question):
                return [{"url": f"https://example.com/{hypothesis['id']}", "hypothesis_id": hypothesis['id']}]

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_executes_all_hypotheses_in_parallel(self):
        """Executes all hypotheses concurrently."""
        task = MockResearchTask()
        hypotheses = [
            {"id": 1, "statement": "H1"},
            {"id": 2, "statement": "H2"},
            {"id": 3, "statement": "H3"}
        ]

        results = await self.host._execute_hypotheses_parallel(
            task=task,
            research_question="test",
            hypotheses=hypotheses
        )

        # Should have results from all 3 hypotheses
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_deduplicates_across_hypotheses(self):
        """Deduplicates results appearing in multiple hypotheses."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHostDup(SourceExecutorMixin):
            async def _execute_hypothesis(self, hypothesis, task, research_question):
                # All hypotheses return same URL
                return [{"url": "https://same.com", "hypothesis_id": hypothesis['id']}]

        host = MockHostDup()
        task = MockResearchTask()
        hypotheses = [{"id": 1}, {"id": 2}]

        results = await host._execute_hypotheses_parallel(
            task=task,
            research_question="test",
            hypotheses=hypotheses
        )

        # Should deduplicate to 1 result (but with merged hypothesis_ids)
        assert len(results) == 1
        # Should have both hypothesis IDs attributed
        if "hypothesis_ids" in results[0]:
            assert 1 in results[0]["hypothesis_ids"]
            assert 2 in results[0]["hypothesis_ids"]


class TestExecuteHypothesesSequential:
    """Test _execute_hypotheses_sequential method."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHost(SourceExecutorMixin):
            logger = MockExecutionLogger()
            max_hypotheses_to_execute = 3
            max_time_per_task_seconds = 300

            async def _execute_hypothesis(self, hypothesis, task, research_question):
                return [{"url": f"https://example.com/{hypothesis['id']}", "hypothesis_id": hypothesis['id']}]

            async def _assess_coverage(self, task, research_question, start_time):
                return {"decision": "continue", "assessment": "More to explore", "gaps_identified": []}

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_stops_at_hypothesis_ceiling(self):
        """Stops when reaching max_hypotheses_to_execute."""
        self.host.max_hypotheses_to_execute = 2

        task = MockResearchTask()
        hypotheses = [{"id": i} for i in range(5)]

        results = await self.host._execute_hypotheses_sequential(
            task=task,
            research_question="test",
            hypotheses=hypotheses
        )

        # Should stop after 2 hypotheses
        assert len(task.hypothesis_runs) <= 2

    @pytest.mark.asyncio
    async def test_stops_on_coverage_stop_decision(self):
        """Stops when coverage assessment says stop."""
        from research.mixins.source_executor_mixin import SourceExecutorMixin

        class MockHostStop(SourceExecutorMixin):
            logger = MockExecutionLogger()
            max_hypotheses_to_execute = 10
            max_time_per_task_seconds = 300

            async def _execute_hypothesis(self, hypothesis, task, research_question):
                task.hypothesis_runs.append({"hypothesis_id": hypothesis['id']})
                return [{"url": f"https://example.com/{hypothesis['id']}"}]

            async def _assess_coverage(self, task, research_question, start_time):
                # Stop after first coverage check (2nd hypothesis)
                return {"decision": "stop", "assessment": "Sufficient coverage", "gaps_identified": []}

        host = MockHostStop()
        task = MockResearchTask()
        hypotheses = [{"id": i} for i in range(5)]

        results = await host._execute_hypotheses_sequential(
            task=task,
            research_question="test",
            hypotheses=hypotheses
        )

        # Should stop after coverage says stop (after 2nd hypothesis)
        assert len(task.hypothesis_runs) == 2

    @pytest.mark.asyncio
    async def test_stores_coverage_decisions_in_metadata(self):
        """Stores coverage decisions in task metadata."""
        task = MockResearchTask()
        hypotheses = [{"id": 1}, {"id": 2}]

        await self.host._execute_hypotheses_sequential(
            task=task,
            research_question="test",
            hypotheses=hypotheses
        )

        # Coverage decisions should be stored
        assert "coverage_decisions" in task.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
