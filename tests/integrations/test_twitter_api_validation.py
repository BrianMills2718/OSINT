#!/usr/bin/env python3
"""
Phase 1, Task 1.2: Test API Client with Real Request
Validates that api_client.py works with current twitter-api45 API
"""

from experiments.twitterexplorer_sigint.api_client import execute_api_step
from dotenv import load_dotenv
import os
import json

load_dotenv()

step_plan = {
    "endpoint": "search.php",
    "params": {
        "query": "python",  # Simple, guaranteed results
        "search_type": "Latest"
    },
    "max_pages": 1,
    "reason": "Pre-integration validation"
}

print("=" * 80)
print("TWITTER API CLIENT VALIDATION - Phase 1, Task 1.2")
print("=" * 80)
print(f"Testing endpoint: search.php")
print(f"Query: {step_plan['params']['query']}")
print(f"Search type: {step_plan['params']['search_type']}")
print()

result = execute_api_step(step_plan, [], os.getenv('RAPIDAPI_KEY'))

print("=" * 80)
print("RESULTS")
print("=" * 80)

if "error" in result:
    print(f"❌ FAILED: {result['error']}")
    print(f"\nEndpoint: {result.get('endpoint')}")
    print(f"Status Code: {result.get('status_code', 'N/A')}")
    print("\n⚠️ BLOCKER: API client cannot connect to Twitter API")
    print("Possible causes:")
    print("  1. API key invalid or subscription inactive")
    print("  2. twitter-api45 endpoint changed")
    print("  3. RapidAPI service unavailable")
    print("\nRecommendation: STOP - Investigate API access before proceeding")
    exit(1)
else:
    timeline = result.get("data", {}).get("timeline", [])
    response_time = result.get('response_time_ms', 'N/A')

    print(f"✅ SUCCESS")
    print(f"Results returned: {len(timeline)}")
    print(f"Response time: {response_time}ms")

    if timeline:
        print(f"\nSample tweets (first 3):")
        for i, tweet in enumerate(timeline[:3], 1):
            user_info = tweet.get('user_info', {})
            screen_name = user_info.get('screen_name', 'unknown')
            text = tweet.get('text', '')[:80]
            created = tweet.get('created_at', 'unknown')
            favorites = tweet.get('favorites', 0)
            retweets = tweet.get('retweets', 0)

            print(f"\n{i}. @{screen_name}")
            print(f"   Text: {text}...")
            print(f"   Created: {created}")
            print(f"   Engagement: {favorites} likes, {retweets} RTs")

        # Verify expected fields exist
        print("\n" + "=" * 80)
        print("FIELD VALIDATION")
        print("=" * 80)

        sample = timeline[0]
        required_fields = {
            'text': sample.get('text'),
            'created_at': sample.get('created_at'),
            'tweet_id': sample.get('tweet_id'),
            'user_info': sample.get('user_info'),
            'user_info.screen_name': sample.get('user_info', {}).get('screen_name'),
        }

        all_present = True
        for field, value in required_fields.items():
            status = "✅" if value else "❌"
            print(f"{status} {field}: {'Present' if value else 'MISSING'}")
            if not value:
                all_present = False

        if all_present:
            print("\n✅ ALL REQUIRED FIELDS PRESENT")
        else:
            print("\n⚠️ WARNING: Some fields missing - may need field mapping adjustments")

    print("\n" + "=" * 80)
    print("✅ API CLIENT READY FOR INTEGRATION")
    print("=" * 80)
    print("\nNext step: Proceed to Phase 2 (TwitterIntegration implementation)")
