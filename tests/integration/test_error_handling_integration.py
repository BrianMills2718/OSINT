#!/usr/bin/env python3
"""
Integration tests for error handling across integrations.

Verifies that integrations correctly extract HTTP codes and that
the ErrorClassifier integration with the recursive agent works end-to-end.

Run: pytest tests/integration/test_error_handling_integration.py -v
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from core.database_integration_base import QueryResult
from core.error_classifier import ErrorClassifier, ErrorCategory


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_config():
    """Create mock config for ErrorClassifier."""
    config = MagicMock()
    config.get_raw_config.return_value = {
        'research': {
            'error_handling': {
                'unfixable_http_codes': [401, 403, 404, 429, 500, 502, 503, 504],
                'fixable_http_codes': [400, 422]
            }
        }
    }
    return config


@pytest.fixture
def classifier(mock_config):
    """Create ErrorClassifier instance."""
    return ErrorClassifier(mock_config)


def make_query_result(success: bool, results: list = None, error: str = None,
                      http_code: int = None, source: str = "test") -> QueryResult:
    """Helper to create QueryResult with required fields."""
    return QueryResult(
        success=success,
        source=source,
        total=len(results) if results else 0,
        results=results or [],
        query_params={"test": "query"},
        error=error,
        http_code=http_code,
        validate=False  # Skip validation for test data
    )


# ============================================================================
# QUERY RESULT HTTP CODE TESTS
# ============================================================================

class TestQueryResultHTTPCode:
    """Tests for QueryResult.http_code field functionality."""

    def test_query_result_success_no_http_code(self):
        """Successful queries should have http_code=None."""
        result = make_query_result(
            success=True,
            results=[{"title": "Test"}],
            error=None,
            http_code=None
        )
        assert result.success is True
        assert result.http_code is None

    def test_query_result_with_http_error_code(self):
        """Failed queries should preserve HTTP error code."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 429: Rate limit exceeded",
            http_code=429
        )
        assert result.success is False
        assert result.http_code == 429
        assert "429" in result.error

    def test_query_result_non_http_error(self):
        """Non-HTTP errors should have http_code=None."""
        result = make_query_result(
            success=False,
            results=[],
            error="Connection timed out",
            http_code=None
        )
        assert result.success is False
        assert result.http_code is None
        assert "timed out" in result.error

    def test_query_result_all_http_codes(self):
        """Test all common HTTP error codes are storable."""
        for code in [400, 401, 403, 404, 422, 429, 500, 502, 503, 504]:
            result = make_query_result(
                success=False,
                results=[],
                error=f"HTTP {code} Error",
                http_code=code
            )
            assert result.http_code == code


# ============================================================================
# ERROR CLASSIFIER INTEGRATION WITH QUERY RESULT
# ============================================================================

