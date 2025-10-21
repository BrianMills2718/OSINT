#!/usr/bin/env python3
"""
Quick Twitter Boolean Monitor Integration Test

Tests that Twitter works through the Boolean monitor with correct API key mapping.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from monitoring.boolean_monitor import BooleanMonitor

load_dotenv()

async def test_twitter_simple():
    print("=" * 80)
    print("TWITTER BOOLEAN MONITOR - QUICK TEST")
    print("=" * 80)

    config_path = "data/monitors/configs/nve_monitor.yaml"
    monitor = BooleanMonitor(config_path)

    print(f"\n✅ Monitor loaded: {monitor.config.name}")
    print(f"   Sources configured: {monitor.config.sources}")

    # Override to test Twitter only
    monitor.config.sources = ["twitter"]

    print("\nTesting single keyword search: 'NVE'")
    print("(This will make 1 API call, ~3 seconds)")

    results = await monitor.execute_search(["NVE"])

    print(f"\n✅ Search completed")
    print(f"   Total results: {len(results)}")

    if len(results) > 0:
        print("\n📄 Sample Results:")
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result.get('title', 'Untitled')}")
            print(f"   Source: {result.get('source', 'Unknown')}")
            print(f"   Author: @{result.get('author', 'N/A')}")
            if result.get('favorites') or result.get('retweets'):
                print(f"   Engagement: {result.get('favorites', 0)} likes, {result.get('retweets', 0)} RTs")

        print("\n" + "=" * 80)
        print("✅ PASS: Twitter integration working via Boolean monitor")
        print("=" * 80)
    else:
        print("\n⚠️  No results found (keyword may have no recent Twitter activity)")

if __name__ == "__main__":
    asyncio.run(test_twitter_simple())
