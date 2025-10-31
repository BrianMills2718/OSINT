#!/usr/bin/env python3
"""
Analyze Deep Research Execution Logs

Provides command-line tools for filtering and analyzing JSONL execution logs.

Examples:
    # Show all actions for ClearanceJobs
    python3 scripts/analyze_execution_log.py data/research_output/.../execution_log.jsonl --source ClearanceJobs

    # Show action chain for Task 0
    python3 scripts/analyze_execution_log.py data/research_output/.../execution_log.jsonl --task 0

    # Show all relevance scoring decisions
    python3 scripts/analyze_execution_log.py data/research_output/.../execution_log.jsonl --action relevance_scoring

    # Show summary statistics
    python3 scripts/analyze_execution_log.py data/research_output/.../execution_log.jsonl --format summary

    # Show what ClearanceJobs actually returned
    python3 scripts/analyze_execution_log.py data/research_output/.../execution_log.jsonl --source ClearanceJobs --action raw_response
"""

import json
import argparse
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict


def load_log(log_path: str) -> List[Dict[str, Any]]:
    """Load JSONL log file."""
    entries = []
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                entries.append(json.loads(line))
    return entries


def filter_by_source(entries: List[Dict], source_name: str) -> List[Dict]:
    """Filter entries by source name."""
    return [e for e in entries if e.get('action_payload', {}).get('source_name') == source_name]


def filter_by_task(entries: List[Dict], task_id: int) -> List[Dict]:
    """Filter entries by task ID."""
    return [e for e in entries if e.get('task_id') == task_id]


def filter_by_action(entries: List[Dict], action_type: str) -> List[Dict]:
    """Filter entries by action type."""
    return [e for e in entries if e.get('action_type') == action_type]


