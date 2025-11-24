#!/usr/bin/env python3
"""
CLI test for full research system including all integrations.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from research.deep_research import SimpleDeepResearch


def show_progress(message: str):
    """Print progress updates."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


async def main():
    """Run full research test."""
    question = sys.argv[1] if len(sys.argv) > 1 else "How is AI and autonomous systems affecting defense contracting?"

    print("\n" + "="*80)
    print(f"FULL RESEARCH TEST")
    print("="*80)
    print(f"Question: {question}")
    print("="*80 + "\n")

    # Create research engine
    engine = SimpleDeepResearch(
        max_tasks=3,  # Limit tasks for faster test
        max_retries_per_task=1,
        max_time_minutes=30,
        min_results_per_task=5,
        progress_callback=show_progress
    )

    # Run research
    try:
        result = await engine.research(question)

        print("\n" + "="*80)
        print("RESEARCH COMPLETE")
        print("="*80)
        print(f"Tasks executed: {result.get('tasks_executed', 0)}")
        print(f"Total results: {result.get('total_results', 0)}")
        print(f"Sources searched: {', '.join(result.get('sources_searched', []))}")
        print(f"Output directory: {result.get('output_dir', 'N/A')}")
        print("="*80)

        # Show sample results
        if result.get('all_results'):
            print("\nSample Results:")
            for i, item in enumerate(result['all_results'][:5], 1):
                print(f"\n[{i}] {item.get('title', 'Untitled')[:100]}")
                print(f"    Source: {item.get('source', 'Unknown')}")
                print(f"    URL: {item.get('url', 'N/A')}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Research cancelled by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
