#!/usr/bin/env python3
"""Test DVIDS after fixing comma-separated keywords issue."""
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
    print("DVIDS Test After Prompt Fix")
    print("=" * 60)

    integration = DVIDSIntegration()
    api_key = os.getenv('DVIDS_API_KEY')

    # Test with military training query (should work)
    query = "military training exercises"
    print(f"\nTest 1: {query}")

    query_params = await integration.generate_query(query)
    print(f"Query params: {query_params}")

    if query_params:
        result = await integration.execute_search(
            query_params=query_params,
            api_key=api_key,
            limit=5
        )
        print(f"Success: {result.success}")
        print(f"Total: {result.total}")
        if result.total > 0:
            print(f"✅ WORKING - First result: {result.results[0].get('title', 'No title')[:80]}")
        else:
            print(f"⚠️  0 results")

    # Test with SIGINT query (should mark not relevant since SIGINT isn't visual media)
    await asyncio.sleep(3)  # Rate limit

    query2 = "SIGINT signals intelligence"
    print(f"\n\nTest 2: {query2}")

    query_params2 = await integration.generate_query(query2)
    if not query_params2:
        print(f"✅ Correctly marked as NOT relevant (SIGINT isn't visual military media)")
    else:
        print(f"Query params: {query_params2}")
        result2 = await integration.execute_search(
            query_params=query_params2,
            api_key=api_key,
            limit=5
        )
        print(f"Success: {result2.success}")
        print(f"Total: {result2.total}")

if __name__ == "__main__":
    asyncio.run(test())
