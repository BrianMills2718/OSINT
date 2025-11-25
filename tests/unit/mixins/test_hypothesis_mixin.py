#!/usr/bin/env python3
"""
Unit tests for HypothesisMixin.

Tests:
- _generate_hypotheses (mocked LLM)
- _assess_coverage (mocked LLM)
"""

import asyncio
import json
import pytest
import time
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
        self.status = "pending"


class TestGenerateHypotheses:
    """Test _generate_hypotheses method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.hypothesis_mixin import HypothesisMixin

        class MockHost(HypothesisMixin):
            max_hypotheses_per_task = 5

            def _get_available_source_names(self):
                return ["SAM.gov", "USASpending", "Brave Search"]

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_generates_hypotheses_for_task(self):
        """LLM generates 1-5 hypotheses with search strategies."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "hypotheses": [
                {
                    "id": 1,
                    "statement": "F-35 contracts are primarily awarded to Lockheed Martin",
                    "confidence": 85,
                    "confidence_reasoning": "Lockheed is the prime contractor",
                    "search_strategy": {
                        "sources": ["SAM.gov", "USASpending"],
                        "signals": ["Lockheed", "F-35", "contract award"],
                        "expected_entities": ["Lockheed Martin", "DoD"]
                    },
                    "exploration_priority": 1,
                    "priority_reasoning": "Highest confidence pathway"
                },
                {
                    "id": 2,
                    "statement": "F-35 supply chain involves multiple subcontractors",
                    "confidence": 70,
                    "confidence_reasoning": "Complex program has many suppliers",
                    "search_strategy": {
                        "sources": ["USASpending"],
                        "signals": ["subcontract", "supplier", "F-35"],
                        "expected_entities": ["Northrop Grumman", "BAE Systems"]
                    },
                    "exploration_priority": 2,
                    "priority_reasoning": "Secondary exploration"
                }
            ],
            "coverage_assessment": "Two hypotheses cover prime and subcontractor aspects"
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_hypotheses(
                task_query="F-35 contracts",
                research_question="What are F-35 defense contracts?",
                all_tasks=[MockResearchTask()]
            )

        assert len(result["hypotheses"]) == 2
        assert result["hypotheses"][0]["id"] == 1
        assert "Lockheed Martin" in result["hypotheses"][0]["statement"]
        assert result["coverage_assessment"] == "Two hypotheses cover prime and subcontractor aspects"

    @pytest.mark.asyncio
    async def test_respects_max_hypotheses_limit(self):
        """Generated hypotheses respect max_hypotheses_per_task."""
        self.host.max_hypotheses_per_task = 3

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "hypotheses": [
                {
                    "id": i,
                    "statement": f"Hypothesis {i}",
                    "confidence": 80,
                    "confidence_reasoning": "Test",
                    "search_strategy": {"sources": ["SAM.gov"], "signals": ["test"], "expected_entities": []},
                    "exploration_priority": i,
                    "priority_reasoning": "Test"
                }
                for i in range(1, 4)  # 3 hypotheses
            ],
            "coverage_assessment": "Test"
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_hypotheses(
                task_query="test",
                research_question="test",
                all_tasks=[]
            )

        assert len(result["hypotheses"]) <= self.host.max_hypotheses_per_task

    @pytest.mark.asyncio
    async def test_passes_existing_hypotheses_for_diversity(self):
        """Existing hypotheses are passed to LLM for diversity."""
        existing = [{"id": 1, "statement": "Already explored hypothesis"}]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "hypotheses": [
                {
                    "id": 2,
                    "statement": "New different hypothesis",
                    "confidence": 75,
                    "confidence_reasoning": "Test",
                    "search_strategy": {"sources": ["SAM.gov"], "signals": [], "expected_entities": []},
                    "exploration_priority": 1,
                    "priority_reasoning": "Test"
                }
            ],
            "coverage_assessment": "Diversified from existing"
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._generate_hypotheses(
                task_query="test",
                research_question="test",
                all_tasks=[],
                existing_hypotheses=existing
            )

        # Verify LLM was called (prompt should include existing hypotheses)
        assert mock_llm.called


