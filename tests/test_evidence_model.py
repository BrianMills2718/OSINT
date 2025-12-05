#!/usr/bin/env python3
"""
Unit tests for the three-tier Evidence data model.

Tests:
    - RawResult creation and serialization
    - ProcessedEvidence creation and serialization
    - Evidence composition with from_raw()
    - Backward compatibility with legacy Evidence creation
    - Serialization roundtrips
"""

import pytest
from datetime import datetime
import json

from core.raw_result import RawResult
from core.processed_evidence import ProcessedEvidence, ExtractedDate
from core.database_integration_base import Evidence, SearchResult


class TestRawResult:
    """Tests for RawResult dataclass."""

    def test_creation_from_api_response(self):
        """Test creating RawResult from API response."""
        raw = RawResult.from_api_response(
            api_response={"id": "123", "description": "Full content here"},
            source_id="sam",
            query_params={"q": "AI contracts"},
            title="Test Contract",
            raw_content="Full content that should never be truncated no matter how long it is",
            url="https://sam.gov/contract/123",
            structured_date="2024-11-15"
        )

        assert raw.source_id == "sam"
        assert raw.title == "Test Contract"
        assert raw.raw_content == "Full content that should never be truncated no matter how long it is"
        assert raw.url == "https://sam.gov/contract/123"
        assert raw.structured_date == "2024-11-15"
        assert raw.api_response["id"] == "123"
        assert len(raw.id) == 36  # UUID format

    def test_no_truncation_of_raw_content(self):
        """Test that raw_content is never truncated."""
        long_content = "A" * 10000  # 10,000 characters
        raw = RawResult.from_api_response(
            api_response={},
            source_id="test",
            query_params={},
            title="Test",
            raw_content=long_content
        )

        assert len(raw.raw_content) == 10000
        assert raw.content_length == 10000

    def test_serialization_roundtrip(self):
        """Test to_dict() and from_dict() roundtrip."""
        raw = RawResult.from_api_response(
            api_response={"key": "value"},
            source_id="test",
            query_params={"q": "test"},
            title="Test Title",
            raw_content="Test content",
            url="https://example.com",
            structured_date="2024-01-01"
        )

        data = raw.to_dict()
        restored = RawResult.from_dict(data)

        assert restored.id == raw.id
        assert restored.source_id == raw.source_id
        assert restored.title == raw.title
        assert restored.raw_content == raw.raw_content
        assert restored.structured_date == raw.structured_date

    def test_json_serializable(self):
        """Test that to_dict() output is JSON serializable."""
        raw = RawResult.from_api_response(
            api_response={"nested": {"key": "value"}},
            source_id="test",
            query_params={},
            title="Test",
            raw_content="Content"
        )

        # Should not raise
        json_str = json.dumps(raw.to_dict())
        assert len(json_str) > 0


