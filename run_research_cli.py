#!/usr/bin/env python3
"""Simple CLI for running deep research in background."""

import asyncio
import sys
from research.deep_research import SimpleDeepResearch, ResearchProgress

def show_progress(progress: ResearchProgress):
    """Display progress updates."""
    print(f"[{progress.timestamp}] {progress.event}: {progress.message}")

async def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "Test query"

    print(f"Starting research: {question}\n")

    engine = SimpleDeepResearch(
        max_tasks=8,
        max_time_minutes=60,
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
