#!/usr/bin/env python3
"""
Live test suite for ICIJ Offshore Leaks integration.

Tests:
1. Metadata check
2. Relevance filtering (offshore ✓, jobs ✗)
3. Query generation (offshore entity search)
4. Live API search (search database)
5. Result validation

REQUIRES: No API key (ICIJ database is free/public)
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from integrations.investigative.icij_offshore_leaks import ICIJOffshoreLeaksIntegration


async def test_metadata():
    """Test 1: Check integration metadata."""
    print("\n" + "="*60)
    print("TEST 1: Metadata Check")
    print("="*60)

    integration = ICIJOffshoreLeaksIntegration()
    metadata = integration.metadata

    print(f"✅ Name: {metadata.name}")
    print(f"✅ ID: {metadata.id}")
    print(f"✅ Category: {metadata.category.value}")
    print(f"✅ Requires API Key: {metadata.requires_api_key}")
    print(f"✅ Cost per query: ${metadata.cost_per_query_estimate:.4f}")
    print(f"✅ Response time: {metadata.typical_response_time}s")
    print(f"✅ Rate limit: {metadata.rate_limit_daily or 'None (be respectful)'}")
    print(f"✅ Description: {metadata.description}")

    return True


async def test_relevance():
    """Test 2: Relevance filtering."""
    print("\n" + "="*60)
    print("TEST 2: Relevance Filtering")
    print("="*60)

    integration = ICIJOffshoreLeaksIntegration()

    test_cases = [
        ("Is Vladimir Putin in the Panama Papers?", True),
        ("Does Apple have offshore entities?", True),
        ("What companies are in the British Virgin Islands?", True),
        ("Who is Mossack Fonseca?", True),
        ("Defense contractor opportunities", False),
        ("Latest NAICS codes", False),
        ("Federal Register rules", False),
        ("Job openings at NASA", False),
    ]

    for question, expected_relevant in test_cases:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected_relevant else "❌"
        print(f"{status} '{question}': {relevant} (expected {expected_relevant})")

        if relevant != expected_relevant:
            print(f"   FAILED: Expected {expected_relevant}, got {relevant}")
            return False

    return True


async def test_query_generation():
    """Test 3: Query generation with LLM."""
    print("\n" + "="*60)
    print("TEST 3: Query Generation")
    print("="*60)

    integration = ICIJOffshoreLeaksIntegration()
    question = "Is there any connection between Elon Musk and offshore entities?"

    print(f"Research Question: {question}")
    print("Generating query parameters...")

    query_params = await integration.generate_query(question)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Search Name: {query_params.get('search_name')}")
        print(f"   Entity Type: {query_params.get('entity_type')}")
        print(f"   Jurisdiction: {query_params.get('jurisdiction') or '(all)'}")
        print(f"   Leak Source: {query_params.get('leak_source') or '(all leaks)'}")
        return True
    else:
        print("❌ Query generation returned None")
        return False


async def test_api_search():
    """Test 4: Live API search."""
    print("\n" + "="*60)
    print("TEST 4: Live API Search")
    print("="*60)

    integration = ICIJOffshoreLeaksIntegration()

    # Test query: search for "Mossack Fonseca" (the law firm at center of Panama Papers)
    search_params = {
        "search_name": "Mossack Fonseca",
        "entity_type": "Intermediary",
        "jurisdiction": "",
        "leak_source": ""
    }

    print(f"\nExecuting search:")
    print(f"   Search: Mossack Fonseca")
    print(f"   Type: Intermediary (law firm)")
    print(f"   Note: No API key needed (public database)")

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    if result.success:
        print(f"✅ Search successful")
        print(f"   Total results: {result.total}")
        print(f"   Results returned: {len(result.results)}")
        print(f"   Response time: {result.response_time_ms:.0f}ms")

        if result.results:
            print(f"\n   Sample results:")
            for i, entity in enumerate(result.results[:3], 1):
                print(f"   {i}. {entity.get('title', 'Untitled')}")
                metadata = entity.get('metadata', {})
                print(f"      Type: {metadata.get('entity_type', 'N/A')}")
                print(f"      Jurisdiction: {metadata.get('jurisdiction', 'N/A')}")
                print(f"      Match Score: {metadata.get('match_score', 'N/A')}")

        return True
    else:
        print(f"❌ Search failed: {result.error}")
        return False


async def test_result_validation():
    """Test 5: Validate SearchResult format."""
    print("\n" + "="*60)
    print("TEST 5: Result Validation (Pydantic Schema)")
    print("="*60)

    integration = ICIJOffshoreLeaksIntegration()

    # Simple search for a known entity
    search_params = {
        "search_name": "Panama",
        "entity_type": "Entity",
        "jurisdiction": "",
        "leak_source": ""
    }

    result = await integration.execute_search(search_params, api_key=None, limit=3)

    if not result.success:
        print(f"❌ Search failed: {result.error}")
        return False

    print(f"✅ Retrieved {len(result.results)} results")

    # Validate each result has required fields
    required_fields = ['title', 'url', 'snippet', 'date', 'metadata']

    for i, entity in enumerate(result.results, 1):
        print(f"\n   Result {i}:")
        for field in required_fields:
            if field in entity:
                value = entity[field]
                # Show truncated value
                if isinstance(value, str) and len(value) > 50:
                    display = value[:50] + "..."
                elif isinstance(value, dict):
                    display = f"{{...{len(value)} fields...}}"
                else:
                    display = value
                print(f"      ✅ {field}: {display}")
            else:
                print(f"      ❌ {field}: MISSING")
                return False

    return True


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ICIJ Offshore Leaks Integration - Live Test Suite")
    print("="*60)

    tests = [
        ("Metadata", test_metadata),
        ("Relevance Filtering", test_relevance),
        ("Query Generation", test_query_generation),
        ("Live API Search", test_api_search),
        ("Result Validation", test_result_validation),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results[test_name] = success
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(results.values())
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
