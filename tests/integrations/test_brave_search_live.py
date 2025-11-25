#!/usr/bin/env python3
"""
Live test for Brave Search integration.

Tests Brave Search integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Web search results are retrieved
- Results are properly formatted
- API key authentication works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.social.brave_search_integration import BraveSearchIntegration


async def main():
    print("Testing Brave Search Integration...")
    print("=" * 80)

    integration = BraveSearchIntegration()

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
        ("What information is publicly available about hypersonic weapons?", True),
        ("What is the latest on AI regulation developments?", True),
        ("What are Apple's recent SEC filings?", False),  # Should use SEC EDGAR
        ("What FBI files exist on COINTELPRO?", False),  # Should use FBI Vault
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What are the latest developments in quantum computing?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Query: {query_params.get('query')}")
        print(f"   Country: {query_params.get('country')}")
        print(f"   Freshness: {query_params.get('freshness')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (quantum computing)")
    print("-" * 80)

    search_params = {
        "query": "quantum computing breakthroughs 2024",
        "country": "US",
        "freshness": None,
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
        print(f"\nFirst 3 Search Results:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet', '')[:150]}...")

    # Test 5: Freshness Filter
    print("\n[TEST 5] Recent Results (past week)")
    print("-" * 80)

    recent_params = {
        "query": "artificial intelligence news",
        "country": "US",
        "freshness": "pw",  # Past week
        "limit": 3
    }

    result = await integration.execute_search(recent_params, api_key=None, limit=3)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nRecent AI News:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')}")
            print(f"     {doc.get('url')[:60]}...")

    print("\n" + "=" * 80)
    print("Brave Search Integration Test Complete!")
    print("\nNOTE: Brave Search features:")
    print("- Requires API key from BRAVE_SEARCH_API_KEY env var")
    print("- Privacy-focused web search")
    print("- Free tier: 2000 queries/month")
    print("- Fast response times (<1 second)")


if __name__ == "__main__":
    asyncio.run(main())
