#!/usr/bin/env python3
"""
Query reformulation mixin for deep research.

Provides LLM-based query reformulation for improved search results.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class QueryReformulationMixin:
    """
    Mixin providing query reformulation for improved search results.

    Requires host class to have:
        - Access to render_prompt, config, acompletion
    """

    async def _reformulate_for_relevance(
        self: "SimpleDeepResearch",
        original_query: str,
        research_question: str,
        results_count: int,
        source_performance: Optional[List[Dict]] = None,
        available_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Reformulate query to get MORE RELEVANT results.

        Phase 2: LLM intelligently re-selects sources based on performance.

        Args:
            original_query: Current query
            research_question: Original research question
            results_count: Number of results found
            source_performance: List of dicts with source performance data (name, status, results_returned, results_kept, quality_rate, error_type)
            available_sources: List of available source names (all sources minus rate-limited)

        Returns Dict with:
        - query: New query text
        - param_adjustments: Dict of source-specific parameter hints (e.g., {"reddit": {"time_filter": "year"}})
        - source_adjustments: (Optional) Dict with keep/drop/add lists for source re-selection
        """
        prompt = render_prompt(
            "deep_research/query_reformulation_relevance.j2",
            research_question=research_question,
            original_query=original_query,
            results_count=results_count,
            source_performance=source_performance or [],
            available_sources=available_sources or []
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reformulated query text"
                },
                "source_adjustments": {
                    "type": "object",
                    "description": "Phase 2: Optional source re-selection based on performance",
                    "properties": {
                        "keep": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources that performed well (high quality, keep querying)"
                        },
                        "drop": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources with poor performance (0% quality, errors, off-topic - stop querying)"
                        },
                        "add": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources not yet tried that might perform better"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why you made these source selection decisions"
                        }
                    },
                    "required": ["keep", "drop", "add", "reasoning"],
                    "additionalProperties": False
                },
                "param_adjustments": {
                    "type": "object",
                    "description": "Source-specific parameter hints",
                    "properties": {
                        "reddit": {
                            "type": "object",
                            "properties": {
                                "time_filter": {
                                    "type": "string",
                                    "enum": ["hour", "day", "week", "month", "year", "all"]
                                }
                            },
                            "required": ["time_filter"],
                            "additionalProperties": False
                        },
                        "usajobs": {
                            "type": "object",
                            "properties": {
                                "keywords": {"type": "string"}
                            },
                            "required": ["keywords"],
                            "additionalProperties": False
                        },
                        "twitter": {
                            "type": "object",
                            "properties": {
                                "search_type": {
                                    "type": "string",
                                    "enum": ["Latest", "Top", "People", "Photos", "Videos"]
                                },
                                "max_pages": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3
                                }
                            },
                            "required": ["search_type", "max_pages"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["reddit", "usajobs", "twitter"],
                    "additionalProperties": False
                }
            },
            "required": ["query", "param_adjustments"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "query_reformulation_relevance",
                    "schema": schema
                }
            }
        )

        return json.loads(response.choices[0].message.content)

    async def _reformulate_query_simple(
        self: "SimpleDeepResearch",
        original_query: str,
        results_count: int
    ) -> Dict[str, Any]:
        """
        Reformulate query when it returns insufficient results.

        Returns Dict with:
        - query: New query text
        - param_adjustments: Dict of source-specific parameter hints
        """
        prompt = render_prompt(
            "deep_research/query_reformulation_simple.j2",
            original_query=original_query,
            results_count=results_count
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reformulated query text (broader and simpler)"
                },
                "param_adjustments": {
                    "type": "object",
                    "description": "Source-specific parameter hints",
                    "properties": {
                        "reddit": {
                            "type": "object",
                            "properties": {
                                "time_filter": {
                                    "type": "string",
                                    "enum": ["hour", "day", "week", "month", "year", "all"]
                                }
                            },
                            "required": ["time_filter"],
                            "additionalProperties": False
                        },
                        "usajobs": {
                            "type": "object",
                            "properties": {
                                "keywords": {"type": "string"}
                            },
                            "required": ["keywords"],
                            "additionalProperties": False
                        },
                        "twitter": {
                            "type": "object",
                            "properties": {
                                "search_type": {
                                    "type": "string",
                                    "enum": ["Latest", "Top", "People", "Photos", "Videos"]
                                },
                                "max_pages": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3
                                }
                            },
                            "required": ["search_type", "max_pages"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["reddit", "usajobs", "twitter"],
                    "additionalProperties": False
                }
            },
            "required": ["query", "param_adjustments"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "query_reformulation_simple",
                    "schema": schema
                }
            }
        )

        return json.loads(response.choices[0].message.content)

    async def _reformulate_on_api_error(
        self: "SimpleDeepResearch",
        source_name: str,
        research_question: str,
        original_params: Dict[str, Any],
        error_message: str,
        error_code: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Reformulate query parameters when an API returns a validation error.

        This enables automatic recovery from API errors by letting the LLM
        understand what went wrong and generate a corrected query.

        Design principles:
            - Generic: Works with any integration without source-specific code
            - LLM-driven: LLM understands error and fixes it intelligently
            - Fail-safe: Returns None if reformulation fails (caller handles gracefully)

        Args:
            source_name: Name of the source (e.g., "usaspending", "sam_gov")
            research_question: The original research question
            original_params: The query parameters that caused the error
            error_message: The error message from the API
            error_code: HTTP status code if available (e.g., 422, 400)

        Returns:
            Dict with reformulated query parameters, or None if cannot fix

        Example:
            If USAspending returns HTTP 422 "keyword 'AI' too short (min 3 chars)",
            the LLM will reformulate to use "artificial intelligence" instead.
        """
        try:
            prompt = render_prompt(
                "deep_research/query_reformulation_error.j2",
                source_name=source_name,
                research_question=research_question,
                original_params=original_params,
                error_message=error_message,
                error_code=error_code
            )

            # Use json_object mode (not strict schema) because fixed_params
            # needs to be a flexible object matching the original params structure
            # which varies by source. Gemini's strict mode rejects empty object schemas.
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            if result.get("can_fix") and result.get("fixed_params"):
                logger.info(
                    f"[REFORMULATE] {source_name}: {result.get('explanation', 'Fixed query')}"
                )
                return result["fixed_params"]
            else:
                logger.warning(
                    f"[REFORMULATE] {source_name}: Cannot fix error - {result.get('explanation', 'Unknown reason')}"
                )
                return None

        except Exception as e:
            logger.error(f"[REFORMULATE] {source_name}: Reformulation failed - {e}", exc_info=True)
            return None
