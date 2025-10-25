#!/usr/bin/env python3
"""
Test DVIDS Origin Header Fix

Tests that DVIDS integration properly sends Origin/Referer headers
when configured, to avoid HTTP 403 errors from origin-restricted API keys.

AGENT2 - DVIDS 403 Investigation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.government.dvids_integration import DVIDSIntegration
from config_loader import config

async def test_dvids_with_different_origins():
    """Test DVIDS with various origin configurations."""

    print("=" * 80)
    print("TESTING: DVIDS Origin Header Fix")
    print("=" * 80)

    # Test query that previously failed with 403
    test_query = "military special operations JSOC"

    integration = DVIDSIntegration()
    api_key = os.getenv("DVIDS_API_KEY")

    if not api_key:
        print("\n❌ DVIDS_API_KEY not found in .env")
        print("Cannot test - API key required")
        return False

    # Test 1: No origin (current behavior - may fail with 403)
    print("\n" + "=" * 80)
    print("TEST 1: No Origin Header (Baseline)")
    print("=" * 80)

    # Temporarily clear origin config
    original_origin = config.get_database_config("dvids").get("origin")
    config.get_database_config("dvids")["origin"] = None

    query_params = await integration.generate_query(test_query)
    result1 = await integration.execute_search(query_params, api_key, limit=5)

    print(f"\nResult: {'SUCCESS' if result1.success else 'FAILED'}")
    if result1.success:
        print(f"  Total: {result1.total} results")
        print(f"  Response time: {result1.response_time_ms:.0f}ms")
    else:
        print(f"  Error: {result1.error}")
        if "403" in str(result1.error):
            print("  ⚠️ HTTP 403 - Origin restriction confirmed")

    # Test 2: Try with localhost origin
    print("\n" + "=" * 80)
    print("TEST 2: Origin = http://localhost")
    print("=" * 80)

    config.get_database_config("dvids")["origin"] = "http://localhost"

    result2 = await integration.execute_search(query_params, api_key, limit=5)

    print(f"\nResult: {'SUCCESS' if result2.success else 'FAILED'}")
    if result2.success:
        print(f"  Total: {result2.total} results")
        print(f"  Response time: {result2.response_time_ms:.0f}ms")
    else:
        print(f"  Error: {result2.error}")
        if "403" in str(result2.error):
            print("  ⚠️ HTTP 403 - localhost not registered origin")

    # Test 3: Try with different origins (user should update based on their key)
    test_origins = [
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1",
    ]

    print("\n" + "=" * 80)
    print("TEST 3: Testing Common Origins")
    print("=" * 80)

    success_origins = []

    for origin in test_origins:
        config.get_database_config("dvids")["origin"] = origin
        result = await integration.execute_search(query_params, api_key, limit=5)

        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        print(f"\n  {origin}: {status}")

        if result.success:
            success_origins.append(origin)
            print(f"    Total: {result.total} results")
        else:
            if "403" in str(result.error):
                print(f"    403 Forbidden - not registered origin")
            else:
                print(f"    Error: {result.error}")

    # Restore original config
    config.get_database_config("dvids")["origin"] = original_origin

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nTest 1 (No origin): {'PASS' if result1.success else 'FAIL'}")
    print(f"Test 2 (localhost): {'PASS' if result2.success else 'FAIL'}")
    print(f"Test 3 (Common origins): {len(success_origins)}/{len(test_origins)} passed")

    if success_origins:
        print(f"\n✅ Working origins found: {', '.join(success_origins)}")
        print(f"\nRECOMMENDATION: Set dvids.origin in config_default.yaml to: {success_origins[0]}")
    else:
        print("\n⚠️ NO working origins found")
        print("\nACTION REQUIRED:")
        print("1. Check DVIDS developer portal for registered origin")
        print("2. OR request unrestricted API key")
        print("3. OR contact DVIDS support for origin details")

    return len(success_origins) > 0

if __name__ == "__main__":
    success = asyncio.run(test_dvids_with_different_origins())

    print("\n" + "=" * 80)
    if success:
        print("✅ DVIDS ORIGIN FIX: Working origin found")
        print("=" * 80)
        exit(0)
    else:
        print("⚠️ DVIDS ORIGIN FIX: No working origin found - user action required")
        print("=" * 80)
        exit(1)
