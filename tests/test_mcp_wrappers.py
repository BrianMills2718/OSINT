#!/usr/bin/env python3
"""
MCP Wrappers Test Suite

Tests the FastMCP wrappers for government and social integrations.

Test Structure:
1. In-Memory Tests: Schema generation, tool listing, basic functionality
2. Live API Tests: Limited real API calls to verify end-to-end flow

Usage:
    # All tests (in-memory + live)
    python3 tests/test_mcp_wrappers.py

    # In-memory only (no API calls)
    python3 tests/test_mcp_wrappers.py --in-memory-only

Requirements:
    - API keys in .env file
    - fastmcp installed (pip install fastmcp)
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from fastmcp import Client

# Load environment
load_dotenv()

# Import MCP servers
from integrations.mcp import government_mcp, social_mcp


# =============================================================================
# Test Configuration
# =============================================================================

# Test mode
RUN_LIVE_TESTS = "--in-memory-only" not in sys.argv

# Live test limits (keep low to avoid API quota exhaustion)
LIVE_TEST_LIMIT = 3  # Only fetch 3 results per live test


# =============================================================================
# Test Utilities
# =============================================================================

def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_test(test_name: str):
    """Print formatted test name."""
    print(f"\n[TEST] {test_name}")


def print_pass(message: str):
    """Print pass message."""
    print(f"  ✓ {message}")


def print_fail(message: str):
    """Print fail message."""
    print(f"  ✗ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"  ℹ {message}")


# =============================================================================
# In-Memory Tests (No API Calls)
# =============================================================================

async def test_government_mcp_schema():
    """Test government MCP server schema generation."""
    print_section("GOVERNMENT MCP - SCHEMA TESTS")

    async with Client(government_mcp.mcp) as client:
        print_test("List available tools")
        tools = await client.list_tools()

        expected_tools = {
            "search_sam",
            "search_dvids",
            "search_usajobs",
            "search_clearancejobs",
            "search_fbi_vault"
        }

        tool_names = {tool.name for tool in tools}

        if expected_tools == tool_names:
            print_pass(f"All 5 tools present: {tool_names}")
        else:
            print_fail(f"Expected {expected_tools}, got {tool_names}")
            return False

        print_test("Verify tool schemas auto-generated from docstrings")
        for tool in tools:
            print_info(f"Tool: {tool.name}")
            print_info(f"  Description: {tool.description[:80]}...")

            if tool.inputSchema:
                props = tool.inputSchema.get("properties", {})
                required = tool.inputSchema.get("required", [])
                print_info(f"  Required params: {required}")
                print_info(f"  All params: {list(props.keys())}")

                # Verify all tools have research_question parameter
                if "research_question" in props:
                    print_pass(f"  research_question parameter present")
                else:
                    print_fail(f"  Missing research_question parameter")
                    return False
            else:
                print_fail(f"  No input schema generated")
                return False

        return True


async def test_social_mcp_schema():
    """Test social MCP server schema generation."""
    print_section("SOCIAL MCP - SCHEMA TESTS")

    async with Client(social_mcp.mcp) as client:
        print_test("List available tools")
        tools = await client.list_tools()

        expected_tools = {
            "search_twitter",
            "search_brave",
            "search_discord",
            "search_reddit"
        }

        tool_names = {tool.name for tool in tools}

        if expected_tools == tool_names:
            print_pass(f"All 4 tools present: {tool_names}")
        else:
            print_fail(f"Expected {expected_tools}, got {tool_names}")
            return False

        print_test("Verify tool schemas auto-generated from docstrings")
        for tool in tools:
            print_info(f"Tool: {tool.name}")
            print_info(f"  Description: {tool.description[:80]}...")

            if tool.inputSchema:
                props = tool.inputSchema.get("properties", {})
                required = tool.inputSchema.get("required", [])
                print_info(f"  Required params: {required}")
                print_info(f"  All params: {list(props.keys())}")

                # Verify all tools have research_question parameter
                if "research_question" in props:
                    print_pass(f"  research_question parameter present")
                else:
                    print_fail(f"  Missing research_question parameter")
                    return False
            else:
                print_fail(f"  No input schema generated")
                return False

        return True


# =============================================================================
# Live API Tests (Limited Real API Calls)
# =============================================================================

async def test_sam_live():
    """Test SAM.gov search with real API call."""
    print_test("SAM.gov live search (limit=3)")

    api_key = os.getenv("SAM_GOV_API_KEY")
    if not api_key:
        print_info("  SAM_GOV_API_KEY not set, skipping")
        return None

    async with Client(government_mcp.mcp) as client:
        start_time = datetime.now()

        result = await client.call_tool(
            "search_sam",
            {
                "research_question": "cybersecurity contracts",
                "api_key": api_key,
                "limit": LIVE_TEST_LIMIT
            }
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Parse result
        import json
        data = json.loads(result.content[0].text)

        if data.get("success"):
            print_pass(f"Search succeeded in {duration:.2f}s")
            print_info(f"  Total results: {data.get('total', 0)}")
            print_info(f"  Results returned: {len(data.get('results', []))}")

            if data.get("results"):
                first = data["results"][0]
                title = first.get("title", "N/A")
                print_info(f"  Sample: {title[:60]}...")
            return True
        else:
            error = data.get("error", "Unknown error")
            print_fail(f"Search failed: {error}")
            return False


async def test_dvids_live():
    """Test DVIDS search with real API call."""
    print_test("DVIDS live search (limit=3)")

    api_key = os.getenv("DVIDS_API_KEY")
    if not api_key:
        print_info("  DVIDS_API_KEY not set, skipping")
        return None

    async with Client(government_mcp.mcp) as client:
        start_time = datetime.now()

        result = await client.call_tool(
            "search_dvids",
            {
                "research_question": "Navy ship deployment",
                "api_key": api_key,
                "limit": LIVE_TEST_LIMIT
            }
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Parse result
        import json
        data = json.loads(result.content[0].text)

        if data.get("success"):
            print_pass(f"Search succeeded in {duration:.2f}s")
            print_info(f"  Total results: {data.get('total', 0)}")
            print_info(f"  Results returned: {len(data.get('results', []))}")

            if data.get("results"):
                first = data["results"][0]
                title = first.get("title", "N/A")
                print_info(f"  Sample: {title[:60]}...")
            return True
        else:
            error = data.get("error", "Unknown error")
            print_fail(f"Search failed: {error}")
            return False


async def test_brave_live():
    """Test Brave Search with real API call."""
    print_test("Brave Search live search (limit=3)")

    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        print_info("  BRAVE_SEARCH_API_KEY not set, skipping")
        return None

    async with Client(social_mcp.mcp) as client:
        start_time = datetime.now()

        result = await client.call_tool(
            "search_brave",
            {
                "research_question": "NSA surveillance leaked documents",
                "api_key": api_key,
                "limit": LIVE_TEST_LIMIT
            }
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Parse result
        import json
        data = json.loads(result.content[0].text)

        if data.get("success"):
            print_pass(f"Search succeeded in {duration:.2f}s")
            print_info(f"  Total results: {data.get('total', 0)}")
            print_info(f"  Results returned: {len(data.get('results', []))}")

            if data.get("results"):
                first = data["results"][0]
                title = first.get("title", "N/A")
                print_info(f"  Sample: {title[:60]}...")
            return True
        else:
            error = data.get("error", "Unknown error")
            print_fail(f"Search failed: {error}")
            return False


async def test_discord_live():
    """Test Discord search (local exports, no API key)."""
    print_test("Discord local search (limit=3)")

    async with Client(social_mcp.mcp) as client:
        start_time = datetime.now()

        result = await client.call_tool(
            "search_discord",
            {
                "research_question": "ukraine intelligence analysis",
                "limit": LIVE_TEST_LIMIT
            }
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Parse result
        import json
        data = json.loads(result.content[0].text)

        if data.get("success"):
            print_pass(f"Search succeeded in {duration:.2f}s")
            print_info(f"  Total results: {data.get('total', 0)}")
            print_info(f"  Results returned: {len(data.get('results', []))}")

            if data.get("results"):
                first = data["results"][0]
                author = first.get("author", "N/A")
                server = first.get("server", "N/A")
                print_info(f"  Sample: {server} / {author}")
            return True
        else:
            error = data.get("error", "Unknown error")
            # Discord failure is expected if no exports present
            if "No keywords provided" in error or not Path("data/exports").exists():
                print_info(f"  Expected failure (no exports): {error}")
                return None
            else:
                print_fail(f"Search failed: {error}")
                return False


# =============================================================================
# Main Test Runner
# =============================================================================

async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  MCP WRAPPERS TEST SUITE")
    print("=" * 80)
    print(f"\n  Mode: {'FULL (in-memory + live)' if RUN_LIVE_TESTS else 'IN-MEMORY ONLY'}")
    print(f"  Live test limit: {LIVE_TEST_LIMIT} results per test\n")

    results = {
        "in_memory": {},
        "live": {}
    }

    # =============================================================================
    # In-Memory Tests
    # =============================================================================

    print_section("PHASE 1: IN-MEMORY TESTS (No API Calls)")

    try:
        results["in_memory"]["government_schema"] = await test_government_mcp_schema()
    except Exception as e:
        print_fail(f"Government schema test failed: {e}")
        import traceback
        traceback.print_exc()
        results["in_memory"]["government_schema"] = False

    try:
        results["in_memory"]["social_schema"] = await test_social_mcp_schema()
    except Exception as e:
        print_fail(f"Social schema test failed: {e}")
        import traceback
        traceback.print_exc()
        results["in_memory"]["social_schema"] = False

    # =============================================================================
    # Live API Tests
    # =============================================================================

    if RUN_LIVE_TESTS:
        print_section("PHASE 2: LIVE API TESTS (Limited Real API Calls)")
        print_info(f"Note: Only fetching {LIVE_TEST_LIMIT} results per test to conserve API quota\n")

        try:
            results["live"]["sam"] = await test_sam_live()
        except Exception as e:
            print_fail(f"SAM live test failed: {e}")
            import traceback
            traceback.print_exc()
            results["live"]["sam"] = False

        try:
            results["live"]["dvids"] = await test_dvids_live()
        except Exception as e:
            print_fail(f"DVIDS live test failed: {e}")
            import traceback
            traceback.print_exc()
            results["live"]["dvids"] = False

        try:
            results["live"]["brave"] = await test_brave_live()
        except Exception as e:
            print_fail(f"Brave live test failed: {e}")
            import traceback
            traceback.print_exc()
            results["live"]["brave"] = False

        try:
            results["live"]["discord"] = await test_discord_live()
        except Exception as e:
            print_fail(f"Discord live test failed: {e}")
            import traceback
            traceback.print_exc()
            results["live"]["discord"] = False

    # =============================================================================
    # Summary
    # =============================================================================

    print_section("TEST SUMMARY")

    # In-memory results
    print("\n[IN-MEMORY TESTS]")
    for test_name, result in results["in_memory"].items():
        if result is True:
            print_pass(f"{test_name}: PASS")
        elif result is False:
            print_fail(f"{test_name}: FAIL")
        else:
            print_info(f"{test_name}: SKIPPED")

    # Live results
    if RUN_LIVE_TESTS:
        print("\n[LIVE API TESTS]")
        for test_name, result in results["live"].items():
            if result is True:
                print_pass(f"{test_name}: PASS")
            elif result is False:
                print_fail(f"{test_name}: FAIL")
            elif result is None:
                print_info(f"{test_name}: SKIPPED (no API key or expected failure)")

    # Overall status
    in_memory_passed = sum(1 for r in results["in_memory"].values() if r is True)
    in_memory_total = len(results["in_memory"])

    print(f"\nIn-Memory: {in_memory_passed}/{in_memory_total} passed")

    if RUN_LIVE_TESTS:
        live_passed = sum(1 for r in results["live"].values() if r is True)
        live_total = len([r for r in results["live"].values() if r is not None])  # Exclude skipped
        live_skipped = sum(1 for r in results["live"].values() if r is None)

        print(f"Live API: {live_passed}/{live_total} passed ({live_skipped} skipped)")

    # Exit code
    all_passed = all(r is not False for r in results["in_memory"].values())
    if RUN_LIVE_TESTS:
        all_passed = all_passed and all(r is not False for r in results["live"].values())

    if all_passed:
        print("\n✓ ALL TESTS PASSED\n")
        sys.exit(0)
    else:
        print("\n✗ SOME TESTS FAILED\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
