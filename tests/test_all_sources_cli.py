#!/usr/bin/env python3
"""
Simple CLI test of all sources WITHOUT Streamlit.
Proves which sources work and which don't with actual evidence.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.social.twitter_integration import TwitterIntegration
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.brave_search_integration import BraveSearchIntegration

async def test_source(name, integration, api_key=None, query="SIGINT signals intelligence"):
    """Test a single source and return results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    try:
        # Generate query
        print(f"1. Generating query...")
        query_params = await integration.generate_query(query)

        if not query_params:
            print(f"   ℹ️  LLM said: Not relevant")
            return {"source": name, "relevant": False, "success": None, "total": 0}

        print(f"   ✅ Query params generated")
        print(f"   Params: {query_params}")

        # Execute search
        print(f"\n2. Executing search...")
        result = await integration.execute_search(
            query_params=query_params,
            api_key=api_key,
            limit=5
        )

        print(f"   Success: {result.success}")
        print(f"   Total: {result.total}")
        print(f"   Error: {result.error}")

        if result.success and result.total > 0:
            print(f"   ✅ WORKING - Got {result.total} results")
            print(f"   First result: {result.results[0].get('title', 'No title')[:80]}...")
        elif result.success and result.total == 0:
            print(f"   ⚠️  Success but 0 results (might be no matches)")
        else:
            print(f"   ❌ FAILED: {result.error}")

        return {
            "source": name,
            "relevant": True,
            "success": result.success,
            "total": result.total,
            "error": result.error
        }

    except Exception as e:
        print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
        return {
            "source": name,
            "relevant": True,
            "success": False,
            "total": 0,
            "error": str(e)
        }

async def main():
    load_dotenv()

    print("\n" + "="*60)
    print("CLI TEST - ALL SOURCES")
    print("Query: 'SIGINT signals intelligence'")
    print("="*60)

    results = []

    # Test SAM.gov
    results.append(await test_source(
        "SAM.gov",
        SAMIntegration(),
        api_key=os.getenv('SAM_GOV_API_KEY')
    ))

    await asyncio.sleep(2)  # Rate limit delay

    # Test DVIDS
    results.append(await test_source(
        "DVIDS",
        DVIDSIntegration(),
        api_key=os.getenv('DVIDS_API_KEY')
    ))

    await asyncio.sleep(2)  # Rate limit delay

    # Test USAJobs
    results.append(await test_source(
        "USAJobs",
        USAJobsIntegration(),
        api_key=os.getenv('USAJOBS_API_KEY')
    ))

    await asyncio.sleep(2)  # Rate limit delay

    # Test ClearanceJobs
    results.append(await test_source(
        "ClearanceJobs",
        ClearanceJobsIntegration()
    ))

    await asyncio.sleep(2)  # Rate limit delay

    # Test Twitter
    results.append(await test_source(
        "Twitter",
        TwitterIntegration(),
        api_key=os.getenv('RAPIDAPI_KEY')
    ))

    await asyncio.sleep(2)  # Rate limit delay

    # Test Brave Search
    results.append(await test_source(
        "Brave Search",
        BraveSearchIntegration(),
        api_key=os.getenv('BRAVE_SEARCH_API_KEY')
    ))

    # Test Discord (no API key needed)
    results.append(await test_source(
        "Discord",
        DiscordIntegration()
    ))

    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    for r in results:
        if not r['relevant']:
            print(f"ℹ️  {r['source']}: Not relevant")
        elif r['success'] and r['total'] > 0:
            print(f"✅ {r['source']}: {r['total']} results")
        elif r['success'] and r['total'] == 0:
            print(f"⚠️  {r['source']}: 0 results (no matches)")
        else:
            print(f"❌ {r['source']}: FAILED - {r['error']}")

    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
