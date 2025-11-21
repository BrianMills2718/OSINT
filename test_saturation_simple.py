#!/usr/bin/env python3
"""Simple test to validate query saturation is working - creates minimal hypothesis."""

import asyncio
import sys
from research.deep_research import SimpleDeepResearch

async def test_saturation():
    """Run a minimal test with saturation enabled."""

    engine = SimpleDeepResearch()

    print(f"\n✓ Config loaded:")
    print(f"  Query saturation enabled: {engine.query_saturation_enabled}")
    print(f"  Max queries for SAM.gov: {engine.max_queries_per_source.get('SAM.gov')}")
    print(f"  Max queries for Brave: {engine.max_queries_per_source.get('Brave Search')}")
    print(f"  Max time per source: {engine.max_time_per_source_seconds}s\n")

    if not engine.query_saturation_enabled:
        print("❌ ERROR: Saturation not enabled in config!")
        return

    # Create a simple hypothesis for testing
    hypothesis = {
        'id': 'test-1',
        'statement': 'DARPA has official websites and news presence',
        'search_strategy': {'approach': 'direct_search'},
        'information_gaps': ['basic DARPA information']
    }

    # Mock task
    class MockTask:
        id = 1
        query = "What is DARPA?"
        original_question = "What is DARPA?"

    task = MockTask()

    print("🔬 Testing saturation with Brave Search (max 2 queries)...")
    print("=" * 60)

    try:
        results = await engine._execute_source_with_saturation(
            task_id=task.id,
            task=task,
            hypothesis=hypothesis,
            source_name="Brave Search"
        )

        print("\n" + "=" * 60)
        print(f"✓ Saturation test completed!")
        print(f"  Total results: {len(results)}")
        print(f"\n  Check execution_log.jsonl for saturation events:")
        print(f"    - source_saturation_start")
        print(f"    - query_attempt (should see 1-2 queries)")
        print(f"    - source_saturation_complete")

    except Exception as e:
        print(f"\n❌ Error during saturation test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_saturation())
