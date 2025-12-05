#!/usr/bin/env python3
"""
RawResult - Immutable raw API response data.

This module provides the RawResult dataclass which preserves complete API responses
without any truncation. This is the first tier of the three-tier evidence model:

    RawResult -> ProcessedEvidence -> Evidence

Design Principles:
    - Store EVERYTHING from the API (storage is essentially free)
    - Never truncate raw content
    - Preserve complete provenance (query params, timestamps)
    - Immutable after creation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawResult:
    """
    Immutable raw API response data.

    This class captures the complete response from an API call without any
    processing, truncation, or filtering. The data is preserved exactly as
    received for:
        - Audit trails
        - Re-processing with different goals
        - Full content analysis
        - Timeline reconstruction

    Attributes:
        id: Unique identifier for this raw result (UUID)
        api_response: Complete API response as received (unmodified)
        source_id: Integration identifier (e.g., "sam", "usaspending")
        query_params: The query parameters used to fetch this result
        fetched_at: Timestamp when the API call was made
        response_time_ms: How long the API call took

        title: Extracted title (convenience field, never truncated)
        url: Extracted URL (convenience field)
        raw_content: Full content/description/snippet (NEVER TRUNCATED)
        structured_date: Date from API's structured date field (if present)
        content_dates: Dates extracted from text content (list)

    Usage:
        raw = RawResult.from_api_response(
            api_response={"title": "...", "description": "full content here..."},
            source_id="newsapi",
            query_params={"q": "AI contracts"},
            title=response["title"],
            raw_content=response["description"]  # No truncation!
        )
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Complete API data (never modified)
    api_response: Dict[str, Any] = field(default_factory=dict)

    # Provenance
    source_id: str = ""
    query_params: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0

    # Extracted fields (convenience, never truncated)
    title: str = ""
    url: Optional[str] = None
    raw_content: str = ""  # Full content - NEVER TRUNCATE
    structured_date: Optional[str] = None  # From API date field
    content_dates: List[str] = field(default_factory=list)  # Extracted from text

    @classmethod
    def from_api_response(
        cls,
        api_response: Dict[str, Any],
        source_id: str,
        query_params: Dict[str, Any],
        title: str,
        raw_content: str,
        url: Optional[str] = None,
        structured_date: Optional[str] = None,
        response_time_ms: float = 0.0
    ) -> 'RawResult':
        """
        Create RawResult from an API response.

        Args:
            api_response: Complete API response dict (preserved as-is)
            source_id: Integration ID (e.g., "sam", "usaspending")
            query_params: Query parameters used
            title: Result title (not truncated)
            raw_content: Full content (NEVER TRUNCATE)
            url: Link to source (optional)
            structured_date: Date from API (optional)
            response_time_ms: API response time

        Returns:
            RawResult with complete data preserved
        """
        return cls(
            api_response=api_response,
            source_id=source_id,
            query_params=query_params,
            title=title,
            raw_content=raw_content,
            url=url,
            structured_date=structured_date,
            response_time_ms=response_time_ms,
            fetched_at=datetime.now()
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dict for JSON storage.

        Returns complete data without any truncation.
        """
        return {
            "id": self.id,
            "api_response": self.api_response,
            "source_id": self.source_id,
            "query_params": self.query_params,
            "fetched_at": self.fetched_at.isoformat(),
            "response_time_ms": self.response_time_ms,
            "title": self.title,
            "url": self.url,
            "raw_content": self.raw_content,
            "structured_date": self.structured_date,
            "content_dates": self.content_dates
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RawResult':
        """
        Deserialize from dict.

        Args:
            data: Dict from to_dict() or JSON storage

        Returns:
            RawResult instance
        """
        fetched_at = data.get("fetched_at")
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)
        elif fetched_at is None:
            fetched_at = datetime.now()

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            api_response=data.get("api_response", {}),
            source_id=data.get("source_id", ""),
            query_params=data.get("query_params", {}),
            fetched_at=fetched_at,
            response_time_ms=data.get("response_time_ms", 0.0),
            title=data.get("title", ""),
            url=data.get("url"),
            raw_content=data.get("raw_content", ""),
            structured_date=data.get("structured_date"),
            content_dates=data.get("content_dates", [])
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        content_preview = self.raw_content[:100] + "..." if len(self.raw_content) > 100 else self.raw_content
        return f"RawResult({self.source_id}): {self.title[:50]} | {len(self.raw_content)} chars"

    @property
    def content_length(self) -> int:
        """Length of raw content in characters."""
        return len(self.raw_content)

    @property
    def has_date(self) -> bool:
        """Whether any date information is available."""
        return bool(self.structured_date or self.content_dates)


# Export
__all__ = ["RawResult"]
