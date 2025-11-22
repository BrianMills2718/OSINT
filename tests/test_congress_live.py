#!/usr/bin/env python3
"""
Test Congress.gov integration with live API.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Test imports
from integrations.government.congress_integration import CongressIntegration


async def main():
    print("🧪 Congress.gov Live API Test")
    print("=" * 80)

    # Get API key
    api_key = os.getenv('CONGRESS_API_KEY')

    if not api_key:
        print("✗ No CONGRESS_API_KEY found in .env")
        print("  Get one at: https://api.congress.gov/sign-up/")
        return

    print(f"✓ API key loaded: {api_key[:10]}...")
    print()

    # Test 1: Search for AI-related bills
    print("Test 1: AI Regulation Bills (118th Congress)")
    print("-" * 80)

    congress = CongressIntegration()
    query = await congress.generate_query("artificial intelligence regulation bills")

    if query:
        print(f"✓ Query generated:")
        print(f"  Endpoint: {query.get('endpoint')}")
        print(f"  Keywords: {query.get('keywords')}")
        print(f"  Congress: {query.get('congress')}")

        result = await congress.execute_search(query, api_key=api_key, limit=5)

        if result.success:
            print(f"✓ Search successful: {result.total} results found")
            print(f"  Response time: {result.response_time_ms:.0f}ms")

            if result.results:
                print(f"\n  First result:")
                first = result.results[0]
                print(f"    Title: {first.get('title', 'N/A')[:80]}...")
                print(f"    URL: {first.get('url', 'N/A')[:60]}...")
                print(f"    Snippet: {first.get('snippet', 'N/A')[:100]}...")

                # Test field normalization
                print(f"\n  Field Normalization Test:")
                has_title = 'title' in first
                has_snippet = 'snippet' in first
                has_url = 'url' in first
                has_metadata = 'metadata' in first

                print(f"    ✓ Has 'title' field: {has_title}")
                print(f"    ✓ Has 'snippet' field: {has_snippet}")
                print(f"    ✓ Has 'url' field: {has_url}")
                print(f"    ✓ Has 'metadata' field: {has_metadata}")

                if has_title and has_snippet and has_url:
                    print(f"    ✅ All required fields present")
                else:
                    print(f"    ❌ MISSING FIELDS - check QueryResult format!")
        else:
            print(f"✗ Search failed: {result.error}")
    else:
        print("✗ Query generation failed (not relevant)")

    print()

    # Test 2: Search for defense appropriations members
    print("Test 2: Defense Appropriations Committee Members")
    print("-" * 80)

    query2 = await congress.generate_query("members of defense appropriations committee")

    if query2:
        print(f"✓ Query generated:")
        print(f"  Endpoint: {query2.get('endpoint')}")
        print(f"  Keywords: {query2.get('keywords')}")

        result2 = await congress.execute_search(query2, api_key=api_key, limit=3)

        if result2.success:
            print(f"✓ Search successful: {result2.total} results found")
            print(f"  Response time: {result2.response_time_ms:.0f}ms")

            if result2.results:
                print(f"\n  Sample results:")
                for i, member in enumerate(result2.results[:3], 1):
                    print(f"    {i}. {member.get('title', 'N/A')}")
        else:
            print(f"✗ Search failed: {result2.error}")
    else:
        print("✗ Query generation failed")

    print()

    # Test 3: Error handling (invalid API key)
    print("Test 3: Error Handling (Invalid API Key)")
    print("-" * 80)

    query3 = await congress.generate_query("infrastructure bills")
    if query3:
        result3 = await congress.execute_search(query3, api_key="invalid_key", limit=1)

        if not result3.success:
            print(f"✓ Error handled correctly: {result3.error[:80]}...")
        else:
            print(f"✗ Expected error but got success (API key validation may be broken)")

    print()
    print("=" * 80)
    print("✅ Congress.gov API test complete!")


if __name__ == "__main__":
    asyncio.run(main())