class TestAssessCoverage:
    """Test _assess_coverage method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with required attributes."""
        from research.mixins.hypothesis_mixin import HypothesisMixin

        class MockHost(HypothesisMixin):
            max_time_per_task_seconds = 300
            max_hypotheses_to_execute = 5

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_returns_continue_when_gaps_remain(self):
        """Returns 'continue' decision when gaps identified."""
        task = MockResearchTask()
        task.hypotheses = {
            "hypotheses": [
                {"id": 1, "statement": "Test hypothesis", "exploration_priority": 1, "confidence": 80}
            ]
        }
        task.hypothesis_runs = [
            {
                "hypothesis_id": 1,
                "statement": "Test hypothesis",
                "delta_metrics": {"results_new": 5, "results_duplicate": 2, "total_results": 7},
                "sources": ["SAM.gov"]
            }
        ]
        task.accumulated_results = [{"url": "1"}, {"url": "2"}]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "continue",
            "assessment": "Good progress but timeline information missing",
            "gaps_identified": ["Timeline of contracts", "Budget breakdown"]
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._assess_coverage(
                task=task,
                research_question="What are F-35 contracts?",
                start_time=time.time()
            )

        assert result["decision"] == "continue"
        assert len(result["gaps_identified"]) == 2
        assert "facts" in result  # Auto-injected facts

    @pytest.mark.asyncio
    async def test_returns_stop_when_coverage_sufficient(self):
        """Returns 'stop' decision when coverage is sufficient."""
        task = MockResearchTask()
        task.hypotheses = {"hypotheses": [{"id": 1, "statement": "Test", "exploration_priority": 1, "confidence": 80}]}
        task.hypothesis_runs = [
            {
                "hypothesis_id": 1,
                "statement": "Test",
                "delta_metrics": {"results_new": 20, "results_duplicate": 5, "total_results": 25},
                "sources": ["SAM.gov", "USASpending"]
            }
        ]
        task.accumulated_results = [{"url": str(i)} for i in range(20)]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "stop",
            "assessment": "Comprehensive coverage achieved across all aspects",
            "gaps_identified": []
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._assess_coverage(
                task=task,
                research_question="test",
                start_time=time.time()
            )

        assert result["decision"] == "stop"
        assert result["gaps_identified"] == []

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        """Falls back to hard ceiling logic on LLM error."""
        task = MockResearchTask()
        task.hypotheses = {"hypotheses": [{"id": 1}]}
        task.hypothesis_runs = [{
            "hypothesis_id": 1,
            "statement": "Test hypothesis",
            "delta_metrics": {
                "results_new": 5,
                "results_duplicate": 0,
                "total_results": 5
            },
            "sources": ["SAM.gov"]
        }]

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API Error")

            result = await self.host._assess_coverage(
                task=task,
                research_question="test",
                start_time=time.time()
            )

        # Should return a decision based on hard ceilings
        assert result["decision"] in ["continue", "stop"]
        assert "failed" in result["assessment"].lower() or "fallback" in result["assessment"].lower()

    @pytest.mark.asyncio
    async def test_injects_computed_facts(self):
        """Auto-injects computed facts into decision."""
        task = MockResearchTask()
        task.hypotheses = {"hypotheses": [{"id": 1}]}
        task.hypothesis_runs = [
            {
                "hypothesis_id": 1,
                "statement": "Test",
                "delta_metrics": {
                    "results_new": 10,
                    "results_duplicate": 3,
                    "entities_new": 5,
                    "total_results": 13
                },
                "sources": ["SAM.gov"]
            }
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "continue",
            "assessment": "Test",
            "gaps_identified": []
        })

        with patch("research.mixins.hypothesis_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._assess_coverage(
                task=task,
                research_question="test",
                start_time=time.time()
            )

        # Check injected facts
        assert "facts" in result
        assert result["facts"]["results_new"] == 10
        assert result["facts"]["results_duplicate"] == 3
        assert result["facts"]["hypotheses_executed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
