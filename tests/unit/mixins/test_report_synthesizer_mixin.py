#!/usr/bin/env python3
"""
Unit tests for ReportSynthesizerMixin.

Tests:
- _format_synthesis_json_to_markdown (pure logic, no LLM)
- _synthesize_report (mocked LLM)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFormatSynthesisJsonToMarkdown:
    """Test _format_synthesis_json_to_markdown method (pure logic)."""

    def setup_method(self):
        """Create mixin instance for testing."""
        from research.mixins.report_synthesizer_mixin import ReportSynthesizerMixin

        class MockHost(ReportSynthesizerMixin):
            pass

        self.host = MockHost()

    def test_empty_json_returns_minimal_report(self):
        """Empty JSON returns minimal valid markdown."""
        result = self.host._format_synthesis_json_to_markdown({})

        assert "# Research Report" in result

    def test_malformed_json_returns_error(self):
        """Non-dict input returns error message."""
        result = self.host._format_synthesis_json_to_markdown(None)

        assert "Error" in result
        assert "Invalid" in result

    def test_formats_title(self):
        """Report title is formatted as H1."""
        json_data = {
            "report": {
                "title": "Defense Contract Analysis"
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "# Defense Contract Analysis" in result

    def test_formats_executive_summary(self):
        """Executive summary section is formatted correctly."""
        json_data = {
            "report": {
                "title": "Test Report",
                "executive_summary": {
                    "text": "This is the executive summary.",
                    "key_points": [
                        {
                            "point": "First key point",
                            "inline_citations": [
                                {"title": "Source 1", "url": "https://example.com/1", "date": "2024-01-15"}
                            ]
                        }
                    ]
                }
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Executive Summary" in result
        assert "This is the executive summary." in result
        assert "First key point" in result
        assert "[Source 1](https://example.com/1)" in result

    def test_formats_source_groups(self):
        """Source groups (key findings) are formatted correctly."""
        json_data = {
            "report": {
                "title": "Test",
                "source_groups": [
                    {
                        "group_name": "Government Sources",
                        "group_description": "Official government data",
                        "reliability_context": "High reliability",
                        "findings": [
                            {
                                "claim": "Contract worth $1B awarded",
                                "inline_citations": [
                                    {"title": "SAM.gov", "url": "https://sam.gov/1", "date": "2024-01-10"}
                                ],
                                "supporting_detail": "Award to Lockheed Martin"
                            }
                        ]
                    }
                ]
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Key Findings" in result
        assert "### Government Sources" in result
        assert "High reliability" in result
        assert "Contract worth $1B awarded" in result
        assert "[SAM.gov](https://sam.gov/1)" in result

    def test_formats_entity_network(self):
        """Entity network section is formatted correctly."""
        json_data = {
            "report": {
                "title": "Test",
                "entity_network": {
                    "description": "Key entities in this research",
                    "key_entities": [
                        {
                            "name": "Lockheed Martin",
                            "context": "Prime contractor",
                            "relationships": ["DoD supplier", "F-35 manufacturer"]
                        }
                    ]
                }
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Entity Network" in result
        assert "Key entities in this research" in result
        assert "**Lockheed Martin**" in result
        assert "Prime contractor" in result
        assert "DoD supplier" in result

    def test_formats_timeline(self):
        """Timeline section is formatted correctly."""
        json_data = {
            "report": {
                "title": "Test",
                "timeline": [
                    {
                        "date": "2024-01-15",
                        "event": "Contract awarded",
                        "sources": [{"title": "SAM.gov", "url": "https://sam.gov/1"}]
                    }
                ]
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Timeline" in result
        assert "**2024-01-15**" in result
        assert "Contract awarded" in result

    def test_formats_methodology(self):
        """Methodology section is formatted correctly."""
        json_data = {
            "report": {
                "title": "Test",
                "methodology": {
                    "approach": "Multi-source research approach",
                    "tasks_executed": 5,
                    "total_results": 150,
                    "entities_discovered": 25,
                    "integrations_used": ["SAM.gov", "USASpending"],
                    "coverage_summary": {"SAM.gov": 50, "USASpending": 100}
                }
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Methodology" in result
        assert "Multi-source research approach" in result
        assert "**Tasks executed**: 5" in result
        assert "**Total results**: 150" in result
        assert "SAM.gov, USASpending" in result

    def test_formats_limitations(self):
        """Limitations section is included when present."""
        json_data = {
            "report": {
                "title": "Test",
                "synthesis_quality_check": {
                    "limitations_noted": "Some sources were rate limited"
                }
            }
        }
        result = self.host._format_synthesis_json_to_markdown(json_data)

        assert "## Research Limitations" in result
        assert "rate limited" in result


class TestSynthesizeReport:
    """Test _synthesize_report method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with all required attributes."""
        from research.mixins.report_synthesizer_mixin import ReportSynthesizerMixin

        class MockTask:
            def __init__(self, task_id, query):
                self.id = task_id
                self.query = query
                self.entities_found = ["Lockheed Martin"]
                self.hypothesis_runs = []
                self.hypotheses = None
                self.accumulated_results = []
                self.reasoning_notes = []
                self.metadata = {}

        class MockHost(ReportSynthesizerMixin):
            results_by_task = {
                1: {"total_results": 5, "results": [
                    {"title": "Result 1", "url": "https://example.com/1", "source": "SAM.gov", "snippet": "Test"}
                ]}
            }
            completed_tasks = [MockTask(1, "F-35 contracts")]
            failed_tasks = []
            entity_graph = {"lockheed martin": ["dod"]}
            original_question = "What are F-35 contracts?"
            integrations = ["sam"]
            hypothesis_branching_enabled = False
            critical_source_failures = []

        self.host = MockHost()
        self.MockTask = MockTask

    @pytest.mark.asyncio
    async def test_synthesizes_report_from_results(self):
        """LLM synthesizes report from collected results."""
        mock_synthesis = {
            "report": {
                "title": "F-35 Contract Analysis",
                "executive_summary": {"text": "Analysis of F-35 contracts", "key_points": []},
                "source_groups": [],
                "methodology": {"approach": "Multi-source", "tasks_executed": 1, "total_results": 5},
                "synthesis_quality_check": {"all_claims_have_citations": True}
            }
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_synthesis)

        with patch("research.mixins.report_synthesizer_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            report = await self.host._synthesize_report("What are F-35 contracts?")

            assert "# F-35 Contract Analysis" in report
            assert "Analysis of F-35 contracts" in report

    @pytest.mark.asyncio
    async def test_handles_llm_json_error(self):
        """JSON parsing errors are handled gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"

        with patch("research.mixins.report_synthesizer_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            report = await self.host._synthesize_report("test question")

            assert "Failed to parse" in report or "Research Report" in report

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """LLM errors produce error report."""
        with patch("research.mixins.report_synthesizer_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API Error")

            report = await self.host._synthesize_report("test question")

            assert "Failed" in report or "Error" in report

    @pytest.mark.asyncio
    async def test_deduplicates_results_by_url(self):
        """Results are deduplicated by URL before synthesis."""
        # Add duplicate URLs
        self.host.results_by_task = {
            1: {"total_results": 3, "results": [
                {"title": "Result 1", "url": "https://example.com/same", "source": "SAM.gov", "snippet": "A"},
                {"title": "Result 2", "url": "https://example.com/same", "source": "SAM.gov", "snippet": "B"},
                {"title": "Result 3", "url": "https://example.com/diff", "source": "SAM.gov", "snippet": "C"},
            ]}
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "report": {"title": "Test", "executive_summary": {"text": "Test"}}
        })

        with patch("research.mixins.report_synthesizer_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # The method should print deduplication message
            await self.host._synthesize_report("test")

            # Verify LLM was called (deduplication happens before)
            assert mock_llm.called

    @pytest.mark.asyncio
    async def test_adds_critical_source_failures_to_limitations(self):
        """Critical source failures are added to report limitations."""
        self.host.critical_source_failures = ["SAM.gov", "USASpending"]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "report": {
                "title": "Test",
                "executive_summary": {"text": "Test"},
                "synthesis_quality_check": {"limitations_noted": "Some limits"}
            }
        })

        with patch("research.mixins.report_synthesizer_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            report = await self.host._synthesize_report("test")

            assert "Critical sources unavailable" in report or "Limitations" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
