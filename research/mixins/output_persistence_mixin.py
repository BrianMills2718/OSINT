#!/usr/bin/env python3
"""
Output persistence mixin for deep research.

Provides file saving and coverage summary generation.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class OutputPersistenceMixin:
    """
    Mixin providing research output saving and coverage summaries.

    Requires host class to have:
        - self.start_time: datetime
        - self.output_dir: str
        - self.completed_tasks: List of ResearchTask
        - self.failed_tasks: List of ResearchTask
        - self.results_by_task: Dict
        - Various config attributes (max_tasks, etc.)
    """

    def _save_research_output(self: "SimpleDeepResearch", question: str, result: Dict) -> str:
        """
        Save research output to timestamped directory.

        Creates directory structure:
        data/research_output/YYYY-MM-DD_HH-MM-SS_query_slug/
            ├── results.json       # Complete structured results
            ├── report.md          # Final synthesized report
            └── metadata.json      # Research metadata

        Args:
            question: Original research question
            result: Complete research results dict

        Returns:
            Path to output directory
        """
        # Create slug from question (first 50 chars, alphanumeric + hyphens)
        slug = re.sub(r'[^a-z0-9]+', '_', question.lower())[:50].strip('_')

        # Use start_time (research start) instead of datetime.now() (save time)
        # This ensures _save_research_output() uses the SAME timestamp as ExecutionLogger
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        dir_name = f"{timestamp}_{slug}"
        output_path = Path(self.output_dir) / dir_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Priority 2 Fix: Load and aggregate raw task result files (survive timeout)
        # 1. Check for raw task files in output directory
        raw_path = output_path / "raw"
        aggregated_results_by_task = {}

        if raw_path.exists():
            for raw_file in sorted(raw_path.glob("task_*.json")):
                try:
                    task_id = int(raw_file.stem.split("_")[1])
                    with open(raw_file, 'r', encoding='utf-8') as f:
                        aggregated_results_by_task[task_id] = json.load(f)
                    logger.info(f"Loaded raw task file: {raw_file.name}")
                # Exception caught - error logged, execution continues
                except Exception as e:
                    logger.warning(f"Failed to load raw task file {raw_file.name}: {e}", exc_info=True)

        # Fallback: if a per-task raw file is missing, synthesize it from per-source files
        # This prevents losing data when a task never wrote task_{id}_results.json
        if raw_path.exists():
            # Candidate task_ids from completed/failed tasks and already-aggregated ones
            candidate_task_ids = set(aggregated_results_by_task.keys())
            candidate_task_ids.update([t.id for t in (self.completed_tasks + self.failed_tasks)])

            for task_id in candidate_task_ids:
                if task_id in aggregated_results_by_task:
                    continue  # already have a consolidated file

                merged_results = []
                for src_file in sorted(raw_path.glob(f"*task{task_id}_*.json")):
                    try:
                        with open(src_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # Per-source files can be arrays (list of results) or dicts with "results"
                        if isinstance(data, list):
                            merged_results.extend(data)
                        elif isinstance(data, dict) and "results" in data:
                            merged_results.extend(data.get("results", []))
                        else:
                            logging.debug(f"Skipping unrecognized raw format: {src_file.name}")
                    # Exception caught - error logged, execution continues
                    except Exception as e:
                        logger.warning(f"Failed to load per-source file {src_file.name}: {e}", exc_info=True)

                if merged_results:
                    aggregated_results_by_task[task_id] = {
                        "total_results": len(merged_results),
                        "results": merged_results
                    }
                    logger.info(f"Synthesized task_{task_id}_results from per-source files ({len(merged_results)} items)")

        # 2. Merge with results_by_task from memory (in case some tasks didn't write raw files)
        for task_id, result_dict in self.results_by_task.items():
            if task_id not in aggregated_results_by_task:
                aggregated_results_by_task[task_id] = result_dict
            else:
                # Merge new results (e.g., hypotheses) with raw file contents
                merged_results = aggregated_results_by_task[task_id].get("results", []) + result_dict.get("results", [])
                aggregated_results_by_task[task_id]["results"] = merged_results
                aggregated_results_by_task[task_id]["total_results"] = len(merged_results)

        # 3. Update result dict to use aggregated data
        aggregated_total = sum(
            r.get('total_results', 0) for r in aggregated_results_by_task.values()
        )
        aggregated_results_list = []
        for r in aggregated_results_by_task.values():
            aggregated_results_list.extend(r.get('results', []))

        # Codex Fix: Deduplicate results by (url, title) to avoid inflated counts
        seen = {}
        deduplicated_results_list = []
        for result_item in aggregated_results_list:
            # Create unique key from URL and title (both normalized)
            url = (result_item.get('url') or '').strip().lower()
            title = (result_item.get('title') or '').strip().lower()
            key = (url, title)

            # Merge attribution if duplicate encountered
            if (url or title) and key in seen:
                existing = seen[key]
                # Normalize attribution fields
                attrs = set()
                for res in (existing, result_item):
                    if "hypothesis_ids" in res:
                        attrs.update(res.get("hypothesis_ids") or [])
                    if "hypothesis_id" in res:
                        attrs.add(res["hypothesis_id"])
                if attrs:
                    existing["hypothesis_ids"] = sorted(list(attrs))
                    existing.pop("hypothesis_id", None)
            else:
                if url or title:
                    seen[key] = result_item
                deduplicated_results_list.append(result_item)

        # Log deduplication stats (Codex Fix #2: Add console output for visibility)
        duplicates_removed = len(aggregated_results_list) - len(deduplicated_results_list)
        if duplicates_removed > 0:
            logger.info(f"Deduplication: Removed {duplicates_removed} duplicate results ({len(aggregated_results_list)} → {len(deduplicated_results_list)})")
            print(f"\n📊 Deduplication: Removed {duplicates_removed} duplicates ({len(aggregated_results_list)} → {len(deduplicated_results_list)} unique results)")

        # Use deduplicated list for counts and output
        aggregated_results_list = deduplicated_results_list
        aggregated_total = len(deduplicated_results_list)

        # Gap #2 Fix: Update BOTH result_to_save AND the incoming result dict
        # This ensures CLI output matches results.json counts
        result["total_results"] = aggregated_total  # Sync in-memory with disk (deduplicated count)
        result["results_by_task"] = aggregated_results_by_task  # Add aggregated data
        result["duplicates_removed"] = duplicates_removed  # Codex Fix #2: Add dedup stats visibility
        result["results_before_dedup"] = len(aggregated_results_list) + duplicates_removed

        # Timeline: build from dated items in results (simple event list)
        timeline_out = result.get("timeline", []) or []
        if not timeline_out:
            dated_items = []
            for item in deduplicated_results_list:
                if item.get("date") and item.get("url"):
                    dated_items.append({
                        "date": item.get("date"),
                        "title": item.get("title", "") or item.get("snippet", "")[:80],
                        "url": item.get("url", "")
                    })
            # Keep top 10 by date order as provided
            timeline_out = dated_items[:10]
            result["timeline"] = timeline_out

        # Update result dict with aggregated counts
        # Phase 3B: collect hypotheses + execution summaries for persistence
        hypotheses_by_task = {}
        hypothesis_execution_summary = {}
        # Phase 3C+ evidence snapshots (use safe defaults to avoid UnboundLocal errors)
        key_documents = result.get("key_documents", []) or []
        source_counts_out = result.get("source_counts", {}) or {}
        hypothesis_findings_out = result.get("hypothesis_findings", []) or []
        for task in (self.completed_tasks + self.failed_tasks):
            if task.hypotheses:
                hypotheses_by_task[task.id] = task.hypotheses
            if task.hypothesis_runs:
                hypothesis_execution_summary[task.id] = task.hypothesis_runs

        result_to_save = {
            **result,
            "total_results": aggregated_total,
            "results_by_task": aggregated_results_by_task,
            "results": aggregated_results_list,  # Gap #3 Fix: Add flat results array for easy iteration
            "entity_relationships": {k: list(v) for k, v in result.get("entity_relationships", {}).items()},
            "hypotheses_by_task": hypotheses_by_task,
            "hypothesis_execution_summary": hypothesis_execution_summary,
            "key_documents": key_documents,
            "source_counts": source_counts_out,
            "hypothesis_findings": hypothesis_findings_out,
            "timeline": timeline_out
        }

        # 4. Save complete JSON results (for programmatic access)
        results_file = output_path / "results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result_to_save, f, indent=2, ensure_ascii=False)

        # 2. Save markdown report (for human reading)
        report_file = output_path / "report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result.get("report", "Report unavailable."))

        # 3. Save metadata (research parameters + execution info)
        metadata_file = output_path / "metadata.json"
        metadata = {
            "research_question": question,
            "timestamp": timestamp,
            "engine_config": {
                "max_tasks": self.max_tasks,
                "max_retries_per_task": self.max_retries_per_task,
                "max_time_minutes": self.max_time_minutes,
                "min_results_per_task": self.min_results_per_task,
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "hypothesis_branching_enabled": self.hypothesis_branching_enabled,
                "hypothesis_mode": getattr(self, "hypothesis_mode", "off"),
                "max_hypotheses_per_task": self.max_hypotheses_per_task,
                # Phase 4: Manager-Agent configuration
                "task_prioritization_enabled": self.manager_enabled,
                "saturation_detection_enabled": self.saturation_detection_enabled,
                "saturation_check_interval": self.saturation_check_interval,
                "saturation_confidence_threshold": self.saturation_confidence_threshold
            },
            # Phase 4A: Task execution order analysis
            "task_execution_order": [
                {
                    "task_id": task.id,
                    "query": task.query,
                    "priority": task.priority,
                    "priority_reasoning": task.priority_reasoning,
                    "estimated_value": task.estimated_value,
                    "estimated_redundancy": task.estimated_redundancy,
                    "actual_results": len(task.accumulated_results),
                    # Phase 5: Store qualitative assessment instead of numeric score
                    "final_assessment": task.metadata.get("coverage_decisions", [{}])[-1].get("assessment", "")[:200] if task.metadata.get("coverage_decisions") else None,
                    "final_gaps": task.metadata.get("coverage_decisions", [{}])[-1].get("gaps_identified", []) if task.metadata.get("coverage_decisions") else [],
                    "parent_task_id": task.parent_task_id
                }
                for task in (self.completed_tasks + self.failed_tasks)
            ],
            "execution_summary": {
                "tasks_executed": result["tasks_executed"],
                "tasks_failed": result["tasks_failed"],
                "total_results": result["total_results"],
                "elapsed_minutes": result["elapsed_minutes"],
                "sources_searched": result["sources_searched"],
                "entities_discovered_count": len(result["entities_discovered"]),
                "duplicates_removed": duplicates_removed,
                "results_before_dedup": len(aggregated_results_list) + duplicates_removed
            }
        }

        # Phase 3A/B: Add hypotheses and execution summaries if generated
        if self.hypothesis_branching_enabled:
            hypotheses_by_task = {}
            hypothesis_execution_summary = {}
            for task in (self.completed_tasks + self.failed_tasks):
                if task.hypotheses:
                    hypotheses_by_task[task.id] = task.hypotheses
                if task.hypothesis_runs:
                    hypothesis_execution_summary[task.id] = task.hypothesis_runs

            if hypotheses_by_task:
                metadata["hypotheses_by_task"] = hypotheses_by_task
            if hypothesis_execution_summary:
                metadata["hypothesis_execution_summary"] = hypothesis_execution_summary

        # Phase 3C: Add coverage decisions if available
        coverage_decisions_by_task = {}
        for task in (self.completed_tasks + self.failed_tasks):
            if task.metadata.get("coverage_decisions"):
                coverage_decisions_by_task[task.id] = task.metadata["coverage_decisions"]

        if coverage_decisions_by_task:
            metadata["coverage_decisions_by_task"] = coverage_decisions_by_task

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Research output saved to: {output_path}")
        return str(output_path)

    def _generate_global_coverage_summary(self: "SimpleDeepResearch") -> str:
        """
        Generate concise summary of overall research coverage (Phase 4A).

        Used for task prioritization context - helps manager LLM understand
        what's been found and what gaps remain.

        Returns:
            Text summary for prioritization/saturation context
        """
        if not self.completed_tasks:
            return "No tasks completed yet - initial decomposition."

        # Phase 5: Collect qualitative assessments instead of numeric scores
        recent_assessments = []
        for task in self.completed_tasks[-3:]:  # Last 3 tasks
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            if coverage_decisions:
                latest = coverage_decisions[-1]
                assessment = latest.get("assessment", "")
                if assessment:
                    # Extract key phrases (first sentence or ~100 chars)
                    brief = assessment.split('.')[0][:100]
                    recent_assessments.append(f"Task {task.id}: {brief}")

        # Collect all gaps across tasks
        all_gaps = []
        for task in self.completed_tasks:
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            for decision in coverage_decisions:
                all_gaps.extend(decision.get("gaps_identified", []))

        # Deduplicate gaps while preserving order
        unique_gaps = list(dict.fromkeys(all_gaps))[:5]  # Top 5 unique gaps

        # Calculate total results
        total_results = sum(len(t.accumulated_results) for t in self.completed_tasks)

        # Build qualitative summary
        summary_parts = [
            f"Completed {len(self.completed_tasks)} tasks, {total_results} results found"
        ]

        if recent_assessments:
            summary_parts.append(f"Recent progress: {'; '.join(recent_assessments[:2])}")

        if unique_gaps:
            summary_parts.append(f"Key gaps remaining: {'; '.join(unique_gaps[:3])}")

        return ". ".join(summary_parts) + "."
