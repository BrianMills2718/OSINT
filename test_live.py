#!/usr/bin/env python3
"""
Quick live test of the agentic search system after reorganization.
Tests actual API calls with real keys.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test imports
from integrations.sam_integration import SAMIntegration
from integrations.dvids_integration import DVIDSIntegration
from core.parallel_executor import ParallelExecutor


async def main():
    print("🧪 Live Integration Test")
    print("=" * 80)

    # Get API keys
    sam_key = os.getenv('SAM_GOV_API_KEY')
    dvids_key = os.getenv('DVIDS_API_KEY')

    if not sam_key:
        print("✗ No SAM_GOV_API_KEY found in .env")
        sys.exit(1)

    if not dvids_key:
        print("✗ No DVIDS_API_KEY found in .env")
        sys.exit(1)

    print(f"✓ API keys loaded")
    print()

    # Test 1: SAM.gov
    print("Test 1: SAM.gov - Cybersecurity Contracts")
    print("-" * 80)

    sam = SAMIntegration()
    query = await sam.generate_query("cybersecurity contracts")

    if query:
        print(f"✓ Query generated: {query.get('keywords')}")
        result = await sam.execute_search(query, api_key=sam_key, limit=3)

        if result.success:
            print(f"✓ Search successful: {result.total:,} results found")
            print(f"  Response time: {result.response_time_ms:.0f}ms")
            if result.results:
                print(f"  First result: {result.results[0].get('title', 'N/A')[:60]}...")
        else:
            print(f"✗ Search failed: {result.error}")
    else:
        print("✗ Query generation failed")

    print()

    # Test 2: DVIDS
    print("Test 2: DVIDS - Military Photos")
    print("-" * 80)

    dvids = DVIDSIntegration()
    query2 = await dvids.generate_query("training photos")

    if query2:
        print(f"✓ Query generated: {query2.get('keywords')}")
        result2 = await dvids.execute_search(query2, api_key=dvids_key, limit=3)

        if result2.success:
            print(f"✓ Search successful: {result2.total:,} results found")
            print(f"  Response time: {result2.response_time_ms:.0f}ms")
        else:
            print(f"✗ Search failed: {result2.error}")
    else:
        print("✗ Query generation failed")

    print()

    # Test 3: Parallel Execution
    print("Test 3: Parallel Executor - Multiple Databases")
    print("-" * 80)

    executor = ParallelExecutor()
    databases = [sam, dvids]
    api_keys = {'sam': sam_key, 'dvids': dvids_key}

    results = await executor.execute_all(
        research_question="military training",
        databases=databases,
        api_keys=api_keys,
        limit=3
    )

    print(f"✓ Searched {len(results)} databases in parallel")
    for db_id, result in results.items():
        if result.success:
            print(f"  {result.source}: {result.total:,} results ({result.response_time_ms:.0f}ms)")
        else:
            print(f"  {result.source}: Failed - {result.error}")

    print()
    print("=" * 80)
    print("✅ Live integration tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
