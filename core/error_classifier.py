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
        # HTTP code-based classification (most reliable)
        if http_code is not None:
            return self._classify_by_http_code(error_str, http_code, source_id)

        # Text pattern fallback (for non-HTTP errors)
        return self._classify_by_pattern(error_str, source_id)

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
