#!/usr/bin/env python3
"""
Live test for NewsAPI integration.

Tests NewsAPI integration with real API calls to verify:
- Relevance checking works
- Query generation works
- News articles are retrieved
- Results are properly formatted
- API key authentication works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.news.newsapi_integration import NewsAPIIntegration


async def main():
    print("Testing NewsAPI Integration...")
    print("=" * 80)

    integration = NewsAPIIntegration()

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
        ("What is the media saying about AI regulation?", True),
        ("What controversies has Boeing faced recently?", True),
        ("What are the details of Apple's latest SEC 10-K filing?", False),  # Should use SEC EDGAR
        ("What government contracts does Lockheed Martin have?", False),  # Should use SAM.gov
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What is the latest news about SpaceX Starship launches?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Query: {query_params.get('query')}")
        print(f"   From: {query_params.get('from_date')}")
        print(f"   To: {query_params.get('to_date')}")
        print(f"   Language: {query_params.get('language')}")
        print(f"   Sort By: {query_params.get('sort_by')}")
        print(f"   Limit: {query_params.get('limit')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (SpaceX Starship news)")
    print("-" * 80)

    search_params = {
        "query": "SpaceX Starship launch",
        "from_date": None,
        "to_date": None,
        "language": "en",
        "sort_by": "relevancy",
        "limit": 10
    }

    result = await integration.execute_search(search_params, api_key=None, limit=10)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 5 Articles:")
        for i, doc in enumerate(result.results[:5], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Source: {doc.get('metadata', {}).get('source')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet')[:150]}...")

    # Test 5: Date Range Search
    print("\n[TEST 5] Date Range Search (AI regulation in October 2024)")
    print("-" * 80)

    date_params = {
        "query": "artificial intelligence regulation",
        "from_date": "2024-10-01",
        "to_date": "2024-10-31",
        "language": "en",
        "sort_by": "publishedAt",
        "limit": 5
    }

    result = await integration.execute_search(date_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nArticles from October 2024:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')} ({doc.get('date')})")
            print(f"     {doc.get('metadata', {}).get('source')}")

    print("\n" + "=" * 80)
    print("NewsAPI Integration Test Complete!")
    print("\nNOTE: Free tier limits:")
    print("- 100 requests/day")
    print("- Articles up to 1 month old")
    print("- 24-hour delay before articles searchable")


if __name__ == "__main__":
    asyncio.run(main())
