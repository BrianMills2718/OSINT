#!/usr/bin/env python3
"""
Unit tests for QueryReformulationMixin.

Tests:
- _reformulate_for_relevance (mocked LLM)
- _reformulate_query_simple (mocked LLM)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestReformulateForRelevance:
    """Test _reformulate_for_relevance method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.query_reformulation_mixin import QueryReformulationMixin

        class MockHost(QueryReformulationMixin):
            pass

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_reformulates_query_with_source_adjustments(self):
        """Reformulates query and adjusts source selection."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "F-35 Lightning II contract awards 2024",
            "source_adjustments": {
                "keep": ["SAM.gov", "USASpending"],
                "drop": ["Reddit"],
                "add": ["Brave Search"],
                "reasoning": "Reddit had 0% quality, Brave may have news coverage"
            },
            "param_adjustments": {
                "reddit": {"time_filter": "year"},
                "usajobs": {"keywords": "F-35 contractor"},
                "twitter": {"search_type": "Latest", "max_pages": 2}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_for_relevance(
                original_query="F-35 contracts",
                research_question="What are F-35 defense contracts?",
                results_count=15,
                source_performance=[
                    {"name": "SAM.gov", "status": "success", "results_returned": 10, "results_kept": 8, "quality_rate": 80},
                    {"name": "Reddit", "status": "success", "results_returned": 5, "results_kept": 0, "quality_rate": 0}
                ],
                available_sources=["SAM.gov", "USASpending", "Reddit", "Brave Search"]
            )

        assert result["query"] == "F-35 Lightning II contract awards 2024"
        assert "source_adjustments" in result
        assert result["source_adjustments"]["drop"] == ["Reddit"]
        assert "param_adjustments" in result

    @pytest.mark.asyncio
    async def test_handles_missing_source_performance(self):
        """Works without source performance data."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "reformulated query",
            "param_adjustments": {
                "reddit": {"time_filter": "all"},
                "usajobs": {"keywords": "test"},
                "twitter": {"search_type": "Top", "max_pages": 1}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_for_relevance(
                original_query="test query",
                research_question="test question",
                results_count=5,
                source_performance=None,
                available_sources=None
            )

        assert "query" in result

    @pytest.mark.asyncio
    async def test_returns_param_adjustments(self):
        """Returns source-specific parameter adjustments."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "defense contracts 2024",
            "param_adjustments": {
                "reddit": {"time_filter": "month"},
                "usajobs": {"keywords": "defense analyst"},
                "twitter": {"search_type": "Latest", "max_pages": 3}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_for_relevance(
                original_query="defense",
                research_question="What are defense contracts?",
                results_count=3
            )

        assert result["param_adjustments"]["reddit"]["time_filter"] == "month"
        assert result["param_adjustments"]["twitter"]["max_pages"] == 3


class TestReformulateQuerySimple:
    """Test _reformulate_query_simple method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance."""
        from research.mixins.query_reformulation_mixin import QueryReformulationMixin

        class MockHost(QueryReformulationMixin):
            pass

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_reformulates_to_broader_query(self):
        """Reformulates query to be broader when results insufficient."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "military aircraft contracts",
            "param_adjustments": {
                "reddit": {"time_filter": "all"},
                "usajobs": {"keywords": "aircraft"},
                "twitter": {"search_type": "Top", "max_pages": 2}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_query_simple(
                original_query="F-35A Block 4 upgrade contracts",
                results_count=2
            )

        assert result["query"] == "military aircraft contracts"
        # Simpler query (fewer specific terms)
        assert len(result["query"].split()) < len("F-35A Block 4 upgrade contracts".split())

    @pytest.mark.asyncio
    async def test_extends_time_filter_for_reddit(self):
        """Extends Reddit time filter when results insufficient."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "broader query",
            "param_adjustments": {
                "reddit": {"time_filter": "year"},  # Extended from default
                "usajobs": {"keywords": "broad"},
                "twitter": {"search_type": "Top", "max_pages": 1}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_query_simple(
                original_query="specific query",
                results_count=0
            )

        assert result["param_adjustments"]["reddit"]["time_filter"] in ["year", "all"]

    @pytest.mark.asyncio
    async def test_handles_zero_results(self):
        """Handles zero results case."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "very broad query",
            "param_adjustments": {
                "reddit": {"time_filter": "all"},
                "usajobs": {"keywords": "general"},
                "twitter": {"search_type": "Top", "max_pages": 1}
            }
        })

        with patch("research.mixins.query_reformulation_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await self.host._reformulate_query_simple(
                original_query="extremely specific query that returns nothing",
                results_count=0
            )

        assert "query" in result
        assert result["query"] != "extremely specific query that returns nothing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
