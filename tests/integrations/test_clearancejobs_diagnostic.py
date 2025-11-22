#!/usr/bin/env python3
"""Diagnostic test for ClearanceJobs Playwright download issue."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration

async def test():
    load_dotenv()

    print("=" * 60)
    print("ClearanceJobs Diagnostic Test - SIGINT Query")
    print("=" * 60)

    integration = ClearanceJobsIntegration()

    # Test 1: is_relevant check
    print(f"\n1. Testing is_relevant()...")
    query = "SIGINT signals intelligence"
    is_relevant = await integration.is_relevant(query)
    print(f"   Is relevant: {is_relevant}")

    # Test 2: generate_query
    print(f"\n2. Testing generate_query()...")
    query_params = await integration.generate_query(query)

    if not query_params:
        print(f"   ❌ Query generation returned None (deemed not relevant)")
        return False

    print(f"   ✅ Query params generated:")
    print(f"   Keywords: {query_params.get('keywords')}")
    print(f"   Location: {query_params.get('location')}")
    print(f"   Clearance level: {query_params.get('clearance_level')}")

    # Test 3: execute_search with those exact params
    print(f"\n3. Testing execute_search() with generated params...")
    try:
        result = await integration.execute_search(
            query_params=query_params,
            limit=10
        )

        print(f"\n4. Results:")
        print(f"   Success: {result.success}")
        print(f"   Total: {result.total}")
        print(f"   Error: {result.error}")

        if result.success:
            print(f"\n✅ TEST PASSED: ClearanceJobs working with SIGINT query")
            if result.total > 0:
                print(f"   First result: {result.results[0].get('title', 'No title')[:100]}...")
            return True
        else:
            print(f"\n❌ TEST FAILED: {result.error}")
            print(f"\n   Debug info:")
            print(f"   Metadata: {result.metadata}")
            return False

    except Exception as e:
        print(f"\n❌ Exception during execute_search:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
