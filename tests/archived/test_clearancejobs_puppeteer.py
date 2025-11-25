#!/usr/bin/env python3
"""
Test script for ClearanceJobs Puppeteer scraper.

This tests the new Puppeteer-based scraper that replaces the broken
ClearanceJobs API.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from integrations.clearancejobs_puppeteer import search_clearancejobs, PuppeteerNotAvailableError


async def test_search():
    """Test the Puppeteer-based search with a simple query."""

    print("=" * 70)
    print("CLEARANCEJOBS PUPPETEER SCRAPER TEST")
    print("=" * 70)
    print()

    # NOTE: This test requires the Puppeteer MCP server to be running
    # When run from Claude Code, MCP tools are available
    # When run standalone, this will fail with PuppeteerNotAvailableError

    try:
        # These MCP tools are available when run from Claude Code
        from mcp_tools import (
            puppeteer_navigate,
            puppeteer_fill,
            puppeteer_evaluate,
            puppeteer_click
        )

        print("✓ Puppeteer MCP tools loaded")
        print()

    except ImportError:
        print("✗ Puppeteer MCP tools not available")
        print()
        print("This test must be run from Claude Code with Puppeteer MCP server configured.")
        print("Standalone Python execution is not supported.")
        sys.exit(1)

    # Test query
    test_keyword = "cybersecurity analyst"
    print(f"Searching for: {test_keyword}")
    print()

    try:
        result = await search_clearancejobs(
            keywords=test_keyword,
            limit=5,
            puppeteer_navigate=puppeteer_navigate,
            puppeteer_fill=puppeteer_fill,
            puppeteer_evaluate=puppeteer_evaluate,
            puppeteer_click=puppeteer_click
        )

        if not result["success"]:
            print(f"✗ Search failed: {result.get('error')}")
            sys.exit(1)

        print("✓ Search completed successfully")
        print()
        print(f"Total results available: {result['total']}")
        print(f"Results returned: {len(result['jobs'])}")
        print()

        # Display results
        for i, job in enumerate(result['jobs'], 1):
            print(f"{i}. {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   Clearance: {job['clearance'] or 'Not Specified'}")
            print(f"   Posted: {job['updated'] or 'Unknown'}")
            print(f"   URL: {job['url']}")
            print()

        print("=" * 70)
        print("✓ TEST PASSED")
        print("=" * 70)

    except PuppeteerNotAvailableError as e:
        print(f"✗ Puppeteer error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_search())
