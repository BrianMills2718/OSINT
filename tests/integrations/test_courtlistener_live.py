#!/usr/bin/env python3
"""
Live test suite for CourtListener integration.

Tests:
1. Metadata check
2. Relevance filtering (litigation ✓, contracts ✗)
3. Query generation (corporate litigation)
4. Live API search (antitrust cases)
5. Search result validation

REQUIRES: COURTLISTENER_API_KEY in .env
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.legal.courtlistener_integration import CourtListenerIntegration


async def test_metadata():
    """Test 1: Check integration metadata."""
    print("\n" + "="*60)
    print("TEST 1: Metadata Check")
    print("="*60)

    integration = CourtListenerIntegration()
    metadata = integration.metadata

    print(f"✅ Name: {metadata.name}")
    print(f"✅ ID: {metadata.id}")
    print(f"✅ Category: {metadata.category.value}")
    print(f"✅ Requires API Key: {metadata.requires_api_key}")
    print(f"✅ Cost per query: ${metadata.cost_per_query_estimate:.4f}")
    print(f"✅ Response time: {metadata.typical_response_time}s")
    print(f"✅ Rate limit: {metadata.rate_limit_daily:,} requests/day")
    print(f"✅ Description: {metadata.description}")

    return True


async def test_relevance():
    """Test 2: Relevance filtering."""
    print("\n" + "="*60)
    print("TEST 2: Relevance Filtering")
    print("="*60)

    integration = CourtListenerIntegration()

    test_cases = [
        ("Has Google been sued for antitrust?", True),
        ("What lawsuits has Boeing faced?", True),
        ("Recent Supreme Court rulings on privacy", True),
        ("When did Toys R Us file bankruptcy?", True),
        ("Defense contractor opportunities", False),
        ("Latest NAICS codes for cybersecurity", False),
        ("Federal Register rules on emissions", False),
        ("Job openings at Department of Defense", False),
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

    integration = CourtListenerIntegration()
    question = "Has Google been sued for antitrust violations by the Department of Justice?"

    print(f"Research Question: {question}")
    print("Generating query parameters...")

    query_params = await integration.generate_query(question)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Search Query: {query_params.get('q')}")
        print(f"   Type: {query_params.get('type')}")
        print(f"   Courts: {query_params.get('court') or '(all courts)'}")
        print(f"   Filed After: {query_params.get('filed_after') or 'No limit'}")
        print(f"   Filed Before: {query_params.get('filed_before') or 'No limit'}")
        print(f"   Case Name: {query_params.get('case_name') or '(no filter)'}")
        return True
    else:
        print("❌ Query generation returned None")
        return False


async def test_api_search():
    """Test 4: Live API search."""
    print("\n" + "="*60)
    print("TEST 4: Live API Search")
    print("="*60)

    # Load API key
    load_dotenv()
    api_key = os.getenv("COURTLISTENER_API_KEY")

    if not api_key:
        print("❌ COURTLISTENER_API_KEY not found in .env")
        print("   Get one at: https://www.courtlistener.com/sign-in/register/")
        return False

    print(f"✅ API key loaded: {api_key[:10]}...{api_key[-4:]}")

    integration = CourtListenerIntegration()

    # Test query: antitrust cases
    search_params = {
        "q": "antitrust",
        "type": "o",  # Opinions
        "court": "",  # All courts
        "filed_after": "2020-01-01",
        "filed_before": None,
        "case_name": ""
    }

    print(f"\nExecuting search:")
    print(f"   Query: {search_params['q']}")
    print(f"   Type: Opinions")
    print(f"   Date range: 2020-01-01 to present")

    result = await integration.execute_search(search_params, api_key, limit=5)

    if result.success:
        print(f"✅ Search successful")
        print(f"   Total results: {result.total}")
        print(f"   Results returned: {len(result.results)}")
        print(f"   Response time: {result.response_time_ms:.0f}ms")

        if result.results:
            print(f"\n   Sample results:")
            for i, doc in enumerate(result.results[:3], 1):
                print(f"   {i}. {doc.get('title', 'Untitled')}")
                print(f"      URL: {doc.get('url', 'No URL')}")
                print(f"      Date: {doc.get('date', 'No date')}")
                court = doc.get('metadata', {}).get('court', 'Unknown court')
                print(f"      Court: {court}")

        return True
    else:
        print(f"❌ Search failed: {result.error}")
        return False


async def test_result_validation():
    """Test 5: Validate SearchResult format."""
    print("\n" + "="*60)
    print("TEST 5: Result Validation (Pydantic Schema)")
    print("="*60)

    load_dotenv()
    api_key = os.getenv("COURTLISTENER_API_KEY")

    if not api_key:
        print("⚠️  Skipping (no API key)")
        return True

    integration = CourtListenerIntegration()

    # Simple search
    search_params = {
        "q": "Supreme Court",
        "type": "o",
        "court": "scotus",
        "filed_after": "2024-01-01",
        "filed_before": None,
        "case_name": ""
    }

    result = await integration.execute_search(search_params, api_key, limit=3)

    if not result.success:
        print(f"❌ Search failed: {result.error}")
        return False

    print(f"✅ Retrieved {len(result.results)} results")

    # Validate each result has required fields
    required_fields = ['title', 'url', 'snippet', 'date', 'metadata']

    for i, doc in enumerate(result.results, 1):
        print(f"\n   Result {i}:")
        for field in required_fields:
            if field in doc:
                value = doc[field]
                # Show truncated value
                if isinstance(value, str) and len(value) > 50:
                    display = value[:50] + "..."
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
    print("CourtListener Integration - Live Test Suite")
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