class TestProcessedEvidence:
    """Tests for ProcessedEvidence dataclass."""

    def test_creation(self):
        """Test basic ProcessedEvidence creation."""
        processed = ProcessedEvidence(
            raw_result_id="abc123",
            goal="Find AI contracts",
            extracted_by="gemini-2.0-flash-exp",
            extracted_facts=["Fact 1", "Fact 2"],
            extracted_entities=["Palantir", "Pentagon"],
            relevance_score=0.92,
            summary="Pentagon awarded contract to Palantir"
        )

        assert processed.raw_result_id == "abc123"
        assert processed.goal == "Find AI contracts"
        assert len(processed.extracted_facts) == 2
        assert len(processed.extracted_entities) == 2
        assert processed.relevance_score == 0.92
        assert processed.has_facts
        assert processed.has_entities

    def test_from_llm_response(self):
        """Test creation from LLM extraction response."""
        llm_response = {
            "extracted_facts": ["Contract worth $200M"],
            "extracted_entities": ["Pentagon", "Anduril"],
            "extracted_dates": [
                {"date": "2024-11-15", "context": "Award date"}
            ],
            "relevance_score": 0.85,
            "relevance_reasoning": "Directly relevant to AI contracts query",
            "summary": "Pentagon awarded $200M to Anduril for AI"
        }

        processed = ProcessedEvidence.from_llm_response(
            raw_result_id="raw123",
            goal="Find AI contracts",
            llm_response=llm_response,
            model="gemini-2.0-flash-exp"
        )

        assert processed.raw_result_id == "raw123"
        assert len(processed.extracted_dates) == 1
        assert processed.extracted_dates[0].date == "2024-11-15"
        assert processed.llm_context == "Pentagon awarded $200M to Anduril for AI"

    def test_serialization_roundtrip(self):
        """Test to_dict() and from_dict() roundtrip."""
        processed = ProcessedEvidence(
            raw_result_id="abc123",
            goal="Test goal",
            extracted_facts=["Fact"],
            extracted_dates=[ExtractedDate("2024-01-01", "Test date")],
            relevance_score=0.5,
            summary="Test summary"
        )

        data = processed.to_dict()
        restored = ProcessedEvidence.from_dict(data)

        assert restored.id == processed.id
        assert restored.raw_result_id == processed.raw_result_id
        assert restored.extracted_facts == processed.extracted_facts
        assert len(restored.extracted_dates) == 1

    def test_date_strings_property(self):
        """Test date_strings property extracts just dates."""
        processed = ProcessedEvidence(
            raw_result_id="test",
            goal="test",
            extracted_dates=[
                ExtractedDate("2024-01-01", "Start date"),
                ExtractedDate("2024-12-31", "End date")
            ]
        )

        assert processed.date_strings == ["2024-01-01", "2024-12-31"]


class TestEvidenceFromRaw:
    """Tests for Evidence.from_raw() factory method."""

    def test_from_raw_basic(self):
        """Test basic Evidence creation from RawResult."""
        raw = RawResult.from_api_response(
            api_response={"id": "123"},
            source_id="sam",
            query_params={},
            title="Contract Title",
            raw_content="Full content here",
            url="https://sam.gov/123"
        )

        evidence = Evidence.from_raw(raw)

        assert evidence.source_id == "sam"
        assert evidence.title == "Contract Title"
        assert evidence.raw_content == "Full content here"
        assert evidence.raw_result_id == raw.id
        assert evidence.has_raw_data

    def test_from_raw_with_processed(self):
        """Test Evidence creation with ProcessedEvidence."""
        raw = RawResult.from_api_response(
            api_response={},
            source_id="test",
            query_params={},
            title="Test",
            raw_content="Content"
        )

        processed = ProcessedEvidence(
            raw_result_id=raw.id,
            goal="Test goal",
            extracted_facts=["Fact 1"],
            extracted_entities=["Entity 1"],
            relevance_score=0.75,
            summary="Summary"
        )

        evidence = Evidence.from_raw(raw, processed)

        assert evidence.relevance_score == 0.75
        assert evidence.extracted_facts == ["Fact 1"]
        assert evidence.extracted_entities == ["Entity 1"]
        assert evidence.processed_id == processed.id
        assert evidence.has_processed_data

    def test_snippet_truncation_for_llm(self):
        """Test that snippet is truncated but raw_content is not."""
        long_content = "A" * 1000
        raw = RawResult.from_api_response(
            api_response={},
            source_id="test",
            query_params={},
            title="Test",
            raw_content=long_content
        )

        evidence = Evidence.from_raw(raw)

        # snippet should be truncated for LLM context
        assert len(evidence.snippet) <= 500
        assert evidence.snippet.endswith("...")

        # raw_content should be preserved
        assert len(evidence.raw_content) == 1000
        assert evidence.full_content == long_content


