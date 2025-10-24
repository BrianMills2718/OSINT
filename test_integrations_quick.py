#!/usr/bin/env python3
"""Quick test of all integrations to verify they work."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_integration(name, integration_class, api_key_env_var=None):
    """Test a single integration."""
    try:
        db = integration_class()
        query = await db.generate_query("military cybersecurity")

        if query is None:
            print(f"⊘ {name}: Not relevant for this query")
            return True  # Not an error

        # Get API key if needed
        api_key = None
        if api_key_env_var:
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                print(f"❌ {name}: Missing {api_key_env_var}")
                return False

        result = await db.execute_search(query, api_key=api_key, limit=3)

        if result.success:
            print(f"✅ {name}: {result.total} total, {len(result.results)} returned")
            return True
        else:
            print(f"❌ {name}: {result.error}")
            return False

    except Exception as e:
        print(f"❌ {name}: {type(e).__name__}: {str(e)}")
        return False

async def main():
    from integrations.government.sam_integration import SAMIntegration
    from integrations.government.dvids_integration import DVIDSIntegration
    from integrations.government.usajobs_integration import USAJobsIntegration
    from integrations.social.twitter_integration import TwitterIntegration
    from integrations.social.discord_integration import DiscordIntegration
    from integrations.social.reddit_integration import RedditIntegration

    tests = [
        ("SAM.gov", SAMIntegration, "SAM_GOV_API_KEY"),
        ("DVIDS", DVIDSIntegration, "DVIDS_API_KEY"),
        ("USAJobs", USAJobsIntegration, "USAJOBS_API_KEY"),
        ("Twitter", TwitterIntegration, "RAPIDAPI_KEY"),
        ("Discord", DiscordIntegration, None),
        ("Reddit", RedditIntegration, None),
    ]

    print("\n=== Testing All Integrations ===\n")
    results = []
    for name, cls, key in tests:
        passed = await test_integration(name, cls, key)
        results.append((name, passed))

    print("\n=== Summary ===\n")
    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"Passed: {passed}/{total}")

if __name__ == "__main__":
    asyncio.run(main())
