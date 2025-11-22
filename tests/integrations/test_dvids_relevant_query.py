#!/usr/bin/env python3
"""Test DVIDS with a query it SHOULD consider relevant (military training)."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.government.dvids_integration import DVIDSIntegration

async def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Test with Relevant Query")
    print("=" * 60)

    integration = DVIDSIntegration()
    api_key = os.getenv('DVIDS_API_KEY')

    # Test with military training (DVIDS is visual media of military activities)
    query = "military training exercises"
    print(f"\nTest: {query}")

    query_params = await integration.generate_query(query)
    print(f"Query params: {query_params}")

    if query_params:
        result = await integration.execute_search(
            query_params=query_params,
            api_key=api_key,
            limit=10
        )
        print(f"\nSuccess: {result.success}")
        print(f"Total: {result.total}")
        print(f"Response time: {result.response_time_ms:.0f}ms")

        if result.total > 0:
            print(f"\n✅ DVIDS WORKING - {result.total} results")
            print(f"\nFirst 3 results:")
            for i, item in enumerate(result.results[:3], 1):
                print(f"\n  Result {i}:")
                print(f"    Title: {item.get('title', 'No title')[:70]}")
                print(f"    Type: {item.get('type', 'Unknown')}")
                print(f"    Branch: {item.get('branch', 'Unknown')}")
        else:
            print(f"❌ DVIDS RETURNING 0 - decomposition may not be working")
    else:
        print("❌ Query generation returned None (not relevant)")

if __name__ == "__main__":
    asyncio.run(test())
