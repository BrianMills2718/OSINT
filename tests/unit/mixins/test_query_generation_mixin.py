#!/usr/bin/env python3
"""
Unit tests for QueryGenerationMixin.

Tests:
- _generate_hypothesis_query (mocked LLM)
- _generate_initial_query (mocked LLM)
- _generate_next_query_or_stop (mocked LLM)
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


class MockExecutionLogger:
    """Mock ExecutionLogger for testing."""

    def __init__(self):
        self.logged_events = []

    def log_hypothesis_query_generation(self, **kwargs):
        self.logged_events.append(("hypothesis_query_generation", kwargs))


class TestGenerateHypothesisQuery:
    """Test _generate_hypothesis_query method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.query_generation_mixin import QueryGenerationMixin

        class MockHost(QueryGenerationMixin):
            logger = MockExecutionLogger()

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_generates_source_specific_query(self):
        """Generates optimized query for specific source."""
        hypothesis = {
            "id": 1,
            "statement": "F-35 contracts are awarded to Lockheed Martin",
            "confidence": 85,
            "search_strategy": {
                "sources": ["SAM.gov", "USASpending"],
                "signals": ["Lockheed", "F-35", "contract"],
                "expected_entities": ["Lockheed Martin"]
            }
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "Lockheed Martin F-35 contract award",
            "reasoning": "Combines prime contractor name with program and action type"
        })

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            with patch("research.mixins.query_generation_mixin.registry") as mock_registry:
                mock_registry.get_display_name.return_value = "SAM.gov"
                mock_llm.return_value = mock_response

                query = await self.host._generate_hypothesis_query(
                    hypothesis=hypothesis,
                    source_tool_name="sam",
                    research_question="What are F-35 contracts?",
                    task_query="F-35 contracts",
                    task=MockResearchTask()
                )

        assert query == "Lockheed Martin F-35 contract award"

    @pytest.mark.asyncio
    async def test_logs_query_generation(self):
        """Logs query generation to execution logger."""
        hypothesis = {
            "id": 1,
            "statement": "Test hypothesis",
            "confidence": 80,
            "search_strategy": {"sources": [], "signals": [], "expected_entities": []}
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "test query",
            "reasoning": "test reasoning"
        })

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            with patch("research.mixins.query_generation_mixin.registry") as mock_registry:
                mock_registry.get_display_name.return_value = "Test Source"
                mock_llm.return_value = mock_response

                await self.host._generate_hypothesis_query(
                    hypothesis=hypothesis,
                    source_tool_name="test",
                    research_question="test",
                    task_query="test",
                    task=MockResearchTask()
                )

        # Check logger was called
        assert len(self.host.logger.logged_events) == 1
        assert self.host.logger.logged_events[0][0] == "hypothesis_query_generation"

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        """Returns None on LLM error."""
        hypothesis = {
            "id": 1,
            "statement": "Test",
            "confidence": 80,
            "search_strategy": {"sources": [], "signals": [], "expected_entities": []}
        }

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            with patch("research.mixins.query_generation_mixin.registry") as mock_registry:
                mock_registry.get_display_name.return_value = "Test"
                mock_llm.side_effect = Exception("LLM Error")

                result = await self.host._generate_hypothesis_query(
                    hypothesis=hypothesis,
                    source_tool_name="test",
                    research_question="test",
                    task_query="test",
                    task=MockResearchTask()
                )

        assert result is None


class TestGenerateInitialQuery:
    """Test _generate_initial_query method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.query_generation_mixin import QueryGenerationMixin

        class MockHost(QueryGenerationMixin):
            pass

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_generates_first_query_from_hypothesis(self):
        """Generates initial query from hypothesis without history."""
        hypothesis = {
            "statement": "Defense contractors receive large awards",
            "search_strategy": {"sources": ["SAM.gov"]},
            "information_gaps": ["Award amounts", "Timeline"]
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "defense contractor contract awards",
            "reasoning": "Broad initial query to establish baseline"
        })

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_initial_query(
                hypothesis=hypothesis,
                source_name="SAM.gov",
                source_metadata={"description": "Federal contracts database"}
            )

        assert result["query"] == "defense contractor contract awards"
        assert "reasoning" in result


class TestGenerateNextQueryOrStop:
    """Test _generate_next_query_or_stop method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.query_generation_mixin import QueryGenerationMixin

        class MockHost(QueryGenerationMixin):
            pass

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_returns_continue_with_next_query(self):
        """Returns CONTINUE decision with next query suggestion."""
        hypothesis = {
            "statement": "Test hypothesis",
            "information_gaps": ["Timeline", "Budget"]
        }
        query_history = [
            {"query": "first query", "results_total": 10, "results_accepted": 5, "effectiveness": 0.5}
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "CONTINUE",
            "reasoning": "More relevant results likely available",
            "confidence": 75,
            "existence_confidence": 80,
            "strategies_tried": ["broad search"],
            "next_query_suggestion": "timeline contract awards 2024",
            "next_query_reasoning": "Focus on timeline gap",
            "expected_value": "high",
            "remaining_gaps": ["Budget"]
        })

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_next_query_or_stop(
                task=MockResearchTask(),
                hypothesis=hypothesis,
                source_name="SAM.gov",
                query_history=query_history,
                source_metadata={},
                total_results_accepted=5
            )

        assert result["decision"] == "CONTINUE"
        assert result["next_query_suggestion"] == "timeline contract awards 2024"
        assert "strategies_tried" in result

    @pytest.mark.asyncio
    async def test_returns_saturated_when_exhausted(self):
        """Returns SATURATED decision when source exhausted."""
        hypothesis = {
            "statement": "Test hypothesis",
            "information_gaps": []
        }
        query_history = [
            {"query": "query1", "results_total": 10, "results_accepted": 8, "effectiveness": 0.8},
            {"query": "query2", "results_total": 5, "results_accepted": 1, "effectiveness": 0.2},
            {"query": "query3", "results_total": 2, "results_accepted": 0, "effectiveness": 0.0}
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "SATURATED",
            "reasoning": "Diminishing returns, tried multiple strategies",
            "confidence": 90,
            "strategies_tried": ["broad search", "specific terms", "date filtering"],
            "remaining_gaps": []
        })

        with patch("research.mixins.query_generation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_next_query_or_stop(
                task=MockResearchTask(),
                hypothesis=hypothesis,
                source_name="SAM.gov",
                query_history=query_history,
                source_metadata={},
                total_results_accepted=9
            )

        assert result["decision"] == "SATURATED"
        assert len(result["strategies_tried"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
