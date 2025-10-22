#!/usr/bin/env python3
"""
Test 2: Test Brave Search API directly (minimal code, no integrations).

This tests whether the Brave Search API itself works with our key.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import aiohttp

async def test_brave_search_direct():
    """Test Brave Search API with minimal code."""
    print("=" * 60)
    print("TEST 2: Brave Search API Direct Test")
    print("=" * 60)

    # Load environment
    load_dotenv()
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    print(f"\n1. API Key Check:")
    if not api_key:
        print(f"   ❌ BRAVE_SEARCH_API_KEY not found in environment")
        return False

    print(f"   ✅ API Key found: {api_key[:10]}...")

    # Test API call
    print(f"\n2. Making test API call to Brave Search...")
    print(f"   Query: 'cybersecurity contracts'")
    print(f"   Max results: 5")

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": "cybersecurity contracts",
        "count": 5
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                print(f"\n3. Response:")
                print(f"   Status code: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    print(f"   ❌ Error response: {error_text}")
                    return False

                data = await response.json()

                # Check results
                if "web" in data and "results" in data["web"]:
                    results = data["web"]["results"]
                    print(f"   ✅ Found {len(results)} results")

                    print(f"\n4. Sample Results:")
                    for i, result in enumerate(results[:3], 1):
                        title = result.get("title", "No title")
                        url = result.get("url", "No URL")
                        print(f"   {i}. {title}")
                        print(f"      {url}")

                    print("\n" + "=" * 60)
                    print("✅ TEST 2 PASSED: Brave Search API working correctly")
                    print("=" * 60)
                    return True
                else:
                    print(f"   ❌ No results in response")
                    print(f"   Response data: {data}")
                    return False

    except Exception as e:
        print(f"\n   ❌ Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_brave_search_direct())
    sys.exit(0 if success else 1)
