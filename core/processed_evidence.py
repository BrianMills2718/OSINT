#!/usr/bin/env python3
"""
ProcessedEvidence - LLM-processed evidence with extracted information.

This module provides the ProcessedEvidence dataclass which contains goal-focused
extraction results from raw API data. This is the second tier of the three-tier
evidence model:

    RawResult -> ProcessedEvidence -> Evidence

Design Principles:
    - Goal-focused extraction (what matters for THIS goal)
    - Structured facts, entities, and dates
    - Token-efficient summaries for LLM context
    - Full provenance (extraction model, goal, timestamp)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDate:
    """A date extracted from content with context."""
    date: str  # ISO format or approximate (e.g., "2024-Q1")
    context: str  # What this date refers to (e.g., "contract award date")
    confidence: float = 1.0  # LLM confidence in extraction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "context": self.context,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedDate':
        return cls(
            date=data.get("date", ""),
            context=data.get("context", ""),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class ProcessedEvidence:
    """
    LLM-processed evidence with goal-focused extraction.

    This class contains the structured information extracted from raw content
    by an LLM, focused on what's relevant to a specific research goal.

    Attributes:
        id: Unique identifier for this processed evidence (UUID)
        raw_result_id: Reference to the source RawResult
        goal: The research goal this extraction was performed for
        extracted_by: LLM model used for extraction

        extracted_facts: Key facts relevant to the goal
        extracted_entities: Named entities found (people, orgs, etc.)
        extracted_dates: Dates with context
        extracted_amounts: Dollar amounts with context
        relevance_score: LLM-assigned relevance to goal (0-1)
        relevance_reasoning: Why this is/isn't relevant

        summary: Token-efficient summary for LLM context (~150 chars)
        processed_at: When extraction was performed

    Usage:
        processed = ProcessedEvidence(
            raw_result_id=raw.id,
            goal="Find AI contracts awarded in 2024",
            extracted_facts=["Pentagon awarded $200M contract", ...],
            extracted_entities=["Pentagon", "Palantir", ...],
            summary="Pentagon awarded $200M AI contract to Palantir..."
        )
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Reference to raw data
    raw_result_id: str = ""

    # Goal context
    goal: str = ""
    extracted_by: str = ""  # LLM model used

    # Extracted information
    extracted_facts: List[str] = field(default_factory=list)
    extracted_entities: List[str] = field(default_factory=list)
    extracted_dates: List[ExtractedDate] = field(default_factory=list)
    extracted_amounts: List[Dict[str, Any]] = field(default_factory=list)  # {"amount": 1000000, "context": "..."}

    # Relevance assessment
    relevance_score: float = 0.0
    relevance_reasoning: str = ""

    # Token-efficient summary for LLM prompts
    summary: str = ""  # ~150 chars, goal-focused

    # Provenance
    processed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_llm_response(
        cls,
        raw_result_id: str,
        goal: str,
        llm_response: Dict[str, Any],
        model: str
    ) -> 'ProcessedEvidence':
        """
        Create ProcessedEvidence from LLM extraction response.

        Args:
            raw_result_id: ID of the source RawResult
            goal: Research goal this was extracted for
            llm_response: LLM's extraction output (structured JSON)
            model: LLM model identifier

        Returns:
            ProcessedEvidence with extracted data
        """
        # Parse extracted dates if present
        extracted_dates = []
        for date_data in llm_response.get("extracted_dates", []):
            if isinstance(date_data, dict):
                extracted_dates.append(ExtractedDate.from_dict(date_data))
            elif isinstance(date_data, str):
                extracted_dates.append(ExtractedDate(date=date_data, context=""))

        return cls(
            raw_result_id=raw_result_id,
            goal=goal,
            extracted_by=model,
            extracted_facts=llm_response.get("extracted_facts", []),
            extracted_entities=llm_response.get("extracted_entities", []),
            extracted_dates=extracted_dates,
            extracted_amounts=llm_response.get("extracted_amounts", []),
            relevance_score=llm_response.get("relevance_score", 0.0),
            relevance_reasoning=llm_response.get("relevance_reasoning", ""),
            summary=llm_response.get("summary", ""),
            processed_at=datetime.now()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "id": self.id,
            "raw_result_id": self.raw_result_id,
            "goal": self.goal,
            "extracted_by": self.extracted_by,
            "extracted_facts": self.extracted_facts,
            "extracted_entities": self.extracted_entities,
            "extracted_dates": [d.to_dict() for d in self.extracted_dates],
            "extracted_amounts": self.extracted_amounts,
            "relevance_score": self.relevance_score,
            "relevance_reasoning": self.relevance_reasoning,
            "summary": self.summary,
            "processed_at": self.processed_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedEvidence':
        """Deserialize from dict."""
        processed_at = data.get("processed_at")
        if isinstance(processed_at, str):
            processed_at = datetime.fromisoformat(processed_at)
        elif processed_at is None:
            processed_at = datetime.now()

        # Parse extracted dates
        extracted_dates = []
        for date_data in data.get("extracted_dates", []):
            if isinstance(date_data, dict):
                extracted_dates.append(ExtractedDate.from_dict(date_data))

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            raw_result_id=data.get("raw_result_id", ""),
            goal=data.get("goal", ""),
            extracted_by=data.get("extracted_by", ""),
            extracted_facts=data.get("extracted_facts", []),
            extracted_entities=data.get("extracted_entities", []),
            extracted_dates=extracted_dates,
            extracted_amounts=data.get("extracted_amounts", []),
            relevance_score=data.get("relevance_score", 0.0),
            relevance_reasoning=data.get("relevance_reasoning", ""),
            summary=data.get("summary", ""),
            processed_at=processed_at
        )

    @property
    def llm_context(self) -> str:
        """
        Token-efficient representation for LLM prompts.

        Returns the summary, which should be ~150 chars goal-focused text.
        """
        return self.summary

    @property
    def has_entities(self) -> bool:
        """Whether entities were extracted."""
        return len(self.extracted_entities) > 0

    @property
    def has_facts(self) -> bool:
        """Whether facts were extracted."""
        return len(self.extracted_facts) > 0

    @property
    def has_dates(self) -> bool:
        """Whether dates were extracted."""
        return len(self.extracted_dates) > 0

    @property
    def date_strings(self) -> List[str]:
        """Get just the date strings (without context)."""
        return [d.date for d in self.extracted_dates]

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"ProcessedEvidence(goal='{self.goal[:30]}...', "
            f"facts={len(self.extracted_facts)}, "
            f"entities={len(self.extracted_entities)}, "
            f"dates={len(self.extracted_dates)}, "
            f"relevance={self.relevance_score:.2f})"
        )


# Export
__all__ = ["ProcessedEvidence", "ExtractedDate"]
