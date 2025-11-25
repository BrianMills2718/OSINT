#!/usr/bin/env python3
"""
Live test for FBI Vault integration.

Tests FBI Vault integration with real web scraping to verify:
- Relevance checking works
- Query generation works
- FBI documents are retrieved
- Results are properly formatted
- No API key required (web scraping)
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.fbi_vault import FBIVaultIntegration


async def main():
    print("Testing FBI Vault Integration...")
    print("=" * 80)

    integration = FBIVaultIntegration()

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
        ("What FBI files exist on Operation COINTELPRO?", True),
        ("Are there declassified documents about UFO investigations?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What jobs are at NASA?", False),  # Should use USAJobs
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What FBI files exist about Nikola Tesla?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Search Terms: {query_params.get('search_terms')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (Tesla FBI files)")
    print("-" * 80)
    print("NOTE: This uses web scraping - may take a few seconds")

    search_params = {
        "search_terms": "Tesla"
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 FBI Vault Documents:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet', '')[:100]}...")

    print("\n" + "=" * 80)
    print("FBI Vault Integration Test Complete!")
    print("\nNOTE: FBI Vault characteristics:")
    print("- Completely FREE, no API key required")
    print("- FBI declassified documents and FOIA releases")
    print("- Web scraping (may be slower than APIs)")


if __name__ == "__main__":
    asyncio.run(main())
