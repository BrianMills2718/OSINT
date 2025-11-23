#!/usr/bin/env python3
"""Simple CLI for running deep research in background."""

import asyncio
import sys
from research.deep_research import SimpleDeepResearch, ResearchProgress
from config_loader import config

def show_progress(progress: ResearchProgress):
    """Display progress updates."""
    print(f"[{progress.timestamp}] {progress.event}: {progress.message}")

async def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "Test query"

    print(f"Starting research: {question}\n")

    # Load config from config.yaml
    deep_config = config.get("research", {}).get("deep_research", {})

    engine = SimpleDeepResearch(
        max_tasks=deep_config.get("max_tasks", 20),
        max_time_minutes=deep_config.get("max_time_minutes", 120),
        max_retries_per_task=deep_config.get("max_retries_per_task", 3),
        max_concurrent_tasks=deep_config.get("max_concurrent_tasks", 4),
        progress_callback=show_progress,
        save_output=True,
        output_dir="data/research_output"
    )

    result = await engine.research(question)

    print("\n" + "="*80)
    print("RESEARCH COMPLETE")
    print("="*80)
    print(f"Output saved to: {result.get('output_dir', 'data/research_output')}")
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Total results: {result.get('total_results', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
