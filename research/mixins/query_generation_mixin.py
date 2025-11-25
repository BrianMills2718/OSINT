#!/usr/bin/env python3
"""
Query generation mixin for deep research.

Provides LLM-based query generation for hypothesis execution.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

# Registry for source display names
from integrations.registry import registry

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch, ResearchTask

logger = logging.getLogger(__name__)


class QueryGenerationMixin:
    """
    Mixin providing query generation for hypothesis execution.

    Requires host class to have:
        - self.logger: ExecutionLogger instance
    """

    async def _generate_hypothesis_query(
        self: "SimpleDeepResearch",
        hypothesis: Dict,
        source_tool_name: str,
        research_question: str,
        task_query: str,
        task: 'ResearchTask'
    ) -> Optional[str]:
        """
        Generate source-specific query for hypothesis execution (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with statement, confidence, search_strategy
            source_tool_name: Integration ID (e.g., "usajobs")
            research_question: Original research question
            task_query: Task query this hypothesis belongs to

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

        # Define JSON schema for query generation
        schema = {
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

        try:
            # Call LLM to generate query
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "hypothesis_query",
                        "strict": True,
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)

            # Log to structured log
            if self.logger:
                self.logger.log_hypothesis_query_generation(
                    task_id=task.id,
                    hypothesis_id=hypothesis['id'],
                    source_name=source_display_name,
                    query=result['query'],
                    reasoning=result['reasoning']
                )

            # Also print for real-time visibility
            print(f"      Query: '{result['query']}'")
            print(f"      Reasoning: {result['reasoning']}")

            return result["query"]

        # Query reformulation failure - acceptable to proceed with existing query
        except Exception as e:
            logger.error(f"Hypothesis {hypothesis['id']} query generation failed for {source_display_name}: {type(e).__name__}: {e}", exc_info=True)
            return None

    async def _generate_initial_query(
        self: "SimpleDeepResearch",
        hypothesis: Dict[str, Any],
        source_name: str,
        source_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate first query from hypothesis (no query history yet).

        This is separate from _generate_next_query_or_stop because:
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
        # Use existing hypothesis query generation prompt
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

    async def _generate_next_query_or_stop(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        hypothesis: Dict[str, Any],
        source_name: str,
        query_history: List[Dict],
        source_metadata: Dict,
        total_results_accepted: int
    ) -> Dict[str, Any]:
        """
        LLM decides: continue with next query or stop (saturated).

        Args:
            task: Research task
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
                "strategies_tried": ["list", "of", "strategies"],  # Strategy diversity assessment
                "next_query_suggestion": "...",  # if CONTINUE
                "next_query_reasoning": "...",   # if CONTINUE
                "expected_value": "high" | "medium" | "low",
                "remaining_gaps": [...]  # Updated list of info gaps
            }
        """
        # NOTE: information_gaps should be updated dynamically:
        # - Initial gaps from hypothesis generation
        # - LLM updates "remaining_gaps" field after each query
        # - Caller updates hypothesis['information_gaps'] with remaining_gaps
        # This enables adaptive query generation targeting unaddressed gaps

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

        # LLM decision
        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "saturation_decision",
                    "strict": True,
                    "schema": {
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
                }
            }
        )

        decision = json.loads(response.choices[0].message.content)
        return decision
