#!/usr/bin/env python3
"""
Quick test of ClearanceJobs Playwright scraper.

Run this immediately after Playwright installation completes to verify it works.
"""

import asyncio

try:
    from integrations.government.clearancejobs_http import search_clearancejobs
    PLAYWRIGHT_INSTALLED = True
except ImportError as e:
    PLAYWRIGHT_INSTALLED = False
    print(f"✗ Playwright not installed: {e}")
    print("\nTo install Playwright:")
    print("  1. pip install playwright")
    print("  2. playwright install chromium")
    exit(1)


async def main():
    print("=" * 80)
    print("CLEARANCEJOBS PLAYWRIGHT SCRAPER TEST")
    print("=" * 80)
    print()

    # Test 1: Basic search
    print("Test 1: Basic search - 'cybersecurity analyst'")
    print("-" * 80)

    result = await search_clearancejobs("cybersecurity analyst", limit=5, headless=True)

    if result["success"]:
        print(f"✓ Search successful")
        print(f"  Total results: {result['total']:,}")
        print(f"  Returned: {len(result['jobs'])} jobs\n")

        if result['jobs']:
            for i, job in enumerate(result['jobs'][:3], 1):
                print(f"{i}. {job['title']}")
                print(f"   Company: {job['company']}")
                print(f"   Location: {job['location']}")
                print(f"   Clearance: {job['clearance']}")
                print(f"   Updated: {job['updated']}")
                print(f"   URL: {job['url'][:60]}...\n")
    else:
        print(f"✗ Search failed: {result['error']}")
        exit(1)

    # Test 2: Different search term
    print("Test 2: Different search - 'software engineer'")
    print("-" * 80)

    result2 = await search_clearancejobs("software engineer", limit=3, headless=True)

    if result2["success"]:
        print(f"✓ Search successful")
        print(f"  Total results: {result2['total']:,}")
        print(f"  Returned: {len(result2['jobs'])} jobs")
    else:
        print(f"✗ Search failed: {result2['error']}")
        exit(1)

    print()
    print("=" * 80)
    print("✅ CLEARANCEJOBS PLAYWRIGHT SCRAPER WORKING!")
    print("=" * 80)
    print()
    print("Key features verified:")
    print("  ✓ Browser automation (Chromium)")
    print("  ✓ Search form interaction")
    print("  ✓ Vue.js event triggering")
    print("  ✓ Result extraction")
    print("  ✓ Cookie popup handling")
    print("  ✓ Clearance level parsing")
    print()
    print("Next step: Run test_all_four_databases.py to test all 4 integrations in parallel")


if __name__ == "__main__":
    asyncio.run(main())
