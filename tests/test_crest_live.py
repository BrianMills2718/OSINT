#!/usr/bin/env python3
"""
Test CREST (CIA Reading Room) integration with live web scraping.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports
from integrations.government.crest_integration import CRESTIntegration


async def main():
    print("🧪 CREST (CIA Reading Room) Live Test")
    print("=" * 80)

    # Check Playwright availability
    try:
        from playwright.async_api import async_playwright
        print("✓ Playwright installed")
    except ImportError:
        print("✗ Playwright not installed")
        print("  Run: pip install playwright && playwright install chromium")
        return

    print()

    # Test 1: Search for MK-ULTRA documents
    print("Test 1: MK-ULTRA Declassified Documents")
    print("-" * 80)

    crest = CRESTIntegration()
    query = await crest.generate_query("MK-ULTRA mind control program")

    if query:
        print(f"✓ Query generated:")
        print(f"  Keyword: {query.get('keyword')}")
        print(f"  Max pages: {query.get('max_pages')}")

        print(f"\n  Starting web scraping (this may take 30-60 seconds)...")
        result = await crest.execute_search(query, limit=3)

        if result.success:
            print(f"✓ Search successful: {result.total} results found")
            print(f"  Response time: {result.response_time_ms:.0f}ms")

            if result.results:
                print(f"\n  First result:")
                first = result.results[0]
                print(f"    Title: {first.get('title', 'N/A')[:80]}...")
                print(f"    URL: {first.get('url', 'N/A')[:60]}...")
                print(f"    Snippet: {first.get('snippet', 'N/A')[:150]}...")

                # Test field normalization
                print(f"\n  Field Normalization Test:")
                has_title = 'title' in first
                has_snippet = 'snippet' in first
                has_url = 'url' in first
                has_metadata = 'metadata' in first

                print(f"    ✓ Has 'title' field: {has_title}")
                print(f"    ✓ Has 'snippet' field: {has_snippet}")
                print(f"    ✓ Has 'url' field: {has_url}")
                print(f"    ✓ Has 'metadata' field: {has_metadata}")

                if has_title and has_snippet and has_url:
                    print(f"    ✅ All required fields present")
                    print(f"    Snippet length: {len(first.get('snippet', ''))} chars")
                else:
                    print(f"    ❌ MISSING FIELDS - check QueryResult format!")
        else:
            print(f"✗ Search failed: {result.error}")
    else:
        print("✗ Query generation failed (not relevant)")

    print()

    # Test 2: Search for Cold War intelligence documents
    print("Test 2: Cold War Soviet Intelligence")
    print("-" * 80)

    query2 = await crest.generate_query("Soviet intelligence operations Cold War")

    if query2:
        print(f"✓ Query generated:")
        print(f"  Keyword: {query2.get('keyword')}")

        print(f"\n  Starting web scraping (this may take 30-60 seconds)...")
        result2 = await crest.execute_search(query2, limit=2)

        if result2.success:
            print(f"✓ Search successful: {result2.total} results found")
            print(f"  Response time: {result2.response_time_ms:.0f}ms")

            if result2.results:
                print(f"\n  Sample results:")
                for i, doc in enumerate(result2.results[:2], 1):
                    title = doc.get('title', 'N/A')
                    print(f"    {i}. {title[:70]}...")
        else:
            print(f"✗ Search failed: {result2.error}")
    else:
        print("✗ Query generation failed")

    print()

    # Test 3: Test relevance filtering (modern topic should fail)
    print("Test 3: Relevance Filtering (Modern Topic - Should Not Be Relevant)")
    print("-" * 80)

    query3 = await crest.generate_query("cryptocurrency regulations 2024")

    if query3:
        print(f"✗ Query generated for modern topic (LLM should have rejected this)")
    else:
        print(f"✓ Query correctly rejected (CREST only has pre-2000 documents)")

    print()
    print("=" * 80)
    print("✅ CREST web scraping test complete!")
    print()
    print("⚠️  NOTE: CREST uses Playwright web scraping (slow ~30-60s per search)")
    print("    Use sparingly in production. Consider caching results.")


if __name__ == "__main__":
    asyncio.run(main())
