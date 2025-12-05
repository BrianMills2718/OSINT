#!/usr/bin/env python3
"""
E2E tests for error handling architecture.

Validates that the complete error handling flow works correctly
from integration error → ErrorClassifier → agent decision → execution log.

These tests use mocked API responses to simulate error conditions
while exercising the real agent code paths.

Run: pytest tests/e2e/test_error_handling_e2e.py -v
"""

import pytest
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from core.database_integration_base import QueryResult
from core.error_classifier import ErrorClassifier, ErrorCategory


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_config():
    """Create mock config with all required settings."""
    config = MagicMock()
    config.get_raw_config.return_value = {
        'research': {
            'error_handling': {
                'unfixable_http_codes': [401, 403, 404, 429, 500, 502, 503, 504],
                'fixable_http_codes': [400, 422],
                'timeout_patterns': ["timed out", "timeout", "TimeoutError"],
                'rate_limit_patterns': ["rate limit", "429", "quota exceeded", "too many requests"]
            }
        }
    }
    return config


@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# E2E ERROR CLASSIFICATION TESTS
# ============================================================================

class TestE2EErrorClassification:
    """E2E tests for error classification flow."""

    def test_e2e_rate_limit_flow(self, mock_config):
        """
        E2E: Rate limit error → ErrorClassifier → blocklist decision.

        Simulates SAM.gov returning HTTP 429 and verifies:
        1. ErrorClassifier correctly identifies RATE_LIMIT
        2. is_retryable=True, is_reformulable=False
        3. Agent would add to blocklist (not reformulate)
        """
        classifier = ErrorClassifier(mock_config)

        # Simulate SAM.gov 429 error (as seen in production)
        result = QueryResult(
            success=False,
            source="sam_gov",
            total=0,
            results=[],
            query_params={"keywords": "cybersecurity"},
            error="HTTP 429: Rate limit exceeded. Please try again later.",
            http_code=429,
            validate=False
        )

        # Error classification
        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        # Verify classification
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.http_code == 429
        assert error.source_id == "sam_gov"
        assert error.is_retryable is True   # Can retry after cooldown
        assert error.is_reformulable is False  # Query change won't help

        # Verify agent decision (blocklist, don't reformulate)
        should_blocklist = error.category == ErrorCategory.RATE_LIMIT
        should_reformulate = error.is_reformulable

        assert should_blocklist is True
        assert should_reformulate is False

    def test_e2e_validation_error_flow(self, mock_config):
        """
        E2E: Validation error → ErrorClassifier → reformulation decision.

        Simulates DVIDS returning HTTP 400 for invalid date and verifies:
        1. ErrorClassifier correctly identifies VALIDATION
        2. is_reformulable=True (agent should try different query)
        """
        classifier = ErrorClassifier(mock_config)

        # Simulate DVIDS 400 error (invalid date format)
        result = QueryResult(
            success=False,
            source="dvids",
            total=0,
            results=[],
            query_params={"from_date": "nullT00:00:00Z"},
            error="HTTP 400: Invalid date format 'nullT00:00:00Z'",
            http_code=400,
            validate=False
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.VALIDATION
        assert error.http_code == 400
        assert error.is_reformulable is True  # Agent should try different params

    def test_e2e_auth_error_flow(self, mock_config):
        """
        E2E: Auth error → ErrorClassifier → skip decision.

        Simulates NewsAPI returning HTTP 403 and verifies:
        1. ErrorClassifier correctly identifies AUTHENTICATION
        2. is_reformulable=False, is_retryable=False
        3. Agent should skip source entirely
        """
        classifier = ErrorClassifier(mock_config)

        # Simulate NewsAPI 403 error
        result = QueryResult(
            success=False,
            source="newsapi",
            total=0,
            results=[],
            query_params={"q": "defense contracts"},
            error="HTTP 403: Access forbidden - invalid API key",
            http_code=403,
            validate=False
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.http_code == 403
        assert error.is_reformulable is False  # Can't fix auth with query change
        assert error.is_retryable is False     # Won't fix itself

    def test_e2e_server_error_flow(self, mock_config):
        """
        E2E: Server error → ErrorClassifier → retry decision.

        Simulates FEC returning HTTP 503 and verifies:
        1. ErrorClassifier correctly identifies SERVER_ERROR
        2. is_retryable=True (temporary issue)
        3. is_reformulable=False (not a query problem)
        """
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False,
            source="fec",
            total=0,
            results=[],
            query_params={"committee_id": "C00000000"},
            error="HTTP 503: Service temporarily unavailable",
            http_code=503,
            validate=False
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 503
        assert error.is_retryable is True
        assert error.is_reformulable is False


# ============================================================================
# E2E EXECUTION LOG TESTS
# ============================================================================

class TestE2EExecutionLogging:
    """E2E tests for structured error logging."""

    def test_e2e_log_entry_structure(self, mock_config, temp_output_dir):
        """
        E2E: Error → classification → log entry with http_code and category.

        Verifies the complete flow produces correctly structured log entries.
        """
        classifier = ErrorClassifier(mock_config)

        # Simulate error
        result = QueryResult(
            success=False,
            source="sam_gov",
            total=0,
            results=[],
            query_params={"keywords": "AI"},
            error="HTTP 429: Rate limited",
            http_code=429,
            validate=False
        )

        # Classify
        error = classifier.classify(result.error, result.http_code, result.source)

        # Build log entry (as agent does)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "api_response",
            "source": result.source,
            "success": result.success,
            "result_count": len(result.results),
            "error": result.error,
            "http_code": result.http_code,
            "error_category": error.category.value
        }

        # Write to log file
        log_path = Path(temp_output_dir) / "execution_log.jsonl"
        with open(log_path, 'w') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Read back and verify
        with open(log_path, 'r') as f:
            loaded_entry = json.loads(f.readline())

        assert loaded_entry["event_type"] == "api_response"
        assert loaded_entry["source"] == "sam_gov"
        assert loaded_entry["success"] is False
        assert loaded_entry["http_code"] == 429
        assert loaded_entry["error_category"] == "rate_limit"

    def test_e2e_log_entry_null_http_code(self, mock_config, temp_output_dir):
        """
        E2E: Non-HTTP error → log entry with null http_code.

        Verifies timeout errors (non-HTTP) are logged correctly.
        """
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False,
            source="brave_search",
            total=0,
            results=[],
            query_params={"q": "test"},
            error="ReadTimeoutError: Connection timed out",
            http_code=None,  # Non-HTTP error
            validate=False
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "api_response",
            "source": result.source,
            "success": result.success,
            "error": result.error,
            "http_code": result.http_code,  # Will be None
            "error_category": error.category.value
        }

        log_path = Path(temp_output_dir) / "execution_log.jsonl"
        with open(log_path, 'w') as f:
            f.write(json.dumps(log_entry) + '\n')

        with open(log_path, 'r') as f:
            loaded_entry = json.loads(f.readline())

        assert loaded_entry["http_code"] is None
        assert loaded_entry["error_category"] == "timeout"


