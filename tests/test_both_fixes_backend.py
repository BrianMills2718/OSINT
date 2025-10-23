#!/usr/bin/env python3
"""
Backend test for both DVIDS and Discord fixes.
Tests integrations directly (no Streamlit) to verify fixes work.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.social.discord_integration import DiscordIntegration

async def test():
    load_dotenv()

    print("=" * 70)
    print("BACKEND TEST: DVIDS + Discord Fixes")
    print("=" * 70)

    query = "SIGINT signals intelligence"

    # Test 1: DVIDS
    print(f"\n{'='*70}")
    print("TEST 1: DVIDS (Query Decomposition Fix)")
    print(f"{'='*70}")
    print(f"Query: {query}")

    dvids = DVIDSIntegration()
    api_key = os.getenv('DVIDS_API_KEY')

    dvids_params = await dvids.generate_query(query)
    print(f"Generated params: {dvids_params}")

    if dvids_params:
        dvids_result = await dvids.execute_search(
            query_params=dvids_params,
            api_key=api_key,
            limit=10
        )
        print(f"\nSuccess: {dvids_result.success}")
        print(f"Total: {dvids_result.total}")
        print(f"Response time: {dvids_result.response_time_ms:.0f}ms")

        if dvids_result.total > 0:
            print(f"✅ DVIDS FIX WORKING - {dvids_result.total} results")
            first = dvids_result.results[0]
            print(f"   First result: {first.get('title', 'No title')[:60]}")
        else:
            print(f"❌ DVIDS STILL BROKEN - 0 results")
    else:
        print("ℹ️  DVIDS not relevant (may be expected)")

    # Test 2: Discord
    print(f"\n{'='*70}")
    print("TEST 2: Discord (ANY-Match Fix)")
    print(f"{'='*70}")
    print(f"Query: {query}")

    discord = DiscordIntegration()

    discord_params = await discord.generate_query(query)
    print(f"Generated params: {discord_params}")

    if discord_params:
        discord_result = await discord.execute_search(
            query_params=discord_params,
            limit=10
        )
        print(f"\nSuccess: {discord_result.success}")
        print(f"Total: {discord_result.total}")
        print(f"Response time: {discord_result.response_time_ms:.0f}ms")

        if discord_result.total > 0:
            print(f"✅ DISCORD FIX WORKING - {discord_result.total} results")
            first = discord_result.results[0]
            print(f"   First result: {first.get('server')} / {first.get('channel')}")
            print(f"   Content: {first.get('content')[:60]}...")
        else:
            print(f"❌ DISCORD STILL BROKEN - 0 results")
    else:
        print("❌ DISCORD query generation failed")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    dvids_status = "✅ PASS" if (dvids_params and dvids_result.total > 0) or not dvids_params else "❌ FAIL"
    discord_status = "✅ PASS" if discord_params and discord_result.total > 0 else "❌ FAIL"

    print(f"DVIDS:   {dvids_status} ({dvids_result.total if dvids_params else 'not relevant'} results)")
    print(f"Discord: {discord_status} ({discord_result.total if discord_params else 'no params'} results)")

    if dvids_status == "✅ PASS" and discord_status == "✅ PASS":
        print("\n🎯 BACKEND FIXES WORKING - Ready to test with Streamlit local")
    else:
        print("\n⚠️  Some fixes not working - debug before Streamlit")

if __name__ == "__main__":
    asyncio.run(test())
