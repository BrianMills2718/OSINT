"""
Research Supervisor

Executes research briefs via task delegation and source routing.

Key Features:
- Category-based source routing (uses DatabaseMetadata.category)
- Parallel subtask execution (independent workers)
- Graceful degradation (fallback to shotgun if routing fails)
- Result synthesis (aggregate findings)

Architecture:
- execute(): Main entry point, orchestrates full research flow
- _route_to_sources(): Maps categories to source IDs
- _execute_subtask(): Executes single subtask via ParallelExecutor
- _synthesize_results(): Aggregates findings into final report
"""

import json
import logging
import asyncio
from typing import Dict, List, Any
from schemas.research_brief import ResearchBrief
from llm_utils import acompletion_with_role


class ResearchSupervisor:
    """
    Execute research briefs via task decomposition and source routing.

    Delegates subtasks to ParallelExecutor with selective source lists.
    """

    def __init__(self, parallel_executor, registry):
        """
        Initialize ResearchSupervisor.

        Args:
            parallel_executor: ParallelExecutor instance for executing queries
            registry: DatabaseRegistry instance for source metadata
        """
        self.parallel_executor = parallel_executor
        self.registry = registry

        logging.info("ResearchSupervisor initialized")

    async def execute(self, brief: ResearchBrief) -> Dict[str, Any]:
        """
        Execute research brief via task delegation.

        Args:
            brief: Validated ResearchBrief from ScopingAgent

        Returns:
            Dict with synthesized results:
            {
                "objective": str,
                "synthesis": str,  # Aggregated findings
                "subtask_results": List[Dict]  # Raw results per subtask
            }
        """
        logging.info(
            f"Executing research brief: {len(brief.sub_questions)} subtasks, "
            f"objective: {brief.objective[:60]}..."
        )

        # Create tasks for parallel execution
        tasks = []
        for i, sub_q in enumerate(brief.sub_questions):
            logging.info(
                f"Subtask {i+1}/{len(brief.sub_questions)}: {sub_q.question[:60]}... "
                f"(categories: {sub_q.suggested_categories})"
            )

            # Route categories to source IDs
            source_ids = self._route_to_sources(sub_q.suggested_categories)

            # Create execution task
            task = self._execute_subtask(
                question=sub_q.question,
                source_ids=source_ids,
                subtask_index=i
            )
            tasks.append(task)

        # Execute all subtasks in parallel
        logging.info(f"Executing {len(tasks)} subtasks in parallel...")
        subtask_results = await asyncio.gather(*tasks)

        # Synthesize findings
        logging.info("Synthesizing findings...")
        final_result = await self._synthesize_results(brief, subtask_results)

        logging.info("Research execution complete")
        return final_result

    def _route_to_sources(self, categories: List[str]) -> List[str]:
        """
        Map categories to source IDs using DatabaseMetadata.category.

        Args:
            categories: List of category names (e.g., ["government_contracts", "social_media"])

        Returns:
            List of source IDs to query

        Example:
            categories = ["government_contracts"]
            → returns ["sam_gov", "usajobs", "clearancejobs"]
        """
        source_ids = set()  # Use set to deduplicate

        for integration_id in self.registry.list_enabled_ids():
            try:
                integration = self.registry.get_instance(integration_id)
                metadata = integration.metadata

                # Match on category
                if metadata.category in categories:
                    source_ids.add(integration_id)
                    logging.debug(f"Matched {integration_id} via category: {metadata.category}")
                    continue

                # Match on tags (if present)
                if hasattr(metadata, 'tags') and metadata.tags:
                    for tag in metadata.tags:
                        if tag in categories or any(cat in tag for cat in categories):
                            source_ids.add(integration_id)
                            logging.debug(f"Matched {integration_id} via tag: {tag}")
                            break

            except Exception as e:
                logging.warning(f"Error checking {integration_id} metadata: {e}")
                continue

        # Fallback: if no matches, use all sources (shotgun mode)
        if not source_ids:
            logging.warning(
                f"No sources matched categories {categories}, "
                f"falling back to all enabled sources"
            )
            source_ids = set(self.registry.list_enabled_ids())

        result = list(source_ids)
        logging.info(f"Routed categories {categories} → {len(result)} sources: {result}")
        return result

    async def _execute_subtask(
        self,
        question: str,
        source_ids: List[str],
        subtask_index: int
    ) -> Dict[str, Any]:
        """
        Execute single subtask using ParallelExecutor.

        Args:
            question: Research question for this subtask
            source_ids: List of source IDs to query
            subtask_index: Index for logging

        Returns:
            Dict with subtask results:
            {
                "question": str,
                "source_ids": List[str],
                "results": Dict,  # Raw results from ParallelExecutor
                "num_results": int
            }
        """
        logging.info(f"[Subtask {subtask_index+1}] Executing: {question[:60]}...")

        try:
            # Call ParallelExecutor with selective sources
            results = await self.parallel_executor.execute_with_sources(
                research_question=question,
                source_ids=source_ids,
                limit=10  # Results per source
            )

            # Count total results
            num_results = 0
            if isinstance(results, dict) and 'results' in results:
                for source_results in results['results'].values():
                    if isinstance(source_results, dict) and 'results' in source_results:
                        num_results += len(source_results['results'])

            logging.info(
                f"[Subtask {subtask_index+1}] Complete: {num_results} results "
                f"from {len(source_ids)} sources"
            )

            return {
                "question": question,
                "source_ids": source_ids,
                "results": results,
                "num_results": num_results
            }

        except Exception as e:
            logging.error(f"[Subtask {subtask_index+1}] Failed: {e}", exc_info=True)
            return {
                "question": question,
                "source_ids": source_ids,
                "error": str(e),
                "num_results": 0
            }

    async def _synthesize_results(
        self,
        brief: ResearchBrief,
        subtask_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Aggregate subtask results into final report.

        Uses LLM to synthesize findings from multiple subtasks.

        Args:
            brief: Original research brief
            subtask_results: Results from all subtasks

        Returns:
            Dict with final report:
            {
                "objective": str,
                "synthesis": str,  # LLM-generated summary
                "subtask_results": List[Dict],  # Raw results
                "total_results": int
            }
        """
        # Count total results
        total_results = sum(st.get('num_results', 0) for st in subtask_results)

        logging.info(f"Synthesizing {total_results} results across {len(subtask_results)} subtasks")

        # If no results, return early
        if total_results == 0:
            return {
                "objective": brief.objective,
                "synthesis": "No results found across any data sources.",
                "subtask_results": subtask_results,
                "total_results": 0
            }

        # Prepare summary of results for LLM
        subtask_summaries = []
        for i, st in enumerate(subtask_results, 1):
            if 'error' in st:
                subtask_summaries.append(f"{i}. {st['question']}\n   Error: {st['error']}")
            else:
                subtask_summaries.append(
                    f"{i}. {st['question']}\n   Found: {st['num_results']} results from {len(st['source_ids'])} sources"
                )

        summary_text = "\n\n".join(subtask_summaries)

        # Use LLM to synthesize findings
        synthesis_prompt = f"""Research Objective: {brief.objective}

Sub-task Results:
{summary_text}

Total Results: {total_results} across {len(subtask_results)} subtasks

Synthesize these findings into a coherent 2-3 paragraph summary that addresses the research objective.
Focus on what was found, key patterns, and any gaps."""

        try:
            response = await acompletion_with_role(
                role="synthesis",
                messages=[{"role": "user", "content": synthesis_prompt}]
            )

            synthesis = response.choices[0].message.content

        except Exception as e:
            logging.error(f"Synthesis failed: {e}", exc_info=True)
            synthesis = (
                f"Found {total_results} results across {len(subtask_results)} subtasks. "
                f"Synthesis failed due to LLM error."
            )

        return {
            "objective": brief.objective,
            "synthesis": synthesis,
            "subtask_results": subtask_results,
            "total_results": total_results
        }
