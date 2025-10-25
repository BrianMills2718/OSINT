#!/usr/bin/env python3
"""
Test DVIDS Parallel Execution - Verify 403 Error Root Cause

Tests whether DVIDS returns 403 errors during parallel execution
(as observed in Deep Research) to verify concurrent throttling hypothesis.

AGENT2 - DVIDS 403 Investigation (Parallel Test)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.government.dvids_integration import DVIDSIntegration
from config_loader import config

async def test_parallel_dvids_execution():
    """Test DVIDS with parallel execution (replicates Deep Research scenario)."""

    print("=" * 80)
    print("TESTING: DVIDS Parallel Execution (403 Root Cause)")
    print("=" * 80)

    integration = DVIDSIntegration()
    api_key = os.getenv("DVIDS_API_KEY")

    if not api_key:
        print("\n❌ DVIDS_API_KEY not found in .env")
        return False

    # Generate 3 different queries (like Deep Research does)
    test_queries = [
        "JSOC mission and role in U.S. special operations",
        "JSOC organizational structure units Delta Force DEVGRU",
        "JSOC notable operations missions Bin Laden raid"
    ]

    print(f"\nGenerating query parameters for {len(test_queries)} queries...")
    query_params_list = []
    for i, query in enumerate(test_queries, 1):
        params = await integration.generate_query(query)
        query_params_list.append(params)
        print(f"  Query {i}: Generated")

    # Test 1: Sequential execution (baseline - should work)
    print("\n" + "=" * 80)
    print("TEST 1: Sequential Execution (Baseline)")
    print("=" * 80)

    sequential_results = []
    sequential_start = asyncio.get_event_loop().time()

    for i, params in enumerate(query_params_list, 1):
        result = await integration.execute_search(params, api_key, limit=5)
        sequential_results.append(result)
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  Query {i}: {status}")
        if not result.success:
            print(f"    Error: {result.error}")

    sequential_time = asyncio.get_event_loop().time() - sequential_start

    sequential_success = sum(1 for r in sequential_results if r.success)
    print(f"\nSequential: {sequential_success}/{len(sequential_results)} succeeded in {sequential_time:.1f}s")

    # Test 2: Parallel execution (actual Deep Research scenario)
    print("\n" + "=" * 80)
    print("TEST 2: Parallel Execution (Deep Research Scenario)")
    print("=" * 80)

    parallel_start = asyncio.get_event_loop().time()

    # Execute all 3 queries simultaneously
    tasks = [
        integration.execute_search(params, api_key, limit=5)
        for params in query_params_list
    ]

    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

    parallel_time = asyncio.get_event_loop().time() - parallel_start

    print("\nParallel results:")
    for i, result in enumerate(parallel_results, 1):
        if isinstance(result, Exception):
            print(f"  Query {i}: ✗ EXCEPTION - {str(result)}")
        elif result.success:
            print(f"  Query {i}: ✓ SUCCESS - {result.total} results")
        else:
            print(f"  Query {i}: ✗ FAILED - {result.error}")
            if "403" in str(result.error):
                print(f"    ⚠️ HTTP 403 DETECTED")

    parallel_success = sum(1 for r in parallel_results if not isinstance(r, Exception) and r.success)
    parallel_403 = sum(1 for r in parallel_results if not isinstance(r, Exception) and not r.success and "403" in str(r.error or ""))

    print(f"\nParallel: {parallel_success}/{len(parallel_results)} succeeded in {parallel_time:.1f}s")
    if parallel_403 > 0:
        print(f"  ⚠️ {parallel_403} requests failed with HTTP 403")

    # Test 3: Rapid sequential (to test rate limiting vs concurrency)
    print("\n" + "=" * 80)
    print("TEST 3: Rapid Sequential (Rate Limit Test)")
    print("=" * 80)
    print("Executing queries with 0.1s delay between them...")

    rapid_results = []
    rapid_start = asyncio.get_event_loop().time()

    for i, params in enumerate(query_params_list, 1):
        result = await integration.execute_search(params, api_key, limit=5)
        rapid_results.append(result)
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"  Query {i}: {status}")
        if not result.success and "403" in str(result.error or ""):
            print(f"    ⚠️ HTTP 403 DETECTED")

        # Small delay before next request
        if i < len(query_params_list):
            await asyncio.sleep(0.1)

    rapid_time = asyncio.get_event_loop().time() - rapid_start
    rapid_success = sum(1 for r in rapid_results if r.success)
    rapid_403 = sum(1 for r in rapid_results if not r.success and "403" in str(r.error or ""))

    print(f"\nRapid Sequential: {rapid_success}/{len(rapid_results)} succeeded in {rapid_time:.1f}s")
    if rapid_403 > 0:
        print(f"  ⚠️ {rapid_403} requests failed with HTTP 403")

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    print(f"\nSequential execution:    {sequential_success}/{len(sequential_results)} success, 0 x 403")
    print(f"Parallel execution:      {parallel_success}/{len(parallel_results)} success, {parallel_403} x 403")
    print(f"Rapid sequential:        {rapid_success}/{len(rapid_results)} success, {rapid_403} x 403")

    # Determine root cause
    if parallel_403 > 0 and sequential_success == len(sequential_results):
        print("\n✅ ROOT CAUSE CONFIRMED: Concurrent request throttling")
        print("   - Sequential execution: All succeed")
        print("   - Parallel execution: Some fail with 403")
        print("   - Diagnosis: DVIDS API limits concurrent requests")
        return "concurrent_throttling"
    elif parallel_403 == 0 and sequential_success == len(sequential_results):
        print("\n⚠️ ROOT CAUSE UNKNOWN: No 403 errors observed")
        print("   - Sequential execution: All succeed")
        print("   - Parallel execution: All succeed")
        print("   - Diagnosis: Cannot replicate original 403 errors")
        return "cannot_replicate"
    else:
        print("\n⚠️ ROOT CAUSE UNCLEAR: Inconsistent results")
        print(f"   - Sequential: {sequential_success}/{len(sequential_results)}")
        print(f"   - Parallel: {parallel_success}/{len(parallel_results)}")
        return "unclear"

if __name__ == "__main__":
    result = asyncio.run(test_parallel_dvids_execution())

    print("\n" + "=" * 80)
    if result == "concurrent_throttling":
        print("✅ DVIDS 403 ROOT CAUSE: Concurrent throttling CONFIRMED")
    elif result == "cannot_replicate":
        print("⚠️ DVIDS 403 ROOT CAUSE: Cannot replicate (403 errors may be transient)")
    else:
        print("⚠️ DVIDS 403 ROOT CAUSE: Unclear - more investigation needed")
    print("=" * 80)
