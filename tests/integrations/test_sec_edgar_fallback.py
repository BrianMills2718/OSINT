#!/usr/bin/env python3
"""
Test SEC EDGAR fallback integration.

Validates that SEC EDGAR uses the generic fallback pattern correctly.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from integrations.government.sec_edgar import SECEdgarIntegration


async def test_fallback_metadata_configured():
    """Test 1: Verify SEC EDGAR metadata supports fallback."""
    print("\n" + "="*80)
    print("TEST 1: SEC EDGAR Fallback Metadata")
    print("="*80)

    # Use integration.metadata (single source of truth)
    integration = SECEdgarIntegration()
    metadata = integration.metadata

    if not metadata:
        print("[FAIL] SEC EDGAR metadata not found")
        return False

    supports_fallback = metadata.characteristics.get('supports_fallback')
    search_strategies = metadata.characteristics.get('search_strategies', [])

    print(f"\nSupports fallback: {supports_fallback}")
    print(f"Search strategies: {len(search_strategies)}")

    if supports_fallback and len(search_strategies) == 4:
        print("\n[PASS] SEC EDGAR metadata configured for fallback")
        print(f"  Strategies: {[s['method'] for s in search_strategies]}")
        return True
    else:
        print("\n[FAIL] SEC EDGAR metadata not properly configured")
        return False


async def test_search_methods_exist():
    """Test 2: Verify all search methods exist."""
    print("\n" + "="*80)
    print("TEST 2: SEC EDGAR Search Methods")
    print("="*80)

    integration = SECEdgarIntegration()

    required_methods = [
        '_search_by_cik',
        '_search_by_ticker',
        '_search_by_name_exact',
        '_search_by_name_fuzzy'
    ]

    all_exist = True
    for method_name in required_methods:
        if hasattr(integration, method_name):
            method = getattr(integration, method_name)
            is_async = asyncio.iscoroutinefunction(method)
            status = "✅" if is_async else "⚠️  (not async)"
            print(f"  {status} {method_name}: exists")
            if not is_async:
                all_exist = False
        else:
            print(f"  ❌ {method_name}: missing")
            all_exist = False

    if all_exist:
        print("\n✅ PASS: All search methods exist and are async")
        return True
    else:
        print("\n❌ FAIL: Some search methods missing or not async")
        return False


async def test_execute_search_uses_fallback():
    """Test 3: Verify execute_search uses fallback pattern."""
    print("\n" + "="*80)
    print("TEST 3: execute_search() Uses Fallback")
    print("="*80)

    import inspect
    integration = SECEdgarIntegration()

    # Check if execute_search imports execute_with_fallback
    source = inspect.getsource(integration.execute_search)

    checks = [
        ("execute_with_fallback" in source, "Imports execute_with_fallback"),
        ("get_source_metadata" in source, "Gets source metadata"),
        ("supports_fallback" in source, "Checks supports_fallback flag"),
        ("search_methods" in source, "Defines search_methods dict"),
    ]

    all_passed = True
    for passed, description in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {description}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ PASS: execute_search() uses fallback pattern")
        return True
    else:
        print("\n❌ FAIL: execute_search() missing fallback implementation")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("SEC EDGAR Fallback Integration Tests")
    print("="*80)

    tests = [
        test_fallback_metadata_configured,
        test_search_methods_exist,
        test_execute_search_uses_fallback,
    ]

    results = []
    for test in tests:
        try:
            results.append(await test())
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✅ ALL TESTS PASSED")
        print("\nSEC EDGAR fallback integration complete:")
        print("  • Metadata configured with 4 search strategies")
        print("  • All search methods implemented")
        print("  • execute_search() uses generic fallback pattern")
        print("\nReady for real-world testing.")
    else:
        print("\n❌ SOME TESTS FAILED")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
