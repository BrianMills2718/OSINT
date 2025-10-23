#!/usr/bin/env python3
"""End-to-end backend test without Streamlit - tests all 3 fixed integrations."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration

async def test():
    load_dotenv()

    print("=" * 60)
    print("Backend E2E Test - All 3 Fixed Integrations")
    print("=" * 60)

    query = "SIGINT signals intelligence"
    print(f"\nQuery: {query}\n")

    # Test 1: SAM.gov
    print("1. SAM.gov:")
    sam = SAMIntegration()
    sam_params = await sam.generate_query(query)
    if sam_params:
        sam_result = await sam.execute_search(
            sam_params,
            api_key=os.getenv('SAM_GOV_API_KEY'),
            limit=5
        )
        print(f"   Success: {sam_result.success}")
        print(f"   Total: {sam_result.total}")
        print(f"   Error: {sam_result.error}")
    else:
        print(f"   Not relevant (returned None)")

    # Test 2: DVIDS
    print("\n2. DVIDS:")
    dvids = DVIDSIntegration()
    dvids_params = await dvids.generate_query(query)
    if dvids_params:
        dvids_result = await dvids.execute_search(
            dvids_params,
            api_key=os.getenv('DVIDS_API_KEY'),
            limit=5
        )
        print(f"   Success: {dvids_result.success}")
        print(f"   Total: {dvids_result.total}")
        print(f"   Error: {dvids_result.error}")
    else:
        print(f"   Not relevant (returned None)")

    # Test 3: ClearanceJobs
    print("\n3. ClearanceJobs:")
    cj = ClearanceJobsIntegration()
    cj_params = await cj.generate_query(query)
    if cj_params:
        cj_result = await cj.execute_search(
            cj_params,
            limit=5
        )
        print(f"   Success: {cj_result.success}")
        print(f"   Total: {cj_result.total}")
        print(f"   Error: {cj_result.error}")
        if cj_result.total > 0:
            print(f"   First result: {cj_result.results[0].get('title', 'No title')[:60]}...")
    else:
        print(f"   Not relevant (returned None)")

    print("\n" + "=" * 60)
    print("✅ E2E TEST COMPLETE - All 3 integrations executed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test())
