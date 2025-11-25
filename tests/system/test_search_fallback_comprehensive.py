#!/usr/bin/env python3
"""
Comprehensive unit tests for core/search_fallback.py.

Tests all fallback scenarios, edge cases, and error handling.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.search_fallback import execute_with_fallback
from core.database_integration_base import QueryResult


# Test fixtures and mocks

class FakeMetadata:
    """Mock metadata for testing."""
    def __init__(self, strategies=None, supports_fallback=True):
        self.characteristics = {
            'supports_fallback': supports_fallback,
            'search_strategies': strategies or []
        }


async def mock_success_search(param_value):
    """Mock search that always succeeds."""
    return QueryResult(
        success=True,
        source="Test Source",
        total=5,
        results=[{"title": f"Result for {param_value}"}],
        query_params={"param": param_value}
    )


async def mock_failure_search(param_value):
    """Mock search that always fails."""
    return QueryResult(
        success=False,
        source="Test Source",
        total=0,
        results=[],
        query_params={"param": param_value},
        error="Mock failure"
    )


async def mock_empty_search(param_value):
    """Mock search that succeeds but returns no results."""
    return QueryResult(
        success=True,
        source="Test Source",
        total=0,
        results=[],
        query_params={"param": param_value}
    )


async def mock_error_search(param_value):
    """Mock search that raises exception."""
    raise ValueError("Mock exception from search")


# Test cases

async def test_first_strategy_succeeds():
    """Test 1: First strategy succeeds - should return immediately."""
    print("\n" + "="*80)
    print("TEST 1: First Strategy Succeeds")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        'primary': mock_success_search,
        'secondary': mock_success_search,  # Should never be called
    }

    query_params = {
        'id': '123',
        'name': 'Test'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.total == 5:
        print("✅ PASS: First strategy succeeded immediately")
        print(f"   Used strategy: {result.metadata.get('fallback_strategy_used')}")
        print(f"   Attempts: {result.metadata.get('fallback_attempts')}")
        return True
    else:
        print(f"❌ FAIL: Expected success, got {result}")
        return False


async def test_first_fails_second_succeeds():
    """Test 2: First strategy fails, second succeeds."""
    print("\n" + "="*80)
    print("TEST 2: First Fails, Second Succeeds (Fallback)")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        'primary': mock_failure_search,  # Fails
        'secondary': mock_success_search,  # Succeeds
    }

    query_params = {
        'id': '123',
        'name': 'Test'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.metadata.get('fallback_strategy_used') == 'secondary':
        print("✅ PASS: Fallback to second strategy worked")
        print(f"   Attempts: {result.metadata.get('fallback_attempts')}")
        return True
    else:
        print(f"❌ FAIL: Expected fallback to secondary, got {result}")
        return False


async def test_all_strategies_fail():
    """Test 3: All strategies fail - comprehensive error."""
    print("\n" + "="*80)
    print("TEST 3: All Strategies Fail")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
        {'method': 'tertiary', 'param': 'keyword', 'reliability': 'low'},
    ])

    search_methods = {
        'primary': mock_failure_search,
        'secondary': mock_empty_search,  # Success=True but total=0
        'tertiary': mock_failure_search,
    }

    query_params = {
        'id': '123',
        'name': 'Test',
        'keyword': 'foo'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if not result.success and 'All 3 search strategies failed' in result.error:
        attempts = result.metadata.get('fallback_attempts', [])
        if len(attempts) == 3:
            print("✅ PASS: All strategies failed, comprehensive error returned")
            print(f"   Error: {result.error}")
            print(f"   Attempts: {len(attempts)}")
            return True

    print(f"❌ FAIL: Expected comprehensive failure, got {result}")
    return False


async def test_strategy_skipped_missing_param():
    """Test 4: Strategy skipped when parameter not in query_params."""
    print("\n" + "="*80)
    print("TEST 4: Strategy Skipped (Missing Parameter)")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},  # param missing
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        'primary': mock_success_search,
        'secondary': mock_success_search,
    }

    query_params = {
        'name': 'Test'  # 'id' missing
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.metadata.get('fallback_strategy_used') == 'secondary':
        print("✅ PASS: Primary skipped (missing param), secondary succeeded")
        return True
    else:
        print(f"❌ FAIL: Expected secondary strategy, got {result}")
        return False


async def test_search_method_not_implemented():
    """Test 5: Search method not provided - should skip."""
    print("\n" + "="*80)
    print("TEST 5: Search Method Not Implemented")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},  # method missing
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        # 'primary' not provided
        'secondary': mock_success_search,
    }

    query_params = {
        'id': '123',
        'name': 'Test'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.metadata.get('fallback_strategy_used') == 'secondary':
        print("✅ PASS: Primary skipped (not implemented), secondary succeeded")
        return True
    else:
        print(f"❌ FAIL: Expected secondary strategy, got {result}")
        return False


async def test_missing_search_strategies():
    """Test 6: Metadata missing search_strategies - should raise ValueError."""
    print("\n" + "="*80)
    print("TEST 6: Missing search_strategies in Metadata")
    print("="*80)

    metadata = FakeMetadata([])  # Empty strategies

    search_methods = {
        'primary': mock_success_search,
    }

    query_params = {'id': '123'}

    try:
        result = await execute_with_fallback(
            "Test Source",
            query_params,
            search_methods,
            metadata
        )
        print(f"❌ FAIL: Expected ValueError, got result: {result}")
        return False
    except ValueError as e:
        if "No search_strategies declared" in str(e):
            print("✅ PASS: ValueError raised for missing strategies")
            print(f"   Error: {e}")
            return True
        else:
            print(f"❌ FAIL: Wrong ValueError message: {e}")
            return False


async def test_none_metadata():
    """Test 7: None metadata - should raise ValueError."""
    print("\n" + "="*80)
    print("TEST 7: None Metadata")
    print("="*80)

    search_methods = {
        'primary': mock_success_search,
    }

    query_params = {'id': '123'}

    try:
        result = await execute_with_fallback(
            "Test Source",
            query_params,
            search_methods,
            None  # None metadata
        )
        print(f"❌ FAIL: Expected ValueError, got result: {result}")
        return False
    except ValueError as e:
        if "No metadata provided" in str(e):
            print("✅ PASS: ValueError raised for None metadata")
            print(f"   Error: {e}")
            return True
        else:
            print(f"❌ FAIL: Wrong ValueError message: {e}")
            return False


async def test_non_callable_search_method():
    """Test 8: Non-callable search method - should skip."""
    print("\n" + "="*80)
    print("TEST 8: Non-Callable Search Method")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        'primary': "not_a_function",  # String instead of function
        'secondary': mock_success_search,
    }

    query_params = {
        'id': '123',
        'name': 'Test'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.metadata.get('fallback_strategy_used') == 'secondary':
        print("✅ PASS: Non-callable primary skipped, secondary succeeded")
        return True
    else:
        print(f"❌ FAIL: Expected secondary strategy, got {result}")
        return False


async def test_exception_handling():
    """Test 9: Search method raises exception - should continue to next."""
    print("\n" + "="*80)
    print("TEST 9: Exception Handling (Continue to Next Strategy)")
    print("="*80)

    metadata = FakeMetadata([
        {'method': 'primary', 'param': 'id', 'reliability': 'high'},
        {'method': 'secondary', 'param': 'name', 'reliability': 'medium'},
    ])

    search_methods = {
        'primary': mock_error_search,  # Raises exception
        'secondary': mock_success_search,
    }

    query_params = {
        'id': '123',
        'name': 'Test'
    }

    result = await execute_with_fallback(
        "Test Source",
        query_params,
        search_methods,
        metadata
    )

    if result.success and result.metadata.get('fallback_strategy_used') == 'secondary':
        print("✅ PASS: Exception caught, fallback to secondary succeeded")
        return True
    else:
        print(f"❌ FAIL: Expected secondary strategy, got {result}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE UNIT TESTS: core/search_fallback.py")
    print("="*80)

    tests = [
        test_first_strategy_succeeds,
        test_first_fails_second_succeeds,
        test_all_strategies_fail,
        test_strategy_skipped_missing_param,
        test_search_method_not_implemented,
        test_missing_search_strategies,
        test_none_metadata,
        test_non_callable_search_method,
        test_exception_handling,
    ]

    results = []
    for test in tests:
        try:
            results.append(await test())
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✅ ALL TESTS PASSED")
        print("\ncore/search_fallback.py is comprehensively tested:")
        print("  • Success path (first strategy succeeds)")
        print("  • Fallback path (first fails, second succeeds)")
        print("  • Error path (all strategies fail)")
        print("  • Skip conditions (missing param, not implemented, not callable)")
        print("  • Validation (None metadata, missing strategies)")
        print("  • Exception handling (errors caught and continued)")
    else:
        print("\n❌ SOME TESTS FAILED")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
