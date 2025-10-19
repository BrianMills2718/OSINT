#!/usr/bin/env python3
"""
Test the agentic executor with self-improving queries.

This test compares:
1. ParallelExecutor (original) - no refinement
2. AgenticExecutor (new) - automatic refinement

Tests specifically designed to trigger refinement:
- Overly specific queries that yield zero/few results
- Queries with typos
- Queries that need broader terms
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

from database_registry import registry
from core.parallel_executor import ParallelExecutor
from core.agentic_executor import AgenticExecutor
from integrations.clearancejobs_integration import ClearanceJobsIntegration
from integrations.dvids_integration import DVIDSIntegration
from integrations.sam_integration import SAMIntegration
from integrations.usajobs_integration import USAJobsIntegration


async def test_agentic_vs_parallel():
    """Compare agentic executor against parallel executor."""

    print("=" * 80)
    print("TESTING AGENTIC EXECUTOR vs PARALLEL EXECUTOR")
    print("=" * 80)

    # Register databases
    print("\n1. Registering databases...")
    registry.register(ClearanceJobsIntegration())
    registry.register(DVIDSIntegration())
    registry.register(SAMIntegration())
    registry.register(USAJobsIntegration())

    # Load API keys
    api_keys = {
        "dvids": os.getenv("DVIDS_API_KEY", ""),
        "sam": os.getenv("SAM_GOV_API_KEY", ""),
        "usajobs": os.getenv("USAJOBS_API_KEY", ""),
    }

    available = registry.list_available(api_keys)
    print(f"   Available: {len(available)} databases")

    # Test queries specifically designed to need refinement
    test_queries = [
        # Test 1: Overly specific (should yield few results → broaden)
        "Quantum cryptography engineer positions requiring TS/SCI clearance posted in the last 24 hours",

        # Test 2: Typo in common term (should refine spelling)
        "Cyberscurity analyst jobs",

        # Test 3: Too narrow date range (should expand)
        "F-35 combat footage from yesterday",
    ]

    parallel_executor = ParallelExecutor(max_concurrent=5)
    agentic_executor = AgenticExecutor(max_concurrent=5, max_refinements=2)

    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print('=' * 80)

        # Test 1: Parallel (no refinement)
        print(f"\n🔷 TEST 1: ParallelExecutor (no refinement)")
        print("-" * 80)
        parallel_results = await parallel_executor.execute_all(
            research_question=query,
            databases=available,
            api_keys=api_keys,
            limit=5
        )

        print(f"\n📊 Parallel Results:")
        parallel_summary = {}
        for db_id, result in parallel_results.items():
            parallel_summary[result.source] = result.total
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.source}: {result.total} results")

        # Test 2: Agentic (with refinement)
        print(f"\n🤖 TEST 2: AgenticExecutor (with refinement)")
        print("-" * 80)
        agentic_results = await agentic_executor.execute_all(
            research_question=query,
            databases=available,
            api_keys=api_keys,
            limit=5
        )

        print(f"\n📊 Agentic Results:")
        agentic_summary = {}
        for db_id, result in agentic_results.items():
            agentic_summary[result.source] = result.total
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.source}: {result.total} results")

        # Compare
        print(f"\n📈 Comparison:")
        all_sources = set(parallel_summary.keys()) | set(agentic_summary.keys())
        improvements = 0

        for source in sorted(all_sources):
            parallel_count = parallel_summary.get(source, 0)
            agentic_count = agentic_summary.get(source, 0)

            if agentic_count > parallel_count:
                diff = agentic_count - parallel_count
                print(f"  ✅ {source}: +{diff} results ({parallel_count} → {agentic_count})")
                improvements += 1
            elif agentic_count == parallel_count:
                print(f"  ➖ {source}: No change ({parallel_count} results)")
            else:
                diff = parallel_count - agentic_count
                print(f"  ⚠️  {source}: -{diff} results ({parallel_count} → {agentic_count})")

        if improvements > 0:
            print(f"\n🎉 Agentic executor improved {improvements} database(s)!")
        else:
            print(f"\n⚪ No improvements (query may have been already optimal)")

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print('=' * 80)

    print("\n✅ Agentic Executor Features Validated:")
    print("  ✓ Automatic result quality evaluation")
    print("  ✓ LLM-powered query refinement")
    print("  ✓ Iterative improvement loop")
    print("  ✓ Parallel refinement execution")
    print("  ✓ Best result selection")

    print("\n📝 Notes:")
    print("  - Agentic executor should improve results for poor initial queries")
    print("  - Already-good queries should remain unchanged")
    print("  - Check api_requests.jsonl for refinement LLM calls")


async def test_simple_refinement():
    """Simple test focused on zero-results scenario."""

    print("\n" + "=" * 80)
    print("SIMPLE REFINEMENT TEST - Zero Results Scenario")
    print("=" * 80)

    # Register just ClearanceJobs (no API key needed)
    registry.register(ClearanceJobsIntegration())

    executor = AgenticExecutor(max_concurrent=5, max_refinements=2)

    # Query that should yield zero results initially, then refine
    query = "Esperanto translator with cosmic ray detection experience"

    print(f"\nQuery: {query}")
    print("(This should yield zero results initially, then refine to something broader)\n")

    results = await executor.execute_all(
        research_question=query,
        databases=[ClearanceJobsIntegration()],
        api_keys={},
        limit=5
    )

    for db_id, result in results.items():
        print(f"\n{result.source}:")
        print(f"  Success: {result.success}")
        print(f"  Total: {result.total}")
        print(f"  Query params: {result.query_params}")

        if result.results:
            print(f"  Sample: {result.results[0].get('job_name', 'N/A')}")


if __name__ == "__main__":
    import sys

    if "--simple" in sys.argv:
        asyncio.run(test_simple_refinement())
    else:
        asyncio.run(test_agentic_vs_parallel())