def generate_summary(entries: List[Dict]) -> str:
    """Generate human-readable summary of log."""
    summary_lines = []

    # Overall stats
    summary_lines.append(f"Total entries: {len(entries)}")
    summary_lines.append("")

    # Action type breakdown
    action_counts = defaultdict(int)
    for e in entries:
        action_type = e.get('action_type', 'unknown')
        action_counts[action_type] += 1

    summary_lines.append("Action type breakdown:")
    for action, count in sorted(action_counts.items()):
        summary_lines.append(f"  {action}: {count}")
    summary_lines.append("")

    # Source breakdown (for actions that have source_name)
    source_counts = defaultdict(int)
    for e in entries:
        source_name = e.get('action_payload', {}).get('source_name')
        if source_name:
            source_counts[source_name] += 1

    if source_counts:
        summary_lines.append("Source breakdown:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            summary_lines.append(f"  {source}: {count} actions")
        summary_lines.append("")

    # Task breakdown
    task_ids = set(e.get('task_id') for e in entries if e.get('task_id') is not None)
    summary_lines.append(f"Tasks: {len(task_ids)} tasks tracked")
    summary_lines.append("")

    # Run outcomes (if run_complete exists)
    run_complete = [e for e in entries if e.get('action_type') == 'run_complete']
    if run_complete:
        payload = run_complete[0].get('action_payload', {})
        summary_lines.append("Run outcome:")
        summary_lines.append(f"  Tasks executed: {payload.get('tasks_executed', 0)}")
        summary_lines.append(f"  Tasks failed: {payload.get('tasks_failed', 0)}")
        summary_lines.append(f"  Total results: {payload.get('total_results', 0)}")
        summary_lines.append(f"  Sources searched: {', '.join(payload.get('sources_searched', []))}")
        summary_lines.append(f"  Time: {payload.get('elapsed_minutes', 0):.1f} minutes")
        summary_lines.append("")

    # Failed tasks analysis
    task_complete_entries = [e for e in entries if e.get('action_type') == 'task_complete']
    failed_tasks = [e for e in task_complete_entries if e.get('action_payload', {}).get('status') == 'FAILED']

    if failed_tasks:
        summary_lines.append(f"Failed tasks: {len(failed_tasks)}")
        for task in failed_tasks:
            task_id = task.get('task_id')
            reason = task.get('action_payload', {}).get('reason', 'Unknown')
            summary_lines.append(f"  Task {task_id}: {reason}")
        summary_lines.append("")

    # Relevance scoring analysis
    relevance_entries = [e for e in entries if e.get('action_type') == 'relevance_scoring']
    if relevance_entries:
        passed = [e for e in relevance_entries if e.get('action_payload', {}).get('passes_threshold')]
        failed = [e for e in relevance_entries if not e.get('action_payload', {}).get('passes_threshold')]

        summary_lines.append("Relevance scoring:")
        summary_lines.append(f"  Passed: {len(passed)}")
        summary_lines.append(f"  Failed: {len(failed)}")

        if failed:
            summary_lines.append("  Failed sources:")
            for e in failed:
                source = e.get('action_payload', {}).get('source_name')
                score = e.get('action_payload', {}).get('llm_response', {}).get('relevance_score', 0)
                reasoning = e.get('action_payload', {}).get('llm_response', {}).get('reasoning', 'N/A')
                summary_lines.append(f"    {source}: {score}/10 - {reasoning[:80]}...")
        summary_lines.append("")

    return "\n".join(summary_lines)


def format_entry_human(entry: Dict[str, Any]) -> str:
    """Format single entry in human-readable format."""
    lines = []
    lines.append(f"[{entry.get('timestamp')}] {entry.get('action_type')}")

    if entry.get('task_id') is not None:
        lines.append(f"  Task: {entry.get('task_id')}")

    payload = entry.get('action_payload', {})

    # Format payload based on action type
    action_type = entry.get('action_type')

    if action_type == 'source_selection':
        lines.append(f"  Query: {payload.get('query', 'N/A')}")
        lines.append(f"  Selected: {', '.join(payload.get('selected_sources', []))}")
        lines.append(f"  Reasoning: {payload.get('selection_reasoning', 'N/A')}")

    elif action_type == 'api_call':
        lines.append(f"  Source: {payload.get('source_name')}")
        lines.append(f"  Params: {json.dumps(payload.get('query_params', {}), indent=4)}")

    elif action_type == 'raw_response':
        lines.append(f"  Source: {payload.get('source_name')}")
        lines.append(f"  Success: {payload.get('success')}")
        lines.append(f"  Results: {payload.get('total_results', 0)}")
        lines.append(f"  Time: {payload.get('response_time_ms', 0):.1f}ms")
        if payload.get('raw_archive'):
            lines.append(f"  Raw archive: {payload.get('raw_archive')}")
        if payload.get('preview'):
            lines.append(f"  Preview:")
            for i, result in enumerate(payload.get('preview', []), 1):
                lines.append(f"    {i}. {result.get('title', 'N/A')}")

    elif action_type == 'relevance_scoring':
        lines.append(f"  Source: {payload.get('source_name')}")
        llm_response = payload.get('llm_response', {})
        lines.append(f"  Score: {llm_response.get('relevance_score', 0)}/10")
        lines.append(f"  Passes: {payload.get('passes_threshold')}")
        lines.append(f"  Reasoning: {llm_response.get('reasoning', 'N/A')}")

    elif action_type == 'filter_decision':
        lines.append(f"  Source: {payload.get('source_name')}")
        lines.append(f"  Decision: {payload.get('decision')}")
        lines.append(f"  Reason: {payload.get('reason')}")
        lines.append(f"  Kept: {payload.get('results_kept')}, Discarded: {payload.get('results_discarded')}")

    elif action_type == 'task_start':
        lines.append(f"  Query: {payload.get('query')}")
        lines.append(f"  Attempt: {payload.get('attempt')}")

    elif action_type == 'task_complete':
        lines.append(f"  Status: {payload.get('status')}")
        lines.append(f"  Reason: {payload.get('reason')}")
        lines.append(f"  Results: {payload.get('total_results')}")
        lines.append(f"  Sources tried: {', '.join(payload.get('sources_tried', []))}")
        lines.append(f"  Sources succeeded: {', '.join(payload.get('sources_succeeded', []))}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Analyze Deep Research execution logs')
    parser.add_argument('log_path', help='Path to execution_log.jsonl')
    parser.add_argument('--source', help='Filter by source name (e.g., "ClearanceJobs")')
    parser.add_argument('--task', type=int, help='Filter by task ID')
    parser.add_argument('--action', help='Filter by action type (e.g., "relevance_scoring")')
    parser.add_argument('--format', choices=['json', 'summary', 'human'], default='human',
                       help='Output format (default: human)')

    args = parser.parse_args()

    # Load log
    try:
        entries = load_log(args.log_path)
    except FileNotFoundError:
        print(f"Error: Log file not found: {args.log_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in log file: {e}")
        return 1

    # Apply filters
    if args.source:
        entries = filter_by_source(entries, args.source)
    if args.task is not None:
        entries = filter_by_task(entries, args.task)
    if args.action:
        entries = filter_by_action(entries, args.action)

    # Output
    if not entries:
        print("No entries match filters.")
        return 0

    if args.format == 'json':
        print(json.dumps(entries, indent=2))
    elif args.format == 'summary':
        print(generate_summary(entries))
    elif args.format == 'human':
        for i, entry in enumerate(entries):
            if i > 0:
                print()  # Blank line between entries
            print(format_entry_human(entry))


if __name__ == '__main__':
    exit(main() or 0)
