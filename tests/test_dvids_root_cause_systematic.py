#!/usr/bin/env python3
"""
Systematic DVIDS 403 Root Cause Test

Tests to isolate the actual cause of 403 errors:
1. JSOC queries (sequential) - Test if content filtering exists
2. Generic queries (parallel) - Test if concurrency is the issue
3. JSOC queries (parallel) - Test combined effect

AGENT2 - Proper Root Cause Investigation
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.government.dvids_integration import DVIDSIntegration

async def test_systematic():
    """Systematic test to isolate 403 root cause."""

    integration = DVIDSIntegration()
    api_key = os.getenv("DVIDS_API_KEY")

    if not api_key:
        print("❌ DVIDS_API_KEY not found")
        return

    print("=" * 80)
    print("SYSTEMATIC DVIDS 403 ROOT CAUSE TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Query sets
    jsoc_queries = [
        "JSOC mission and role in U.S. special operations",
        "JSOC organizational structure units Delta Force",
        "JSOC notable operations missions"
    ]

    generic_queries = [
        "Air Force training exercises",
        "Navy ship deployments",
        "Army equipment maintenance"
    ]

    results = {}

    # TEST 1: JSOC queries (sequential) - Tests content filtering hypothesis
    print("=" * 80)
    print("TEST 1: JSOC Queries - Sequential Execution")
    print("=" * 80)
    print("Hypothesis: If content filtering exists, these should fail")
    print()

    jsoc_sequential = []
    for i, query in enumerate(jsoc_queries, 1):
        print(f"Query {i}: {query}")
        params = await integration.generate_query(query)
        result = await integration.execute_search(params, api_key, limit=5)
        jsoc_sequential.append(result)

        if result.success:
            print(f"  ✅ SUCCESS - {result.total} results")
        else:
            print(f"  ❌ FAILED - {result.error}")
            if "403" in str(result.error):
                print(f"     HTTP 403 detected")

        # Small delay to avoid rapid-fire
        await asyncio.sleep(0.5)

    jsoc_seq_success = sum(1 for r in jsoc_sequential if r.success)
    jsoc_seq_403 = sum(1 for r in jsoc_sequential if not r.success and "403" in str(r.error or ""))

    print(f"\nResult: {jsoc_seq_success}/{len(jsoc_queries)} succeeded, {jsoc_seq_403} x 403")
    results['jsoc_sequential'] = {
        'success': jsoc_seq_success,
        'total': len(jsoc_queries),
        'errors_403': jsoc_seq_403
    }

    # TEST 2: Generic queries (parallel) - Tests concurrency hypothesis
    print("\n" + "=" * 80)
    print("TEST 2: Generic Queries - Parallel Execution")
    print("=" * 80)
    print("Hypothesis: If concurrency throttling exists, these should fail")
    print()

    # Generate params first
    generic_params = []
    for query in generic_queries:
        params = await integration.generate_query(query)
        generic_params.append(params)

    # Execute in parallel
    print("Executing 3 generic queries simultaneously...")
    tasks = [
        integration.execute_search(params, api_key, limit=5)
        for params in generic_params
    ]
    generic_parallel = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(generic_parallel, 1):
        if isinstance(result, Exception):
            print(f"  Query {i}: ❌ EXCEPTION - {str(result)}")
        elif result.success:
            print(f"  Query {i}: ✅ SUCCESS - {result.total} results")
        else:
            print(f"  Query {i}: ❌ FAILED - {result.error}")
            if "403" in str(result.error):
                print(f"     HTTP 403 detected")

    generic_par_success = sum(1 for r in generic_parallel if not isinstance(r, Exception) and r.success)
    generic_par_403 = sum(1 for r in generic_parallel if not isinstance(r, Exception) and not r.success and "403" in str(r.error or ""))

    print(f"\nResult: {generic_par_success}/{len(generic_queries)} succeeded, {generic_par_403} x 403")
    results['generic_parallel'] = {
        'success': generic_par_success,
        'total': len(generic_queries),
        'errors_403': generic_par_403
    }

    # TEST 3: JSOC queries (parallel) - Tests combined effect
    print("\n" + "=" * 80)
    print("TEST 3: JSOC Queries - Parallel Execution")
    print("=" * 80)
    print("Hypothesis: Combined content + concurrency effect")
    print()

    # Generate params first
    jsoc_params = []
    for query in jsoc_queries:
        params = await integration.generate_query(query)
        jsoc_params.append(params)

    # Execute in parallel
    print("Executing 3 JSOC queries simultaneously...")
    tasks = [
        integration.execute_search(params, api_key, limit=5)
        for params in jsoc_params
    ]
    jsoc_parallel = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(jsoc_parallel, 1):
        if isinstance(result, Exception):
            print(f"  Query {i}: ❌ EXCEPTION - {str(result)}")
        elif result.success:
            print(f"  Query {i}: ✅ SUCCESS - {result.total} results")
        else:
            print(f"  Query {i}: ❌ FAILED - {result.error}")
            if "403" in str(result.error):
                print(f"     HTTP 403 detected")

    jsoc_par_success = sum(1 for r in jsoc_parallel if not isinstance(r, Exception) and r.success)
    jsoc_par_403 = sum(1 for r in jsoc_parallel if not isinstance(r, Exception) and not r.success and "403" in str(r.error or ""))

    print(f"\nResult: {jsoc_par_success}/{len(jsoc_queries)} succeeded, {jsoc_par_403} x 403")
    results['jsoc_parallel'] = {
        'success': jsoc_par_success,
        'total': len(jsoc_queries),
        'errors_403': jsoc_par_403
    }

    # ANALYSIS
    print("\n" + "=" * 80)
    print("ANALYSIS - ROOT CAUSE DETERMINATION")
    print("=" * 80)

    print("\nTest Results:")
    print(f"  1. JSOC Sequential:    {results['jsoc_sequential']['success']}/{results['jsoc_sequential']['total']} success, {results['jsoc_sequential']['errors_403']} x 403")
    print(f"  2. Generic Parallel:   {results['generic_parallel']['success']}/{results['generic_parallel']['total']} success, {results['generic_parallel']['errors_403']} x 403")
    print(f"  3. JSOC Parallel:      {results['jsoc_parallel']['success']}/{results['jsoc_parallel']['total']} success, {results['jsoc_parallel']['errors_403']} x 403")

    print("\n" + "=" * 80)
    print("CONCLUSIONS")
    print("=" * 80)

    # Determine root cause
    conclusions = []

    # Content filtering test
    if results['jsoc_sequential']['errors_403'] > 0:
        conclusions.append("❌ CONTENT FILTERING DETECTED: JSOC queries fail even when sequential")
        content_filtering = True
    else:
        conclusions.append("✅ NO CONTENT FILTERING: JSOC queries succeed when sequential")
        content_filtering = False

    # Concurrency throttling test
    if results['generic_parallel']['errors_403'] > 0:
        conclusions.append("❌ CONCURRENCY THROTTLING DETECTED: Generic queries fail when parallel")
        concurrency_throttling = True
    else:
        conclusions.append("✅ NO CONCURRENCY THROTTLING: Generic queries succeed when parallel")
        concurrency_throttling = False

    # Combined effect
    if results['jsoc_parallel']['errors_403'] > results['jsoc_sequential']['errors_403']:
        conclusions.append("⚠️ PARALLEL EXECUTION WORSENS FAILURES: Combined effect detected")

    print()
    for conclusion in conclusions:
        print(f"  {conclusion}")

    # Root cause statement
    print("\n" + "=" * 80)
    print("ROOT CAUSE")
    print("=" * 80)

    if content_filtering and concurrency_throttling:
        print("\n🔴 BOTH content filtering AND concurrency throttling detected")
        print("   - JSOC queries fail even when sequential (content issue)")
        print("   - Generic queries fail when parallel (concurrency issue)")
        root_cause = "both"
    elif content_filtering:
        print("\n🔴 CONTENT FILTERING is the primary issue")
        print("   - JSOC queries fail even when sequential")
        print("   - Generic queries succeed when parallel")
        root_cause = "content"
    elif concurrency_throttling:
        print("\n🔴 CONCURRENCY THROTTLING is the primary issue")
        print("   - JSOC queries succeed when sequential")
        print("   - Generic queries fail when parallel")
        root_cause = "concurrency"
    else:
        print("\n🟢 NO CONSISTENT ISSUES DETECTED")
        print("   - JSOC queries succeed when sequential")
        print("   - Generic queries succeed when parallel")
        print("   - Previous 403 errors may have been transient rate limiting")
        root_cause = "none_or_transient"

    print("\n" + "=" * 80)

    return root_cause, results

if __name__ == "__main__":
    root_cause, results = asyncio.run(test_systematic())

    print(f"\n✅ SYSTEMATIC TEST COMPLETE")
    print(f"Root Cause: {root_cause}")

    # Save results
    with open('dvids_root_cause_results.txt', 'w') as f:
        f.write(f"DVIDS Root Cause Test - {datetime.now()}\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"Root Cause: {root_cause}\n\n")
        f.write(f"Results:\n")
        for test_name, test_results in results.items():
            f.write(f"  {test_name}: {test_results['success']}/{test_results['total']} success, {test_results['errors_403']} x 403\n")

    print(f"\nResults saved to: dvids_root_cause_results.txt")
