#!/usr/bin/env python3
"""
Test Brave Search integration with real API calls.

This script verifies:
1. Integration registered correctly
2. Relevance check (always True per user feedback)
3. Query generation via LLM
4. Search execution via Brave API
5. Result format standardization
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from integrations.social.brave_search_integration import BraveSearchIntegration


async def test_registration():
    """Test that Brave Search is registered in the integration registry."""
    print("\n=== Test 1: Registration ===")

    from integrations.registry import registry

    # Check if brave_search is in registry
    all_ids = registry.list_ids()
    assert "brave_search" in all_ids, "Brave Search not registered!"

    print(f"✓ Brave Search registered in registry")
    print(f"  Available integrations: {', '.join(all_ids)}")
    print()


async def test_relevance_check():
    """Test relevance check (should always return True per user feedback)."""
    print("=== Test 2: Relevance Check ===")

    integration = BraveSearchIntegration()

    # Test with various questions
    test_questions = [
        "NSA surveillance programs",
        "ICE detention facilities",
        "list federal contracts for cybersecurity",  # This is SAM query but should still return True
        "completely random nonsense query"
    ]

    for question in test_questions:
        relevant = await integration.is_relevant(question)
        assert relevant == True, f"Expected True for '{question}', got {relevant}"
        print(f"✓ '{question[:50]}...' -> {relevant}")

    print("✓ Relevance check always returns True (as designed)\n")


async def test_query_generation():
    """Test LLM-based query generation."""
    print("=== Test 3: Query Generation ===")

    integration = BraveSearchIntegration()

    # Test with investigative query
    question = "NSA surveillance programs leaked documents"
    print(f"Question: {question}")

    query_params = await integration.generate_query(question)

    assert query_params is not None, "Query params should not be None for investigative query"
    assert "query" in query_params, "Missing 'query' field"
    assert "count" in query_params, "Missing 'count' field"

    print(f"✓ Generated query params:")
    print(f"  Query: {query_params['query']}")
    print(f"  Count: {query_params['count']}")
    print(f"  Freshness: {query_params.get('freshness', 'None')}")
    print(f"  Country: {query_params.get('country', 'None')}")
    print()

    return query_params


async def test_search_execution(query_params):
    """Test actual Brave Search API call."""
    print("=== Test 4: Search Execution ===")

    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        print("✗ BRAVE_API_KEY not set in .env - skipping API test")
        return

    integration = BraveSearchIntegration()

    print(f"Executing search with query: {query_params['query']}")
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: NOT SET")

    result = await integration.execute_search(
        query_params=query_params,
        api_key=api_key,
        limit=5
    )

    assert result.success, f"Search failed: {result.error}"
    assert len(result.results) > 0, "Expected at least 1 result"

    print(f"✓ Search succeeded")
    print(f"  Results: {len(result.results)}")
    print(f"  Response time: {result.response_time_ms:.2f}ms")
    print(f"\n  First 3 results:")

    for i, item in enumerate(result.results[:3], 1):
        print(f"\n  {i}. {item.get('title', 'NO TITLE')[:60]}")
        print(f"     URL: {item.get('url', 'NO URL')[:80]}")
        print(f"     Age: {item.get('age', 'unknown')}")
        print(f"     Description: {item.get('description', '')[:100]}...")

    print()


async def test_error_handling():
    """Test error handling with missing API key."""
    print("=== Test 5: Error Handling ===")

    integration = BraveSearchIntegration()

    query_params = {
        "query": "test query",
        "count": 10,
        "country": "us"
    }

    # Test with no API key
    result = await integration.execute_search(
        query_params=query_params,
        api_key=None,
        limit=5
    )

    assert result.success == False, "Expected failure with no API key"
    assert "API key required" in result.error, f"Unexpected error: {result.error}"

    print(f"✓ Error handling works correctly")
    print(f"  Error message: {result.error}")
    print()


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Testing Brave Search Integration")
    print("="*60)

    try:
        await test_registration()
        await test_relevance_check()
        query_params = await test_query_generation()
        await test_search_execution(query_params)
        await test_error_handling()

        print("="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check .venv activation
    import shutil
    if shutil.which("python3") and ".venv" not in shutil.which("python3"):
        print("WARNING: .venv not activated. Run: source .venv/bin/activate")
        sys.exit(1)

    asyncio.run(main())
