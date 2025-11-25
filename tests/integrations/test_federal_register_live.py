#!/usr/bin/env python3
"""
Live test for Federal Register integration.

Tests Federal Register integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Federal regulations and notices are retrieved
- Results are properly formatted
- Free API access works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.federal_register import FederalRegisterIntegration


async def main():
    print("Testing Federal Register Integration...")
    print("=" * 80)

    integration = FederalRegisterIntegration()

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
        ("What new regulations has the EPA proposed?", True),
        ("Are there any AI-related federal rules?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What FBI files exist on COINTELPRO?", False),  # Should use FBI Vault
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What new AI regulations has the federal government proposed?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Term: {query_params.get('term')}")
        print(f"   Agencies: {query_params.get('agencies')}")
        print(f"   Document Types: {query_params.get('document_types')}")
        print(f"   Date Range: {query_params.get('date_range_days')} days")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (AI regulations)")
    print("-" * 80)

    search_params = {
        "term": "artificial intelligence",
        "agencies": [],
        "document_types": ["RULE", "PRORULE"],
        "date_range_days": 180
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Federal Register Documents:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Agency: {doc.get('metadata', {}).get('agency')}")
            print(f"     Type: {doc.get('metadata', {}).get('type')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     URL: {doc.get('url')}")

    print("\n" + "=" * 80)
    print("Federal Register Integration Test Complete!")
    print("\nNOTE: Federal Register characteristics:")
    print("- Completely FREE, no API key required")
    print("- Official U.S. federal regulations and notices")
    print("- Fast API (typically <1 second)")


if __name__ == "__main__":
    asyncio.run(main())
