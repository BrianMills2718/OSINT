#!/usr/bin/env python3
"""
Live test for Congress.gov integration.

Tests Congress.gov integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Congressional bills and legislation are retrieved
- Results are properly formatted
- API key authentication works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.congress_integration import CongressIntegration


async def main():
    print("Testing Congress.gov Integration...")
    print("=" * 80)

    integration = CongressIntegration()

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
        ("What AI legislation is Congress considering?", True),
        ("Has any cybersecurity bill passed the Senate?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What is the latest news?", False),  # Should use NewsAPI
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What AI regulation bills is Congress considering?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Query: {query_params.get('query')}")
        print(f"   Congress: {query_params.get('congress')}")
        print(f"   Bill Type: {query_params.get('bill_type')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (AI legislation)")
    print("-" * 80)

    search_params = {
        "query": "artificial intelligence",
        "congress": None,  # Current congress
        "bill_type": None,  # All types
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
        print(f"\nFirst 3 Congressional Bills:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Bill Number: {doc.get('metadata', {}).get('bill_number')}")
            print(f"     Congress: {doc.get('metadata', {}).get('congress')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     URL: {doc.get('url')}")

    print("\n" + "=" * 80)
    print("Congress.gov Integration Test Complete!")
    print("\nNOTE: Congress.gov requirements:")
    print("- Requires API key from CONGRESS_API_KEY env var")
    print("- Congressional bills, resolutions, and legislation")
    print("- Fast API (typically <1 second)")


if __name__ == "__main__":
    asyncio.run(main())
