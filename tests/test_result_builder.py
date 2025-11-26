#!/usr/bin/env python3
"""
Unit tests for SearchResultBuilder defensive data transformation.

Tests all static methods and builder pattern to ensure null safety.
"""

import pytest
from datetime import datetime, date
from core.result_builder import SearchResultBuilder, build_result


class TestSafeAmount:
    """Tests for SearchResultBuilder.safe_amount()"""

    def test_none_returns_default(self):
        assert SearchResultBuilder.safe_amount(None) == 0.0
        assert SearchResultBuilder.safe_amount(None, default=100.0) == 100.0

    def test_valid_float(self):
        assert SearchResultBuilder.safe_amount(123.45) == 123.45

    def test_valid_int(self):
        assert SearchResultBuilder.safe_amount(100) == 100.0

    def test_string_number(self):
        assert SearchResultBuilder.safe_amount("123.45") == 123.45
        assert SearchResultBuilder.safe_amount("100") == 100.0

    def test_invalid_string_returns_default(self):
        assert SearchResultBuilder.safe_amount("not a number") == 0.0
        assert SearchResultBuilder.safe_amount("") == 0.0

    def test_empty_dict_returns_default(self):
        assert SearchResultBuilder.safe_amount({}) == 0.0


class TestFormatAmount:
    """Tests for SearchResultBuilder.format_amount()"""

    def test_none_formats_default(self):
        assert SearchResultBuilder.format_amount(None) == "$0.00"

    def test_valid_amount(self):
        assert SearchResultBuilder.format_amount(1234.56) == "$1,234.56"

    def test_large_amount_with_commas(self):
        assert SearchResultBuilder.format_amount(1234567.89) == "$1,234,567.89"

    def test_string_amount(self):
        assert SearchResultBuilder.format_amount("1000") == "$1,000.00"


class TestSafeText:
    """Tests for SearchResultBuilder.safe_text()"""

    def test_none_returns_default(self):
        assert SearchResultBuilder.safe_text(None) == ""
        assert SearchResultBuilder.safe_text(None, default="N/A") == "N/A"

    def test_valid_string(self):
        assert SearchResultBuilder.safe_text("Hello World") == "Hello World"

    def test_strips_whitespace(self):
        assert SearchResultBuilder.safe_text("  Hello  ") == "Hello"

    def test_max_length_truncation(self):
        result = SearchResultBuilder.safe_text("Hello World", max_length=8)
        assert result == "Hello..."
        assert len(result) == 8

    def test_no_truncation_when_shorter(self):
        result = SearchResultBuilder.safe_text("Hi", max_length=10)
        assert result == "Hi"

    def test_converts_non_string(self):
        assert SearchResultBuilder.safe_text(123) == "123"


class TestSafeDate:
    """Tests for SearchResultBuilder.safe_date()"""

    def test_none_returns_none(self):
        assert SearchResultBuilder.safe_date(None) is None

    def test_datetime_object(self):
        dt = datetime(2024, 1, 15, 12, 30, 45)
        assert SearchResultBuilder.safe_date(dt) == "2024-01-15T12:30:45"

    def test_date_object(self):
        d = date(2024, 1, 15)
        assert SearchResultBuilder.safe_date(d) == "2024-01-15"

    def test_string_date_passthrough(self):
        assert SearchResultBuilder.safe_date("2024-01-15") == "2024-01-15"

    def test_empty_string_returns_none(self):
        assert SearchResultBuilder.safe_date("") is None
        assert SearchResultBuilder.safe_date("   ") is None


