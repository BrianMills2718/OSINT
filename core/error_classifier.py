#!/usr/bin/env python3
"""
Centralized error classification for research system.

Provides structured error categorization to replace brittle text pattern matching.
Uses HTTP status codes (primary) and text patterns (fallback) to classify errors
and determine retry/reformulation strategies.

Architecture:
    - APIError dataclass: Structured error representation
    - ErrorCategory enum: Semantic categories
    - ErrorClassifier: Classification logic with config-driven rules

Usage:
    from core.error_classifier import ErrorClassifier, ErrorCategory

    classifier = ErrorClassifier(config)
    error = classifier.classify(
        error_str="403 Forbidden",
        http_code=403,
        source_id="dvids"
    )

    if error.is_reformulable:
        # Attempt query reformulation
        ...
    elif error.category == ErrorCategory.RATE_LIMIT:
        # Add to session blocklist
        ...
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Semantic error categories for structured handling."""

    AUTHENTICATION = "auth"        # 401, 403 - invalid/missing API key
    RATE_LIMIT = "rate_limit"      # 429 - too many requests
    VALIDATION = "validation"      # 400, 422 - fixable by reformulation
    NOT_FOUND = "not_found"        # 404 - endpoint/resource doesn't exist
    SERVER_ERROR = "server"        # 500, 502, 503, 504 - server issues
    TIMEOUT = "timeout"            # Timeout patterns - network/infra
    NETWORK = "network"            # Connection errors
    UNKNOWN = "unknown"            # Fallback for unclassified


@dataclass
class APIError:
    """Structured error representation with decision flags."""

    http_code: Optional[int]       # HTTP status code (if HTTP error)
    category: ErrorCategory        # Semantic category
    message: str                   # Original error message
    is_retryable: bool            # Can we retry same query later?
    is_reformulable: bool         # Can we fix by changing query?
    source_id: str                # Which integration failed

    def __str__(self) -> str:
        """Human-readable representation."""
        code_str = f"HTTP {self.http_code}" if self.http_code else "Non-HTTP"
        return f"{code_str} {self.category.value} error from {self.source_id}: {self.message}"


