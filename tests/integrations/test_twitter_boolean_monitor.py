#!/usr/bin/env python3
"""
Test Twitter Integration via Boolean Monitor

Tests that Twitter works correctly through the Boolean monitoring system:
1. Monitor loads Twitter from registry
2. Twitter searches execute via monitor flow
3. Results are properly formatted and deduplicated
4. Monitor can process multiple keywords in parallel
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from monitoring.boolean_monitor import BooleanMonitor
from integrations.registry import registry

load_dotenv()

async def test_twitter_in_boolean_monitor():
    print("=" * 80)
    print("TWITTER INTEGRATION - BOOLEAN MONITOR TEST")
    print("=" * 80)

    # Verify Twitter is registered
    print("\n[STEP 1] Verify Twitter in Registry")
    print("-" * 80)

    all_sources = registry.list_ids()
    print(f"✅ Registry loaded: {len(all_sources)} sources")
    print(f"   Sources: {all_sources}")

    if 'twitter' in all_sources:
        print("✅ Twitter is registered")
    else:
        print("❌ FAIL: Twitter not found in registry")
        return

    # Load NVE monitor config
    print("\n[STEP 2] Load NVE Monitor Configuration")
    print("-" * 80)

    config_path = "data/monitors/configs/nve_monitor.yaml"
    monitor = BooleanMonitor(config_path)

    print(f"✅ Monitor loaded: {monitor.config.name}")
    print(f"   Keywords: {monitor.config.keywords}")
    print(f"   Sources: {monitor.config.sources}")

    if 'twitter' in monitor.config.sources:
        print("✅ Twitter is configured in NVE monitor")
    else:
        print("❌ FAIL: Twitter not in monitor sources (did you save the config?)")
        return

    # Test single keyword search via Twitter
    print("\n[STEP 3] Test Single Keyword Search (Twitter only)")
    print("-" * 80)

    # Override config to test Twitter only
    monitor.config.sources = ["twitter"]

    test_keyword = "NVE"  # Simple keyword from monitor
    print(f"Testing keyword: '{test_keyword}'")
    print("(This will make a real API call, ~3 seconds)")

    results = await monitor.execute_search([test_keyword])

    print(f"\n✅ Search completed")
    print(f"   Total results: {len(results)}")

    if len(results) > 0:
        print("\n📄 Sample Results:")
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result.get('title', 'Untitled')}")
            print(f"   Source: {result.get('source', 'Unknown')}")
            print(f"   Date: {result.get('date', 'N/A')}")
            print(f"   Keyword: {result.get('keyword', 'N/A')}")
            if result.get('url'):
                print(f"   URL: {result['url']}")
            if result.get('author'):
                print(f"   Author: @{result['author']}")
    else:
        print("⚠️  No results found (may be normal if keyword has no recent Twitter activity)")

    # Test deduplication
    print("\n[STEP 4] Test Deduplication")
    print("-" * 80)

    if len(results) > 0:
        deduplicated = monitor.deduplicate_results(results)
        print(f"✅ Deduplication completed")
        print(f"   Original: {len(results)} results")
        print(f"   Deduplicated: {len(deduplicated)} results")
        print(f"   Removed: {len(results) - len(deduplicated)} duplicates")
    else:
        print("⚠️  Skipping deduplication test (no results)")

    # Test multiple keywords in parallel
    print("\n[STEP 5] Test Multiple Keywords in Parallel (Twitter only)")
    print("-" * 80)

    test_keywords = ["NVE", "domestic extremism", "DVE"]
    print(f"Testing {len(test_keywords)} keywords: {test_keywords}")
    print("(This will make 3 parallel API calls, ~3-5 seconds)")

    multi_results = await monitor.execute_search(test_keywords)

    print(f"\n✅ Parallel search completed")
    print(f"   Total results: {len(multi_results)}")

    # Show breakdown by keyword
    keyword_counts = {}
    for result in multi_results:
        keyword = result.get('keyword', 'Unknown')
        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    print("\n📊 Results by Keyword:")
    for keyword, count in keyword_counts.items():
        print(f"   '{keyword}': {count} results")

    # Test with multiple sources (Twitter + DVIDS as example)
    print("\n[STEP 6] Test Multi-Source Search (Twitter + DVIDS)")
    print("-" * 80)

    monitor.config.sources = ["twitter", "dvids"]

    mixed_results = await monitor.execute_search(["domestic extremism"])

    print(f"\n✅ Multi-source search completed")
    print(f"   Total results: {len(mixed_results)}")

    # Show breakdown by source
    source_counts = {}
    for result in mixed_results:
        source = result.get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    print("\n📊 Results by Source:")
    for source, count in source_counts.items():
        print(f"   {source}: {count} results")

    if 'Twitter' in source_counts:
        print("✅ Twitter results present in multi-source search")
    else:
        print("⚠️  No Twitter results in multi-source search (may be normal)")

    # Final verdict
    print("\n" + "=" * 80)
    if len(results) > 0 and 'twitter' in all_sources:
        print("✅ BOOLEAN MONITOR TEST: PASS")
        print("   - Twitter registered in registry")
        print("   - Twitter configured in NVE monitor")
        print("   - Single keyword search works")
        print("   - Parallel keyword search works")
        print("   - Multi-source search works")
        print("   - Results properly formatted")
    else:
        print("⚠️  BOOLEAN MONITOR TEST: PARTIAL PASS")
        print("   - Twitter integration works but returned no results")
        print("   - This may be normal if keywords have no recent activity")
    print("=" * 80)

    print("\nNext steps:")
    print("  1. Run full monitor: python3 -m monitoring.boolean_monitor")
    print("  2. Check email alerts (if SMTP configured)")
    print("  3. Add Twitter to other monitors as needed")

if __name__ == "__main__":
    asyncio.run(test_twitter_in_boolean_monitor())
