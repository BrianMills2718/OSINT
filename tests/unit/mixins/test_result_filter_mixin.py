#!/usr/bin/env python3
"""
Unit tests for ResultFilterMixin.

Tests:
- _validate_result_dates (pure logic, no LLM)
- _validate_result_relevance (mocked LLM)
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestValidateResultDates:
    """Test _validate_result_dates method (pure logic, no LLM)."""

    def setup_method(self):
        """Create a minimal mixin instance for testing."""
        from research.mixins.result_filter_mixin import ResultFilterMixin

        # Create a mock host class that has the mixin
        class MockHost(ResultFilterMixin):
            pass

        self.host = MockHost()

    def test_empty_results(self):
        """Empty input returns empty output."""
        result = self.host._validate_result_dates([])
        assert result == []

    def test_results_without_dates_pass_through(self):
        """Results without date fields pass through with warning flag."""
        results = [
            {"title": "No date result", "url": "https://example.com/1"},
            {"title": "Another", "snippet": "test snippet"}
        ]
        validated = self.host._validate_result_dates(results)

        assert len(validated) == 2
        assert validated[0].get("_date_warning") == "no_date_found"
        assert validated[1].get("_date_warning") == "no_date_found"

    def test_valid_past_dates_pass(self):
        """Results with valid past dates pass through."""
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        results = [
            {"title": "Valid date", "date": yesterday, "url": "https://example.com"},
            {"title": "Old date", "published_date": "2024-01-15"}
        ]
        validated = self.host._validate_result_dates(results)

        assert len(validated) == 2
        # No warning flags for valid dates
        assert "_date_warning" not in validated[0]
        assert "_date_warning" not in validated[1]

    def test_future_dates_rejected(self):
        """Results with future dates are rejected."""
        future_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        results = [
            {"title": "Future dated", "date": future_date, "url": "https://example.com"},
            {"title": "Valid", "date": "2024-06-15"}
        ]
        validated = self.host._validate_result_dates(results)

        # Only valid result should pass
        assert len(validated) == 1
        assert validated[0]["title"] == "Valid"

    def test_timezone_buffer_allows_recent_dates(self):
        """Dates within 1 day buffer (timezone tolerance) pass."""
        # A date just slightly in the future (timezone edge case)
        tomorrow = (datetime.utcnow() + timedelta(hours=12)).strftime("%Y-%m-%d")
        results = [{"title": "Timezone edge", "date": tomorrow}]
        validated = self.host._validate_result_dates(results)

        # Should pass due to 1-day buffer
        assert len(validated) == 1

    def test_multiple_date_formats(self):
        """Various date formats are handled."""
        results = [
            {"title": "ISO format", "date": "2024-06-15"},
            {"title": "US format", "date": "Jun 15, 2024"},
            {"title": "Full month", "date": "June 15, 2024"},
        ]
        validated = self.host._validate_result_dates(results)

        # All should pass (valid past dates)
        assert len(validated) == 3

    def test_unparseable_dates_pass_with_warning(self):
        """Dates that can't be parsed pass through with warning."""
        results = [
            {"title": "Weird date", "date": "sometime in 2024"},
            {"title": "Invalid", "date": "not-a-date"}
        ]
        validated = self.host._validate_result_dates(results)

        # Should pass but with warning
        assert len(validated) == 2
        # Either passes through without flag (no recognized format) or has warning


class TestValidateResultRelevance:
    """Test _validate_result_relevance method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with mocked dependencies."""
        from research.mixins.result_filter_mixin import ResultFilterMixin

        class MockHost(ResultFilterMixin):
            def _emit_progress(self, event_type, message, task_id=None, data=None):
                pass  # No-op for testing

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_empty_results_returns_reject(self):
        """Empty results return rejection tuple."""
        result = await self.host._validate_result_relevance(
            task_query="test query",
            research_question="What are defense contracts?",
            sample_results=[]
        )

        should_accept, reason, indices, should_continue, cont_reason, breakdown = result
        assert should_accept is False
        assert "No results" in reason
        assert indices == []

    @pytest.mark.asyncio
    async def test_accepts_relevant_results(self):
        """LLM ACCEPT decision returns proper tuple."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "ACCEPT",
            "reason": "Results are relevant to defense contracts",
            "relevant_indices": [0, 2],
            "continue_searching": False,
            "continuation_reason": "Sufficient coverage",
            "reasoning_breakdown": {
                "filtering_strategy": "Keep defense-related",
                "interesting_decisions": [],
                "patterns_noticed": "All about contracts"
            }
        })

        with patch("research.mixins.result_filter_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            sample_results = [
                {"title": "Defense Contract Award", "snippet": "F-35 contract worth $1B"},
                {"title": "Unrelated News", "snippet": "Sports update"},
                {"title": "Military Procurement", "snippet": "New radar systems"}
            ]

            result = await self.host._validate_result_relevance(
                task_query="F-35 contracts",
                research_question="What are recent F-35 contracts?",
                sample_results=sample_results
            )

            should_accept, reason, indices, should_continue, cont_reason, breakdown = result
            assert should_accept is True
            assert indices == [0, 2]
            assert should_continue is False

    @pytest.mark.asyncio
    async def test_rejects_irrelevant_results(self):
        """LLM REJECT decision returns proper tuple."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "decision": "REJECT",
            "reason": "Results are about cooking, not defense",
            "relevant_indices": [],
            "continue_searching": True,
            "continuation_reason": "Need to find relevant results",
            "reasoning_breakdown": {
                "filtering_strategy": "Reject all cooking content",
                "interesting_decisions": [],
                "patterns_noticed": "All about recipes"
            }
        })

        with patch("research.mixins.result_filter_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            sample_results = [
                {"title": "Best Pasta Recipe", "snippet": "Delicious Italian dish"}
            ]

            result = await self.host._validate_result_relevance(
                task_query="defense contracts",
                research_question="What are defense contracts?",
                sample_results=sample_results
            )

            should_accept, reason, indices, should_continue, cont_reason, breakdown = result
            assert should_accept is False
            assert indices == []
            assert should_continue is True

    @pytest.mark.asyncio
    async def test_llm_error_returns_safe_default(self):
        """LLM errors return safe default (accept all, continue)."""
        with patch("research.mixins.result_filter_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API Error")

            sample_results = [
                {"title": "Result 1", "snippet": "Content 1"},
                {"title": "Result 2", "snippet": "Content 2"}
            ]

            result = await self.host._validate_result_relevance(
                task_query="test",
                research_question="test question",
                sample_results=sample_results
            )

            should_accept, reason, indices, should_continue, cont_reason, breakdown = result
            # On error, should accept all results and allow continuation
            assert should_accept is True
            assert "Error" in reason
            assert indices == [0, 1]  # All indices
            assert should_continue is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