class ErrorClassifier:
    """
    Centralized error classification logic.

    Classifies errors using:
    1. HTTP status codes (most reliable)
    2. Text pattern matching (fallback for non-HTTP errors)
    3. Conservative defaults for unknowns
    """

    def __init__(self, config):
        """
        Initialize classifier with config-driven rules.

        Args:
            config: ConfigLoader instance with error_handling settings
        """
        self.config = config

        # Load HTTP code classifications from config
        raw_config = config.get_raw_config()
        error_config = raw_config.get('research', {}).get('error_handling', {})

        self.unfixable_http_codes = set(error_config.get('unfixable_http_codes', [
            401, 403, 404, 429, 500, 502, 503, 504
        ]))

        self.fixable_http_codes = set(error_config.get('fixable_http_codes', [
            400, 422
        ]))

        # Load text pattern fallbacks
        self.timeout_patterns = [
            p.lower() for p in error_config.get('timeout_patterns', [
                "timed out", "timeout", "TimeoutError", "ReadTimeoutError",
                "ConnectTimeout", "handshake operation timed out"
            ])
        ]

        self.rate_limit_patterns = [
            p.lower() for p in error_config.get('rate_limit_patterns', [
                "rate limit", "429", "quota exceeded", "too many requests",
                "throttl", "daily limit"
            ])
        ]

        self.auth_patterns = [
            p.lower() for p in [
                "401", "403", "unauthorized", "forbidden", "authentication failed"
            ]
        ]

        # Network error patterns (connection failures, server disconnects)
        self.network_patterns = [
            p.lower() for p in error_config.get('network_patterns', [
                "server disconnected", "connection refused", "connection reset",
                "connection closed", "connection aborted", "network unreachable",
                "host unreachable", "no route to host", "connection error",
                "clientconnectorerror", "serverdisconnectederror"
            ])
        ]

        logger.info(
            f"ErrorClassifier initialized: "
            f"{len(self.unfixable_http_codes)} unfixable codes, "
            f"{len(self.fixable_http_codes)} fixable codes, "
            f"{len(self.timeout_patterns)} timeout patterns, "
            f"{len(self.rate_limit_patterns)} rate limit patterns"
        )

    def classify(
        self,
        error_str: str,
        http_code: Optional[int],
        source_id: str
    ) -> APIError:
        """
        Classify error into structured form.

        Args:
            error_str: Error message text
            http_code: HTTP status code (None for non-HTTP errors)
            source_id: Integration identifier

        Returns:
            APIError with categorization and decision flags
        """
        # Treat http_code=0 as None (bug in some integrations where e.response is None)
        if http_code == 0:
            http_code = None

        # Try to extract HTTP code from error message if not provided
        # This handles cases like "HTTP 0: 500 Server Error" where response was None
        if http_code is None:
            http_code = self._extract_http_code_from_message(error_str)

        # HTTP code-based classification (most reliable)
        if http_code is not None:
            return self._classify_by_http_code(error_str, http_code, source_id)

        # Text pattern fallback (for non-HTTP errors)
        return self._classify_by_pattern(error_str, source_id)

    def _extract_http_code_from_message(self, error_str: str) -> Optional[int]:
        """
        Extract HTTP status code from error message text.

        Handles cases where e.response was None but the error message
        contains the actual status code (e.g., "500 Server Error").

        Args:
            error_str: Error message text

        Returns:
            HTTP status code if found, None otherwise
        """
        import re

        # Pattern 1: "HTTP X:" at the start (from our own formatting)
        # Skip "HTTP 0:" as that indicates missing code
        match = re.search(r'HTTP (\d{3}):', error_str)
        if match and match.group(1) != '000':
            code = int(match.group(1))
            if code > 0:
                return code

        # Pattern 2: "NNN Status Message" common HTTP error format
        # e.g., "500 Server Error", "429 Too Many Requests", "403 Forbidden"
        # Note: Added "Client|Error" alternatives to catch "NNN Client Error" format
        http_error_patterns = [
            (r'500\s+(?:Server|Internal|Error)', 500),
            (r'502\s+(?:Bad|Gateway|Error)', 502),
            (r'503\s+(?:Service|Unavailable|Error)', 503),
            (r'504\s+(?:Gateway|Timeout|Error)', 504),
            (r'429\s+(?:Too\s+Many|Rate|Client|Error)', 429),
            (r'403\s+(?:Forbidden|Access|Client|Error)', 403),
            (r'401\s+(?:Unauthorized|Auth|Client|Error)', 401),
            (r'404\s+(?:Not\s+Found|Client|Error)', 404),
            (r'400\s+(?:Bad\s+Request|Client|Error)', 400),
            (r'422\s+(?:Unprocessable|Client|Error)', 422),
        ]

        for pattern, code in http_error_patterns:
            if re.search(pattern, error_str, re.IGNORECASE):
                return code

        # Pattern 3: Just the code word (Forbidden, Unauthorized, etc.)
        # Only use this for clear authentication/rate limit cases
        error_lower = error_str.lower()
        if 'forbidden' in error_lower and '403' not in error_str:
            return 403
        if 'unauthorized' in error_lower and '401' not in error_str:
            return 401

        return None

    def _classify_by_http_code(
        self,
        error_str: str,
        http_code: int,
        source_id: str
    ) -> APIError:
        """Classify error by HTTP status code."""

        # Authentication errors (401, 403)
        if http_code in [401, 403]:
            return APIError(
                http_code=http_code,
                category=ErrorCategory.AUTHENTICATION,
                message=error_str,
                is_retryable=False,      # API key issues don't self-resolve
                is_reformulable=False,   # Query changes won't fix auth
                source_id=source_id
            )

        # Rate limiting (429)
        if http_code == 429:
            return APIError(
                http_code=http_code,
                category=ErrorCategory.RATE_LIMIT,
                message=error_str,
                is_retryable=True,       # Can retry after cooldown
                is_reformulable=False,   # Query changes won't fix rate limit
                source_id=source_id
            )

        # Not Found (404)
        if http_code == 404:
            return APIError(
                http_code=http_code,
                category=ErrorCategory.NOT_FOUND,
                message=error_str,
                is_retryable=False,      # Endpoint doesn't exist
                is_reformulable=False,   # Query changes won't fix 404
                source_id=source_id
            )

        # Validation errors (400, 422) - fixable by reformulation
        if http_code in self.fixable_http_codes:
            return APIError(
                http_code=http_code,
                category=ErrorCategory.VALIDATION,
                message=error_str,
                is_retryable=False,      # Same query will fail again
                is_reformulable=True,    # Can fix by changing query
                source_id=source_id
            )

        # Server errors (500, 502, 503, 504)
        if http_code in [500, 502, 503, 504]:
            return APIError(
                http_code=http_code,
                category=ErrorCategory.SERVER_ERROR,
                message=error_str,
                is_retryable=True,       # Temporary server issues
                is_reformulable=False,   # Query changes won't fix server
                source_id=source_id
            )

        # Unknown HTTP code - conservative approach
        logger.warning(f"Unknown HTTP code {http_code} for {source_id}: {error_str}")
        return APIError(
            http_code=http_code,
            category=ErrorCategory.UNKNOWN,
            message=error_str,
            is_retryable=False,          # Conservative: don't retry unknowns
            is_reformulable=False,       # Conservative: don't reformulate unknowns
            source_id=source_id
        )

    def _classify_by_pattern(
        self,
        error_str: str,
        source_id: str
    ) -> APIError:
        """Classify error by text pattern matching (fallback)."""

        error_lower = error_str.lower()

        # Timeout patterns
        if any(pattern in error_lower for pattern in self.timeout_patterns):
            return APIError(
                http_code=None,
                category=ErrorCategory.TIMEOUT,
                message=error_str,
                is_retryable=True,       # Infrastructure issues may resolve
                is_reformulable=False,   # Query changes won't fix timeouts
                source_id=source_id
            )

        # Rate limit patterns
        if any(pattern in error_lower for pattern in self.rate_limit_patterns):
            return APIError(
                http_code=None,
                category=ErrorCategory.RATE_LIMIT,
                message=error_str,
                is_retryable=True,       # Can retry after cooldown
                is_reformulable=False,   # Query changes won't fix rate limit
                source_id=source_id
            )

        # Authentication patterns
        if any(pattern in error_lower for pattern in self.auth_patterns):
            return APIError(
                http_code=None,
                category=ErrorCategory.AUTHENTICATION,
                message=error_str,
                is_retryable=False,      # API key issues don't self-resolve
                is_reformulable=False,   # Query changes won't fix auth
                source_id=source_id
            )

        # Network error patterns
        if any(pattern in error_lower for pattern in self.network_patterns):
            return APIError(
                http_code=None,
                category=ErrorCategory.NETWORK,
                message=error_str,
                is_retryable=True,       # Network issues may resolve
                is_reformulable=False,   # Query changes won't fix network
                source_id=source_id
            )

        # Unknown error - conservative approach
        logger.warning(f"Unclassified error for {source_id}: {error_str}")
        return APIError(
            http_code=None,
            category=ErrorCategory.UNKNOWN,
            message=error_str,
            is_retryable=False,          # Conservative: don't retry unknowns
            is_reformulable=False,       # Conservative: don't reformulate unknowns
            source_id=source_id
        )


# Export public API
__all__ = [
    "ErrorCategory",
    "APIError",
    "ErrorClassifier"
]
