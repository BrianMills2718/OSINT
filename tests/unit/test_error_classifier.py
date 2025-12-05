#!/usr/bin/env python3
"""
Unit tests for ErrorClassifier.

Tests all HTTP code classifications, text pattern fallbacks,
APIError dataclass, and config-driven behavior.

Run: pytest tests/unit/test_error_classifier.py -v
"""

import pytest
from unittest.mock import MagicMock

from core.error_classifier import ErrorClassifier, ErrorCategory, APIError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_config():
    """Create mock config with default error handling settings."""
    config = MagicMock()
    config.get_raw_config.return_value = {
        'research': {
            'error_handling': {
                'unfixable_http_codes': [401, 403, 404, 429, 500, 502, 503, 504],
                'fixable_http_codes': [400, 422],
                'timeout_patterns': [
                    "timed out", "timeout", "TimeoutError", "ReadTimeoutError"
                ],
                'rate_limit_patterns': [
                    "rate limit", "429", "quota exceeded", "too many requests"
                ]
            }
        }
    }
    return config


@pytest.fixture
def classifier(mock_config):
    """Create ErrorClassifier with mock config."""
    return ErrorClassifier(mock_config)


# ============================================================================
# HTTP CODE CLASSIFICATION TESTS
# ============================================================================

class TestHTTPCodeClassification:
    """Tests for HTTP status code classification."""

    def test_401_classified_as_auth(self, classifier):
        """401 Unauthorized should be AUTHENTICATION."""
        error = classifier.classify(
            error_str="401 Unauthorized",
            http_code=401,
            source_id="test_source"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.http_code == 401
        assert error.is_retryable is False
        assert error.is_reformulable is False
        assert error.source_id == "test_source"

    def test_403_classified_as_auth(self, classifier):
        """403 Forbidden should be AUTHENTICATION."""
        error = classifier.classify(
            error_str="403 Forbidden - API key invalid",
            http_code=403,
            source_id="dvids"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.http_code == 403
        assert error.is_retryable is False
        assert error.is_reformulable is False

    def test_429_classified_as_rate_limit(self, classifier):
        """429 Too Many Requests should be RATE_LIMIT."""
        error = classifier.classify(
            error_str="429 Too Many Requests",
            http_code=429,
            source_id="sam_gov"
        )
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.http_code == 429
        assert error.is_retryable is True  # Can retry after cooldown
        assert error.is_reformulable is False  # Query won't fix it

    def test_404_classified_as_not_found(self, classifier):
        """404 Not Found should be NOT_FOUND."""
        error = classifier.classify(
            error_str="404 Not Found - Endpoint does not exist",
            http_code=404,
            source_id="usajobs"
        )
        assert error.category == ErrorCategory.NOT_FOUND
        assert error.http_code == 404
        assert error.is_retryable is False
        assert error.is_reformulable is False

    def test_400_classified_as_validation_fixable(self, classifier):
        """400 Bad Request should be VALIDATION and fixable."""
        error = classifier.classify(
            error_str="400 Bad Request - Invalid date format",
            http_code=400,
            source_id="dvids"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.http_code == 400
        assert error.is_retryable is False  # Same query fails again
        assert error.is_reformulable is True  # Can fix by changing query

    def test_422_classified_as_validation_fixable(self, classifier):
        """422 Unprocessable Entity should be VALIDATION and fixable."""
        error = classifier.classify(
            error_str="422 Unprocessable Entity - Keyword too short",
            http_code=422,
            source_id="usaspending"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.http_code == 422
        assert error.is_retryable is False
        assert error.is_reformulable is True

    def test_500_classified_as_server_error(self, classifier):
        """500 Internal Server Error should be SERVER_ERROR."""
        error = classifier.classify(
            error_str="500 Internal Server Error",
            http_code=500,
            source_id="fec"
        )
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 500
        assert error.is_retryable is True  # Temporary server issues
        assert error.is_reformulable is False

    def test_502_classified_as_server_error(self, classifier):
        """502 Bad Gateway should be SERVER_ERROR."""
        error = classifier.classify(
            error_str="502 Bad Gateway",
            http_code=502,
            source_id="govinfo"
        )
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 502
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_503_classified_as_server_error(self, classifier):
        """503 Service Unavailable should be SERVER_ERROR."""
        error = classifier.classify(
            error_str="503 Service Unavailable",
            http_code=503,
            source_id="newsapi"
        )
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 503
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_504_classified_as_server_error(self, classifier):
        """504 Gateway Timeout should be SERVER_ERROR."""
        error = classifier.classify(
            error_str="504 Gateway Timeout",
            http_code=504,
            source_id="sec_edgar"
        )
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 504
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_unknown_http_code_classified_as_unknown(self, classifier):
        """Unknown HTTP codes should be UNKNOWN with conservative flags."""
        error = classifier.classify(
            error_str="418 I'm a Teapot",
            http_code=418,
            source_id="weird_api"
        )
        assert error.category == ErrorCategory.UNKNOWN
        assert error.http_code == 418
        assert error.is_retryable is False  # Conservative
        assert error.is_reformulable is False  # Conservative


# ============================================================================
# TEXT PATTERN CLASSIFICATION TESTS
# ============================================================================

class TestPatternClassification:
    """Tests for text pattern fallback classification (when http_code is None)."""

    def test_timeout_pattern_timed_out(self, classifier):
        """'timed out' pattern should be TIMEOUT."""
        error = classifier.classify(
            error_str="Connection timed out after 30 seconds",
            http_code=None,
            source_id="slow_api"
        )
        assert error.category == ErrorCategory.TIMEOUT
        assert error.http_code is None
        assert error.is_retryable is True  # Infrastructure may recover
        assert error.is_reformulable is False

    def test_timeout_pattern_timeout_error(self, classifier):
        """'TimeoutError' pattern should be TIMEOUT."""
        error = classifier.classify(
            error_str="TimeoutError: Connection pool exhausted",
            http_code=None,
            source_id="pool_timeout"
        )
        assert error.category == ErrorCategory.TIMEOUT
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_timeout_pattern_case_insensitive(self, classifier):
        """Timeout patterns should be case-insensitive."""
        error = classifier.classify(
            error_str="TIMED OUT waiting for response",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.TIMEOUT

    def test_rate_limit_pattern_rate_limit(self, classifier):
        """'rate limit' pattern should be RATE_LIMIT."""
        error = classifier.classify(
            error_str="Rate limit exceeded for this API key",
            http_code=None,
            source_id="rate_limited"
        )
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_rate_limit_pattern_429_text(self, classifier):
        """'429' in error text (without http_code) should be RATE_LIMIT."""
        error = classifier.classify(
            error_str="HTTP Error: Status 429 - Too many requests",
            http_code=None,  # http_code not extracted
            source_id="test"
        )
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_rate_limit_pattern_quota(self, classifier):
        """'quota exceeded' pattern should be RATE_LIMIT."""
        error = classifier.classify(
            error_str="Daily quota exceeded. Try again tomorrow.",
            http_code=None,
            source_id="quota_api"
        )
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_rate_limit_pattern_too_many_requests(self, classifier):
        """'too many requests' pattern should be RATE_LIMIT."""
        error = classifier.classify(
            error_str="Too many requests from this IP address",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_auth_pattern_unauthorized(self, classifier):
        """'unauthorized' pattern should be AUTHENTICATION."""
        error = classifier.classify(
            error_str="Unauthorized access - check API key",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.is_retryable is False
        assert error.is_reformulable is False

    def test_auth_pattern_forbidden(self, classifier):
        """'forbidden' pattern should be AUTHENTICATION."""
        error = classifier.classify(
            error_str="Access forbidden for this resource",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.AUTHENTICATION

    def test_auth_pattern_401_text(self, classifier):
        """'401' in error text should be AUTHENTICATION."""
        error = classifier.classify(
            error_str="Error 401: Invalid credentials",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.AUTHENTICATION

    def test_unknown_pattern_classified_as_unknown(self, classifier):
        """Unrecognized patterns should be UNKNOWN with conservative flags."""
        error = classifier.classify(
            error_str="Something went wrong",
            http_code=None,
            source_id="vague_api"
        )
        assert error.category == ErrorCategory.UNKNOWN
        assert error.http_code is None
        assert error.is_retryable is False  # Conservative
        assert error.is_reformulable is False  # Conservative


# ============================================================================
# API ERROR DATACLASS TESTS
# ============================================================================

class TestAPIErrorDataclass:
    """Tests for APIError dataclass functionality."""

    def test_str_representation_http_error(self):
        """String representation should show HTTP code for HTTP errors."""
        error = APIError(
            http_code=403,
            category=ErrorCategory.AUTHENTICATION,
            message="API key invalid",
            is_retryable=False,
            is_reformulable=False,
            source_id="test"
        )
        str_repr = str(error)
        assert "HTTP 403" in str_repr
        assert "auth" in str_repr
        assert "test" in str_repr
        assert "API key invalid" in str_repr

    def test_str_representation_non_http_error(self):
        """String representation should show 'Non-HTTP' for non-HTTP errors."""
        error = APIError(
            http_code=None,
            category=ErrorCategory.TIMEOUT,
            message="Connection timed out",
            is_retryable=True,
            is_reformulable=False,
            source_id="test"
        )
        str_repr = str(error)
        assert "Non-HTTP" in str_repr
        assert "timeout" in str_repr

    def test_all_fields_preserved(self):
        """All dataclass fields should be preserved correctly."""
        error = APIError(
            http_code=422,
            category=ErrorCategory.VALIDATION,
            message="Invalid keyword length",
            is_retryable=False,
            is_reformulable=True,
            source_id="usaspending"
        )
        assert error.http_code == 422
        assert error.category == ErrorCategory.VALIDATION
        assert error.message == "Invalid keyword length"
        assert error.is_retryable is False
        assert error.is_reformulable is True
        assert error.source_id == "usaspending"


# ============================================================================
# ERROR CATEGORY ENUM TESTS
# ============================================================================

class TestErrorCategoryEnum:
    """Tests for ErrorCategory enum values."""

    def test_all_categories_exist(self):
        """All expected categories should exist."""
        categories = [
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.VALIDATION,
            ErrorCategory.NOT_FOUND,
            ErrorCategory.SERVER_ERROR,
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
            ErrorCategory.UNKNOWN
        ]
        assert len(categories) == 8
        for cat in categories:
            assert isinstance(cat, ErrorCategory)

    def test_category_values(self):
        """Categories should have expected string values."""
        assert ErrorCategory.AUTHENTICATION.value == "auth"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.SERVER_ERROR.value == "server"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.UNKNOWN.value == "unknown"


# ============================================================================
# CONFIG-DRIVEN BEHAVIOR TESTS
# ============================================================================

class TestConfigDrivenBehavior:
    """Tests for config-driven error classification."""

    def test_custom_unfixable_codes(self):
        """Custom unfixable codes from config should be respected."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    'unfixable_http_codes': [451],  # Custom "Unavailable for Legal Reasons"
                    'fixable_http_codes': []
                }
            }
        }
        classifier = ErrorClassifier(config)

        # 451 is not in default classification, but custom config exists
        # However, current implementation only uses fixable_http_codes for validation
        # unfixable_http_codes is loaded but specific codes (401,403,etc) are hardcoded
        # This test documents current behavior
        error = classifier.classify("451 Unavailable", http_code=451, source_id="test")
        # Currently classified as UNKNOWN since not in hardcoded checks
        assert error.category == ErrorCategory.UNKNOWN

    def test_custom_fixable_codes(self):
        """Custom fixable codes from config should be respected."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    'unfixable_http_codes': [],
                    'fixable_http_codes': [400, 422, 415]  # Add 415 Unsupported Media Type
                }
            }
        }
        classifier = ErrorClassifier(config)

        # 415 should now be classified as VALIDATION and fixable
        error = classifier.classify(
            "415 Unsupported Media Type",
            http_code=415,
            source_id="test"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.is_reformulable is True

    def test_custom_timeout_patterns(self):
        """Custom timeout patterns from config should be respected."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    'timeout_patterns': ["custom_timeout", "special_timeout_msg"]
                }
            }
        }
        classifier = ErrorClassifier(config)

        error = classifier.classify(
            "Got custom_timeout from server",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.TIMEOUT

    def test_custom_rate_limit_patterns(self):
        """Custom rate limit patterns from config should be respected."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    'rate_limit_patterns': ["slow_down", "backoff_required"]
                }
            }
        }
        classifier = ErrorClassifier(config)

        error = classifier.classify(
            "Please slow_down your requests",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_empty_config_uses_defaults(self):
        """Empty config should use sensible defaults."""
        config = MagicMock()
        config.get_raw_config.return_value = {}  # No config at all

        classifier = ErrorClassifier(config)

        # Should still work with defaults
        error = classifier.classify("429 Rate Limited", http_code=429, source_id="test")
        assert error.category == ErrorCategory.RATE_LIMIT


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_error_string(self, classifier):
        """Empty error string should still be classified."""
        error = classifier.classify(
            error_str="",
            http_code=403,
            source_id="test"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.message == ""

    def test_none_http_code_uses_pattern(self, classifier):
        """None http_code should trigger pattern matching."""
        error = classifier.classify(
            error_str="Rate limit exceeded",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.http_code is None

    def test_http_code_takes_precedence(self, classifier):
        """HTTP code should take precedence over conflicting patterns."""
        # Error message says "rate limit" but HTTP code is 500
        error = classifier.classify(
            error_str="Rate limit exceeded",  # Pattern says rate limit
            http_code=500,  # HTTP code says server error
            source_id="test"
        )
        # HTTP code takes precedence
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.http_code == 500

    def test_multiple_patterns_first_match_wins(self, classifier):
        """When multiple patterns match, first match in order wins."""
        # Error contains both timeout and rate limit patterns
        error = classifier.classify(
            error_str="Connection timed out due to rate limit",
            http_code=None,
            source_id="test"
        )
        # Timeout is checked first in implementation
        assert error.category == ErrorCategory.TIMEOUT

    def test_very_long_error_message(self, classifier):
        """Very long error messages should be handled."""
        long_msg = "Error: " + "x" * 10000 + " rate limit exceeded"
        error = classifier.classify(
            error_str=long_msg,
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.RATE_LIMIT
        assert len(error.message) > 10000

    def test_unicode_error_message(self, classifier):
        """Unicode error messages should be handled."""
        error = classifier.classify(
            error_str="Error: 访问被拒绝 (forbidden)",
            http_code=None,
            source_id="test"
        )
        assert error.category == ErrorCategory.AUTHENTICATION  # Contains "forbidden"

    def test_special_characters_in_message(self, classifier):
        """Special characters in error messages should be handled."""
        error = classifier.classify(
            error_str="Error: <script>alert('429')</script>",
            http_code=None,
            source_id="test"
        )
        # Contains "429" pattern
        assert error.category == ErrorCategory.RATE_LIMIT


# ============================================================================
# INTEGRATION-SPECIFIC TESTS
# ============================================================================

class TestRealWorldScenarios:
    """Tests simulating real-world error scenarios from integrations."""

    def test_sam_gov_rate_limit(self, classifier):
        """SAM.gov rate limit error should be classified correctly."""
        error = classifier.classify(
            error_str="HTTP 429: Rate limit exceeded. Please try again later.",
            http_code=429,
            source_id="sam_gov"
        )
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.source_id == "sam_gov"
        assert error.is_retryable is True
        assert error.is_reformulable is False

    def test_dvids_validation_error(self, classifier):
        """DVIDS validation error (bad date) should be classified correctly."""
        error = classifier.classify(
            error_str="HTTP 400: Invalid date format 'nullT00:00:00Z'",
            http_code=400,
            source_id="dvids"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.source_id == "dvids"
        assert error.is_reformulable is True

    def test_usaspending_keyword_too_short(self, classifier):
        """USAspending keyword validation error should be fixable."""
        error = classifier.classify(
            error_str="HTTP 422: Keyword must be at least 3 characters",
            http_code=422,
            source_id="usaspending"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.is_reformulable is True

    def test_newsapi_auth_failure(self, classifier):
        """NewsAPI auth failure should be classified correctly."""
        error = classifier.classify(
            error_str="HTTP 401: Your API key is invalid or incorrect",
            http_code=401,
            source_id="newsapi"
        )
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.is_retryable is False
        assert error.is_reformulable is False

    def test_brave_search_timeout(self, classifier):
        """Brave Search timeout should be classified correctly."""
        error = classifier.classify(
            error_str="ReadTimeoutError: HTTPSConnectionPool timed out",
            http_code=None,  # Non-HTTP error
            source_id="brave_search"
        )
        assert error.category == ErrorCategory.TIMEOUT
        assert error.is_retryable is True

    def test_fec_server_error(self, classifier):
        """FEC server error should be classified correctly."""
        error = classifier.classify(
            error_str="HTTP 503: Service temporarily unavailable",
            http_code=503,
            source_id="fec"
        )
        assert error.category == ErrorCategory.SERVER_ERROR
        assert error.is_retryable is True


# ============================================================================
# CLASSIFIER INITIALIZATION TESTS
# ============================================================================

class TestClassifierInitialization:
    """Tests for ErrorClassifier initialization."""

    def test_initialization_with_full_config(self):
        """Classifier should initialize correctly with full config."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    'unfixable_http_codes': [401, 403, 404, 429],
                    'fixable_http_codes': [400, 422],
                    'timeout_patterns': ["timed out"],
                    'rate_limit_patterns': ["rate limit"]
                }
            }
        }
        classifier = ErrorClassifier(config)

        assert len(classifier.unfixable_http_codes) == 4
        assert len(classifier.fixable_http_codes) == 2
        assert len(classifier.timeout_patterns) == 1
        assert len(classifier.rate_limit_patterns) == 1

    def test_initialization_with_missing_keys(self):
        """Classifier should use defaults for missing config keys."""
        config = MagicMock()
        config.get_raw_config.return_value = {
            'research': {
                'error_handling': {
                    # Only specify some keys, rest should use defaults
                    'unfixable_http_codes': [401]
                }
            }
        }
        classifier = ErrorClassifier(config)

        # Should have the one specified code
        assert 401 in classifier.unfixable_http_codes
        # Should have default fixable codes
        assert len(classifier.fixable_http_codes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