class TestSafeUrl:
    """Tests for SearchResultBuilder.safe_url()"""

    def test_none_returns_none(self):
        assert SearchResultBuilder.safe_url(None) is None

    def test_valid_https_url(self):
        url = "https://example.com/path"
        assert SearchResultBuilder.safe_url(url) == url

    def test_valid_http_url(self):
        url = "http://example.com"
        assert SearchResultBuilder.safe_url(url) == url

    def test_relative_url(self):
        assert SearchResultBuilder.safe_url("/path/to/resource") == "/path/to/resource"

    def test_empty_string_returns_none(self):
        assert SearchResultBuilder.safe_url("") is None
        assert SearchResultBuilder.safe_url("   ") is None

    def test_non_http_url_still_returned(self):
        # Builder logs debug but doesn't reject
        assert SearchResultBuilder.safe_url("ftp://example.com") == "ftp://example.com"


class TestSafeInt:
    """Tests for SearchResultBuilder.safe_int()"""

    def test_none_returns_default(self):
        assert SearchResultBuilder.safe_int(None) == 0
        assert SearchResultBuilder.safe_int(None, default=10) == 10

    def test_valid_int(self):
        assert SearchResultBuilder.safe_int(42) == 42

    def test_float_truncated(self):
        assert SearchResultBuilder.safe_int(42.9) == 42

    def test_string_number(self):
        assert SearchResultBuilder.safe_int("42") == 42
        assert SearchResultBuilder.safe_int("42.9") == 42

    def test_invalid_returns_default(self):
        assert SearchResultBuilder.safe_int("not a number") == 0


class TestBuilderChaining:
    """Tests for SearchResultBuilder builder pattern"""

    def test_basic_chaining(self):
        result = (SearchResultBuilder()
            .title("Test Title")
            .url("https://example.com")
            .snippet("Test snippet")
            .date("2024-01-15")
            .metadata({"key": "value"})
            .build())

        assert result["title"] == "Test Title"
        assert result["url"] == "https://example.com"
        assert result["snippet"] == "Test snippet"
        assert result["date"] == "2024-01-15"
        assert result["metadata"] == {"key": "value"}

    def test_handles_none_values(self):
        result = (SearchResultBuilder()
            .title(None)
            .url(None)
            .snippet(None)
            .date(None)
            .build())

        assert result["title"] == "Untitled"  # Default
        assert result["url"] is None
        assert result["snippet"] == ""
        assert result["date"] is None

    def test_title_default(self):
        result = (SearchResultBuilder()
            .title(None, default="Custom Default")
            .build())
        assert result["title"] == "Custom Default"

    def test_snippet_max_length(self):
        long_text = "A" * 1000
        result = (SearchResultBuilder()
            .snippet(long_text, max_length=100)
            .build())
        assert len(result["snippet"]) == 100
        assert result["snippet"].endswith("...")

    def test_add_metadata(self):
        result = (SearchResultBuilder()
            .metadata({"key1": "value1"})
            .add_metadata("key2", "value2")
            .build())
        assert result["metadata"]["key1"] == "value1"
        assert result["metadata"]["key2"] == "value2"


class TestFromDict:
    """Tests for SearchResultBuilder.from_dict()"""

    def test_basic_mapping(self):
        data = {
            "title": "My Title",
            "url": "https://example.com",
            "snippet": "Description",
            "date": "2024-01-15"
        }
        builder = SearchResultBuilder.from_dict(data)
        result = builder.build()

        assert result["title"] == "My Title"
        assert result["url"] == "https://example.com"

    def test_custom_key_mapping(self):
        data = {
            "name": "Custom Title",
            "link": "https://example.com"
        }
        builder = SearchResultBuilder.from_dict(
            data,
            title_key="name",
            url_key="link"
        )
        result = builder.build()
        assert result["title"] == "Custom Title"
        assert result["url"] == "https://example.com"


class TestBuildResult:
    """Tests for build_result() convenience function"""

    def test_basic_usage(self):
        result = build_result(
            title="Test",
            url="https://example.com",
            snippet="Description",
            date="2024-01-15",
            metadata={"source": "test"}
        )
        assert result["title"] == "Test"
        assert result["url"] == "https://example.com"
        assert result["metadata"]["source"] == "test"

    def test_handles_none(self):
        result = build_result(title=None)
        assert result["title"] == "Untitled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