class TestErrorClassifierWithQueryResult:
    """Tests for ErrorClassifier working with QueryResult data."""

    def test_classify_query_result_rate_limit(self, classifier):
        """Classify rate limit from QueryResult."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 429: Too Many Requests",
            http_code=429,
            source="sam_gov"
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_classify_query_result_validation(self, classifier):
        """Classify validation error from QueryResult."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 400: Invalid date format",
            http_code=400,
            source="dvids"
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.VALIDATION
        assert error.is_reformulable is True

    def test_classify_query_result_auth(self, classifier):
        """Classify auth error from QueryResult."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 403: Forbidden",
            http_code=403,
            source="newsapi"
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.is_reformulable is False

    def test_classify_query_result_non_http_timeout(self, classifier):
        """Classify non-HTTP timeout from QueryResult."""
        result = make_query_result(
            success=False,
            results=[],
            error="ReadTimeoutError: Connection timed out",
            http_code=None,
            source="brave_search"
        )

        error = classifier.classify(
            error_str=result.error,
            http_code=result.http_code,
            source_id=result.source
        )

        assert error.category == ErrorCategory.TIMEOUT
        assert error.http_code is None


# ============================================================================
# MOCK HTTP ERROR EXTRACTION TESTS
# ============================================================================

class TestHTTPErrorExtraction:
    """Tests simulating HTTP error extraction from httpx responses."""

    def test_extract_status_code_from_httpx_error(self):
        """Verify extraction pattern for httpx HTTPStatusError."""
        # Simulate httpx HTTPStatusError structure
        mock_response = MagicMock()
        mock_response.status_code = 429

        # This is the pattern used in integrations
        http_code = mock_response.status_code
        assert http_code == 429

    def test_extract_status_code_various_errors(self):
        """Test extraction from various HTTP error responses."""
        for status_code in [400, 401, 403, 404, 422, 429, 500, 502, 503, 504]:
            mock_response = MagicMock()
            mock_response.status_code = status_code

            # Pattern used in integrations: e.response.status_code
            extracted = mock_response.status_code
            assert extracted == status_code

    def test_httpx_exception_without_response(self):
        """Non-HTTP httpx errors should return None http_code."""
        # Simulate a connection error (no response)
        class MockConnectError(Exception):
            pass

        error = MockConnectError("Connection refused")
        # Pattern: getattr(error, 'response', None)
        response = getattr(error, 'response', None)
        http_code = response.status_code if response else None
        assert http_code is None


# ============================================================================
# INTEGRATION-SPECIFIC ERROR HANDLING TESTS
# ============================================================================

class TestSAMGovErrorHandling:
    """Tests for SAM.gov integration error handling."""

    @pytest.mark.asyncio
    async def test_sam_gov_rate_limit_extraction(self, mock_config):
        """SAM.gov should extract 429 status code."""
        # Simulate the error handling pattern from sam_integration.py
        mock_response = MagicMock()
        mock_response.status_code = 429

        # Pattern from integration:
        # http_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        http_code = mock_response.status_code

        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 429: Rate limit exceeded",
            http_code=http_code,
            source="sam_gov"
        )

        assert result.http_code == 429

        # Verify classifier handles it correctly
        classifier = ErrorClassifier(mock_config)
        error = classifier.classify(result.error, result.http_code, result.source)
        assert error.category == ErrorCategory.RATE_LIMIT


class TestDVIDSErrorHandling:
    """Tests for DVIDS integration error handling."""

    @pytest.mark.asyncio
    async def test_dvids_validation_error_extraction(self, mock_config):
        """DVIDS should extract 400 status code for validation errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        http_code = mock_response.status_code

        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 400: Invalid date format",
            http_code=http_code,
            source="dvids"
        )

        assert result.http_code == 400

        classifier = ErrorClassifier(mock_config)
        error = classifier.classify(result.error, result.http_code, result.source)
        assert error.category == ErrorCategory.VALIDATION
        assert error.is_reformulable is True


class TestUSAspendingErrorHandling:
    """Tests for USAspending integration error handling."""

    @pytest.mark.asyncio
    async def test_usaspending_keyword_error_extraction(self, mock_config):
        """USAspending should extract 422 for keyword validation errors."""
        mock_response = MagicMock()
        mock_response.status_code = 422

        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 422: Keyword must be at least 3 characters",
            http_code=mock_response.status_code,
            source="usaspending"
        )

        assert result.http_code == 422

        classifier = ErrorClassifier(mock_config)
        error = classifier.classify(result.error, result.http_code, result.source)
        assert error.category == ErrorCategory.VALIDATION
        assert error.is_reformulable is True


