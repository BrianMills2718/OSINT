#!/usr/bin/env python3
"""
Test parallel search WITHOUT relevance filtering or email alerts.
This isolates the search parallelism from LLM/SMTP operations.
"""

import asyncio
import time
from monitoring.boolean_monitor import BooleanMonitor

async def test_search_only():
    """Test just the search execution, skipping filtering and alerts."""

    # Load monitor config
    monitor = BooleanMonitor('data/monitors/configs/parallel_quick_test.yaml')

    print(f"Testing parallel search:")
    print(f"  Keywords: {monitor.config.keywords}")
    print(f"  Sources: {monitor.config.sources}")
    print(f"  Total searches: {len(monitor.config.keywords)} × {len(monitor.config.sources)} = {len(monitor.config.keywords) * len(monitor.config.sources)}")
    print()

    # Execute search (this should be parallel now)
    start = time.time()
    results = await monitor.execute_search(monitor.config.keywords)
    search_time = time.time() - start

    print(f"\n=== SEARCH COMPLETE ===")
    print(f"  Total results: {len(results)}")
    print(f"  Search time: {search_time:.1f}s")
    print(f"  Parallel speedup: {len(monitor.config.keywords) * len(monitor.config.sources) * 10:.0f}s sequential → {search_time:.1f}s parallel")

    # Show sample results
    if results:
        print(f"\nFirst 3 results:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.get('title', 'Untitled')[:60]}... ({result.get('source')})")

if __name__ == "__main__":
    asyncio.run(test_search_only())
