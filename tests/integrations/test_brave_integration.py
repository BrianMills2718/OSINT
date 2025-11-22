#!/usr/bin/env python3
"""Test Brave Search integration as called by Streamlit."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.social.brave_search_integration import BraveSearchIntegration

async def test():
    load_dotenv()

    print("=" * 60)
    print("Brave Search Integration Test")
    print("=" * 60)

    # Check environment
    api_key = os.getenv('BRAVE_SEARCH_API_KEY')
    print(f"\n1. Environment check:")
    print(f"   BRAVE_SEARCH_API_KEY: {'✅ Found' if api_key else '❌ Missing'}")

    if not api_key:
        print("\n❌ FAILED: API key not in environment")
        return False

    # Create integration
    integration = BraveSearchIntegration()

    # Generate query
    print(f"\n2. Generating query...")
    query_params = await integration.generate_query("cybersecurity threat intelligence")

    if not query_params:
        print(f"   ❌ Query generation returned None (not relevant)")
        return False

    print(f"   ✅ Query generated: {query_params['query']}")

    # Execute search WITH api_key parameter
    print(f"\n3. Executing search WITH api_key...")
    result = await integration.execute_search(
        query_params=query_params,
        api_key=api_key,  # Pass explicitly
        limit=5
    )

    print(f"   Success: {result.success}")
    print(f"   Results: {result.total}")
    print(f"   Error: {result.error}")

    if result.success and result.total > 0:
        print(f"\n✅ TEST PASSED: Integration works when API key passed explicitly")
        return True
    else:
        print(f"\n❌ TEST FAILED: {result.error}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
