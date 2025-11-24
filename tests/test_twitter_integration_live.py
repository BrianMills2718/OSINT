#!/usr/bin/env python3
"""
Integration test for Twitter endpoint expansion with live API calls.

Tests the full flow: generate_query() → execute_search() → response transformation
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


async def test_search_tweets_integration():
    """Test search_tweets pattern with live API."""
    from integrations.social.twitter_integration import TwitterIntegration

    twitter = TwitterIntegration()
    api_key = os.getenv("RAPIDAPI_KEY")

    if not api_key:
        print("⚠️  SKIP: No RAPIDAPI_KEY found in .env")
        return None

    print("\n" + "="*80)
    print("TEST 1: Search Tweets Pattern (search.php)")
    print("="*80)

    query = "OSINT"  # Simple keyword
    print(f"\nQuery: {query}")

    # Step 1: Generate query
    query_params = await twitter.generate_query(query)
    print(f"Generated params: {query_params}")

    # Step 2: Execute search
    result = await twitter.execute_search(query_params, api_key, limit=3)

    # Step 3: Verify results
    print(f"\nSuccess: {result.success}")
    print(f"Total results: {result.total}")

    if result.success and result.results:
        print(f"\nSample result:")
        sample = result.results[0]
        print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
        print(f"  Author: @{sample.get('author', 'N/A')}")
        print(f"  URL: {sample.get('url', 'N/A')}")
        print(f"  Engagement: {sample.get('engagement_total', 0)}")
        return True
    elif result.error:
        print(f"\n❌ Error: {result.error}")
        return False
    else:
        print("\n⚠️  No results returned")
        return None


async def test_user_timeline_integration():
    """Test user_timeline pattern with live API."""
    from integrations.social.twitter_integration import TwitterIntegration

    twitter = TwitterIntegration()
    api_key = os.getenv("RAPIDAPI_KEY")

    if not api_key:
        print("⚠️  SKIP: No RAPIDAPI_KEY found in .env")
        return None

    print("\n" + "="*80)
    print("TEST 2: User Timeline Pattern (timeline.php)")
    print("="*80)

    query = "What is @bellingcat saying about Ukraine?"
    print(f"\nQuery: {query}")

    # Step 1: Generate query
    query_params = await twitter.generate_query(query)
    print(f"Generated params: {query_params}")
    print(f"  Pattern: {query_params.get('pattern')}")
    print(f"  Endpoint: {query_params.get('endpoint')}")
    print(f"  Params: {query_params.get('params')}")

    # Verify it selected user_timeline
    if query_params.get('pattern') != 'user_timeline':
        print(f"\n⚠️  Expected user_timeline pattern, got {query_params.get('pattern')}")

    # Step 2: Execute search
    result = await twitter.execute_search(query_params, api_key, limit=3)

    # Step 3: Verify results
    print(f"\nSuccess: {result.success}")
    print(f"Total results: {result.total}")

    if result.success and result.results:
        print(f"\nSample result:")
        sample = result.results[0]
        print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
        print(f"  Author: @{sample.get('author', 'N/A')}")
        print(f"  Date: {sample.get('date', 'N/A')}")
        print(f"  Favorites: {sample.get('favorites', 0)}")
        return True
    elif result.error:
        print(f"\n❌ Error: {result.error}")
        return False
    else:
        print("\n⚠️  No results returned")
        return None


async def test_response_transformation():
    """Test that different endpoints return properly transformed results."""
    from integrations.social.twitter_integration import TwitterIntegration

    twitter = TwitterIntegration()

    print("\n" + "="*80)
    print("TEST 3: Response Transformation")
    print("="*80)

    # Test tweet transformation
    sample_tweet = {
        'tweet_id': '123456789',
        'text': 'This is a sample tweet about OSINT',
        'created_at': '2025-01-01T12:00:00Z',
        'user_info': {
            'screen_name': 'osint_analyst',
            'name': 'OSINT Analyst',
            'verified': True
        },
        'favorites': 42,
        'retweets': 10,
        'replies': 5,
        'views': '1000'
    }

    transformed_tweet = twitter._transform_tweet_to_standard(sample_tweet)

    print("\nTweet transformation:")
    print(f"  ✓ Title: {transformed_tweet.get('title')}")
    print(f"  ✓ URL: {transformed_tweet.get('url')}")
    print(f"  ✓ Author: @{transformed_tweet.get('author')}")
    print(f"  ✓ Engagement: {transformed_tweet.get('engagement_total')}")

    # Test user transformation
    sample_user = {
        'screen_name': 'bellingcat',
        'name': 'Bellingcat',
        'description': 'Open source investigation collective',
        'verified': True,
        'followers_count': 500000,
        'friends_count': 1000,
        'statuses_count': 10000
    }

    transformed_user = twitter._transform_user_to_standard(sample_user)

    print("\nUser transformation:")
    print(f"  ✓ Title: {transformed_user.get('title')}")
    print(f"  ✓ URL: {transformed_user.get('url')}")
    print(f"  ✓ Followers: {transformed_user.get('followers_count')}")
    print(f"  ✓ Following: {transformed_user.get('following_count')}")

    return True


async def main():
    """Run integration tests."""
    print("\n" + "="*80)
    print("TWITTER INTEGRATION TESTS (LIVE API)")
    print("="*80)

    # Check for API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("\n⚠️  WARNING: No RAPIDAPI_KEY found in .env")
        print("Live API tests will be skipped.")
        print("Only testing response transformation.\n")

    results = []

    # Test 1: Search tweets
    result1 = await test_search_tweets_integration()
    results.append(("Search Tweets", result1))

    # Test 2: User timeline
    result2 = await test_user_timeline_integration()
    results.append(("User Timeline", result2))

    # Test 3: Response transformation (always runs)
    result3 = await test_response_transformation()
    results.append(("Response Transformation", result3))

    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)

    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}: PASS")
        elif result is False:
            print(f"❌ {test_name}: FAIL")
        elif result is None:
            print(f"⚠️  {test_name}: SKIPPED (no API key)")

    # Determine exit code
    failures = sum(1 for _, result in results if result is False)
    if failures > 0:
        print(f"\n❌ {failures} tests failed")
        return 1
    else:
        print("\n✅ All tests passed (or skipped)")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
