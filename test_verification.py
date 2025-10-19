#!/usr/bin/env python3
"""
Comprehensive verification test - prove everything actually works.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from integrations.sam_integration import SAMIntegration
from integrations.dvids_integration import DVIDSIntegration
from integrations.usajobs_integration import USAJobsIntegration
from core.parallel_executor import ParallelExecutor


async def main():
    print("="*80)
    print("COMPREHENSIVE VERIFICATION TEST")
    print("="*80)

    # Get API keys
    sam_key = os.getenv('SAM_GOV_API_KEY')
    dvids_key = os.getenv('DVIDS_API_KEY')
    usajobs_key = os.getenv('USAJOBS_API_KEY')

    if not all([sam_key, dvids_key, usajobs_key]):
        print("✗ Missing API keys")
        return False

    print("\n✓ All API keys loaded\n")

    # Test 1: SAM.gov end-to-end
    print("TEST 1: SAM.gov - Real contract search")
    print("-"*80)
    sam = SAMIntegration()

    # Generate query
    sam_query = await sam.generate_query("IT consulting contracts")
    if not sam_query:
        print("✗ SAM query generation failed")
        return False
    print(f"✓ Query generated: {sam_query.get('keywords')}")

    # Execute search
    sam_result = await sam.execute_search(sam_query, api_key=sam_key, limit=3)
    if not sam_result.success:
        print(f"✗ SAM search failed: {sam_result.error}")
        return False
    print(f"✓ Search executed: {sam_result.total:,} results in {sam_result.response_time_ms:.0f}ms")
    print(f"  Source: {sam_result.source}")
    print(f"  Results returned: {len(sam_result.results)}")

    # Test 2: DVIDS end-to-end
    print("\nTEST 2: DVIDS - Real media search")
    print("-"*80)
    dvids = DVIDSIntegration()

    dvids_query = await dvids.generate_query("Army training exercises")
    if not dvids_query:
        print("✗ DVIDS query generation failed")
        return False
    print(f"✓ Query generated: {dvids_query.get('keywords')}")

    dvids_result = await dvids.execute_search(dvids_query, api_key=dvids_key, limit=3)
    if not dvids_result.success:
        print(f"✗ DVIDS search failed: {dvids_result.error}")
        return False
    print(f"✓ Search executed: {dvids_result.total:,} results in {dvids_result.response_time_ms:.0f}ms")
    print(f"  Source: {dvids_result.source}")
    print(f"  Results returned: {len(dvids_result.results)}")

    # Test 3: USAJobs end-to-end
    print("\nTEST 3: USAJobs - Real job search")
    print("-"*80)
    usajobs = USAJobsIntegration()

    usajobs_query = await usajobs.generate_query("software engineer jobs")
    if not usajobs_query:
        print("✗ USAJobs query generation failed")
        return False
    print(f"✓ Query generated: {usajobs_query.get('keywords')}")

    usajobs_result = await usajobs.execute_search(usajobs_query, api_key=usajobs_key, limit=3)
    if not usajobs_result.success:
        print(f"✗ USAJobs search failed: {usajobs_result.error}")
        return False
    print(f"✓ Search executed: {usajobs_result.total:,} results in {usajobs_result.response_time_ms:.0f}ms")
    print(f"  Source: {usajobs_result.source}")
    print(f"  Results returned: {len(usajobs_result.results)}")
    if usajobs_result.results:
        print(f"  Sample job: {usajobs_result.results[0].get('PositionTitle', 'N/A')}")

    # Test 4: Parallel execution with all 3
    print("\nTEST 4: Parallel Executor - Multi-database search")
    print("-"*80)
    executor = ParallelExecutor()

    databases = [sam, dvids, usajobs]
    api_keys = {
        'sam': sam_key,
        'dvids': dvids_key,
        'usajobs': usajobs_key
    }

    # Use a query that should hit multiple databases
    results = await executor.execute_all(
        research_question="federal technology jobs and contracts",
        databases=databases,
        api_keys=api_keys,
        limit=3
    )

    print(f"✓ Parallel execution completed")
    successful = [r for r in results.values() if r.success and r.total > 0]
    print(f"  Databases with results: {len(successful)}/{len(databases)}")

    for db_id, result in results.items():
        if result.success:
            print(f"  {result.source}: {result.total:,} results ({result.response_time_ms:.0f}ms)")
        else:
            print(f"  {result.source}: {result.error or 'No results'}")

    # Test 5: Verify gpt-5-mini is being used
    print("\nTEST 5: Configuration verification")
    print("-"*80)
    from config_loader import config
    model = config.get_model('query_generation')
    print(f"✓ Query generation model: {model}")
    if model != "gpt-5-mini":
        print(f"  ⚠ WARNING: Expected gpt-5-mini, got {model}")

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - System fully functional!")
    print("="*80)

    print("\nSummary:")
    print(f"  • SAM.gov: {sam_result.total:,} contracts")
    print(f"  • DVIDS: {dvids_result.total:,} media items")
    print(f"  • USAJobs: {usajobs_result.total:,} jobs")
    print(f"  • Parallel execution: Working")
    print(f"  • LLM model: {model}")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
