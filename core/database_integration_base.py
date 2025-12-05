#!/usr/bin/env python3
"""
Base classes for database integrations in the multi-database research system.

This module provides the abstract base class and supporting types that all
database integrations must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
import random
from pydantic import BaseModel, Field, field_validator

# Type variable for generic retry function
T = TypeVar('T')

# Set up logger for this module
logger = logging.getLogger(__name__)


class DatabaseCategory(Enum):
    """Category of database for relevance filtering and organization."""
    JOBS = "jobs"
    CONTRACTS = "contracts"
    NEWS = "news"
    RESEARCH = "research"
    MEDIA = "media"
    GENERAL = "general"

    # Government document categories by agency
    GOV_FBI = "government_fbi"
    GOV_CONGRESS = "government_congress"
    GOV_EXECUTIVE = "government_executive"
    GOV_FEDERAL_REGISTER = "government_federal_register"
    GOV_GENERAL = "government_general"

    # Social media categories
    SOCIAL_REDDIT = "social_reddit"
    SOCIAL_TWITTER = "social_twitter"
    SOCIAL_TELEGRAM = "social_telegram"
    SOCIAL_GENERAL = "social_general"

    # Web search
    WEB_SEARCH = "web_search"


@dataclass
class DatabaseMetadata:
    """
    Complete metadata about a database integration.

    This is the SINGLE SOURCE OF TRUTH for all integration configuration.
    All fields that describe a source should be here - not scattered across
    multiple files (source_metadata.py, deep_research.py hardcoding, etc.)

    Used for:
    - Routing and relevance filtering
    - Cost estimation and rate limiting
    - User display and LLM prompts
    - Query generation guidance
    - API key management
    """
    # === Core Identity ===
    name: str                          # Display name (e.g., "SAM.gov")
    id: str                           # Unique identifier / integration_id (e.g., "sam")
    category: DatabaseCategory        # Category for filtering
    description: str                  # Brief description for users/LLMs

    # === API Configuration ===
    requires_api_key: bool            # Whether API key is required
    api_key_env_var: Optional[str] = None  # Environment variable name (e.g., "SAM_GOV_API_KEY")

    # === Performance & Limits ===
    cost_per_query_estimate: float = 0.001  # Estimated cost in USD per query
    typical_response_time: float = 2.0      # Typical response time in seconds
    rate_limit_daily: Optional[int] = None  # Daily rate limit, None if unknown
    default_result_limit: int = 50          # Default max results per query

    # === Stealth/Bot Detection ===
    requires_stealth: bool = False    # Whether bot detection bypass needed
    stealth_method: Optional[str] = None  # "playwright", "selenium", or None

    # === Query Generation Guidance (merged from source_metadata.py) ===
    query_strategies: Optional[List[str]] = None  # Valid query approaches for this source
    characteristics: Optional[Dict[str, Any]] = None  # Source-specific traits for LLM context
    typical_result_count: int = 50    # Typical number of results returned
    max_queries_recommended: int = 5  # Max queries before diminishing returns

    # === Rate Limit Recovery Configuration ===
    # These fields configure retry behavior when a source is rate-limited (HTTP 429)
    rate_limit_recovery_seconds: Optional[int] = None  # Estimated recovery time. None = unknown
    retry_on_rate_limit_within_session: bool = True    # Whether retrying within session is worthwhile
    # Examples:
    #   - SAM.gov: recovery ~86400s (1 day), retry_within_session=False (pointless to retry)
    #   - Brave: recovery ~60-300s, retry_within_session=True (worth waiting)
    #   - USAspending: no rate limit documented, retry_within_session=True (retry on transient errors)

    def __post_init__(self):
        """Set defaults for optional collections."""
        if self.query_strategies is None:
            self.query_strategies = []
        if self.characteristics is None:
            self.characteristics = {}


class SearchResult(BaseModel):
    """
    Standardized search result format enforced via Pydantic.

    ALL integrations must return results with these required fields.
    This prevents the field mapping bugs we've been fixing.

    Required fields:
        - title: Human-readable title/name of the result

    Optional fields:
        - url: Link to the full result (web page, PDF, etc.) - may be None if source doesn't provide one
        - snippet: Brief excerpt/summary (max 500 chars recommended)
        - date: Publication/creation date (ISO format string or None)
        - metadata: Dict of source-specific additional data
    """
    title: str = Field(..., description="Title of the result", min_length=1)
    url: Optional[str] = Field(default=None, description="URL link to full result (may be None if unavailable)")
    snippet: str = Field(default="", description="Brief excerpt or summary")
    date: Optional[str] = Field(default=None, description="Publication or creation date")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Source-specific metadata")

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty or whitespace")
        return v.strip()

    @field_validator('snippet')
    @classmethod
    def snippet_max_length(cls, v: str) -> str:
        """Recommend keeping snippets under 500 chars."""
        if len(v) > 500:
            # Don't fail, just truncate and warn
            return v[:497] + "..."
        return v


class Evidence(SearchResult):
    """
    SearchResult enriched with research context.

    ARCHITECTURE: Evidence EXTENDS SearchResult via inheritance.
    This guarantees:
    - All SearchResult fields are automatically inherited (zero drift)
    - Type safety via Pydantic validation
    - Single source of truth for field definitions

    Three-Tier Data Model (NEW):
        - raw_result_id: Reference to complete raw API response (RawResult)
        - processed_id: Reference to LLM-extracted data (ProcessedEvidence)
        - raw_content: Full content (NEVER TRUNCATED) - optional for backward compat

    Legacy fields (backward compatibility):
        - source_id: Which integration provided this result
        - relevance_score: LLM-assigned relevance (0-1)

    The 'content' property provides backward compatibility with code
    that uses 'content' instead of 'snippet'.
    """
    source_id: str = Field(..., description="Integration ID that provided this result")
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="LLM-assigned relevance score"
    )

    # === NEW: Three-tier data model fields ===
    # These are optional for backward compatibility with existing code
    raw_result_id: Optional[str] = Field(
        default=None,
        description="Reference to RawResult with complete API response"
    )
    processed_id: Optional[str] = Field(
        default=None,
        description="Reference to ProcessedEvidence with extracted data"
    )
    raw_content: Optional[str] = Field(
        default=None,
        description="Full content (never truncated) - use this for full text"
    )

    # Extracted data (populated from ProcessedEvidence if available)
    extracted_facts: Optional[List[str]] = Field(
        default=None,
        description="Key facts extracted by LLM"
    )
    extracted_entities: Optional[List[str]] = Field(
        default=None,
        description="Named entities extracted by LLM"
    )
    extracted_dates: Optional[List[str]] = Field(
        default=None,
        description="Dates extracted from content"
    )

    @property
    def content(self) -> str:
        """
        Backward compatibility alias for snippet.

        If raw_content is available (three-tier model), prefer it.
        Otherwise fall back to snippet (legacy model).
        """
        if self.raw_content:
            return self.raw_content
        return self.snippet

    @property
    def full_content(self) -> str:
        """
        Get full content without truncation.

        Use this when you need the complete text, not truncated snippet.
        """
        return self.raw_content or self.snippet

    @property
    def source(self) -> str:
        """Backward compatibility alias for source_id."""
        return self.source_id

    @property
    def llm_context(self) -> str:
        """
        Token-efficient representation for LLM prompts.

        Uses snippet (truncated) to control token usage.
        For full content, use .full_content or .raw_content.
        """
        return self.snippet

    @property
    def has_raw_data(self) -> bool:
        """Whether this Evidence has linked raw data (three-tier model)."""
        return self.raw_result_id is not None

    @property
    def has_processed_data(self) -> bool:
        """Whether this Evidence has LLM-extracted data."""
        return self.processed_id is not None or bool(self.extracted_facts)

    @classmethod
    def from_search_result(
        cls,
        result: 'SearchResult',
        source_id: str,
        relevance_score: Optional[float] = None,
        raw_content: Optional[str] = None
    ) -> 'Evidence':
        """
        Create Evidence from a validated SearchResult.

        This is the ONLY way to create Evidence from integration results.
        Type-safe: takes SearchResult, not Dict.
        If SearchResult changes, type checker catches mismatches.

        Args:
            result: Validated SearchResult object
            source_id: Integration ID
            relevance_score: Optional LLM-assigned relevance score
            raw_content: Optional full content (from three-tier model)
        """
        return cls(
            source_id=source_id,
            relevance_score=relevance_score,
            raw_content=raw_content,  # Preserve full content if provided
            **result.model_dump()
        )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        source_id: str,
        relevance_score: Optional[float] = None
    ) -> 'Evidence':
        """
        Create Evidence from a raw dict (validates via SearchResult first).

        Use this when receiving data from integrations that return dicts.
        The dict is validated as SearchResult, then converted to Evidence.

        NOTE: If data contains 'raw_content' field (from build_with_raw()),
        it will be preserved separately and passed through.
        """
        # Extract raw_content before validation (SearchResult doesn't have this field)
        raw_content = data.get("raw_content")

        # Validate as SearchResult first (strips unknown fields)
        search_result = SearchResult.model_validate(data)

        return cls.from_search_result(
            search_result,
            source_id,
            relevance_score,
            raw_content=raw_content  # Pass through preserved raw_content
        )

    @classmethod
    def from_raw(
        cls,
        raw_result: 'RawResult',
        processed: Optional['ProcessedEvidence'] = None,
        source_id: Optional[str] = None
    ) -> 'Evidence':
        """
        Create Evidence from RawResult and optional ProcessedEvidence.

        This is the NEW factory method for the three-tier model.
        Preserves complete data while providing backward-compatible interface.

        Args:
            raw_result: Complete raw API response
            processed: Optional LLM-extracted data
            source_id: Override source (defaults to raw_result.source_id)

        Returns:
            Evidence with full data lineage
        """
        # Import here to avoid circular imports
        from core.raw_result import RawResult
        from core.processed_evidence import ProcessedEvidence

        return cls(
            # Core fields (backward compatible)
            source_id=source_id or raw_result.source_id,
            title=raw_result.title,
            url=raw_result.url,
            snippet=raw_result.raw_content[:497] + "..." if len(raw_result.raw_content) > 500 else raw_result.raw_content,
            date=raw_result.structured_date,
            metadata=raw_result.api_response.get("metadata", {}),
            relevance_score=processed.relevance_score if processed else None,

            # Three-tier model fields (NEW)
            raw_result_id=raw_result.id,
            processed_id=processed.id if processed else None,
            raw_content=raw_result.raw_content,  # Full content, never truncated

            # Extracted data
            extracted_facts=processed.extracted_facts if processed else None,
            extracted_entities=processed.extracted_entities if processed else None,
            extracted_dates=processed.date_strings if processed else None
        )

    def to_dict(self, max_content_length: Optional[int] = None, include_raw: bool = False) -> Dict[str, Any]:
        """
        Convert to dict for JSON serialization or report generation.

        Args:
            max_content_length: Optional truncation for content field
            include_raw: If True, include raw_content and extracted data

        Includes all inherited SearchResult fields plus enrichment fields.
        """
        data = self.model_dump()
        # Add content alias for backward compatibility
        data["content"] = self.content
        data["source"] = self.source_id  # Alias

        # Optionally truncate content (legacy behavior)
        if max_content_length and len(data["snippet"]) > max_content_length:
            data["snippet"] = data["snippet"][:max_content_length]
            data["content"] = data["snippet"]

        # Clean up None values from new fields unless include_raw
        if not include_raw:
            for key in ["raw_result_id", "processed_id", "raw_content",
                       "extracted_facts", "extracted_entities", "extracted_dates"]:
                if key in data and data[key] is None:
                    del data[key]

        return data

    def to_full_dict(self) -> Dict[str, Any]:
        """
        Convert to dict with ALL data, no truncation.

        Use this when saving to storage (not for LLM prompts).
        """
        return self.to_dict(include_raw=True)


class QueryResult:
    """
    Standardized result from any database search.

    All database integrations return this consistent format, making it easy
    to aggregate and display results from different sources.

    Results are validated using the SearchResult Pydantic model to ensure
    all integrations return the required fields (title, url, snippet).
    """

    def __init__(self,
                 success: bool,
                 source: str,
                 total: int,
                 results: List[Dict],
                 query_params: Dict,
                 error: Optional[str] = None,
                 http_code: Optional[int] = None,
                 response_time_ms: float = 0,
                 metadata: Optional[Dict] = None,
                 validate: bool = True):
        """
        Initialize a QueryResult.

        Args:
            success: Whether the query succeeded
            source: Name of the database source
            total: Total number of results available (not just returned)
            results: List of result items (max = limit requested)
            query_params: The query parameters that were used
            error: Error message if success=False
            http_code: HTTP status code (for HTTP errors, None for non-HTTP)
            response_time_ms: Time taken for the query in milliseconds
            metadata: Optional database-specific metadata
            validate: Whether to validate results using SearchResult model (default True)

        Raises:
            ValueError: If validate=True and any result is missing required fields
        """
        self.success = success
        self.source = source
        self.total = total
        self.query_params = query_params
        self.error = error
        self.http_code = http_code
        self.response_time_ms = response_time_ms
        self.metadata = metadata or {}

        # Validate results if requested (skip validation for error cases)
        if validate and success and results:
            validated_results = []
            for i, result in enumerate(results):
                try:
                    # Validate using Pydantic model
                    search_result = SearchResult(**result)
                    # Convert back to dict for storage
                    validated_results.append(search_result.model_dump())
                except Exception as e:
                    # Result validation failed - log and re-raise
                    logger.error(f"{source} result #{i} missing required fields: {e}", exc_info=True)
                    raise ValueError(
                        f"{source} result #{i} missing required fields: {e}\n"
                        f"Result was: {result}\n"
                        f"Required fields: title (str), url (str), snippet (str, optional)"
                    )
            self.results = validated_results
        else:
            self.results = results

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "source": self.source,
            "total": self.total,
            "results": self.results,
            "query_params": self.query_params,
            "error": self.error,
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata
        }


class DatabaseIntegration(ABC):
    """
    Abstract base class for all database integrations.

    Each database (ClearanceJobs, DVIDS, SAM.gov, etc.) implements this interface,
    providing a consistent way to:
    1. Check relevance to a research question
    2. Generate database-specific query parameters using LLM
    3. Execute the actual API call

    This architecture allows adding new databases by simply creating a new
    subclass and registering it - no changes to existing code needed.
    """

    @property
    @abstractmethod
    def metadata(self) -> DatabaseMetadata:
        """
        Return metadata about this database.

        This is used for display, routing, and cost tracking.
        """
        pass

    @abstractmethod
    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick check if this database is relevant to the research question.

        This should be a fast check (simple keyword matching, no LLM) to
        filter out obviously irrelevant databases before making expensive
        LLM calls.

        Args:
            research_question: The user's research question

        Returns:
            True if this database should be queried, False to skip it

        Example:
            For a jobs database, return True if question contains
            "job", "career", "employment", etc.
        """
        pass

    @abstractmethod
    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Use LLM to generate database-specific query parameters.

        This is where the database-specific intelligence lives. Each database
        has its own LLM prompt that understands how to query that specific API.

        Args:
            research_question: The user's research question

        Returns:
            Dict of query parameters for execute_search(), or None if upon
            deeper analysis the database is not relevant.

        Example:
            For ClearanceJobs, might return:
            {
                "keywords": "cybersecurity analyst",
                "clearances": ["TS/SCI", "Top Secret"],
                "posted_days_ago": 30
            }
        """
        pass

    @abstractmethod
    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute the actual API call using generated query parameters.

        This method handles the API-specific details (endpoints, authentication,
        response parsing) and returns a standardized QueryResult.

        Args:
            query_params: Parameters generated by generate_query()
            api_key: API key if required by this database
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format

        Note:
            This method should handle errors gracefully and return a
            QueryResult with success=False rather than raising exceptions.
        """
        pass

    async def generate_query_with_reasoning(self, research_question: str) -> Dict:
        """
        Wrapper for generate_query() that ensures rejection reasoning is always captured.

        This method provides a consistent interface for MCP tools to get both query
        parameters AND rejection reasoning when a database is deemed irrelevant.

        Returns:
            Dict with standardized format:
            {
                "relevant": bool,
                "rejection_reason": str (if not relevant),
                "suggested_reformulation": str | None (if not relevant),
                "query_params": dict (if relevant)
            }

        Backward Compatible:
            - If generate_query() returns None → treated as rejection
            - If generate_query() returns dict with relevant=False → extracts reasoning
            - If generate_query() returns dict with relevant=True → passes through
            - If generate_query() returns dict without 'relevant' key → assumes relevant

        Example:
            # Legacy integration that returns None when not relevant
            >>> result = await integration.generate_query_with_reasoning("query")
            {"relevant": False, "rejection_reason": "Not relevant (no reasoning provided)", ...}

            # Modern integration that returns rejection dict
            >>> result = await integration.generate_query_with_reasoning("query")
            {"relevant": False, "rejection_reason": "Query is about jobs, not contracts", ...}

            # Relevant query
            >>> result = await integration.generate_query_with_reasoning("query")
            {"relevant": True, "query_params": {"keywords": "...", ...}}
        """
        # Call child class's generate_query() method
        query_result = await self.generate_query(research_question)

        # Handle None (legacy rejection pattern)
        if query_result is None:
            return {
                "relevant": False,
                "rejection_reason": f"{self.metadata.name} determined query not relevant (no reasoning provided)",
                "suggested_reformulation": None,
                "query_params": None
            }

        # Handle dict response
        if isinstance(query_result, dict):
            # Check if this is a rejection dict (relevant=False)
            if not query_result.get("relevant", True):
                return {
                    "relevant": False,
                    "rejection_reason": query_result.get("rejection_reason") or query_result.get("reasoning", "No reasoning provided"),
                    "suggested_reformulation": query_result.get("suggested_reformulation"),
                    "query_params": None
                }
            # Relevant query - strip metadata keys to avoid polluting execute_search() params
            else:
                # Create clean params dict excluding metadata keys that shouldn't go to execute_search()
                clean_params = {k: v for k, v in query_result.items()
                               if k not in ('relevant', 'rejection_reason', 'suggested_reformulation', 'reasoning')}
                return {
                    "relevant": True,
                    "rejection_reason": None,
                    "suggested_reformulation": None,
                    "query_params": clean_params
                }

        # Unexpected return type (shouldn't happen, but handle gracefully)
        return {
            "relevant": False,
            "rejection_reason": f"Unexpected return type from generate_query(): {type(query_result)}",
            "suggested_reformulation": None,
            "query_params": None
        }

    def get_llm_prompt_template(self) -> str:
        """
        Return the LLM prompt template for query generation.

        Override this to customize the prompt used in generate_query().
        The template should include placeholders for:
        - {research_question}
        - {database_specific_instructions}
        - {response_schema}

        Returns:
            Multi-line string template for LLM prompt
        """
        return f"""You are a search query generator for {self.metadata.name}.

Database: {self.metadata.name}
Description: {self.metadata.description}
Category: {self.metadata.category.value}

Research Question: {{research_question}}

Your task: Generate optimal search parameters for this database.
If this database is not relevant to the research question, indicate that.

{{database_specific_instructions}}

Return your response as JSON following this schema:
{{response_schema}}
"""

    # =========================================================================
    # Retry Helper Methods
    # =========================================================================

    @staticmethod
    def is_retryable_error(error: Optional[str]) -> bool:
        """
        Determine if an error is retryable (transient network/server issue).

        Retryable errors include:
        - HTTP 5xx server errors
        - Connection errors (broken pipe, connection refused, reset)
        - Timeout errors
        - DNS resolution failures

        NOT retryable:
        - HTTP 4xx client errors (bad request, unauthorized, not found)
        - Rate limits (handled separately by session-level tracking)
        - Validation errors
        - API key issues

        Args:
            error: Error message string

        Returns:
            True if the error is likely transient and worth retrying
        """
        if not error:
            return False

        error_lower = error.lower()

        # Server errors (5xx)
        server_error_patterns = [
            "500", "501", "502", "503", "504",
            "internal server error",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
        ]

        # Network/connection errors
        network_error_patterns = [
            "broken pipe",
            "connection refused",
            "connection reset",
            "connection closed",
            "connection aborted",
            "network unreachable",
            "host unreachable",
            "no route to host",
            "dns",
            "name resolution",
            "temporary failure",
            "timeout",
            "timed out",
        ]

        # Check for retryable patterns
        for pattern in server_error_patterns + network_error_patterns:
            if pattern in error_lower:
                return True

        return False

    async def execute_with_retry(
        self,
        request_fn: Callable[[], Any],
        max_retries: int = 2,
        backoff_base: float = 1.0,
        backoff_max: float = 30.0,
        operation_name: str = "request"
    ) -> Any:
        """
        Execute an async function with automatic retry on transient errors.

        This is a helper method that integrations can use for network operations.
        It implements exponential backoff with jitter for retries.

        Args:
            request_fn: Async callable that performs the request (no arguments)
            max_retries: Maximum number of retry attempts (default: 2)
            backoff_base: Base time in seconds for exponential backoff (default: 1.0)
            backoff_max: Maximum backoff time in seconds (default: 30.0)
            operation_name: Name of the operation for logging (default: "request")

        Returns:
            The result of request_fn() if successful

        Raises:
            The last exception if all retries are exhausted

        Example:
            async def _make_api_call():
                response = await session.get(url)
                response.raise_for_status()
                return response

            result = await self.execute_with_retry(
                _make_api_call,
                max_retries=2,
                operation_name="API call"
            )
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await request_fn()
            except Exception as e:
                last_exception = e
                error_str = str(e)

                # Check if error is retryable
                if not self.is_retryable_error(error_str):
                    logger.debug(f"{self.metadata.name}: Non-retryable error: {error_str}")
                    raise

                # Check if we have retries left
                if attempt >= max_retries:
                    logger.warning(
                        f"{self.metadata.name}: {operation_name} failed after "
                        f"{max_retries + 1} attempts: {error_str}"
                    )
                    raise

                # Calculate backoff with exponential increase and jitter
                backoff = min(backoff_base * (2 ** attempt), backoff_max)
                jitter = random.uniform(0, backoff * 0.1)  # 10% jitter
                wait_time = backoff + jitter

                logger.info(
                    f"{self.metadata.name}: {operation_name} failed (attempt {attempt + 1}/"
                    f"{max_retries + 1}), retrying in {wait_time:.1f}s: {error_str}"
                )
                await asyncio.sleep(wait_time)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
