#!/usr/bin/env python3
"""
Performance Analysis Tool

Analyzes execution logs and metadata to identify:
- Time bottlenecks (where is time spent?)
- Cost breakdown (which operations are expensive?)
- Parallelization effectiveness (are we running things concurrently?)
- Optimization opportunities
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

def analyze_research_run(run_dir: str):
    """Analyze a single research run for performance insights."""

    run_path = Path(run_dir)
    exec_log_path = run_path / "execution_log.jsonl"
    metadata_path = run_path / "metadata.json"

    if not exec_log_path.exists():
        print(f"❌ No execution log found at {exec_log_path}")
        return

    print("=" * 80)
    print(f"PERFORMANCE ANALYSIS: {run_path.name}")
    print("=" * 80)
    print()

    # Load execution log
    events = []
    with open(exec_log_path) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    # Load metadata
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    print(f"📊 Total Events Logged: {len(events)}")
    print()

    # 1. TIME BREAKDOWN ANALYSIS
    print("⏱️  TIME BREAKDOWN BY OPERATION")
    print("-" * 80)

    time_breakdown_events = [e for e in events if e.get("event_type") == "time_breakdown"]

    if time_breakdown_events:
        # Aggregate time by operation type
        operation_times = defaultdict(lambda: {"count": 0, "total_ms": 0, "sources": defaultdict(int)})

        for event in time_breakdown_events:
            source = event.get("source", "unknown")
            total_ms = event.get("total_time_ms", 0)
            query_gen_ms = event.get("time_query_generation_ms", 0)
            api_call_ms = event.get("time_api_call_ms", 0)
            filtering_ms = event.get("time_filtering_ms", 0)

            # Track by source
            operation_times["query_generation"]["count"] += 1
            operation_times["query_generation"]["total_ms"] += query_gen_ms
            operation_times["query_generation"]["sources"][source] += query_gen_ms

            operation_times["api_call"]["count"] += 1
            operation_times["api_call"]["total_ms"] += api_call_ms
            operation_times["api_call"]["sources"][source] += api_call_ms

            operation_times["filtering"]["count"] += 1
            operation_times["filtering"]["total_ms"] += filtering_ms
            operation_times["filtering"]["sources"][source] += filtering_ms

            operation_times["total"]["count"] += 1
            operation_times["total"]["total_ms"] += total_ms
            operation_times["total"]["sources"][source] += total_ms

        # Print summary
        for op_type, data in sorted(operation_times.items(), key=lambda x: x[1]["total_ms"], reverse=True):
            total_sec = data["total_ms"] / 1000
            avg_ms = data["total_ms"] / data["count"] if data["count"] > 0 else 0
            print(f"{op_type.upper():20} {total_sec:8.1f}s total ({data['count']:3} ops, {avg_ms:6.0f}ms avg)")

        print()
        print("Top 5 Slowest Sources:")
        source_totals = operation_times["total"]["sources"]
        for source, total_ms in sorted(source_totals.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {source:20} {total_ms/1000:8.1f}s")
    else:
        print("  ⚠️  No time_breakdown events found")

    print()

    # 2. LLM CALL ANALYSIS
    print("🤖 LLM CALLS ANALYSIS")
    print("-" * 80)

    llm_events = [e for e in events if "model" in e or "llm" in e.get("event_type", "").lower()]

    llm_by_operation = defaultdict(list)
    for event in llm_events:
        event_type = event.get("event_type", "unknown")
        model = event.get("model", event.get("llm_model", "unknown"))
        duration_ms = event.get("duration_ms", event.get("response_time_ms", 0))

        llm_by_operation[event_type].append({
            "model": model,
            "duration_ms": duration_ms
        })

    total_llm_calls = 0
    total_llm_time_ms = 0

    for op_type, calls in sorted(llm_by_operation.items()):
        count = len(calls)
        total_ms = sum(c["duration_ms"] for c in calls)
        avg_ms = total_ms / count if count > 0 else 0

        total_llm_calls += count
        total_llm_time_ms += total_ms

        # Get model breakdown
        models = defaultdict(int)
        for call in calls:
            models[call["model"]] += 1

        models_str = ", ".join(f"{m}:{c}" for m, c in models.items())

        print(f"{op_type:30} {count:3} calls, {total_ms/1000:6.1f}s total ({avg_ms:5.0f}ms avg)")
        print(f"{'':30} Models: {models_str}")

    print()
    print(f"TOTAL LLM CALLS: {total_llm_calls} calls, {total_llm_time_ms/1000:.1f}s")
    print()

    # 3. SOURCE UTILIZATION
    print("📚 SOURCE UTILIZATION")
    print("-" * 80)

    source_selection_events = [e for e in events if e.get("event_type") == "source_selection"]
    source_skipped_events = [e for e in events if e.get("event_type") == "source_skipped"]

    sources_selected = set()
    sources_skipped = defaultdict(list)

    for event in source_selection_events:
        selected = event.get("selected_sources", [])
        sources_selected.update(selected)

    for event in source_skipped_events:
        source = event.get("source_name", "unknown")
        reason = event.get("reason", "unknown")
        sources_skipped[source].append(reason)

    print(f"Sources Selected:  {len(sources_selected)}")
    print(f"Sources Skipped:   {len(sources_skipped)}")
    print()

    if sources_selected:
        print("Selected Sources:")
        for source in sorted(sources_selected):
            print(f"  ✓ {source}")

    print()

    if sources_skipped:
        print("Skipped Sources (top 5 by frequency):")
        for source, reasons in sorted(sources_skipped.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            reason_counts = defaultdict(int)
            for r in reasons:
                reason_counts[r] += 1
            reason_str = ", ".join(f"{r}:{c}" for r, c in reason_counts.items())
            print(f"  ✗ {source:20} ({len(reasons)} times) - {reason_str}")

    print()

    # 4. TASK EXECUTION TIMELINE
    print("📈 TASK EXECUTION TIMELINE")
    print("-" * 80)

    task_events = [e for e in events if "task_id" in e]

    tasks_by_id = defaultdict(list)
    for event in task_events:
        task_id = event.get("task_id")
        if task_id is not None:
            tasks_by_id[task_id].append(event)

    print(f"Total Tasks Executed: {len(tasks_by_id)}")

    # Check for parallel execution
    task_start_times = {}
    task_end_times = {}

    for task_id, task_events_list in tasks_by_id.items():
        timestamps = [e.get("timestamp") for e in task_events_list if "timestamp" in e]
        if timestamps:
            task_start_times[task_id] = min(timestamps)
            task_end_times[task_id] = max(timestamps)

    # Find overlapping tasks (evidence of parallelization)
    overlaps = 0
    for t1_id, t1_start in task_start_times.items():
        t1_end = task_end_times.get(t1_id)
        if not t1_end:
            continue

        for t2_id, t2_start in task_start_times.items():
            if t1_id >= t2_id:
                continue

            t2_end = task_end_times.get(t2_id)
            if not t2_end:
                continue

            # Check if tasks overlap
            if (t1_start <= t2_start <= t1_end) or (t2_start <= t1_start <= t2_end):
                overlaps += 1

    if overlaps > 0:
        print(f"✓ Evidence of parallelization: {overlaps} task overlaps detected")
    else:
        print(f"⚠️  No task overlaps detected - tasks may be running sequentially")

    print()

    # 5. METADATA SUMMARY
    if metadata:
        print("📋 RESEARCH SUMMARY (from metadata.json)")
        print("-" * 80)

        stats = metadata.get("statistics", {})
        config_used = metadata.get("configuration", {})

        print(f"Total Results:     {stats.get('total_results', 'N/A')}")
        print(f"Unique Results:    {stats.get('unique_results', 'N/A')}")
        print(f"Tasks Completed:   {stats.get('tasks_completed', 'N/A')}")
        print(f"Entities Found:    {stats.get('entities_discovered', 'N/A')}")

        if "total_time_seconds" in stats:
            total_time = stats["total_time_seconds"]
            print(f"Total Runtime:     {total_time:.1f}s ({total_time/60:.1f} min)")

        print()
        print("Configuration Used:")
        print(f"  max_tasks:              {config_used.get('max_tasks', 'N/A')}")
        print(f"  max_time_minutes:       {config_used.get('max_time_minutes', 'N/A')}")
        print(f"  max_concurrent_tasks:   {config_used.get('max_concurrent_tasks', 'N/A')}")
        print(f"  query_saturation:       {config_used.get('query_saturation_enabled', 'N/A')}")

    print()
    print("=" * 80)

    # 6. OPTIMIZATION RECOMMENDATIONS
    print()
    print("💡 OPTIMIZATION RECOMMENDATIONS")
    print("-" * 80)

    recommendations = []

    # Check if parallelization is effective
    if overlaps == 0 and len(tasks_by_id) > 1:
        recommendations.append(
            "⚠️  No parallel task execution detected\n"
            "   Consider: Increase max_concurrent_tasks if tasks are independent"
        )

    # Check for slow operations
    if time_breakdown_events:
        avg_query_gen = operation_times["query_generation"]["total_ms"] / operation_times["query_generation"]["count"]
        avg_api_call = operation_times["api_call"]["total_ms"] / operation_times["api_call"]["count"]
        avg_filtering = operation_times["filtering"]["total_ms"] / operation_times["filtering"]["count"]

        if avg_query_gen > 2000:  # > 2 seconds
            recommendations.append(
                f"⚠️  Query generation slow (avg {avg_query_gen:.0f}ms)\n"
                f"   Consider: Use faster model (e.g., gpt-4o-mini) for query generation"
            )

        if avg_filtering > 1000:  # > 1 second
            recommendations.append(
                f"⚠️  Filtering slow (avg {avg_filtering:.0f}ms)\n"
                f"   Consider: Use faster model for relevance filtering or increase batch size"
            )

        # Check source performance
        slowest_source = max(source_totals.items(), key=lambda x: x[1])
        if slowest_source[1] > 30000:  # > 30 seconds
            recommendations.append(
                f"⚠️  {slowest_source[0]} very slow ({slowest_source[1]/1000:.1f}s total)\n"
                f"   Consider: Reduce max_queries_per_source or add timeout for this source"
            )

    # Check for excessive LLM calls
    if total_llm_calls > 100:
        recommendations.append(
            f"⚠️  High LLM call count ({total_llm_calls} calls)\n"
            f"   Consider: Cache repeated queries or batch similar operations"
        )

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
            print()
    else:
        print("✓ No obvious performance issues detected!")

    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_performance.py <research_output_directory>")
        print()
        print("Example:")
        print("  python3 analyze_performance.py data/research_output/2025-11-22_17-45-04_*")
        sys.exit(1)

    analyze_research_run(sys.argv[1])
