#!/usr/bin/env python3
"""
Live test for Wayback Machine integration.

Tests Wayback Machine integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Historical snapshots are retrieved
- Results are properly formatted
- No API key required (completely free)
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.archive.wayback_integration import WaybackMachineIntegration


async def main():
    print("Testing Wayback Machine Integration...")
    print("=" * 80)

    integration = WaybackMachineIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Category: {metadata.category}")
    print(f"Requires API Key: {metadata.requires_api_key}")
    print(f"Rate Limit (Daily): {metadata.rate_limit_daily}")
    print(f"Description: {metadata.description}")

    # Test 2: Relevance Check
    print("\n[TEST 2] Relevance Check")
    print("-" * 80)

    test_questions = [
        ("What did Boeing's website say about 737 MAX safety in 2018?", True),
        ("Show me deleted content from Cambridge Analytica's website", True),
        ("What government contracts does Lockheed Martin have?", False),  # Should use SAM.gov
        ("What is the latest news about SpaceX?", False),  # Should use NewsAPI
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What did SpaceX's Starship page look like in 2020?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   URLs: {query_params.get('urls')}")
        print(f"   Timestamp: {query_params.get('timestamp')}")
        print(f"   Description: {query_params.get('description')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search (Recent Snapshot)
    print("\n[TEST 4] Execute Search (Check if URLs are archived)")
    print("-" * 80)

    search_params = {
        "urls": [
            "https://www.archive.org",
            "https://www.wikipedia.org"
        ],
        "timestamp": None,  # Most recent snapshot
        "description": "Testing if Archive.org and Wikipedia are archived"
    }

    result = await integration.execute_search(search_params, api_key=None, limit=10)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nArchived Snapshots Found:")
        for i, doc in enumerate(result.results, 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Snapshot Date: {doc.get('metadata', {}).get('snapshot_date')}")
            print(f"     Archive URL: {doc.get('url')}")
            print(f"     HTTP Status: {doc.get('metadata', {}).get('http_status')}")

    # Test 5: Historical Snapshot Search
    print("\n[TEST 5] Historical Snapshot (SpaceX website from 2020)")
    print("-" * 80)

    historical_params = {
        "urls": ["https://www.spacex.com"],
        "timestamp": "20200101",  # January 1, 2020
        "description": "Checking SpaceX website snapshot from early 2020"
    }

    result = await integration.execute_search(historical_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nHistorical Snapshots from 2020:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')}")
            print(f"     Snapshot: {doc.get('metadata', {}).get('snapshot_date')}")
            print(f"     Archive: {doc.get('url')[:80]}...")

    # Test 6: Non-existent URL (should return gracefully)
    print("\n[TEST 6] Non-existent URL (error handling)")
    print("-" * 80)

    missing_params = {
        "urls": ["https://this-domain-definitely-does-not-exist-12345.com"],
        "timestamp": None,
        "description": "Testing error handling for non-archived URLs"
    }

    result = await integration.execute_search(missing_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")
    if result.total == 0:
        print("✅ Gracefully handled non-archived URL (0 results)")
        print(f"   Metadata note: {result.metadata.get('note', 'N/A')}")

    print("\n" + "=" * 80)
    print("Wayback Machine Integration Test Complete!")
    print("\nNOTE: Wayback Machine features:")
    print("- Completely FREE, no API key required")
    print("- 736 billion pages archived since 1996")
    print("- Historical snapshots for accountability research")


if __name__ == "__main__":
    asyncio.run(main())
