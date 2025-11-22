#!/usr/bin/env python3
"""
Comprehensive verification test - test ALL integrations using the registry.

Tests every enabled integration in the system to ensure:
1. Integration can be instantiated
2. Query generation works
3. Search execution works
4. QueryResult format is correct
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from integrations.registry import registry
from config_loader import config


async def test_integration(integration_id: str, integration):
    """Test a single integration end-to-end."""
    print(f"\n{'='*80}")
    print(f"Testing: {integration.metadata.name} ({integration_id})")
    print(f"{'='*80}")

    # Get API key if needed
    api_key = None
    if integration.metadata.requires_api_key:
        # Try to get key from environment
        key_var = f"{integration_id.upper()}_API_KEY"
        api_key = os.getenv(key_var)

        if not api_key:
            print(f"⚠️  Skipped: No {key_var} found")
            return {"status": "skipped", "reason": f"No {key_var}"}

    # Test 1: Metadata
    print(f"\n1. Metadata Check")
    print(f"   Name: {integration.metadata.name}")
    print(f"   Category: {integration.metadata.category.value}")
    print(f"   Requires API key: {integration.metadata.requires_api_key}")
    print(f"   ✓ Metadata valid")

    # Test 2: Query Generation
    print(f"\n2. Query Generation")
    test_queries = {
        "sam": "IT consulting contracts",
        "dvids": "Army training exercises",
        "usajobs": "software engineer jobs",
        "clearancejobs": "cybersecurity jobs requiring top secret clearance",
        "crest": "MK-ULTRA",
        "congress": "artificial intelligence regulation",
        "fbi_vault": "organized crime investigations",
        "federal_register": "environmental regulations",
        "twitter": "defense technology news",
        "reddit": "military technology discussions",
        "discord": "OSINT intelligence analysis",
        "brave_search": "defense contractors"
    }

    query_text = test_queries.get(integration_id, "government technology")
    query = await integration.generate_query(query_text)

    if not query:
        print(f"   ⚠️  Query generation returned None (may not be relevant)")
        return {"status": "not_relevant", "reason": "Query generation returned None"}

    print(f"   Query: {str(query)[:100]}...")
    print(f"   ✓ Query generated")

    # Test 3: Search Execution
    print(f"\n3. Search Execution")

    try:
        result = await integration.execute_search(query, api_key=api_key, limit=3)

        # Verify QueryResult format
        assert hasattr(result, 'success'), "Missing 'success' field"
        assert hasattr(result, 'source'), "Missing 'source' field"
        assert hasattr(result, 'total'), "Missing 'total' field"
        assert hasattr(result, 'results'), "Missing 'results' field"
        assert hasattr(result, 'query_params'), "Missing 'query_params' field"

        if result.success:
            print(f"   ✓ Search successful")
            print(f"   Total results: {result.total}")
            print(f"   Returned: {len(result.results)}")
            print(f"   Response time: {result.response_time_ms:.0f}ms")

            # Verify result format if we have results
            if result.results:
                first = result.results[0]
                has_title = 'title' in first
                has_snippet = 'snippet' in first or 'description' in first
                has_url = 'url' in first

                print(f"\n4. Result Format Check")
                print(f"   Has 'title': {has_title}")
                print(f"   Has 'snippet' or 'description': {has_snippet}")
                print(f"   Has 'url': {has_url}")

                if has_title and has_snippet and has_url:
                    print(f"   ✓ Result format valid")
                    return {
                        "status": "pass",
                        "total": result.total,
                        "returned": len(result.results),
                        "response_time_ms": result.response_time_ms
                    }
                else:
                    print(f"   ✗ Missing required fields")
                    return {"status": "fail", "reason": "Invalid result format"}
            else:
                print(f"   ⚠️  No results returned (may be normal)")
                return {"status": "pass", "total": 0, "returned": 0, "response_time_ms": result.response_time_ms}
        else:
            print(f"   ✗ Search failed: {result.error}")
            return {"status": "fail", "reason": result.error}

    except Exception as e:
        print(f"   ✗ Exception: {str(e)}")
        return {"status": "fail", "reason": str(e)}


async def main():
    print("="*80)
    print("COMPREHENSIVE INTEGRATION VERIFICATION TEST")
    print("Tests ALL enabled integrations in the registry")
    print("="*80)

    # Get all enabled integrations
    enabled = registry.get_all_enabled()

    print(f"\nFound {len(enabled)} enabled integrations:")
    for integration_id in enabled.keys():
        print(f"  • {integration_id}")

    # Test each integration
    results = {}
    for integration_id, integration in enabled.items():
        result = await test_integration(integration_id, integration)
        results[integration_id] = result

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    passed = [k for k, v in results.items() if v.get("status") == "pass"]
    failed = [k for k, v in results.items() if v.get("status") == "fail"]
    skipped = [k for k, v in results.items() if v.get("status") == "skipped"]
    not_relevant = [k for k, v in results.items() if v.get("status") == "not_relevant"]

    print(f"✅ PASSED: {len(passed)}")
    for integration_id in passed:
        r = results[integration_id]
        print(f"   • {integration_id}: {r.get('total', 0)} results ({r.get('response_time_ms', 0):.0f}ms)")

    if skipped:
        print(f"\n⚠️  SKIPPED: {len(skipped)}")
        for integration_id in skipped:
            print(f"   • {integration_id}: {results[integration_id].get('reason', 'Unknown')}")

    if not_relevant:
        print(f"\n⚠️  NOT RELEVANT: {len(not_relevant)}")
        for integration_id in not_relevant:
            print(f"   • {integration_id}: Query not relevant")

    if failed:
        print(f"\n✗ FAILED: {len(failed)}")
        for integration_id in failed:
            print(f"   • {integration_id}: {results[integration_id].get('reason', 'Unknown')}")

    print(f"\n{'='*80}")

    # Check model configuration
    print("\nConfiguration Check:")
    model = config.get_model('query_generation')
    print(f"   Query generation model: {model}")

    print(f"\n{'='*80}")

    if failed:
        print("⚠️  SOME TESTS FAILED - See details above")
        return False
    else:
        print("✅ ALL TESTS PASSED!")
        return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
