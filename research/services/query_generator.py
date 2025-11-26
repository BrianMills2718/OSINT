#!/usr/bin/env python3
"""
Query generation service for deep research.

Provides LLM-based query generation for hypothesis execution.
Extracted from QueryGenerationMixin to enable composition over inheritance.

This is a stateless service that can be:
- Dependency injected
- Tested in isolation
- Reused across different research contexts
"""

import json
import logging
from typing import Any, Dict, List, Optional

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

# Registry for source display names
from integrations.registry import registry

logger = logging.getLogger(__name__)


class QueryGenerator:
    """
    Stateless service for query generation.

    All state is passed as parameters - no instance attributes required
    except optional execution logger.
    """

    # JSON schema for hypothesis query generation
    HYPOTHESIS_QUERY_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The optimized search query string"
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 sentences explaining why this query will test the hypothesis"
            }
        },
        "required": ["query", "reasoning"],
        "additionalProperties": False
    }

    # JSON schema for saturation decision
    SATURATION_SCHEMA = {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["SATURATED", "CONTINUE"]},
            "reasoning": {"type": "string"},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "existence_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "strategies_tried": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of different strategies attempted (helps assess strategy diversity)"
            },
            "next_query_suggestion": {"type": "string"},
            "next_query_reasoning": {"type": "string"},
            "expected_value": {"type": "string", "enum": ["high", "medium", "low"]},
            "remaining_gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Updated list of information gaps still unaddressed"
            }
        },
        "required": ["decision", "reasoning", "confidence", "strategies_tried"]
    }

    def __init__(
        self,
        execution_logger: Optional[Any] = None
    ):
        """
        Initialize query generator.

        Args:
            execution_logger: Optional ExecutionLogger instance for structured logging
        """
        self._logger = execution_logger

    async def generate_hypothesis_query(
        self,
        hypothesis: Dict,
        source_tool_name: str,
        research_question: str,
        task_query: str,
        task_id: int,
        hypothesis_id: int
    ) -> Optional[str]:
        """
        Generate source-specific query for hypothesis execution.

        Args:
            hypothesis: Hypothesis dict with statement, confidence, search_strategy
            source_tool_name: Integration ID (e.g., "usajobs")
            research_question: Original research question
            task_query: Task query this hypothesis belongs to
            task_id: Task ID for logging
            hypothesis_id: Hypothesis ID for logging

        Returns:
            Query string optimized for this source, or None on error
        """
        source_display_name = registry.get_display_name(source_tool_name)

        # Render prompt with hypothesis context
        prompt = render_prompt(
            "deep_research/hypothesis_query_generation.j2",
            hypothesis_statement=hypothesis["statement"],
            research_question=research_question,
            task_query=task_query,
            hypothesis_confidence=hypothesis["confidence"],
            hypothesis_sources=hypothesis["search_strategy"]["sources"],
            hypothesis_signals=hypothesis["search_strategy"]["signals"],
            hypothesis_entities=hypothesis["search_strategy"]["expected_entities"],
            source_display_name=source_display_name
        )

        try:
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "hypothesis_query",
                        "strict": True,
                        "schema": self.HYPOTHESIS_QUERY_SCHEMA
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)

            # Log to structured log if logger provided
            if self._logger:
                self._logger.log_hypothesis_query_generation(
                    task_id=task_id,
                    hypothesis_id=hypothesis_id,
                    source_name=source_display_name,
                    query=result['query'],
                    reasoning=result['reasoning']
                )

            # Print for real-time visibility
            print(f"      Query: '{result['query']}'")
            print(f"      Reasoning: {result['reasoning']}")

            return result["query"]

        except Exception as e:
            logger.error(f"Hypothesis {hypothesis_id} query generation failed for {source_display_name}: {type(e).__name__}: {e}", exc_info=True)
            return None

    async def generate_initial_query(
        self,
        hypothesis: Dict[str, Any],
        source_name: str,
        source_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate first query from hypothesis (no query history yet).

        This is separate from generate_next_query_or_stop because:
        - First query has no history to reason from
        - Uses hypothesis statement + source metadata only
        - Simpler prompt without saturation decision

        Args:
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            source_metadata: Metadata about the source

        Returns:
            {
                "query": str,
                "reasoning": str
            }
        """
        prompt = render_prompt(
            'deep_research/hypothesis_query_generation.j2',
            hypothesis_statement=hypothesis['statement'],
            source_name=source_name,
            source_metadata=source_metadata,
            search_strategy=hypothesis.get('search_strategy', {}),
            information_gaps=hypothesis.get('information_gaps', [])
        )

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "initial_query",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "reasoning": {"type": "string"}
                        },
                        "required": ["query", "reasoning"]
                    }
                }
            }
        )

        result = json.loads(response.choices[0].message.content)
        return result

    async def generate_next_query_or_stop(
        self,
        hypothesis: Dict[str, Any],
        source_name: str,
        query_history: List[Dict],
        source_metadata: Dict,
        total_results_accepted: int
    ) -> Dict[str, Any]:
        """
        LLM decides: continue with next query or stop (saturated).

        Args:
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            query_history: List of previous query attempts
            source_metadata: Metadata about the source
            total_results_accepted: Total results accepted so far

        Returns:
            {
                "decision": "SATURATED" | "CONTINUE",
                "reasoning": "...",
                "confidence": 0-100,
                "existence_confidence": 0-100,
                "strategies_tried": ["list", "of", "strategies"],
                "next_query_suggestion": "...",  # if CONTINUE
                "next_query_reasoning": "...",   # if CONTINUE
                "expected_value": "high" | "medium" | "low",
                "remaining_gaps": [...]  # Updated list of info gaps
            }
        """
        # Render saturation prompt
        prompt = render_prompt(
            'deep_research/source_saturation.j2',
            hypothesis_statement=hypothesis['statement'],
            source_name=source_name,
            source_metadata=source_metadata,
            query_history=query_history,
            total_results_accepted=total_results_accepted,
            information_gaps=hypothesis.get('information_gaps', [])
        )

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "saturation_decision",
                    "strict": True,
                    "schema": self.SATURATION_SCHEMA
                }
            }
        )

        decision = json.loads(response.choices[0].message.content)
        return decision
