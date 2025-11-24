#!/usr/bin/env python3
"""Simple CLI wrapper for deep research."""

import asyncio
import json
import sys
from research.deep_research import SimpleDeepResearch, ResearchProgress


def show_progress(progress: ResearchProgress):
    """Display progress updates."""
    print(f"\n{'='*80}")
    print(f"[{progress.timestamp}] {progress.event.upper()}")
    print(f"Message: {progress.message}")
    if progress.task_id is not None:
        print(f"Task ID: {progress.task_id}")
    if progress.data:
        data_str = json.dumps(progress.data, indent=2)
        if len(data_str) > 500:
            data_str = data_str[:500] + "..."
        print(f"Data: {data_str}")
    print('='*80)


async def main():
    """Run deep research with user question."""

    if len(sys.argv) < 2:
        print("Usage: python3 run_research.py '<research question>'")
        sys.exit(1)

    question = sys.argv[1]

    print(f"\n{'#'*80}")
    print(f"# DEEP RESEARCH")
    print(f"# Question: {question}")
    print(f"# Output: data/research_output/")
    print(f"{'#'*80}\n")

    # Create engine with production settings
    engine = SimpleDeepResearch(
        max_tasks=10,                    # Up to 10 tasks
        max_retries_per_task=2,          # 2 retries per task
        max_time_minutes=120,            # 2 hour max
        min_results_per_task=5,          # Min 5 results per task
        max_concurrent_tasks=3,          # 3 parallel tasks
        progress_callback=show_progress
    )

    # Execute research
    result = await engine.research(question)

    # Display summary
    print("\n" + "="*80)
    print("RESEARCH COMPLETE")
    print("="*80)
    print(f"Tasks Executed: {result['tasks_executed']}")
    print(f"Tasks Failed: {result['tasks_failed']}")
    print(f"Total Results: {result['total_results']}")
    print(f"Entities: {len(result['entities_discovered'])}")
    print(f"Sources: {', '.join(result['sources_searched'])}")
    print(f"Time: {result['elapsed_minutes']:.1f} minutes")
    print(f"\nOutput directory: {result.get('output_directory', 'N/A')}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
