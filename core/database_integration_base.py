#!/usr/bin/env python3
"""
Base classes for database integrations in the multi-database research system.

This module provides the abstract base class and supporting types that all
database integrations must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from pydantic import BaseModel, Field, field_validator

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
