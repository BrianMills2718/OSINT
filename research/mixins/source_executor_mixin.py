#!/usr/bin/env python3
"""
Source execution mixin for deep research.

Provides hypothesis and source execution capabilities.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import asyncio
import logging
import time
from dataclasses import asdict
from typing import Any, Dict, List, TYPE_CHECKING

from config_loader import config
from integrations.registry import registry

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch, ResearchTask

logger = logging.getLogger(__name__)


class SourceExecutorMixin:
    """
    Mixin providing source and hypothesis execution.

    Requires host class to have:
        - self.logger: ExecutionLogger instance
        - self.max_queries_per_source: Dict[str, int]
        - self.max_time_per_source_seconds: int
        - self.query_saturation_enabled: bool
        - self.coverage_mode: bool
        - self.max_hypotheses_to_execute: int
        - self.max_time_per_task_seconds: int
        - self.mcp_tools: List[Dict]
        - self.integrations: List[str]
        - Methods from other mixins:
            - _generate_initial_query (QueryGenerationMixin)
            - _generate_next_query_or_stop (QueryGenerationMixin)
            - _generate_hypothesis_query (QueryGenerationMixin)
            - _validate_result_relevance (ResultFilterMixin)
            - _assess_coverage (HypothesisMixin)
        - Methods from host class:
            - _map_hypothesis_sources
            - _deduplicate_with_attribution
            - _compute_hypothesis_delta
            - _call_mcp_tool
            - _search_brave
    """

    async def _execute_source_with_saturation(
        self: "SimpleDeepResearch",
        task_id: int,
        task: "ResearchTask",
        hypothesis: Dict[str, Any],
        source_name: str
    ) -> List[Dict[str, Any]]:
        """
        Execute queries against single source until saturated.

        Args:
            task_id: Task ID
            task: Research task
            hypothesis: Hypothesis dictionary
            source_name: Name of the source

        Returns:
            List of accepted results from all queries
        """
        query_history = []
        all_results = []
        seen_result_urls = set()  # Track URLs for within-source deduplication
        start_time = time.time()

        # Get source-specific limits - use registry as single source of truth
        max_queries = self.max_queries_per_source.get(source_name, 5)
        max_time = self.max_time_per_source_seconds
        metadata = registry.get_metadata(source_name)
        source_metadata = asdict(metadata) if metadata else {}

        # Convert DatabaseCategory enum to string for JSON serialization in prompts
        if source_metadata and 'category' in source_metadata:
            category = source_metadata['category']
            if hasattr(category, 'value'):
                source_metadata['category'] = category.value

        # Log saturation start
        if self.logger:
            self.logger.log_source_saturation_start(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                max_queries=max_queries,
                max_time_seconds=max_time
            )

        while True:  # No hardcoded loop count
            query_num = len(query_history) + 1

            try:
                # FIRST QUERY: Different logic than subsequent queries
                if len(query_history) == 0:
                    # Generate initial query from hypothesis (no history yet)
                    initial = await self._generate_initial_query(
                        hypothesis=hypothesis,
                        source_name=source_name,
                        source_metadata=source_metadata
                    )
                    query_decision = {
                        'decision': 'CONTINUE',
                        'reasoning': 'Initial query for hypothesis',
                        'next_query_suggestion': initial['query'],
                        'next_query_reasoning': initial['reasoning'],
                        'confidence': 100,
                        'expected_value': 'high'
                    }
                else:
                    # SUBSEQUENT QUERIES: Check saturation and generate next query
                    query_decision = await self._generate_next_query_or_stop(
                        task=task,
                        hypothesis=hypothesis,
                        source_name=source_name,
                        query_history=query_history,
                        source_metadata=source_metadata,
                        total_results_accepted=len(all_results)
                    )

                    # Update hypothesis information_gaps dynamically (if provided)
                    if 'remaining_gaps' in query_decision:
                        hypothesis['information_gaps'] = query_decision['remaining_gaps']

                    # PRIMARY EXIT: LLM says saturated
                    if query_decision['decision'] == 'SATURATED':
                        if self.logger:
                            self.logger.log_source_saturation_complete(
                                task_id=task_id,
                                hypothesis_id=hypothesis.get('id'),
                                source_name=source_name,
                                exit_reason='llm_saturated',
                                queries_executed=len(query_history),
                                results_accepted=len(all_results),
                                saturation_reasoning=query_decision['reasoning'],
                                decision_confidence=query_decision.get('confidence', 0),
                                strategies_tried=query_decision.get('strategies_tried', [])
                            )
                        break

            # Query reformulation failure - acceptable to proceed with existing query
            except Exception as e:
                logger.error(f"Error generating query for {source_name}: {e}", exc_info=True)
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='query_generation_error',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Query generation failed: {str(e)}"
                    )
                break

            # Validate query suggestion exists
            query = query_decision.get('next_query_suggestion', '').strip()
            if not query:
                logger.warning(f"Empty query suggestion from LLM for {source_name}")
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='empty_query_suggestion',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning="LLM suggested empty query"
                    )
                break

            query_reasoning = query_decision.get('next_query_reasoning', '')

            if self.logger:
                self.logger.log_query_attempt(
                    task_id=task_id,
                    hypothesis_id=hypothesis.get('id'),
                    source_name=source_name,
                    query_num=query_num,
                    query=query,
                    reasoning=query_reasoning,
                    expected_value=query_decision.get('expected_value', 'unknown')
                )

            try:
                # Call source API using existing infrastructure
                # Map display name -> tool name (use registry's normalize function)
                tool_name = registry.normalize_source_name(source_name)
                if not tool_name:
                    logger.error(f"Unknown source: {source_name}")
                    query_history.append({
                        'query': query,
                        'reasoning': query_reasoning,
                        'results_total': 0,
                        'results_accepted': 0,
                        'results_rejected': 0,
                        'error': f"Unknown source: {source_name}",
                        'effectiveness': 0
                    })
                    continue

                # Get limit from config
                limit = config.get_integration_limit(source_name)

                # Execute based on source type
                results = []
                if tool_name in [t["name"] for t in self.mcp_tools]:
                    # MCP tool path (SAM, DVIDS, USAJobs, etc.)
                    mcp_tool = next(t for t in self.mcp_tools if t["name"] == tool_name)
                    tool_result = await self._call_mcp_tool(
                        tool_config=mcp_tool,
                        query=query,
                        param_adjustments=None,
                        task_id=task_id,
                        attempt=0,
                        exec_logger=self.logger,
                        skip_relevance_check=True  # Hypothesis already selected this source with full context
                    )
                    if tool_result.get("success"):
                        results = tool_result.get("results", [])
                    else:
                        error_msg = tool_result.get('error', 'Unknown error')
                        logger.error(f"MCP tool {source_name} failed: {error_msg}")
                        query_history.append({
                            'query': query,
                            'reasoning': query_reasoning,
                            'results_total': 0,
                            'results_accepted': 0,
                            'results_rejected': 0,
                            'error': error_msg,
                            'effectiveness': 0
                        })
                        continue

                elif tool_name == "brave_search":
                    # Brave search path (non-MCP)
                    results = await self._search_brave(query, max_results=limit)

            # Query reformulation failure - acceptable to proceed with existing query
            except Exception as e:
                logger.error(f"Source query failed for {source_name}: {e}", exc_info=True)
                # Track failed attempt and continue
                query_history.append({
                    'query': query,
                    'reasoning': query_reasoning,
                    'results_total': 0,
                    'results_accepted': 0,
                    'results_rejected': 0,
                    'error': str(e),
                    'effectiveness': 0
                })
                continue  # Try next query

            # Filter results using EXISTING relevance evaluation
            if results:
                # Use hypothesis statement as the query context for filtering
                should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                    task_query=hypothesis['statement'],  # Use hypothesis statement
                    research_question=task.query,  # Parent task query
                    sample_results=results
                )

                # Transform to expected format
                filtered = {
                    'accepted_results': [results[i] for i in relevant_indices if i < len(results)] if should_accept else [],
                    'rejection_themes': [relevance_reason] if not should_accept else []
                }
            else:
                filtered = {'accepted_results': [], 'rejection_themes': []}

            # Deduplicate within source (track URLs seen)
            accepted = filtered.get('accepted_results', [])
            new_results = []
            duplicate_count = 0

            for result in accepted:
                result_url = result.get('url', '') or result.get('id', '')
                if result_url and result_url not in seen_result_urls:
                    new_results.append(result)
                    seen_result_urls.add(result_url)
                else:
                    duplicate_count += 1

            all_results.extend(new_results)

            # Track query attempt
            query_history.append({
                'query': query,
                'reasoning': query_reasoning,
                'results_total': len(results),
                'results_accepted': len(new_results),
                'results_rejected': len(results) - len(accepted),
                'results_duplicate': duplicate_count,
                'rejection_themes': filtered.get('rejection_themes', []),
                'effectiveness': len(new_results) / len(results) if results else 0
            })

            # SECONDARY EXIT: User-configured query limit
            if len(query_history) >= max_queries:
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='max_queries_reached',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Reached user-configured limit: {max_queries} queries"
                    )
                break

            # TERTIARY EXIT: User-configured time limit
            elapsed = time.time() - start_time
            if elapsed > max_time:
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='time_limit_reached',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Reached time limit: {max_time}s"
                    )
                break

        return all_results

    async def _execute_hypothesis(
        self: "SimpleDeepResearch",
        hypothesis: Dict,
        task: "ResearchTask",
        research_question: str
    ) -> List[Dict]:
        """
        Execute a single hypothesis with its search strategy (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with id, statement, search_strategy
            task: Parent task this hypothesis belongs to
            research_question: Original research question

        Returns:
            List of results with hypothesis_id tagging
        """
        hypothesis_id = hypothesis["id"]
        print(f"\n   Executing Hypothesis {hypothesis_id}: {hypothesis['statement']}")

        # Map hypothesis sources (display names -> tool names)
        source_tool_names = self._map_hypothesis_sources(hypothesis)
        if not source_tool_names:
            logger.warning(f"Hypothesis {hypothesis_id}: No valid sources to search")
            return []

        # Execute sources (saturation mode or single-shot mode)
        all_results = []

        if self.query_saturation_enabled:
            # NEW: Query saturation mode (iterative querying per source)
            print(f"   Query saturation enabled - iterative querying per source")
            for tool_name in source_tool_names:
                try:
                    source_display = registry.get_display_name(tool_name)
                    print(f"   Saturating {source_display}...")

                    # Execute with saturation (multiple queries until LLM determines saturation)
                    source_results = await self._execute_source_with_saturation(
                        task_id=task.id,
                        task=task,
                        hypothesis=hypothesis,
                        source_name=source_display
                    )

                    print(f"   {source_display}: {len(source_results)} results (after saturation)")
                    all_results.extend(source_results)

                # LLM call failed - hypothesis generation is optional, can proceed without
                except Exception as e:
                    logger.error(f"Hypothesis {hypothesis_id} saturation failed for {source_display}: {type(e).__name__}: {e}", exc_info=True)
                    continue  # Continue with other sources
        else:
            # OLD: Single-shot mode (one query per source)
            for tool_name in source_tool_names:
                try:
                    # Generate source-specific query
                    query = await self._generate_hypothesis_query(
                        hypothesis=hypothesis,
                        source_tool_name=tool_name,
                        research_question=research_question,
                        task_query=task.query,
                        task=task
                    )

                    if not query:
                        continue  # Query generation failed, skip this source

                    # Execute search (single-shot, no retries)
                    source_display = registry.get_display_name(tool_name)
                    print(f"   Searching {source_display}: '{query}'")

                    # Use existing search infrastructure
                    # Get limit from config
                    limit = config.get_integration_limit(source_display)

                    # Execute MCP search
                    if tool_name in [t["name"] for t in self.mcp_tools]:
                        mcp_tool = next(t for t in self.mcp_tools if t["name"] == tool_name)

                        # Call MCP tool using class method
                        tool_result = await self._call_mcp_tool(
                            tool_config=mcp_tool,
                            query=query,
                            param_adjustments=None,  # No param hints in direct hypothesis execution
                            task_id=task.id,
                            attempt=0,
                            exec_logger=self.logger,
                            skip_relevance_check=True  # Hypothesis already selected this source with full context
                        )

                        if tool_result.get("success"):
                            results = tool_result.get("results", [])
                            print(f"   {source_display}: {len(results)} results")
                            all_results.extend(results)
                        else:
                            print(f"   {source_display}: {tool_result.get('error', 'Unknown error')}")
                    elif tool_name == "brave_search":
                        # Web search (non-MCP)
                        results = await self._search_brave(query, max_results=limit)
                        print(f"   {source_display}: {len(results)} results")
                        all_results.extend(results)

                # Query reformulation failure - acceptable to proceed with existing query
                except Exception as e:
                    logger.error(f"Hypothesis {hypothesis_id} search failed for {source_display}: {type(e).__name__}: {e}", exc_info=True)
                    continue  # Continue with other sources

        # Filter hypothesis results for relevance (only in single-shot mode)
        # In saturation mode, results are already filtered per-query
        if all_results and not self.query_saturation_enabled:
            print(f"   Validating relevance of {len(all_results)} hypothesis results...")
            should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                task_query=hypothesis['statement'],  # Use hypothesis statement as query context
                research_question=research_question,
                sample_results=all_results
            )

            decision_str = "ACCEPT" if should_accept else "REJECT"
            print(f"   Decision: {decision_str}")
            print(f"   Reason: {relevance_reason}")
            print(f"   Filtered: {len(relevant_indices)}/{len(all_results)} results kept")

            # Filter to only relevant results
            if should_accept and relevant_indices:
                filtered_results = [all_results[i] for i in relevant_indices if i < len(all_results)]
                discarded_count = len(all_results) - len(filtered_results)
                print(f"   Kept {len(filtered_results)} relevant results, discarded {discarded_count} junk")
                all_results = filtered_results
            elif not should_accept:
                # Reject all results
                print(f"   Rejected all {len(all_results)} results as off-topic")
                all_results = []

        # Deduplicate results with hypothesis tagging
        deduplicated = self._deduplicate_with_attribution(all_results, hypothesis_id)
        print(f"   Hypothesis {hypothesis_id}: {len(deduplicated)} unique results")

        # Compute delta metrics for coverage assessment (Phase 3C)
        delta_metrics = self._compute_hypothesis_delta(task, hypothesis, deduplicated)

        # Record execution summary for reporting/metadata
        try:
            task.hypothesis_runs.append({
                "hypothesis_id": hypothesis_id,
                "statement": hypothesis.get("statement", ""),
                "results_count": len(deduplicated),
                "sources": [registry.get_display_name(s) for s in source_tool_names],
                # Phase 3C: Add delta metrics
                "delta_metrics": delta_metrics
            })
        # LLM call failed - hypothesis generation is optional, can proceed without
        except Exception as e:
            logger.warning(f"Failed to record hypothesis run summary for {hypothesis_id}: {e}", exc_info=True)

        return deduplicated


    async def _execute_hypotheses(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        research_question: str
    ) -> List[Dict]:
        """
        Execute hypotheses for a task.

        Mode behavior:
        - coverage_mode: false -> Parallel execution (Phase 3B)
        - coverage_mode: true -> Sequential with adaptive stopping (Phase 3C)

        Args:
            task: Task with hypotheses to execute
            research_question: Original research question

        Returns:
            Combined deduplicated results from all hypotheses
        """
        if not task.hypotheses or not task.hypotheses.get("hypotheses"):
            return []

        hypotheses = task.hypotheses["hypotheses"]

        # Phase 3C: Sequential execution with coverage assessment
        if self.coverage_mode:
            return await self._execute_hypotheses_sequential(task, research_question, hypotheses)

        # Phase 3B: Parallel execution (backward compatible)
        else:
            return await self._execute_hypotheses_parallel(task, research_question, hypotheses)

    async def _execute_hypotheses_parallel(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        research_question: str,
        hypotheses: List[Dict]
    ) -> List[Dict]:
        """
        Execute all hypotheses in parallel (Phase 3B - default).

        Args:
            task: Task with hypotheses
            research_question: Original research question
            hypotheses: List of hypotheses to execute

        Returns:
            Combined deduplicated results from all hypotheses
        """
        print(f"\n   Executing {len(hypotheses)} hypothesis/hypotheses in parallel...")

        # Execute all hypotheses in parallel
        hypothesis_tasks = [
            self._execute_hypothesis(hyp, task, research_question)
            for hyp in hypotheses
        ]

        try:
            results_by_hypothesis = await asyncio.gather(*hypothesis_tasks, return_exceptions=True)

            # Combine all results, filtering out exceptions
            all_results = []
            for i, result in enumerate(results_by_hypothesis):
                if isinstance(result, Exception):
                    logger.error(f"Hypothesis {i+1} execution failed: {type(result).__name__}: {result}")
                else:
                    all_results.extend(result)

            # Cross-hypothesis deduplication (results may appear across hypotheses)
            # This is already handled by _deduplicate_with_attribution in _execute_hypothesis
            # But we need to deduplicate across hypotheses too
            deduplicated = []
            url_map = {}  # url -> result with hypothesis_ids

            for result in all_results:
                url = result.get("url")
                if not url:
                    deduplicated.append(result)
                    continue

                if url in url_map:
                    # Merge hypothesis attribution
                    existing = url_map[url]
                    if "hypothesis_ids" in existing:
                        # Already multi-attributed
                        if "hypothesis_id" in result:
                            if result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                        elif "hypothesis_ids" in result:
                            for hid in result["hypothesis_ids"]:
                                if hid not in existing["hypothesis_ids"]:
                                    existing["hypothesis_ids"].append(hid)
                    else:
                        # Convert to multi-attribution
                        existing["hypothesis_ids"] = [existing.pop("hypothesis_id")]
                        if "hypothesis_id" in result:
                            if result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                        elif "hypothesis_ids" in result:
                            for hid in result["hypothesis_ids"]:
                                if hid not in existing["hypothesis_ids"]:
                                    existing["hypothesis_ids"].append(hid)
                else:
                    url_map[url] = result
                    deduplicated.append(result)

            print(f"\n   Hypothesis execution complete: {len(deduplicated)} total unique results")
            return deduplicated

        # LLM call failed - hypothesis generation is optional, can proceed without
        except Exception as e:
            logger.error(f"Hypothesis execution failed: {type(e).__name__}: {e}", exc_info=True)
            return []

    async def _execute_hypotheses_sequential(
        self: "SimpleDeepResearch",
        task: "ResearchTask",
        research_question: str,
        hypotheses: List[Dict]
    ) -> List[Dict]:
        """
        Execute hypotheses sequentially with coverage-based stopping (Phase 3C).

        Args:
            task: Task with hypotheses
            research_question: Original research question
            hypotheses: List of hypotheses to execute (sorted by priority)

        Returns:
            Combined deduplicated results from executed hypotheses
        """
        print(f"\n   Executing hypotheses sequentially with coverage assessment...")
        print(f"   Max hypotheses: {self.max_hypotheses_to_execute}")
        print(f"   Time budget: {self.max_time_per_task_seconds}s")

        start_time = time.time()
        all_results = []
        url_map = {}  # For cross-hypothesis deduplication
        coverage_decisions = []  # Store all coverage decisions

        for i, hypothesis in enumerate(hypotheses):
            # Check hard ceilings BEFORE executing
            executed_count = len(task.hypothesis_runs)
            time_elapsed = int(time.time() - start_time)

            if executed_count >= self.max_hypotheses_to_execute:
                print(f"\n   Stopping: Reached hypothesis ceiling ({self.max_hypotheses_to_execute})")
                break

            if time_elapsed >= self.max_time_per_task_seconds:
                print(f"\n   Stopping: Time budget exhausted ({self.max_time_per_task_seconds}s)")
                break

            # Execute hypothesis
            print(f"\n   Hypothesis {i+1}/{len(hypotheses)}: {hypothesis.get('statement', 'unknown')[:80]}...")

            try:
                hypothesis_results = await self._execute_hypothesis(hypothesis, task, research_question)

                # Cross-hypothesis deduplication
                for result in hypothesis_results:
                    url = result.get("url")
                    if not url:
                        all_results.append(result)
                        continue

                    if url in url_map:
                        # Merge attribution (same logic as parallel mode)
                        existing = url_map[url]
                        if "hypothesis_ids" in existing:
                            if "hypothesis_id" in result and result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                            elif "hypothesis_ids" in result:
                                for hid in result["hypothesis_ids"]:
                                    if hid not in existing["hypothesis_ids"]:
                                        existing["hypothesis_ids"].append(hid)
                        else:
                            existing["hypothesis_ids"] = [existing.pop("hypothesis_id")]
                            if "hypothesis_id" in result and result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                            elif "hypothesis_ids" in result:
                                for hid in result["hypothesis_ids"]:
                                    if hid not in existing["hypothesis_ids"]:
                                        existing["hypothesis_ids"].append(hid)
                    else:
                        url_map[url] = result
                        all_results.append(result)

                print(f"   Results: {len(hypothesis_results)} from hypothesis ({len(all_results)} total unique)")

            # LLM call failed - hypothesis generation is optional, can proceed without
            except Exception as e:
                logger.error(f"Hypothesis {i+1} execution failed: {type(e).__name__}: {e}", exc_info=True)
                continue

            # Skip coverage assessment for first hypothesis (need baseline)
            if i == 0:
                print(f"   Coverage: Skipping assessment (establishing baseline)")
                continue

            # Coverage assessment (Phase 3C)
            try:
                decision = await self._assess_coverage(task, research_question, start_time)
                coverage_decisions.append(decision)

                # Log coverage decision to execution log
                if self.logger:
                    self.logger.log_coverage_assessment(
                        task_id=task.id,
                        hypothesis_id=hypothesis.get("id", "unknown"),
                        executed_count=len(task.hypothesis_runs),
                        total_hypotheses=len(hypotheses),
                        coverage_decision=decision,
                        time_elapsed_seconds=int(time.time() - start_time),
                        time_budget_seconds=self.max_time_per_task_seconds
                    )

                if decision["decision"] == "stop":
                    print(f"\n   Coverage assessment: STOP")
                    print(f"   Assessment: {decision['assessment'][:100]}...")
                    print(f"   Hypotheses executed: {executed_count + 1}/{len(hypotheses)}")
                    break
                else:
                    print(f"   Coverage assessment: CONTINUE")
                    print(f"   Assessment: {decision['assessment'][:100]}...")

            # LLM call failed - hypothesis generation is optional, can proceed without
            except Exception as e:
                logger.error(f"Coverage assessment failed: {type(e).__name__}: {e}", exc_info=True)
                # Continue execution on assessment error (don't block progress)

        # Store coverage decisions in task metadata for reporting
        if coverage_decisions:
            task.metadata["coverage_decisions"] = coverage_decisions

        print(f"\n   Sequential execution complete: {len(all_results)} total unique results")
        return all_results