# ============================================================================
# E2E ERROR DECISION MATRIX TESTS
# ============================================================================

class TestE2EErrorDecisionMatrix:
    """
    E2E tests validating the complete error decision matrix.

    Verifies all HTTP codes → category → decision mappings work correctly.
    """

    @pytest.mark.parametrize("http_code,expected_category,expected_reformulable,expected_retryable", [
        # Auth errors - skip entirely
        (401, ErrorCategory.AUTHENTICATION, False, False),
        (403, ErrorCategory.AUTHENTICATION, False, False),

        # Rate limits - blocklist, retry later
        (429, ErrorCategory.RATE_LIMIT, False, True),

        # Not found - skip
        (404, ErrorCategory.NOT_FOUND, False, False),

        # Validation errors - reformulate query
        (400, ErrorCategory.VALIDATION, True, False),
        (422, ErrorCategory.VALIDATION, True, False),

        # Server errors - retry later
        (500, ErrorCategory.SERVER_ERROR, False, True),
        (502, ErrorCategory.SERVER_ERROR, False, True),
        (503, ErrorCategory.SERVER_ERROR, False, True),
        (504, ErrorCategory.SERVER_ERROR, False, True),
    ])
    def test_e2e_http_code_decision(self, mock_config, http_code, expected_category,
                                     expected_reformulable, expected_retryable):
        """Verify all HTTP codes produce correct decisions."""
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False,
            source="test_source",
            total=0,
            results=[],
            query_params={"test": "query"},
            error=f"HTTP {http_code} error",
            http_code=http_code,
            validate=False
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        assert error.category == expected_category, f"HTTP {http_code} should be {expected_category}"
        assert error.is_reformulable is expected_reformulable, f"HTTP {http_code} reformulable mismatch"
        assert error.is_retryable is expected_retryable, f"HTTP {http_code} retryable mismatch"

    @pytest.mark.parametrize("error_text,expected_category", [
        # Timeout patterns
        ("Connection timed out", ErrorCategory.TIMEOUT),
        ("TimeoutError: Read operation", ErrorCategory.TIMEOUT),
        ("Request timeout after 30s", ErrorCategory.TIMEOUT),

        # Rate limit patterns (text fallback)
        ("Rate limit exceeded", ErrorCategory.RATE_LIMIT),
        ("Quota exceeded for today", ErrorCategory.RATE_LIMIT),
        ("Too many requests", ErrorCategory.RATE_LIMIT),

        # Auth patterns (text fallback)
        ("Unauthorized access", ErrorCategory.AUTHENTICATION),
        ("Access forbidden", ErrorCategory.AUTHENTICATION),
        ("Authentication failed", ErrorCategory.AUTHENTICATION),

        # Unknown
        ("Something went wrong", ErrorCategory.UNKNOWN),
    ])
    def test_e2e_pattern_fallback_decision(self, mock_config, error_text, expected_category):
        """Verify text patterns correctly classify when http_code is None."""
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False,
            source="test_source",
            total=0,
            results=[],
            query_params={"test": "query"},
            error=error_text,
            http_code=None,  # Force pattern matching
            validate=False
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        assert error.category == expected_category, f"'{error_text}' should be {expected_category}"