class TestEvidenceBackwardCompatibility:
    """Tests for backward compatibility with legacy Evidence creation."""

    def test_from_dict_still_works(self):
        """Test legacy from_dict() method still works."""
        evidence = Evidence.from_dict(
            {"title": "Legacy Title", "snippet": "Legacy content"},
            source_id="legacy_source"
        )

        assert evidence.title == "Legacy Title"
        assert evidence.content == "Legacy content"
        assert evidence.source_id == "legacy_source"
        assert not evidence.has_raw_data

    def test_from_dict_preserves_raw_content(self):
        """Test from_dict() preserves raw_content from build_with_raw()."""
        # This is the key three-tier model test - integrations now return
        # dicts with raw_content via build_with_raw(), and from_dict()
        # must preserve it through SearchResult validation.
        data = {
            "title": "Contract Award",
            "snippet": "Short snippet for LLM",
            "url": "https://sam.gov/123",
            "raw_content": "Full raw content that should not be truncated even if very long " * 20
        }

        evidence = Evidence.from_dict(data, source_id="sam")

        # Snippet should be short (for LLM prompts)
        assert evidence.snippet == "Short snippet for LLM"

        # raw_content should be preserved without truncation
        assert len(evidence.raw_content) > 500
        assert evidence.raw_content.startswith("Full raw content")

        # .content should prefer raw_content
        assert evidence.content == evidence.raw_content

        # .full_content should return raw_content
        assert evidence.full_content == evidence.raw_content

    def test_from_search_result_still_works(self):
        """Test legacy from_search_result() method still works."""
        search_result = SearchResult(
            title="Search Result",
            snippet="Result content",
            url="https://example.com"
        )

        evidence = Evidence.from_search_result(search_result, source_id="test")

        assert evidence.title == "Search Result"
        assert evidence.content == "Result content"
        assert not evidence.has_raw_data

    def test_content_property_prefers_raw_content(self):
        """Test that .content returns raw_content when available."""
        # Legacy evidence - no raw_content
        legacy = Evidence.from_dict(
            {"title": "Test", "snippet": "Snippet content"},
            source_id="test"
        )
        assert legacy.content == "Snippet content"

        # New evidence - has raw_content
        raw = RawResult.from_api_response(
            api_response={},
            source_id="test",
            query_params={},
            title="Test",
            raw_content="Full raw content"
        )
        new = Evidence.from_raw(raw)
        assert new.content == "Full raw content"

    def test_to_dict_excludes_none_fields_by_default(self):
        """Test that to_dict() excludes None new fields for backward compat."""
        evidence = Evidence.from_dict(
            {"title": "Test", "snippet": "Content"},
            source_id="test"
        )

        data = evidence.to_dict()

        # New fields should not be present if None
        assert "raw_result_id" not in data
        assert "processed_id" not in data
        assert "raw_content" not in data
        assert "extracted_facts" not in data

    def test_to_dict_includes_new_fields_with_flag(self):
        """Test that to_dict(include_raw=True) includes all fields."""
        raw = RawResult.from_api_response(
            api_response={},
            source_id="test",
            query_params={},
            title="Test",
            raw_content="Content"
        )
        evidence = Evidence.from_raw(raw)

        data = evidence.to_dict(include_raw=True)

        assert "raw_result_id" in data
        assert "raw_content" in data
        assert data["raw_result_id"] == raw.id


class TestExtractedDate:
    """Tests for ExtractedDate dataclass."""

    def test_creation(self):
        """Test ExtractedDate creation."""
        date = ExtractedDate(
            date="2024-11-15",
            context="Contract award date",
            confidence=0.95
        )

        assert date.date == "2024-11-15"
        assert date.context == "Contract award date"
        assert date.confidence == 0.95

    def test_serialization(self):
        """Test ExtractedDate serialization."""
        date = ExtractedDate("2024-01-01", "Test date", 0.8)
        data = date.to_dict()
        restored = ExtractedDate.from_dict(data)

        assert restored.date == date.date
        assert restored.context == date.context
        assert restored.confidence == date.confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
