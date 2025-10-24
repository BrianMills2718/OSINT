#!/usr/bin/env python3
"""
Test that Deep Investigation uses government databases, not just Brave Search.

Verifies:
1. Databases are loaded from registry
2. API keys are loaded from environment
3. Databases are passed to adaptive_search()
4. Results include government database sources
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv

load_dotenv()


async def main():
    print("\n" + "="*80)
    print("DEEP INVESTIGATION DATABASE INTEGRATION TEST")
    print("="*80)

    # Create engine
    engine = SimpleDeepResearch(
        max_tasks=3,  # Limited tasks for quick test
        max_retries_per_task=1,
        max_time_minutes=10,
        min_results_per_task=1,
        max_concurrent_tasks=1  # Sequential for easier debugging
    )

    # Verify databases loaded
    print(f"\nDatabases loaded: {len(engine.databases)}")
    for db in engine.databases:
        print(f"  - {db.metadata.name} ({db.metadata.id})")

    # Verify API keys loaded
    print(f"\nAPI keys loaded:")
    for key, value in engine.api_keys.items():
        if value:
            # Mask the API key for security
            masked = f"{value[:8]}***{value[-4:]}" if len(value) > 12 else "***"
            print(f"  - {key}: {masked}")
        else:
            print(f"  - {key}: (none)")

    # Test question that should trigger SAM.gov (defense contractors)
    question = "defense contractors AI security"

    print(f"\n{'='*80}")
    print(f"Test Question: {question}")
    print(f"{'='*80}\n")

    # Execute research
    result = await engine.research(question)

    # Analyze results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Tasks failed: {result['tasks_failed']}")
    print(f"Total results: {result['total_results']}")
    print(f"Sources searched: {', '.join(result['sources_searched'])}")
    print(f"Elapsed time: {result['elapsed_minutes']:.1f} minutes")

    # Check if government databases were used
    gov_sources = [s for s in result['sources_searched'] if s not in ['Brave Search']]
    web_sources = [s for s in result['sources_searched'] if s == 'Brave Search']

    print(f"\nGovernment databases used: {len(gov_sources)}")
    for source in gov_sources:
        print(f"  - {source}")

    print(f"\nWeb search used: {len(web_sources)}")
    for source in web_sources:
        print(f"  - {source}")

    # Verdict
    print("\n" + "="*80)
    if len(gov_sources) > 0:
        print("✓ SUCCESS: Government databases are being searched!")
        print(f"  Found results from {len(gov_sources)} government source(s)")
        return True
    elif len(web_sources) > 0 and len(gov_sources) == 0:
        print("✗ FAILURE: Only web search used, no government databases")
        print("  This is the bug we're trying to fix")
        return False
    else:
        print("⚠ INCONCLUSIVE: No results from any source")
        print("  Check API keys and network connectivity")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
