#!/usr/bin/env python3
"""
Hypothesis generation and coverage assessment mixin for deep research.

Provides LLM-based hypothesis generation and coverage assessment.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
import time
from typing import Any, Dict, List, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch, ResearchTask

logger = logging.getLogger(__name__)


class HypothesisMixin:
    """
    Mixin providing hypothesis generation and coverage assessment.

    Requires host class to have:
        - self._get_available_source_names(): method returning List[str]
        - self.max_hypotheses_per_task: int
        - self.max_time_per_task_seconds: int
        - self.max_hypotheses_to_execute: int
    """

    async def _generate_hypotheses(
        self: "SimpleDeepResearch",
        task_query: str,
        research_question: str,
        all_tasks: List["ResearchTask"],
        existing_hypotheses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate 1-5 investigative hypotheses for a research subtask.

        Phase 3A: Foundation - Hypothesis generation only (no execution yet)

        Args:
            task_query: The specific subtask query to generate hypotheses for
            research_question: The original user research question (for context)
            all_tasks: All research tasks (completed + pending) to avoid duplicate angles
            existing_hypotheses: Hypotheses already generated for this task (for diversity)

        Returns:
            Dict containing:
                - hypotheses: List of hypothesis objects (1-5 items)
                - coverage_assessment: Why this set provides sufficient coverage
        """
        # Get available sources for hypothesis generation
        available_sources = self._get_available_source_names()

        # Format existing tasks for prompt context
        formatted_tasks = [
            {
                "id": task.id,
                "status": task.status,
                "query": task.query
            }
            for task in all_tasks
        ]

        # Render hypothesis generation prompt
        prompt = render_prompt(
            "deep_research/hypothesis_generation.j2",
            research_question=research_question,
            task_query=task_query,
            available_sources=available_sources,
            max_hypotheses=self.max_hypotheses_per_task,
            existing_tasks=formatted_tasks,
            existing_hypotheses=existing_hypotheses or []
        )

        # Define JSON schema for hypothesis structure
        schema = {
            "type": "object",
            "properties": {
                "hypotheses": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": self.max_hypotheses_per_task,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "description": "Hypothesis ID (1, 2, 3, ...)"},
                            "statement": {"type": "string", "description": "What this hypothesis is looking for (1-2 sentences)"},
                            "confidence": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Confidence this pathway will yield results (0-100%)"},
                            "confidence_reasoning": {"type": "string", "description": "Why this confidence level (1 sentence)"},
                            "search_strategy": {
                                "type": "object",
                                "properties": {
                                    "sources": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of database integration names to query"
                                    },
                                    "signals": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Keywords/patterns that indicate relevance"
                                    },
                                    "expected_entities": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Organizations/people/programs/technologies expected if hypothesis succeeds"
                                    }
                                },
                                "required": ["sources", "signals", "expected_entities"],
                                "additionalProperties": False
                            },
                            "exploration_priority": {"type": "integer", "minimum": 1, "description": "Order to explore (1=first, 2=second, etc.)"},
                            "priority_reasoning": {"type": "string", "description": "Why this exploration order (1 sentence)"}
                        },
                        "required": ["id", "statement", "confidence", "confidence_reasoning", "search_strategy", "exploration_priority", "priority_reasoning"],
                        "additionalProperties": False
                    },
                    "minItems": 1,
                    "maxItems": 5
                },
                "coverage_assessment": {
                    "type": "string",
                    "description": "Why this set of hypotheses provides sufficient coverage"
                }
            },
            "required": ["hypotheses", "coverage_assessment"],
            "additionalProperties": False
        }

        # Call LLM with hypothesis generation prompt
        response = await acompletion(
            model=config.get_model("task_decomposition"),  # Use same model as task decomposition
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "hypothesis_generation",
                    "schema": schema
                }
            }
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        # Log hypothesis generation
        hypothesis_count = len(result["hypotheses"])
        print(f"\n🔬 Generated {hypothesis_count} investigative hypothesis/hypotheses:")
        for hyp in result["hypotheses"]:
            print(f"   Hypothesis {hyp['id']}: {hyp['statement']}")
            print(f"   → Confidence: {hyp['confidence']}% - {hyp['confidence_reasoning']}")
            print(f"   → Priority: {hyp['exploration_priority']} - {hyp['priority_reasoning']}")
            print(f"   → Sources: {', '.join(hyp['search_strategy']['sources'])}")
            print()

        print(f"📊 Coverage Assessment: {result['coverage_assessment']}\n")

        return result

    async def _assess_coverage(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        research_question: str,
        start_time: float
    ) -> Dict:
        """
        LLM-driven coverage assessment (Phase 3C).

        Decides whether to continue executing hypotheses or stop based on:
        - Incremental gain (new vs duplicate results)
        - Coverage gaps (unexplored angles)
        - Information sufficiency (total results/entities)
        - Resource budget (time/hypotheses remaining)
        - Hypothesis quality (remaining hypotheses)

        Args:
            task: Task with executed hypotheses so far
            research_question: Original research question
            start_time: Task start timestamp (for time budget tracking)

        Returns:
            Dict with LLM coverage decision:
            {
                "decision": "continue" | "stop",
                "assessment": str,  # Qualitative prose assessment
                "gaps_identified": List[str],
                "facts": {  # Auto-injected by system
                    "results_new": int,
                    "results_duplicate": int,
                    "incremental_gain_last_pct": int,
                    ...
                }
            }
        """
        # Prepare hypothesis execution summary
        hypotheses_all = task.hypotheses.get("hypotheses", [])
        executed_count = len(task.hypothesis_runs)

        # Build executed hypotheses with delta metrics
        hypotheses_executed = []
        for run in task.hypothesis_runs:
            hypotheses_executed.append({
                "hypothesis_id": run["hypothesis_id"],
                "statement": run["statement"],
                "priority": run.get("priority", "N/A"),
                "confidence": run.get("confidence", "N/A"),
                "delta_metrics": run["delta_metrics"],
                "sources": run["sources"]
            })

        # Build remaining hypotheses list
        executed_ids = {run["hypothesis_id"] for run in task.hypothesis_runs}
        hypotheses_remaining = []
        for hyp in hypotheses_all:
            hyp_id = hyp.get("id", "unknown")
            if hyp_id not in executed_ids:
                hypotheses_remaining.append({
                    "id": hyp_id,
                    "statement": hyp.get("statement", ""),
                    "exploration_priority": hyp.get("exploration_priority", "N/A"),
                    "confidence": hyp.get("confidence", "N/A")
                })

        # Calculate time elapsed
        time_elapsed_seconds = int(time.time() - start_time)

        # Render coverage assessment prompt
        prompt = render_prompt(
            "deep_research/coverage_assessment.j2",
            research_question=research_question,
            task_query=task.query,
            task_id=task.id,
            hypotheses_executed=hypotheses_executed,
            executed_count=executed_count,
            total_hypotheses=len(hypotheses_all),
            hypotheses_remaining=hypotheses_remaining,
            task_total_results=len(task.accumulated_results),
            task_total_entities=len(task.entities_found) if task.entities_found else 0,
            time_elapsed_seconds=time_elapsed_seconds,
            max_time_seconds=self.max_time_per_task_seconds,
            max_hypotheses=self.max_hypotheses_to_execute
        )

        # Define schema for coverage decision
        schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["continue", "stop"],
                    "description": "Whether to continue executing hypotheses or stop"
                },
                "assessment": {
                    "type": "string",
                    "description": "2-4 sentences explaining coverage achieved, gaps remaining, and reasoning for decision. Be specific and reference actual findings."
                },
                "gaps_identified": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific remaining gaps (1-3 items if decision is continue, empty if stop)"
                }
            },
            "required": ["decision", "assessment", "gaps_identified"],
            "additionalProperties": False
        }

        # Call LLM for coverage assessment
        try:
            response = await acompletion(
                model=config.get_model("analysis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_schema", "json_schema": {"name": "coverage_decision", "strict": True, "schema": schema}}
            )

            decision = json.loads(response.choices[0].message.content)

            # Phase 5: Auto-inject facts (system calculates, LLM doesn't)
            # Calculate incremental gain from last hypothesis
            if task.hypothesis_runs:
                last_run = task.hypothesis_runs[-1]
                delta = last_run.get("delta_metrics", {})
                incremental_gain_pct = int(delta.get("results_new", 0) / delta.get("total_results", 1) * 100) if delta.get("total_results", 0) > 0 else 0
            else:
                incremental_gain_pct = 0

            decision["facts"] = {
                "results_new": sum(run.get("delta_metrics", {}).get("results_new", 0) for run in task.hypothesis_runs),
                "results_duplicate": sum(run.get("delta_metrics", {}).get("results_duplicate", 0) for run in task.hypothesis_runs),
                "incremental_gain_last_pct": incremental_gain_pct,
                "entities_new": sum(run.get("delta_metrics", {}).get("entities_new", 0) for run in task.hypothesis_runs),
                "hypotheses_executed": executed_count,
                "hypotheses_remaining": len(hypotheses_all) - executed_count,
                "time_elapsed_seconds": time_elapsed_seconds,
                "time_remaining_seconds": self.max_time_per_task_seconds - time_elapsed_seconds
            }

            # Log coverage decision
            logger.info(f"Coverage assessment (Task {task.id}):")
            logger.info(f"   Decision: {decision['decision'].upper()}")
            logger.info(f"   Assessment: {decision['assessment'][:150]}...")
            logger.info(f"   Facts: {decision['facts']['results_new']} new, {decision['facts']['results_duplicate']} dup")

            return decision

        # Coverage assessment failure - acceptable to continue without saturation check
        except Exception as e:
            logger.error(f"Coverage assessment failed: {type(e).__name__}: {e}", exc_info=True)
            # Fallback: continue if under hard ceilings
            return {
                "decision": "continue" if (executed_count < self.max_hypotheses_to_execute and time_elapsed_seconds < self.max_time_per_task_seconds) else "stop",
                "assessment": f"Coverage assessment failed ({type(e).__name__}). Defaulting to hard ceiling logic: continuing if hypotheses remaining and time allows.",
                "gaps_identified": ["Coverage assessment error - using fallback logic"],
                "facts": {  # Minimal facts for failed assessment
                    "results_new": 0,
                    "results_duplicate": 0,
                    "incremental_gain_last_pct": 0,
                    "entities_new": 0,
                    "hypotheses_executed": executed_count,
                    "hypotheses_remaining": len(hypotheses_all) - executed_count,
                    "time_elapsed_seconds": time_elapsed_seconds,
                    "time_remaining_seconds": self.max_time_per_task_seconds - time_elapsed_seconds
                }
            }
