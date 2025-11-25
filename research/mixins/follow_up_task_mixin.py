#!/usr/bin/env python3
"""
Follow-up task generation mixin for deep research.

Provides LLM-based follow-up task generation based on coverage gaps.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from typing import List, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch, ResearchTask

logger = logging.getLogger(__name__)


class FollowUpTaskMixin:
    """
    Mixin providing follow-up task generation based on coverage gaps.

    Requires host class to have:
        - self.completed_tasks: List of completed ResearchTask
        - self.task_queue: List of pending ResearchTask
        - self.max_tasks: int
        - self.max_follow_ups_per_task: Optional[int]
        - self.research_question: str
    """

    def _should_create_follow_ups(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        total_pending_workload: int = 0
    ) -> bool:
        """
        Decide if we should create follow-up tasks based on coverage quality.

        Improvements (2025-11-19):
        - Removed hardcoded heuristics (entities_found >= 3, total_results >= 5)
        - LLM decides if follow-ups needed based on coverage gaps (in _create_follow_up_tasks)
        - Only check: coverage score < 95% and room in workload
        - Aligns with "no hardcoded limits" design philosophy

        Args:
            task: Completed task to evaluate
            total_pending_workload: Total pending tasks (queue + currently executing batch)

        Returns:
            True if follow-ups should be created (LLM will decide actual count 0-N)
        """
        # Phase 5: Check if LLM assessment suggests coverage is excellent
        # No quantitative threshold - trust LLM qualitative assessment
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        if coverage_decisions:
            latest_coverage = coverage_decisions[-1]
            # If LLM said "stop" with no gaps, coverage is likely sufficient
            decision = latest_coverage.get("decision", "continue")
            gaps = latest_coverage.get("gaps_identified", [])
            if decision == "stop" and not gaps:
                logger.info(f"Skipping follow-ups for task {task.id}: Coverage assessment shows sufficient coverage (no critical gaps)")
                return False

        # Codex fix: Check TOTAL workload (completed + pending + would-be follow-ups)
        # This prevents follow-up explosion when parallel execution creates many tasks at once
        # Use configured limit or reasonable default (3) to avoid blocking follow-ups
        max_follow_ups = self.max_follow_ups_per_task if self.max_follow_ups_per_task is not None else 3
        total_workload_if_created = (
            len(self.completed_tasks) +  # Already completed
            total_pending_workload +      # Queue + current batch remainder
            max_follow_ups                # Would-be follow-ups
        )

        # Only check if there's room in workload - LLM decides if follow-ups are actually needed
        return total_workload_if_created < self.max_tasks

    async def _create_follow_up_tasks(
        self: "SimpleDeepResearch",
        parent_task: "ResearchTask",
        current_task_id: int
    ) -> List["ResearchTask"]:
        """
        Create follow-up tasks based on coverage gaps using LLM intelligence.

        Improvements (2025-11-19):
        - LLM-powered gap analysis (not hardcoded entity concatenation)
        - Focus on INFORMATION gaps (timeline, process, conditions) not entity permutations
        - 0-N follow-ups based on coverage quality (no hardcoded limits)
        - Context-based query generation (same principles as task_decomposition.j2)
        """
        # Import ResearchTask here to avoid circular import
        from research.deep_research import ResearchTask

        # Extract coverage data
        coverage_decisions = parent_task.metadata.get("coverage_decisions", [])
        if not coverage_decisions:
            # No coverage data available - skip follow-ups (can't do gap analysis)
            logger.info(f"No coverage data for task {parent_task.id} - skipping follow-ups")
            return []

        # Get latest coverage assessment
        latest_coverage = coverage_decisions[-1]
        assessment_text = latest_coverage.get("assessment", "")
        gaps_identified = latest_coverage.get("gaps_identified", [])

        # Consolidate gaps from all coverage decisions
        all_gaps = []
        for decision in coverage_decisions:
            all_gaps.extend(decision.get("gaps_identified", []))

        # Remove duplicate gaps
        unique_gaps = list(dict.fromkeys(all_gaps))  # Preserves order

        # Gather all existing tasks to avoid duplicates (completed + queue)
        # This gives the LLM full context about what's already been explored
        existing_tasks = []
        for t in self.completed_tasks:
            existing_tasks.append({
                "id": t.id,
                "query": t.query,
                "status": "completed"
            })
        for t in self.task_queue:
            existing_tasks.append({
                "id": t.id,
                "query": t.query,
                "status": "pending"
            })

        # Render follow-up generation prompt
        prompt = render_prompt(
            "deep_research/follow_up_generation.j2",
            research_question=self.research_question,
            parent_task=parent_task,
            coverage_decisions=coverage_decisions,
            gaps_identified=unique_gaps,
            latest_assessment=assessment_text,  # Phase 5: Use prose, not score
            existing_tasks=existing_tasks  # NEW: Give LLM global task context
        )

        # Call LLM to generate follow-ups
        try:
            schema = {
                "type": "object",
                "properties": {
                    "follow_up_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "rationale": {"type": "string"}
                            },
                            "required": ["query", "rationale"],
                            "additionalProperties": False
                        }
                    },
                    "decision_reasoning": {"type": "string"}
                },
                "required": ["follow_up_tasks", "decision_reasoning"],
                "additionalProperties": False
            }

            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "follow_up_generation",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"Follow-up generation for task {parent_task.id}: {result['decision_reasoning']}")

        # Follow-up generation failure - acceptable to continue without follow-ups
        except Exception as e:
            logger.error(f"Follow-up generation failed for task {parent_task.id}: {type(e).__name__}: {e}", exc_info=True)
            return []

        # Build set of existing queries for deduplication
        existing_queries = set()
        for task in self.task_queue + self.completed_tasks:
            existing_queries.add(task.query.lower())

        # Create ResearchTask objects from LLM output
        follow_ups = []
        for task_data in result["follow_up_tasks"]:
            # Skip if duplicate query already exists
            if task_data["query"].lower() in existing_queries:
                logger.info(f"Skipping duplicate follow-up query: {task_data['query']}")
                continue

            follow_up = ResearchTask(
                id=current_task_id + len(follow_ups),
                query=task_data["query"],
                rationale=task_data["rationale"],
                parent_task_id=parent_task.id
            )

            # Log individual follow-up creation with full details for auditing
            print(f"   📌 [FOLLOW_UP] Task {follow_up.id} (parent: {parent_task.id}): {follow_up.query[:80]}")

            follow_ups.append(follow_up)
            existing_queries.add(task_data["query"].lower())

        print(f"✓ Created {len(follow_ups)} follow-up task(s) for task {parent_task.id}")
        return follow_ups
