#!/usr/bin/env python3
"""
Live test for CIA CREST Selenium integration.

Tests CIA CREST using undetected-chromedriver (Selenium) to verify:
- Can bypass Akamai Bot Manager
- Query generation works
- Declassified CIA documents are retrieved
- Results are properly formatted
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.crest_selenium_integration import CRESTSeleniumIntegration


async def main():
    print("Testing CIA CREST Selenium Integration...")
    print("=" * 80)

    integration = CRESTSeleniumIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Method: Selenium/undetected-chromedriver")
    print(f"Headless: False (visible browser - better bot evasion)")

    # Test 2: Query Generation
    print("\n[TEST 2] Query Generation")
    print("-" * 80)

    test_query = "What CIA documents exist about UFO investigations?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keyword: {query_params.get('keyword')}")
        print(f"   Max Pages: {query_params.get('max_pages')}")
    else:
        print("❌ Query generation returned None (not relevant)")
        return

    # Test 3: Execute Search (CRITICAL TEST - Can we bypass Akamai?)
    print("\n[TEST 3] Execute Search - Testing Bot Detection Bypass")
    print("-" * 80)
    print("NOTE: This will open a visible Chrome browser window")
    print("NOTE: undetected-chromedriver is designed to bypass Akamai Bot Manager")
    print("Executing...")

    search_params = {
        "keyword": "UFO",
        "max_pages": 1
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"\nSuccess: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"❌ Error: {result.error}")
        if "ERR_TOO_MANY_REDIRECTS" in result.error:
            print("\n⚠️  VERDICT: Akamai Bot Manager STILL detecting automation")
            print("    Even undetected-chromedriver cannot bypass CIA.gov's protection")
        elif "No such element" in result.error or "timeout" in result.error.lower():
            print("\n⚠️  VERDICT: Page loaded but structure changed or blocked")
    else:
        print("\n✅ VERDICT: Bot detection BYPASSED successfully!")
        print("   undetected-chromedriver works for CIA.gov")

    if result.results:
        print(f"\nFirst 3 CIA CREST Documents:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet', '')[:100]}...")

    print("\n" + "=" * 80)
    print("CIA CREST Selenium Integration Test Complete!")


if __name__ == "__main__":
    asyncio.run(main())
