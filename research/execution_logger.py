#!/usr/bin/env python3
"""
Execution Logger for Deep Research

Provides comprehensive logging of Deep Research execution traces using JSONL format
(one JSON object per line) to enable streaming writes, line-by-line filtering,
and post-hoc forensic analysis.

Key Features:
- JSONL format (append-only, survives crashes, easy to filter)
- Structured action chain (common metadata + action-specific payload)
- Separate raw result archives (keeps main log readable)
- Timestamps per action (performance analysis)
- LLM cost tracking (budget monitoring)
- Schema versioning (backward compatibility)

Usage:
    logger = ExecutionLogger(research_id="2025-10-30_12-34-56_query", output_dir="data/research_output/...")
    logger.log_run_start(original_question="...", config={...})
    logger.log_source_selection(task_id=0, query="...", selected_sources=["SAM.gov"], reasoning="...")
    logger.log_api_call(task_id=0, source_name="SAM.gov", query_params={...})
    logger.log_raw_response(task_id=0, source_name="SAM.gov", results=[...])
    logger.log_relevance_scoring(task_id=0, source_name="SAM.gov", score=2, reasoning="...")
    logger.log_filter_decision(task_id=0, source_name="SAM.gov", decision="REJECT")
    logger.log_task_complete(task_id=0, status="FAILED", reason="...")
    logger.log_run_complete(tasks_executed=0, tasks_failed=5)
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path


class ExecutionLogger:
    """
    Structured logger for Deep Research execution traces.

    Writes JSONL format (one JSON object per line) to enable:
    - Streaming writes (append-only)
    - Line-by-line filtering without loading entire file
    - Easy parsing with standard JSON tools
    - Real-time monitoring with tail -f
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, research_id: str, output_dir: str):
        """
        Initialize execution logger.

        Args:
            research_id: Unique identifier for this research run (e.g., "2025-10-30_12-34-56_query")
            output_dir: Directory to write logs (e.g., "data/research_output/...")
        """
        self.research_id = research_id
        self.output_dir = Path(output_dir)
        self.log_path = self.output_dir / "execution_log.jsonl"
        self.raw_dir = self.output_dir / "raw"

        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _write_entry(self, task_id: Optional[int], action_type: str, action_payload: Dict[str, Any]):
        """
        Write single log entry to JSONL file.

        Args:
            task_id: Task ID (None for run-level actions)
            action_type: Type of action (e.g., "source_selection", "api_call")
            action_payload: Action-specific data
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": self.SCHEMA_VERSION,
            "research_id": self.research_id,
            "task_id": task_id,
            "action_type": action_type,
            "action_payload": action_payload
        }

        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def _save_raw_results(self, task_id: int, attempt: int, source_name: str, results: List[Dict]) -> str:
        """
        Save raw results to separate JSON file (keeps main log readable).

        Args:
            task_id: Task ID
            attempt: Attempt/retry number (0 for first try)
            source_name: Source name (e.g., "ClearanceJobs")
            results: Raw API results

        Returns:
            Relative path to raw results file (for reference in main log)
        """
        # Sanitize source name for filename
        safe_source_name = source_name.lower().replace(' ', '_').replace('.', '_')
        filename = f"{safe_source_name}_task{task_id}_attempt{attempt}.json"
        filepath = self.raw_dir / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        return f"raw/{filename}"

    # =======================
    # Run-Level Actions
    # =======================

    def log_run_start(self, original_question: str, config: Dict[str, Any]):
        """Log research run start."""
        self._write_entry(None, "run_start", {
            "original_question": original_question,
            "config": config
        })

    def log_run_complete(self, original_question: str, tasks_executed: int,
                        tasks_failed: int, total_results: int, sources_searched: List[str],
                        elapsed_minutes: float, report_path: str):
        """Log research run completion."""
        self._write_entry(None, "run_complete", {
            "original_question": original_question,
            "tasks_executed": tasks_executed,
            "tasks_failed": tasks_failed,
            "total_results": total_results,
            "sources_searched": sources_searched,
            "elapsed_minutes": elapsed_minutes,
            "report_path": report_path
        })

    # =======================
    # Task-Level Actions
    # =======================

    def log_task_start(self, task_id: int, query: str, attempt: int):
        """Log task start (or retry)."""
        self._write_entry(task_id, "task_start", {
            "query": query,
            "attempt": attempt
        })

    def log_source_selection(self, task_id: int, query: str, tool_descriptions: Dict[str, str],
                            selected_sources: List[str], reasoning: str,
                            llm_metadata: Optional[Dict[str, Any]] = None):
        """
        Log which sources were selected for a task.

        Args:
            task_id: Task ID
            query: Research query for this task
            tool_descriptions: All available tool descriptions shown to LLM
            selected_sources: Sources selected by LLM
            reasoning: LLM's reasoning for selection
            llm_metadata: Optional LLM cost tracking (model, tokens, cost)
        """
        self._write_entry(task_id, "source_selection", {
            "query": query,
            "tool_descriptions": tool_descriptions,
            "selected_sources": selected_sources,
            "selection_reasoning": reasoning,
            "llm_metadata": llm_metadata or {}
        })

    def log_api_call(self, task_id: int, attempt: int, source_name: str,
                     query_params: Dict[str, Any], timeout: int, retry_count: int):
        """
        Log API call being made.

        Args:
            task_id: Task ID
            attempt: Attempt/retry number (0 for first try)
            source_name: Source name (e.g., "ClearanceJobs")
            query_params: Query parameters sent to API
            timeout: Timeout setting (seconds)
            retry_count: Retry count for this specific call
        """
        self._write_entry(task_id, "api_call", {
            "attempt": attempt,
            "source_name": source_name,
            "query_params": query_params,
            "timeout": timeout,
            "retry_count": retry_count
        })

    def log_raw_response(self, task_id: int, attempt: int, source_name: str,
                        success: bool, response_time_ms: float,
                        results: List[Dict], error: Optional[str]):
        """
        Log raw API response BEFORE relevance filtering.

        Args:
            task_id: Task ID
            attempt: Attempt/retry number (0 for first try)
            source_name: Source name (e.g., "ClearanceJobs")
            success: Whether API call succeeded
            response_time_ms: Response time in milliseconds
            results: Raw API results (saved to separate file if large)
            error: Error message if failed
        """
        # Save raw results to separate file (keeps main log readable)
        raw_archive_path = None
        if success and results:
            raw_archive_path = self._save_raw_results(task_id, attempt, source_name, results)

        # Log summary in main log (with reference to raw archive)
        self._write_entry(task_id, "raw_response", {
            "attempt": attempt,
            "source_name": source_name,
            "success": success,
            "response_time_ms": response_time_ms,
            "total_results": len(results) if success else 0,
            "raw_archive": raw_archive_path,  # Reference to full results
            "preview": results[:3] if success and results else [],  # First 3 for quick inspection
            "error": error
        })

    def log_relevance_scoring(self, task_id: int, attempt: int, source_name: str,
                             original_query: str, results_count: int,
                             llm_prompt: str, llm_response: Dict[str, Any],
                             threshold: int, passes: bool,
                             llm_metadata: Optional[Dict[str, Any]] = None,
                             reasoning_breakdown: Optional[Dict[str, Any]] = None):
        """
        Log LLM relevance evaluation.

        Args:
            task_id: Task ID
            attempt: Attempt/retry number
            source_name: Source name
            original_query: Original research query
            results_count: Number of results evaluated
            llm_prompt: Prompt sent to LLM
            llm_response: LLM response (score + reasoning)
            threshold: Relevance threshold (e.g., 6/10)
            passes: Whether results pass threshold
            llm_metadata: Optional LLM cost tracking
            reasoning_breakdown: Optional detailed reasoning (filtering_strategy, interesting_decisions, patterns_noticed)
        """
        payload = {
            "attempt": attempt,
            "source_name": source_name,
            "original_query": original_query,
            "results_evaluated": results_count,
            "llm_prompt": llm_prompt,
            "llm_response": llm_response,
            "relevance_threshold": threshold,
            "passes_threshold": passes,
            "llm_metadata": llm_metadata or {}
        }

        # Add reasoning_breakdown if provided (Bug fix: audit trail completeness)
        if reasoning_breakdown:
            payload["reasoning_breakdown"] = reasoning_breakdown

        self._write_entry(task_id, "relevance_scoring", payload)

    def log_filter_decision(self, task_id: int, attempt: int, source_name: str,
                           decision: str, reason: str, kept: int, discarded: int):
        """
        Log whether results were kept or filtered out.

        Args:
            task_id: Task ID
            attempt: Attempt/retry number
            source_name: Source name
            decision: "ACCEPT" or "REJECT"
            reason: Reason for decision
            kept: Number of results kept
            discarded: Number of results discarded
        """
        self._write_entry(task_id, "filter_decision", {
            "attempt": attempt,
            "source_name": source_name,
            "decision": decision,
            "reason": reason,
            "results_kept": kept,
            "results_discarded": discarded
        })

    def log_reformulation(self, task_id: int, attempt: int, trigger_reason: str,
                         original_query: str, new_query: str,
                         param_adjustments: Dict[str, Any],
                         sources_with_errors: List[str],
                         sources_with_zero_results: List[str],
                         sources_with_low_quality: List[str]):
        """
        Log query reformulation with context about WHY it happened.

        This enables post-hoc analysis of retry patterns to validate
        whether param_hints are worth implementing for specific sources.

        Args:
            task_id: Task ID
            attempt: Attempt/retry number
            trigger_reason: Why reformulation happened ("continue_searching", "api_error", "zero_results", "off_topic")
            original_query: Query before reformulation
            new_query: Query after reformulation
            param_adjustments: Source-specific parameter hints (e.g., {"reddit": {"time_filter": "year"}})
            sources_with_errors: Sources that returned errors (429, 503, auth) - hints won't help
            sources_with_zero_results: Sources that returned success but 0 results - hints might help
            sources_with_low_quality: Sources that returned results but LLM rejected - hints might help
        """
        self._write_entry(task_id, "reformulation", {
            "attempt": attempt,
            "trigger_reason": trigger_reason,
            "original_query": original_query,
            "new_query": new_query,
            "param_adjustments": param_adjustments,
            "sources_with_errors": sources_with_errors,
            "sources_with_zero_results": sources_with_zero_results,
            "sources_with_low_quality": sources_with_low_quality,
            # Metrics for Phase 0 analysis
            "has_param_adjustments": bool(param_adjustments),
            "error_sources_count": len(sources_with_errors),
            "zero_result_sources_count": len(sources_with_zero_results),
            "low_quality_sources_count": len(sources_with_low_quality)
        })

    def log_coverage_assessment(self, task_id: int, hypothesis_id: str,
                               executed_count: int, total_hypotheses: int,
                               coverage_decision: Dict[str, Any],
                               time_elapsed_seconds: int, time_budget_seconds: int):
        """
        Log LLM coverage assessment for hypothesis execution (Phase 3C/5).

        Args:
            task_id: Task ID
            hypothesis_id: ID of hypothesis just executed
            executed_count: Number of hypotheses executed so far
            total_hypotheses: Total hypotheses available
            coverage_decision: LLM decision with Phase 5 schema:
                {decision, assessment, gaps_identified, facts: {...}}
            time_elapsed_seconds: Time spent on hypothesis execution so far
            time_budget_seconds: Total time budget for task
        """
        # Phase 5: Use new qualitative schema
        facts = coverage_decision.get("facts", {})

        self._write_entry(task_id, "coverage_assessment", {
            "hypothesis_id": hypothesis_id,
            "executed_count": executed_count,
            "total_hypotheses": total_hypotheses,
            "decision": coverage_decision["decision"],
            "assessment": coverage_decision.get("assessment", ""),
            "gaps_identified": coverage_decision.get("gaps_identified", []),
            # Auto-injected facts
            "results_new": facts.get("results_new", 0),
            "results_duplicate": facts.get("results_duplicate", 0),
            "incremental_gain_last_pct": facts.get("incremental_gain_last_pct", 0),
            "entities_new": facts.get("entities_new", 0),
            # Time tracking
            "time_elapsed_seconds": time_elapsed_seconds,
            "time_budget_seconds": time_budget_seconds,
            "time_remaining_seconds": time_budget_seconds - time_elapsed_seconds,
            "hypotheses_remaining": total_hypotheses - executed_count
        })

    def log_task_complete(self, task_id: int, query: str, status: str, reason: str,
                         total_results: int, sources_tried: List[str],
                         sources_succeeded: List[str], retry_count: int,
                         elapsed_seconds: float):
        """
        Log task completion.

        Args:
            task_id: Task ID
            query: Research query
            status: "SUCCESS" or "FAILED"
            reason: Reason for status
            total_results: Total results collected
            sources_tried: All sources attempted
            sources_succeeded: Sources that returned accepted results
            retry_count: Number of retries
            elapsed_seconds: Total elapsed time
        """
        self._write_entry(task_id, "task_complete", {
            "query": query,
            "status": status,
            "reason": reason,
            "total_results": total_results,
            "sources_tried": sources_tried,
            "sources_succeeded": sources_succeeded,
            "retry_count": retry_count,
            "elapsed_seconds": elapsed_seconds
        })

    def log_saturation_assessment(self, completed_tasks: int, saturation_result: Dict[str, Any]):
        """
        Log saturation detection assessment (Phase 4B).

        Args:
            completed_tasks: Number of tasks completed when check performed
            saturation_result: LLM saturation decision with all fields
        """
        self._write_entry(None, "saturation_assessment", {
            "completed_tasks": completed_tasks,
            "saturated": saturation_result.get("saturated"),
            "confidence": saturation_result.get("confidence"),
            "rationale": saturation_result.get("rationale"),
            "recommendation": saturation_result.get("recommendation"),
            "evidence": saturation_result.get("evidence"),
            "recommended_additional_tasks": saturation_result.get("recommended_additional_tasks"),
            "critical_gaps_remaining": saturation_result.get("critical_gaps_remaining", [])
        })

    def log_hypothesis_query_generation(
        self,
        task_id: int,
        hypothesis_id: str,
        source_name: str,
        query: str,
        reasoning: str
    ):
        """
        Log LLM-generated hypothesis query with reasoning (Phase 3B).

        Args:
            task_id: Task this hypothesis belongs to
            hypothesis_id: Hypothesis identifier
            source_name: Target source (e.g., "DVIDS", "Brave Search")
            query: Generated query string
            reasoning: LLM's explanation for why this query tests the hypothesis
        """
        self._write_entry(task_id, "hypothesis_query_generation", {
            "hypothesis_id": hypothesis_id,
            "source_name": source_name,
            "query": query,
            "reasoning": reasoning
        })
