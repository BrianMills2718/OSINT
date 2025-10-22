#!/usr/bin/env python3
"""
Test 3: Test Deep Research Engine's _search_brave method directly.

This tests whether our integration code in research/deep_research.py works.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from research.deep_research import SimpleDeepResearch

async def test_deep_research_brave_method():
    """Test the _search_brave method directly."""
    print("=" * 60)
    print("TEST 3: Deep Research _search_brave Method Test")
    print("=" * 60)

    # Load environment
    load_dotenv()
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    print(f"\n1. Environment Check:")
    print(f"   BRAVE_SEARCH_API_KEY: {'✅ Found' if api_key else '❌ Missing'}")
    print(f"   OPENAI_API_KEY: {'✅ Found' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")

    if not api_key:
        print("\n❌ TEST 3 FAILED: BRAVE_SEARCH_API_KEY not found")
        return False

    # Create Deep Research engine
    print(f"\n2. Creating SimpleDeepResearch engine...")
    try:
        engine = SimpleDeepResearch(
            max_tasks=3,
            max_retries_per_task=1,
            max_time_minutes=5,
            min_results_per_task=1
        )
        print(f"   ✅ Engine created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create engine: {e}")
        return False

    # Test _search_brave method directly
    print(f"\n3. Testing _search_brave method...")
    print(f"   Query: 'cybersecurity threat intelligence'")
    print(f"   Max results: 10")

    try:
        results = await engine._search_brave(
            query="cybersecurity threat intelligence",
            max_results=10
        )

        print(f"\n4. Results:")
        print(f"   Results returned: {len(results)}")

        if not results:
            print(f"   ⚠️ No results returned (may indicate API key issue)")
            return False

        print(f"\n5. Sample Results:")
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            source = result.get("source", "No source")
            print(f"   {i}. {title}")
            print(f"      Source: {source}")
            print(f"      URL: {url}")

        # Check result structure
        print(f"\n6. Result Structure Check:")
        first = results[0]
        required_fields = ["title", "url", "description", "source"]
        all_present = True

        for field in required_fields:
            present = field in first
            print(f"   {field:15}: {'✅' if present else '❌'}")
            if not present:
                all_present = False

        print("\n" + "=" * 60)
        if all_present and len(results) > 0:
            print("✅ TEST 3 PASSED: _search_brave method working correctly")
        else:
            print("❌ TEST 3 FAILED: Results missing required fields")
        print("=" * 60)

        return all_present and len(results) > 0

    except Exception as e:
        print(f"\n   ❌ Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_deep_research_brave_method())
    sys.exit(0 if success else 1)