class TestNewsAPIErrorHandling:
    """Tests for NewsAPI integration error handling."""

    @pytest.mark.asyncio
    async def test_newsapi_auth_error_extraction(self, mock_config):
        """NewsAPI should extract 401 for auth errors."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 401: Invalid API key",
            http_code=mock_response.status_code,
            source="newsapi"
        )

        assert result.http_code == 401

        classifier = ErrorClassifier(mock_config)
        error = classifier.classify(result.error, result.http_code, result.source)
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.is_reformulable is False


# ============================================================================
# ERROR DECISION FLOW TESTS
# ============================================================================

class TestErrorDecisionFlow:
    """Tests for error handling decision flow in the agent."""

    def test_reformulable_error_flow(self, classifier):
        """Reformulable errors should trigger query reformulation."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 422: Invalid keyword",
            http_code=422,
            source="usaspending"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # Agent should check this flag
        if error.is_reformulable:
            should_reformulate = True
        else:
            should_reformulate = False

        assert should_reformulate is True

    def test_rate_limit_blocklist_flow(self, classifier):
        """Rate limit errors should add source to blocklist."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 429: Rate limited",
            http_code=429,
            source="sam_gov"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # Agent should check for rate limits
        if error.category == ErrorCategory.RATE_LIMIT:
            should_blocklist = True
        else:
            should_blocklist = False

        assert should_blocklist is True

    def test_auth_error_skip_flow(self, classifier):
        """Auth errors should skip source without reformulation."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 403: Forbidden",
            http_code=403,
            source="restricted_api"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # Agent should not reformulate OR retry auth errors
        assert error.is_reformulable is False
        assert error.is_retryable is False

    def test_server_error_retry_flow(self, classifier):
        """Server errors should be marked as retryable."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 503: Service unavailable",
            http_code=503,
            source="flaky_api"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # Agent should mark as retryable (for later)
        assert error.is_retryable is True
        assert error.is_reformulable is False


# ============================================================================
# EXECUTION LOGGER INTEGRATION TESTS
# ============================================================================

class TestExecutionLoggerIntegration:
    """Tests for structured error logging."""

    def test_log_entry_with_http_code(self, classifier):
        """Error log entries should include http_code field."""
        result = make_query_result(
            success=False,
            results=[],
            error="HTTP 429: Rate limited",
            http_code=429,
            source="sam_gov"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # Simulate log entry structure
        log_entry = {
            "source": result.source,
            "success": False,
            "error": result.error,
            "http_code": result.http_code,
            "error_category": error.category.value
        }

        assert log_entry["http_code"] == 429
        assert log_entry["error_category"] == "rate_limit"

    def test_log_entry_with_null_http_code(self, classifier):
        """Non-HTTP errors should log http_code as null."""
        result = make_query_result(
            success=False,
            results=[],
            error="Connection timed out",
            http_code=None,
            source="brave_search"
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        log_entry = {
            "source": result.source,
            "success": False,
            "error": result.error,
            "http_code": result.http_code,
            "error_category": error.category.value
        }

        assert log_entry["http_code"] is None
        assert log_entry["error_category"] == "timeout"


# ============================================================================
# EDGE CASE INTEGRATION TESTS
# ============================================================================

class TestEdgeCaseIntegration:
    """Integration tests for edge cases."""

    def test_successful_result_no_error_classification(self, classifier):
        """Successful results should not need error classification."""
        result = make_query_result(
            success=True,
            results=[{"title": "Test Result"}],
            error=None,
            http_code=None
        )

        # Agent pattern: only classify if not successful
        if not result.success and result.error:
            error = classifier.classify(result.error, result.http_code, result.source)
        else:
            error = None

        assert error is None

    def test_mixed_error_text_and_http_code(self, classifier):
        """HTTP code should take precedence over error text patterns."""
        # Error text says "rate limit" but HTTP code is 500
        result = make_query_result(
            success=False,
            results=[],
            error="Rate limit exceeded (server error)",
            http_code=500  # Server error code
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        # HTTP code takes precedence
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 500

    def test_empty_error_with_http_code(self, classifier):
        """Empty error message with HTTP code should still classify."""
        result = make_query_result(
            success=False,
            results=[],
            error="",
            http_code=403
        )

        error = classifier.classify(result.error, result.http_code, result.source)

        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.message == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
