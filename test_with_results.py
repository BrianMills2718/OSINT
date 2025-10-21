#!/usr/bin/env python3
"""
Test all 7 integrations with queries designed to return results.
"""

import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

# Import integrations
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.twitter_integration import TwitterIntegration

load_dotenv()

async def test_sam():
    """Test SAM.gov with broad cybersecurity query."""
    print("\n" + "="*80)
    print("TEST 1: SAM.gov - Federal Contracts")
    print("="*80)

    sam = SAMIntegration()
    query = {
        'keywords': 'cybersecurity',
        'procurement_types': None,
        'set_aside': None,
        'naics_codes': None,
        'organization': None,
        'date_range_days': 30  # Last 30 days
    }

    result = await sam.execute_search(query, api_key=os.getenv('SAM_GOV_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")

async def test_dvids():
    """Test DVIDS with military news query."""
    print("\n" + "="*80)
    print("TEST 2: DVIDS - Military Media")
    print("="*80)

    dvids = DVIDSIntegration()
    query = {
        'keywords': 'training',
        'media_types': ['news', 'image'],
        'branches': None,
        'country': None,
        'from_date': None,
        'to_date': None
    }

    result = await dvids.execute_search(query, api_key=os.getenv('DVIDS_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")

async def test_usajobs():
    """Test USAJobs with broad IT query."""
    print("\n" + "="*80)
    print("TEST 3: USAJobs - Federal Jobs")
    print("="*80)

    usajobs = USAJobsIntegration()
    query = {
        'keywords': 'information technology',
        'location': None,
        'organization': None,
        'pay_grade_low': None,
        'pay_grade_high': None
    }

    result = await usajobs.execute_search(query, api_key=os.getenv('USAJOBS_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")

async def test_clearancejobs():
    """Test ClearanceJobs with security clearance query."""
    print("\n" + "="*80)
    print("TEST 4: ClearanceJobs - Security Clearance Jobs")
    print("="*80)

    clearance = ClearanceJobsIntegration()
    query = {
        'keywords': 'cybersecurity'
    }

    result = await clearance.execute_search(query, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")
        print(f"Clearance: {result.results[0].get('clearance', 'N/A')}")

async def test_fbi_vault():
    """Test FBI Vault with FBI query."""
    print("\n" + "="*80)
    print("TEST 5: FBI Vault - FOIA Documents")
    print("="*80)

    fbi = FBIVaultIntegration()
    query = {
        'query': 'FBI'
    }

    result = await fbi.execute_search(query, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")

async def test_discord():
    """Test Discord with common terms."""
    print("\n" + "="*80)
    print("TEST 6: Discord - OSINT Community Messages")
    print("="*80)

    discord = DiscordIntegration()
    query = {
        'keywords': ['ukraine', 'russia']
    }

    result = await discord.execute_search(query, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst result: {result.results[0].get('title', 'N/A')[:100]}")

async def test_twitter():
    """Test Twitter with simple trending topic."""
    print("\n" + "="*80)
    print("TEST 7: Twitter - Social Media Posts")
    print("="*80)

    twitter = TwitterIntegration()
    query = {
        'query': 'breaking news',
        'search_type': 'Latest',
        'max_pages': 2,
        'reasoning': 'Test query'
    }

    result = await twitter.execute_search(query, api_key=os.getenv('RAPIDAPI_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Returned: {len(result.results)}")
    print(f"Time: {result.response_time_ms:.0f}ms")
    if result.error:
        print(f"Error: {result.error}")
    if result.results:
        print(f"\nFirst tweet: {result.results[0].get('description', 'N/A')[:100]}")
        print(f"Author: @{result.results[0].get('author', 'N/A')}")

async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TESTING ALL 7 INTEGRATIONS WITH QUERIES THAT SHOULD RETURN RESULTS")
    print("="*80)

    start_time = datetime.now()

    # Run all tests
    await test_sam()
    await test_dvids()
    await test_usajobs()
    await test_clearancejobs()
    await test_fbi_vault()
    await test_discord()
    await test_twitter()

    total_time = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*80)
    print(f"ALL TESTS COMPLETE - Total time: {total_time:.1f}s")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
