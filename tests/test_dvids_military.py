#!/usr/bin/env python3
"""Test DVIDS with military-relevant query."""
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
    print("DVIDS Military Query Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    integration = DVIDSIntegration()

    # Test with military-relevant query
    query = "military training exercises"
    print(f"\nQuery: {query}")

    print(f"\n1. Testing generate_query()...")
    query_params = await integration.generate_query(query)

    if not query_params:
        print(f"   ❌ Query generation returned None")
        return False

    print(f"   ✅ Query params: {query_params}")

    print(f"\n2. Testing execute_search()...")
    result = await integration.execute_search(
        query_params=query_params,
        api_key=api_key,
        limit=10
    )

    print(f"\n3. Results:")
    print(f"   Success: {result.success}")
    print(f"   Total: {result.total}")
    print(f"   Error: {result.error}")

    if result.success and result.total > 0:
        print(f"\n✅ TEST PASSED: DVIDS working")
        print(f"   First result: {result.results[0].get('title', 'No title')}")
        return True
    elif result.success and result.total == 0:
        print(f"\n⚠️ Success but 0 results (might be no matches)")
        return True
    else:
        print(f"\n❌ TEST FAILED: {result.error}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
