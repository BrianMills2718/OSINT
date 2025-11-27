"""
Defensive result builder for integration data transformation.

All integrations MUST use this builder to construct search results.
This ensures consistent handling of None values, type mismatches,
and edge cases across all 29+ integrations.

Usage:
    from core.result_builder import SearchResultBuilder

    result = (SearchResultBuilder()
        .title(f"${builder.format_amount(amount)} from {contributor}")
        .url(data.get("url"))
        .snippet(data.get("description"))
        .date(data.get("created_at"))
        .metadata({"source_id": data.get("id")})
        .build())
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResultBuilder:
    """
    Defensive builder for search results.

    Handles None values, type mismatches, and edge cases automatically.
    All setter methods return self for chaining.
    """

    _title: str = ""
    _url: Optional[str] = None
    _snippet: str = ""
    _date: Optional[str] = None
    _metadata: Dict[str, Any] = field(default_factory=dict)

    # === Safe Value Extractors (static methods for use in f-strings) ===

    @staticmethod
    def safe_amount(value: Any, default: float = 0.0) -> float:
        """
        Safely extract a numeric amount.

        Handles None, missing keys, empty strings, and type mismatches.
        Returns default if value cannot be converted to float.
        """
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def format_amount(value: Any, default: float = 0.0) -> str:
        """
        Format amount as currency string (e.g., "$1,234.56").

        Safe to use in f-strings - never raises on None/invalid.
        """
        amount = SearchResultBuilder.safe_amount(value, default)
        return f"${amount:,.2f}"

    @staticmethod
    def safe_text(value: Any, default: str = "", max_length: Optional[int] = None) -> str:
        """
        Safely extract text, with optional truncation.

        Handles None, empty strings, non-string types, and length limits.
        Returns default if value is None or empty after stripping.
        """
        if value is None:
            return default

        text = str(value).strip()

        # Return default for empty strings (after stripping)
        if not text:
            return default

        if max_length and len(text) > max_length:
            return text[:max_length - 3] + "..."

        return text

    @staticmethod
    def safe_date(value: Any) -> Optional[str]:
        """
        Safely extract and normalize date to ISO format string.

        Handles None, datetime objects, date objects, and string dates.
        Returns None if date cannot be parsed.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, str):
            # Return as-is if it's already a string (assume API formatted it)
            return value.strip() if value.strip() else None

        return None

    @staticmethod
    def safe_url(value: Any) -> Optional[str]:
        """
        Safely extract URL.

        Handles None, empty strings, and basic validation.
        """
        if value is None:
            return None

        url = str(value).strip()

        if not url:
            return None

        # Basic URL validation - must start with http(s) or be relative
        if url.startswith(('http://', 'https://', '/')):
            return url

        # Log warning for suspicious URLs but still return
        if not url.startswith(('http://', 'https://')):
            logger.debug(f"URL doesn't start with http(s): {url[:50]}")

        return url

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """
        Safely extract integer value.

        Handles None, floats, strings, and type mismatches.
        """
        if value is None:
            return default
        try:
            return int(float(value))  # Handle "123.0" strings
        except (TypeError, ValueError):
            return default

    # === Builder Methods (chainable) ===

    def title(self, value: Any, default: str = "Untitled") -> 'SearchResultBuilder':
        """Set title with safe text extraction."""
        self._title = self.safe_text(value, default)
        return self

    def url(self, value: Any) -> 'SearchResultBuilder':
        """Set URL with validation."""
        self._url = self.safe_url(value)
        return self

    def snippet(self, value: Any, max_length: int = 500) -> 'SearchResultBuilder':
        """Set snippet with truncation."""
        self._snippet = self.safe_text(value, "", max_length)
        return self

    def date(self, value: Any) -> 'SearchResultBuilder':
        """Set date with normalization."""
        self._date = self.safe_date(value)
        return self

    def metadata(self, value: Dict[str, Any]) -> 'SearchResultBuilder':
        """Set metadata dict (merged with existing)."""
        if value and isinstance(value, dict):
            self._metadata.update(value)
        return self

    def add_metadata(self, key: str, value: Any) -> 'SearchResultBuilder':
        """Add single metadata key-value pair."""
        self._metadata[key] = value
        return self

    # === Build Method ===

    def build(self) -> Dict[str, Any]:
        """
        Build the final result dictionary.

        Returns the standard format expected by QueryResult.results[].
        """
        return {
            "title": self._title,
            "url": self._url,
            "snippet": self._snippet,
            "date": self._date,
            "metadata": self._metadata
        }

    # === Convenience Class Method ===

    @classmethod
    def from_dict(cls, data: Dict[str, Any],
                  title_key: str = "title",
                  url_key: str = "url",
                  snippet_key: str = "snippet",
                  date_key: str = "date") -> 'SearchResultBuilder':
        """
        Create builder from a dict with common key mappings.

        Useful for simple transformations where keys map directly.
        """
        builder = cls()
        builder.title(data.get(title_key))
        builder.url(data.get(url_key))
        builder.snippet(data.get(snippet_key))
        builder.date(data.get(date_key))
        return builder


# === Convenience function for simple cases ===

def build_result(
    title: Any,
    url: Any = None,
    snippet: Any = None,
    date: Any = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    One-liner convenience function for building results.

    Usage:
        result = build_result(
            title=f"{SearchResultBuilder.format_amount(amount)} from {name}",
            url=data.get("link"),
            snippet=data.get("description"),
            date=data.get("created_at")
        )
    """
    builder = SearchResultBuilder()
    builder.title(title)
    builder.url(url)
    builder.snippet(snippet)
    builder.date(date)
    if metadata:
        builder.metadata(metadata)
    return builder.build()
