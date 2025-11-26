#!/usr/bin/env python3
"""Simple CLI for running deep research in background."""

import asyncio
import argparse
import logging
from research.deep_research import SimpleDeepResearch, ResearchProgress
from config_loader import config

# Configure logging to show INFO level for error reformulation visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def show_progress(progress: ResearchProgress):
    """Display progress updates."""
    print(f"[{progress.timestamp}] {progress.event}: {progress.message}")

async def main():
    parser = argparse.ArgumentParser(description='Run deep research with configurable parameters')
    parser.add_argument('question', help='Research question to investigate')
    parser.add_argument('--max-tasks', type=int, help='Maximum tasks (overrides config.yaml)')
    parser.add_argument('--max-time-minutes', type=int, help='Maximum time in minutes (overrides config.yaml)')
    parser.add_argument('--max-retries', type=int, help='Max retries per task (overrides config.yaml)')
    parser.add_argument('--max-concurrent', type=int, help='Max concurrent tasks (overrides config.yaml)')

    args = parser.parse_args()

    print(f"Starting research: {args.question}\n")

    # Load config from config.yaml
    raw_config = config.get_raw_config()
    deep_config = raw_config.get("research", {}).get("deep_research", {})

    # Command-line args override config.yaml defaults
    max_tasks = args.max_tasks if args.max_tasks is not None else deep_config.get("max_tasks", 20)
    max_time_minutes = args.max_time_minutes if args.max_time_minutes is not None else deep_config.get("max_time_minutes", 120)
    max_retries = args.max_retries if args.max_retries is not None else deep_config.get("max_retries_per_task", 3)
    max_concurrent = args.max_concurrent if args.max_concurrent is not None else deep_config.get("max_concurrent_tasks", 4)

    print(f"Configuration: max_tasks={max_tasks}, max_time_minutes={max_time_minutes}, "
          f"max_retries={max_retries}, max_concurrent={max_concurrent}")
    print()

    engine = SimpleDeepResearch(
        max_tasks=max_tasks,
        max_time_minutes=max_time_minutes,
        max_retries_per_task=max_retries,
        max_concurrent_tasks=max_concurrent,
        progress_callback=show_progress,
        save_output=True,
        output_dir="data/research_output"
    )

    result = await engine.research(args.question)

    print("\n" + "="*80)
    print("RESEARCH COMPLETE")
    print("="*80)
    print(f"Output saved to: {result.get('output_dir', 'data/research_output')}")
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Total results: {result.get('total_results', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
