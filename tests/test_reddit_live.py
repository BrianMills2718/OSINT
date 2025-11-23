#!/usr/bin/env python3
"""
Live test for Reddit integration.

Tests Reddit integration with real API calls via PRAW to verify:
- Relevance checking works
- Query generation works
- Reddit posts and comments are retrieved
- Results are properly formatted
- PRAW authentication works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.social.reddit_integration import RedditIntegration


async def main():
    print("Testing Reddit Integration...")
    print("=" * 80)

    integration = RedditIntegration()

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
        ("What are r/defense discussions about hypersonics?", True),
        ("What's the Reddit community saying about AI safety?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What CIA documents exist on UFOs?", False),  # Should use CREST
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What are defense communities discussing about hypersonic weapons?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Subreddits: {query_params.get('subreddits')}")
        print(f"   Time Filter: {query_params.get('time_filter')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (defense subreddit discussions)")
    print("-" * 80)
    print("NOTE: Requires PRAW credentials in .env")

    search_params = {
        "keywords": ["hypersonic", "weapons"],
        "subreddits": ["defense"],
        "time_filter": "month",
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
        print(f"\nFirst 3 Reddit Posts:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Subreddit: {doc.get('metadata', {}).get('subreddit')}")
            print(f"     Author: {doc.get('metadata', {}).get('author')}")
            print(f"     Score: {doc.get('metadata', {}).get('score')}")
            print(f"     Comments: {doc.get('metadata', {}).get('num_comments')}")
            print(f"     URL: {doc.get('url')}")

    print("\n" + "=" * 80)
    print("Reddit Integration Test Complete!")
    print("\nNOTE: Reddit requirements:")
    print("- Requires PRAW credentials (client_id, client_secret, username, password)")
    print("- Environment variables: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,")
    print("                         REDDIT_USERNAME, REDDIT_PASSWORD")
    print("- Good for community discussions and insider perspectives")


if __name__ == "__main__":
    asyncio.run(main())