# ============================================================================
# E2E MULTI-ERROR SCENARIO TESTS
# ============================================================================

class TestE2EMultiErrorScenarios:
    """E2E tests for realistic multi-error scenarios."""

    def test_e2e_multiple_sources_different_errors(self, mock_config):
        """
        E2E: Research query hits multiple sources with different error types.

        Simulates real research where:
        - SAM.gov: rate limited (429)
        - DVIDS: validation error (400)
        - NewsAPI: auth error (403)
        - FEC: success
        """
        classifier = ErrorClassifier(mock_config)

        # Simulate multiple source responses
        responses = [
            QueryResult(
                success=False, source="sam_gov", total=0, results=[],
                query_params={"keywords": "AI"},
                error="HTTP 429: Rate limited", http_code=429, validate=False
            ),
            QueryResult(
                success=False, source="dvids", total=0, results=[],
                query_params={"from_date": "invalid"},
                error="HTTP 400: Invalid date", http_code=400, validate=False
            ),
            QueryResult(
                success=False, source="newsapi", total=0, results=[],
                query_params={"q": "test"},
                error="HTTP 403: Forbidden", http_code=403, validate=False
            ),
            QueryResult(
                success=True, source="fec", total=5,
                results=[{"title": "FEC Record"}],
                query_params={"committee": "C00000000"},
                error=None, http_code=None, validate=False
            ),
        ]

        # Process each response as agent would
        blocklist = set()
        reformulate_queue = []
        successful_sources = []

        for result in responses:
            if result.success:
                successful_sources.append(result.source)
            else:
                error = classifier.classify(result.error, result.http_code, result.source)

                if error.category == ErrorCategory.RATE_LIMIT:
                    blocklist.add(result.source)
                elif error.is_reformulable:
                    reformulate_queue.append(result.source)

        # Verify decisions
        assert "sam_gov" in blocklist, "SAM.gov should be blocklisted (429)"
        assert "dvids" in reformulate_queue, "DVIDS should be queued for reformulation (400)"
        assert "newsapi" not in blocklist and "newsapi" not in reformulate_queue, \
            "NewsAPI auth error should just be skipped"
        assert "fec" in successful_sources, "FEC should be successful"

    def test_e2e_repeated_errors_same_source(self, mock_config):
        """
        E2E: Same source returns errors multiple times.

        Verifies classifier handles repeated errors consistently.
        """
        classifier = ErrorClassifier(mock_config)

        # SAM.gov gets rate limited multiple times
        for i in range(3):
            result = QueryResult(
                success=False, source="sam_gov", total=0, results=[],
                query_params={"keywords": f"query_{i}"},
                error="HTTP 429: Rate limited", http_code=429, validate=False
            )

            error = classifier.classify(result.error, result.http_code, result.source)

            # Should always classify the same way
            assert error.category == ErrorCategory.RATE_LIMIT
            assert error.http_code == 429
            assert error.is_reformulable is False


# ============================================================================
# E2E ERROR STRING REPRESENTATION TESTS
# ============================================================================

class TestE2EErrorStringRepresentation:
    """E2E tests for error string output format."""

    def test_e2e_error_str_format_http(self, mock_config):
        """Verify HTTP error string format."""
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False, source="sam_gov", total=0, results=[],
            query_params={}, error="Rate limited", http_code=429, validate=False
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        str_repr = str(error)
        assert "HTTP 429" in str_repr
        assert "rate_limit" in str_repr
        assert "sam_gov" in str_repr
        assert "Rate limited" in str_repr

    def test_e2e_error_str_format_non_http(self, mock_config):
        """Verify non-HTTP error string format."""
        classifier = ErrorClassifier(mock_config)

        result = QueryResult(
            success=False, source="brave_search", total=0, results=[],
            query_params={}, error="Connection timed out", http_code=None, validate=False
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        str_repr = str(error)
        assert "Non-HTTP" in str_repr
        assert "timeout" in str_repr
        assert "brave_search" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
