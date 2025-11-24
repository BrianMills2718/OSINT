#!/usr/bin/env python3
"""
Profile deep research execution to identify bottlenecks.

Usage:
    python3 tools/profile_research.py "research question"
"""

import asyncio
import cProfile
import pstats
import io
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch
from config_loader import config


def profile_research(question: str):
    """Profile a research query."""

    async def run_research():
        # Use minimal config for faster profiling
        raw_config = config.get_raw_config()
        deep_config = raw_config.get("research", {}).get("deep_research", {})

        engine = SimpleDeepResearch(
            max_tasks=3,  # Reduced for profiling
            max_retries_per_task=1,
            max_time_minutes=5,  # 5 min max for profiling
            min_results_per_task=3,
            max_concurrent_tasks=2
        )

        result = await engine.research(question)
        return result

    # Run with profiling
    profiler = cProfile.Profile()
    profiler.enable()

    result = asyncio.run(run_research())

    profiler.disable()

    # Print results
    print("\n" + "="*80)
    print("PROFILING RESULTS")
    print("="*80)

    # Sort by cumulative time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')

    print("\nTop 30 functions by cumulative time:")
    print("-"*80)
    ps.print_stats(30)
    print(s.getvalue())

    # Sort by total time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('tottime')

    print("\nTop 30 functions by total time:")
    print("-"*80)
    ps.print_stats(30)
    print(s.getvalue())

    # Print summary
    print("\n" + "="*80)
    print("RESEARCH SUMMARY")
    print("="*80)
    print(f"Tasks executed: {result.get('tasks_executed', 0)}")
    print(f"Total results: {result.get('total_results', 0)}")
    print(f"Time: {result.get('elapsed_minutes', 0):.2f} minutes")
    print(f"Sources: {', '.join(result.get('sources_searched', []))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/profile_research.py 'research question'")
        sys.exit(1)

    question = sys.argv[1]
    profile_research(question)
