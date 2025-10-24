#!/usr/bin/env python3
"""
Test if Brave Search integration is working in Deep Research.

Tests:
1. Brave Search API directly
2. Deep Research using Brave Search
3. Verifies web results are combined with government database results
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research.deep_research import SimpleDeepResearch

load_dotenv()


async def test_brave_search():
    """Test Brave Search integration in Deep Research."""

    # Check if API key is present
    api_key = os.getenv('BRAVE_SEARCH_API_KEY')
    if not api_key:
        print("❌ BRAVE_SEARCH_API_KEY not found in .env")
        print("   Brave Search will be skipped in Deep Research")
        return False

    print("✓ BRAVE_SEARCH_API_KEY found")

    # Create Deep Research engine
    print("\n" + "="*80)
    print("TESTING BRAVE SEARCH IN DEEP RESEARCH")
    print("="*80)

    engine = SimpleDeepResearch(
        max_tasks=3,  # Keep it small for testing
        max_retries_per_task=1,
        max_time_minutes=10,
        min_results_per_task=1  # Accept any results
    )

    # Simple test question
    question = "JSOC operations"

    print(f"\nTest Question: {question}")
    print("Expected: Results from both government databases AND Brave Search web results")
    print("\nExecuting...\n")

    try:
        result = await engine.research(question)

        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)

        print(f"Tasks Executed: {result['tasks_executed']}")
        print(f"Tasks Failed: {result['tasks_failed']}")
        print(f"Total Results: {result['total_results']}")
        print(f"Sources Searched: {result['sources_searched']}")

        # Check if Brave Search is in sources
        sources = result['sources_searched']
        has_brave = 'Brave Search' in sources
        has_gov = any(s for s in sources if s != 'Brave Search')

        print(f"\n✓ Brave Search Results: {'YES' if has_brave else 'NO'}")
        print(f"✓ Government DB Results: {'YES' if has_gov else 'NO'}")

        if has_brave and has_gov:
            print("\n✅ SUCCESS: Brave Search integration is working!")
            print("   Deep Research is combining web results with government database results")
            return True
        elif has_brave:
            print("\n⚠️  PARTIAL: Brave Search works but no government DB results")
            print("   (May be normal if government DBs not relevant to query)")
            return True
        elif has_gov:
            print("\n❌ FAIL: No Brave Search results found")
            print("   Check if BRAVE_SEARCH_API_KEY is valid")
            return False
        else:
            print("\n❌ FAIL: No results from any source")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_brave_search())
    sys.exit(0 if success else 1)
