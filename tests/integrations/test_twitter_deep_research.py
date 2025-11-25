#!/usr/bin/env python3
"""
Quick CLI test for Twitter integration with deep research.
Tests that expanded Twitter integration works in full system.
"""

import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from research.deep_research import SimpleDeepResearch, ResearchProgress


async def main():
    """Test Twitter integration in deep research."""

    # Progress callback for live updates
    def show_progress(progress: ResearchProgress):
        """Display progress updates."""
        print(f"[{progress.event.upper()}] {progress.message}")
        if progress.data and progress.event in ["source_selected", "query_generated", "results_found"]:
            print(f"  → {json.dumps(progress.data, indent=2)}")

    # Create engine with limited scope for quick testing
    engine = SimpleDeepResearch(
        max_tasks=2,  # Just 2 tasks for quick test
        max_retries_per_task=1,
        max_time_minutes=15,  # 15 min max
        min_results_per_task=3,
        progress_callback=show_progress
    )

    # Twitter-specific test question (should trigger user_timeline pattern)
    question = "What is @bellingcat saying about Ukraine?"

    print(f"\n{'='*80}")
    print(f"TWITTER INTEGRATION DEEP RESEARCH TEST")
    print(f"Question: {question}")
    print(f"Expected: Should select Twitter user_timeline endpoint")
    print(f"{'='*80}\n")

    # Execute research
    result = await engine.research(question)

    # Display compact summary
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    print(f"✓ Tasks Executed: {result['tasks_executed']}")
    print(f"✓ Total Results: {result['total_results']}")
    print(f"✓ Sources Used: {', '.join(result['sources_searched'])}")
    print(f"✓ Elapsed Time: {result['elapsed_minutes']:.1f} minutes")

    # Check if Twitter was used
    if 'Twitter' in result['sources_searched']:
        print("\n✅ SUCCESS: Twitter integration was used!")

        # Look for Twitter results in raw data
        twitter_results = []
        for item in result.get('all_results', []):
            if item.get('source') == 'Twitter' or '@bellingcat' in str(item.get('url', '')):
                twitter_results.append(item)

        if twitter_results:
            print(f"✅ Found {len(twitter_results)} Twitter results")
            print("\nSample Twitter result:")
            sample = twitter_results[0]
            print(f"  Title: {sample.get('title', 'N/A')[:80]}")
            print(f"  URL: {sample.get('url', 'N/A')}")
            print(f"  Author: {sample.get('author', 'N/A')}")
        else:
            print("⚠️  Twitter was selected but no results found")
    else:
        print("\n❌ FAIL: Twitter integration was NOT used!")
        print(f"Sources used: {result['sources_searched']}")

    # Show snippet of final report
    print("\n" + "="*80)
    print("FINAL REPORT (first 500 chars)")
    print("="*80)
    print(result['report'][:500] + "...\n")

    return 0 if 'Twitter' in result['sources_searched'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
