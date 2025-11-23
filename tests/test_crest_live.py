#!/usr/bin/env python3
"""
Live test for CIA CREST integration.

Tests CIA CREST (FOIA Reading Room) integration with real API/web calls to verify:
- Relevance checking works
- Query generation works
- Declassified CIA documents are retrieved
- Results are properly formatted
- No API key required
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.crest_integration import CRESTIntegration


async def main():
    print("Testing CIA CREST Integration...")
    print("=" * 80)

    integration = CRESTIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Category: {metadata.category}")
    print(f"Requires API Key: {metadata.requires_api_key}")
    print(f"Description: {metadata.description}")

    # Test 2: Relevance Check
    print("\n[TEST 2] Relevance Check")
    print("-" * 80)

    test_questions = [
        ("What CIA documents exist about Cold War operations?", True),
        ("Are there declassified files on Soviet intelligence?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What AI legislation is pending?", False),  # Should use Congress.gov
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What CIA documents exist about UFO investigations?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Date Range: {query_params.get('date_range')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (UFO documents)")
    print("-" * 80)
    print("NOTE: CREST uses web scraping - may take a few seconds")

    search_params = {
        "keywords": "UFO unidentified flying object",
        "date_range": None,
        "limit": 5
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 CIA CREST Documents:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet', '')[:100]}...")

    print("\n" + "=" * 80)
    print("CIA CREST Integration Test Complete!")
    print("\nNOTE: CIA CREST characteristics:")
    print("- Completely FREE, no API key required")
    print("- Declassified CIA documents via FOIA")
    print("- 13 million+ pages of declassified documents")
    print("- May use web scraping (slower than APIs)")


if __name__ == "__main__":
    asyncio.run(main())
