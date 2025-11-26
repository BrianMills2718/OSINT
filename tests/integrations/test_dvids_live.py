#!/usr/bin/env python3
"""
Live test for DVIDS integration.

Tests DVIDS (Defense Visual Information Distribution Service) integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Military media is retrieved
- Results are properly formatted
- Free API access works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')
from dotenv import load_dotenv
load_dotenv()
import os

from integrations.government.dvids_integration import DVIDSIntegration


async def main():
    print("Testing DVIDS Integration...")
    print("=" * 80)

    integration = DVIDSIntegration()

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
        ("What is the military doing in the Pacific?", True),
        ("Show me recent Army training exercises", True),
        ("What contracts does Lockheed Martin have?", False),  # Should use SAM.gov
        ("What is the latest AI news?", False),  # Should use NewsAPI
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What is the U.S. Army doing in Europe?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Branches: {query_params.get('branches')}")
        print(f"   Limit: {query_params.get('limit')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (Army Europe operations)")
    print("-" * 80)

    search_params = {
        "keywords": "Army Europe training",
        "branches": ["army"],
        "limit": 5
    }

    result = await integration.execute_search(search_params, api_key=os.getenv('DVIDS_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Media Items:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     Branch: {doc.get('metadata', {}).get('branch')}")
            print(f"     URL: {doc.get('url')}")

    # Test 5: Specific Branch Search
    print("\n[TEST 5] Specific Branch Search (Marine Corps)")
    print("-" * 80)

    marine_params = {
        "keywords": "training exercise",
        "branches": ["marines"],
        "limit": 3
    }

    result = await integration.execute_search(marine_params, api_key=os.getenv('DVIDS_API_KEY'), limit=3)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nMarine Corps Media:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')} ({doc.get('date')})")

    print("\n" + "=" * 80)
    print("DVIDS Integration Test Complete!")
    print("\nNOTE: DVIDS features:")
    print("- Completely FREE, no API key required")
    print("- Defense Department official media")
    print("- Photos, videos, news from all military branches")


if __name__ == "__main__":
    asyncio.run(main())
