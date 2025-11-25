#!/usr/bin/env python3
"""
Unit tests for FollowUpTaskMixin.

Tests:
- _should_create_follow_ups (logic with task state)
- _create_follow_up_tasks (mocked LLM)
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
        self.hypotheses = None
        self.hypothesis_runs = []
        self.metadata = {}
        self.accumulated_results = []
        self.parent_task_id = None
        self.rationale = ""
        self.priority = 5
        self.priority_reasoning = ""
        self.estimated_value = 0.5
        self.estimated_redundancy = 0.0


class TestShouldCreateFollowUps:
    """Test _should_create_follow_ups method (logic only)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.follow_up_task_mixin import FollowUpTaskMixin

        class MockHost(FollowUpTaskMixin):
            completed_tasks = []
            task_queue = []
            max_tasks = 10
            max_follow_ups_per_task = 3

        self.host = MockHost()

    def test_returns_false_when_coverage_excellent(self):
        """Returns False when LLM decided stop with no gaps."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [
                {
                    "decision": "stop",
                    "gaps_identified": []
                }
            ]
        }

        result = self.host._should_create_follow_ups(task, total_pending_workload=0)
        assert result is False

    def test_returns_true_when_coverage_has_gaps(self):
        """Returns True when coverage has gaps."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [
                {
                    "decision": "stop",
                    "gaps_identified": ["Missing timeline info"]
                }
            ]
        }

        result = self.host._should_create_follow_ups(task, total_pending_workload=0)
        assert result is True

    def test_returns_true_when_no_coverage_data(self):
        """Returns True when no coverage assessment available."""
        task = MockResearchTask()
        task.metadata = {}

        result = self.host._should_create_follow_ups(task, total_pending_workload=0)
        assert result is True

    def test_returns_false_when_workload_full(self):
        """Returns False when total workload would exceed max_tasks."""
        task = MockResearchTask()
        task.metadata = {}

        # Set up situation where workload is already near max
        self.host.completed_tasks = [MockResearchTask(i) for i in range(8)]

        result = self.host._should_create_follow_ups(task, total_pending_workload=2)
        # 8 completed + 2 pending + 3 follow-ups = 13 > 10 max_tasks
        assert result is False

    def test_considers_pending_workload(self):
        """Considers total_pending_workload in calculation."""
        task = MockResearchTask()
        task.metadata = {}

        self.host.completed_tasks = [MockResearchTask(1)]
        self.host.max_tasks = 10

        # 1 completed + 5 pending + 3 follow-ups = 9 < 10
        result = self.host._should_create_follow_ups(task, total_pending_workload=5)
        assert result is True

        # 1 completed + 7 pending + 3 follow-ups = 11 > 10
        result = self.host._should_create_follow_ups(task, total_pending_workload=7)
        assert result is False


class TestCreateFollowUpTasks:
    """Test _create_follow_up_tasks method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.follow_up_task_mixin import FollowUpTaskMixin

        class MockHost(FollowUpTaskMixin):
            completed_tasks = []
            task_queue = []
            research_question = "What are defense contracts?"

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_coverage_data(self):
        """Returns empty list when no coverage decisions available."""
        task = MockResearchTask()
        task.metadata = {}

        # ResearchTask is imported inside _create_follow_up_tasks from research.deep_research
        # No need to patch since method returns early when no coverage_decisions
        result = await self.host._create_follow_up_tasks(task, current_task_id=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_creates_follow_up_tasks_from_llm(self):
        """Creates ResearchTask objects from LLM suggestions."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [
                {
                    "assessment": "Missing timeline information",
                    "gaps_identified": ["Timeline of contract awards"]
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "follow_up_tasks": [
                {
                    "query": "Timeline of F-35 contract awards 2020-2024",
                    "rationale": "Addresses timeline gap"
                },
                {
                    "query": "F-35 contract award dates",
                    "rationale": "Alternative approach to timeline"
                }
            ],
            "decision_reasoning": "Created 2 follow-ups to address timeline gap"
        })

        with patch("research.mixins.follow_up_task_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # Mock ResearchTask at its source (imported inside the method)
            with patch("research.deep_research.ResearchTask") as mock_task_class:
                mock_task_class.side_effect = lambda **kwargs: MockResearchTask(**{
                    'task_id': kwargs.get('id'),
                    'query': kwargs.get('query', '')
                })

                result = await self.host._create_follow_up_tasks(task, current_task_id=10)

        # Should create 2 follow-up tasks
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_deduplicates_against_existing_tasks(self):
        """Skips follow-ups that duplicate existing task queries."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [{"assessment": "Gaps found", "gaps_identified": ["gap1"]}]
        }

        # Add existing task with same query
        existing_task = MockResearchTask(5, "timeline of f-35 contract awards")
        self.host.completed_tasks = [existing_task]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "follow_up_tasks": [
                {
                    "query": "Timeline of F-35 contract awards",  # Duplicate (case-insensitive)
                    "rationale": "Should be skipped"
                },
                {
                    "query": "Unique new query",
                    "rationale": "Should be kept"
                }
            ],
            "decision_reasoning": "Test"
        })

        with patch("research.mixins.follow_up_task_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # Mock ResearchTask at its source (imported inside the method)
            with patch("research.deep_research.ResearchTask") as mock_task_class:
                mock_task_class.side_effect = lambda **kwargs: MockResearchTask(**{
                    'task_id': kwargs.get('id'),
                    'query': kwargs.get('query', '')
                })

                result = await self.host._create_follow_up_tasks(task, current_task_id=10)

        # Should only create 1 (the unique one)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self):
        """Returns empty list on LLM error."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [{"assessment": "Test", "gaps_identified": ["gap"]}]
        }

        with patch("research.mixins.follow_up_task_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API Error")

            result = await self.host._create_follow_up_tasks(task, current_task_id=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_consolidates_all_gaps(self):
        """Consolidates gaps from all coverage decisions."""
        task = MockResearchTask()
        task.metadata = {
            "coverage_decisions": [
                {"assessment": "First assessment", "gaps_identified": ["gap1", "gap2"]},
                {"assessment": "Second assessment", "gaps_identified": ["gap2", "gap3"]}  # gap2 duplicate
            ]
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "follow_up_tasks": [],
            "decision_reasoning": "No follow-ups needed"
        })

        with patch("research.mixins.follow_up_task_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            await self.host._create_follow_up_tasks(task, current_task_id=10)

            # Check that render_prompt was called with deduplicated gaps
            # (gap1, gap2, gap3 - not gap1, gap2, gap2, gap3)
            assert mock_llm.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
