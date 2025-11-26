#!/usr/bin/env python3
"""
Live test for Twitter integration.

Tests Twitter integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Tweets are retrieved
- Results are properly formatted
- API access works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')
from dotenv import load_dotenv
load_dotenv()
import os

from integrations.social.twitter_integration import TwitterIntegration


async def main():
    print("Testing Twitter Integration...")
    print("=" * 80)

    integration = TwitterIntegration()

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
        ("What are defense analysts tweeting about hypersonics?", True),
        ("What's the Twitter discussion about AI regulation?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What FBI files exist on UFOs?", False),  # Should use FBI Vault
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What are defense experts tweeting about hypersonic weapons?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Accounts: {query_params.get('accounts')}")
        print(f"   Date Range Days: {query_params.get('date_range_days')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (hypersonic weapons tweets)")
    print("-" * 80)
    print("NOTE: Requires twitterexplorer_sigint library")

    search_params = {
        "keywords": ["hypersonic", "weapons"],
        "accounts": [],
        "date_range_days": 30,
        "limit": 5
    }

    result = await integration.execute_search(search_params, api_key=os.getenv('RAPIDAPI_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Tweets:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Author: {doc.get('metadata', {}).get('author')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     Engagement: {doc.get('metadata', {}).get('engagement')}")
            print(f"     URL: {doc.get('url')}")

    print("\n" + "=" * 80)
    print("Twitter Integration Test Complete!")
    print("\nNOTE: Twitter requirements:")
    print("- Requires twitterexplorer_sigint library")
    print("- Real-time tweets and discussions")
    print("- Good for expert commentary and breaking news")


if __name__ == "__main__":
    asyncio.run(main())
