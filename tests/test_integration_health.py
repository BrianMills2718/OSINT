#!/usr/bin/env python3
"""
Integration health check - test all registered integrations with live queries.

Run: python3 tests/test_integration_health.py
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.registry import registry


# Test queries by category - simple queries that should return results
TEST_QUERIES = {
    # Government
    "sam": "cybersecurity contracts",
    "usaspending": "Find federal spending on cybersecurity contracts",  # Needs spending-related keywords
    "federal_register": "Find federal regulations on artificial intelligence",  # Needs regulation keywords
    "congress": "defense authorization",
    "govinfo": "government accountability",
    "fec": "campaign contributions",
    "sec_edgar": "Find SEC filings for Microsoft Corporation",  # Needs company name
    "crest_selenium": "Find CIA documents about Cold War operations",

    # Jobs
    "usajobs": "software engineer",
    "clearancejobs": "security clearance",

    # News/Web
    "brave_search": "federal contracts news",
    "exa": "government technology",
    "newsapi": "federal government",

    # Social
    "reddit": "government contracts",
    "twitter": "federal procurement",
    "discord": "government",
    "telegram": "news",

    # Research/Legal
    "courtlistener": "government contract dispute",
    "propublica": "nonprofit",
    "icij_offshore_leaks": "Find offshore connections for Mossack Fonseca",  # Needs entity name
    "fbi_vault": "investigation",

    # Media/Archive
    "dvids": "military training",
    "wayback_machine": "whitehouse.gov",
}


async def test_integration(name: str, query: str) -> dict:
    """Test a single integration with a query."""
    result = {
        "name": name,
        "query": query,
        "status": "unknown",
        "results": 0,
        "time_ms": 0,
        "error": None
    }

    try:
        integration = registry.get_instance(name)
        if not integration:
            result["status"] = "NOT_FOUND"
            result["error"] = "Integration not in registry"
            return result

        start = time.time()

        # Check if relevant
        is_relevant = await integration.is_relevant(query)
        if not is_relevant:
            result["status"] = "SKIPPED"
            result["error"] = "Not relevant for query"
            result["time_ms"] = int((time.time() - start) * 1000)
            return result

        # Generate query
        query_params = await integration.generate_query(query)
        if not query_params:
            result["status"] = "NO_QUERY"
            result["error"] = "generate_query returned None"
            result["time_ms"] = int((time.time() - start) * 1000)
            return result

        # Get API key if needed
        api_key = registry.get_api_key(name)

        # Execute search
        search_result = await integration.execute_search(
            query_params=query_params,
            api_key=api_key,
            limit=5
        )

        elapsed = time.time() - start
        result["time_ms"] = int(elapsed * 1000)

        if search_result.success:
            result["status"] = "PASS"
            result["results"] = search_result.total
        else:
            result["status"] = "FAIL"
            result["error"] = search_result.error or "Unknown error"
            result["results"] = search_result.total

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:200]

    return result


async def run_health_check():
    """Run health check on all integrations."""
    print("=" * 70)
    print("INTEGRATION HEALTH CHECK")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    all_ids = registry.list_ids()
    results = []

    # Test each integration
    for name in sorted(all_ids):
        query = TEST_QUERIES.get(name, "test query")
        print(f"Testing {name}...", end=" ", flush=True)

        result = await test_integration(name, query)
        results.append(result)

        # Print inline result
        if result["status"] == "PASS":
            print(f"[PASS] {result['results']} results in {result['time_ms']}ms")
        elif result["status"] == "SKIPPED":
            print(f"[SKIP] {result['error']}")
        else:
            print(f"[{result['status']}] {result['error'][:50] if result['error'] else 'Unknown'}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    skipped = [r for r in results if r["status"] in ("SKIPPED", "NO_QUERY", "NOT_FOUND")]

    print(f"  PASS:    {len(passed)}/{len(results)}")
    print(f"  FAIL:    {len(failed)}/{len(results)}")
    print(f"  SKIPPED: {len(skipped)}/{len(results)}")
    print()

    if failed:
        print("FAILURES:")
        for r in failed:
            print(f"  - {r['name']}: {r['error'][:60] if r['error'] else 'Unknown'}")
        print()

    if passed:
        print("WORKING INTEGRATIONS:")
        for r in sorted(passed, key=lambda x: x['time_ms']):
            print(f"  - {r['name']}: {r['results']} results ({r['time_ms']}ms)")

    return len(failed) == 0


if __name__ == "__main__":
    success = asyncio.run(run_health_check())
    sys.exit(0 if success else 1)
