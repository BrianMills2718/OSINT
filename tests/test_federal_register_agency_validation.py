#!/usr/bin/env python3
"""
Test Federal Register agency slug validation.

Verifies that the 3-layer validation pattern prevents API errors from invalid agency slugs.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.government.federal_register import FederalRegisterIntegration
from dotenv import load_dotenv

load_dotenv()


async def test_valid_agencies():
    """Test that valid agency slugs work correctly."""
    print("[TEST 1] Valid Agency Slugs")
    print("="*80)

    integration = FederalRegisterIntegration()

    # Query with valid agency slug
    query_params = {
        "term": "cybersecurity",
        "document_types": ["RULE"],
        "agencies": ["homeland-security-department"],  # Valid
        "date_range_days": 90
    }

    result = await integration.execute_search(query_params, limit=5)

    if result.success:
        print(f"✅ Valid agency slug accepted")
        print(f"   Results: {result.total} documents found")
        print(f"   Query params used: {result.query_params}")
    else:
        print(f"❌ Valid agency slug failed: {result.error}")

    print()
    return result.success


async def test_invalid_agencies_filtered():
    """Test that invalid agency slugs are filtered out."""
    print("[TEST 2] Invalid Agency Slug Filtering")
    print("="*80)

    integration = FederalRegisterIntegration()

    # Query with invalid agency slugs (the ones causing 400 errors in production)
    query_params = {
        "term": "artificial intelligence",
        "document_types": ["RULE"],
        "agencies": [
            "office-of-management-and-budget",  # Invalid - doesn't exist
            "homeland-security-department",      # Valid
            "national-science-and-technology-council"  # Invalid - doesn't exist
        ],
        "date_range_days": 180
    }

    print(f"Input agencies: {query_params['agencies']}")
    print("Expected: Filter out 2 invalid, keep 1 valid")
    print()

    result = await integration.execute_search(query_params, limit=5)

    # Check that invalid slugs were filtered
    filtered_agencies = result.query_params.get("agencies", [])

    if result.success:
        print(f"✅ Query succeeded after filtering")
        print(f"   Filtered agencies: {filtered_agencies}")
        print(f"   Results: {result.total} documents found")

        # Verify only valid agency remained
        if filtered_agencies == ["homeland-security-department"]:
            print(f"✅ Correctly filtered to only valid agencies")
            return True
        else:
            print(f"⚠️  Unexpected filtered agencies: {filtered_agencies}")
            return False
    else:
        print(f"❌ Query failed even after filtering: {result.error}")
        return False


async def test_all_invalid_agencies():
    """Test behavior when all agency slugs are invalid."""
    print("[TEST 3] All Invalid Agency Slugs")
    print("="*80)

    integration = FederalRegisterIntegration()

    # Query with only invalid agency slugs
    query_params = {
        "term": "policy",
        "document_types": [],
        "agencies": [
            "office-of-management-and-budget",
            "national-science-and-technology-council"
        ],
        "date_range_days": 90
    }

    print(f"Input agencies: {query_params['agencies']}")
    print("Expected: Filter out all invalid, proceed with no agency filter")
    print()

    result = await integration.execute_search(query_params, limit=5)

    filtered_agencies = result.query_params.get("agencies", [])

    if result.success:
        print(f"✅ Query succeeded with no agency filter")
        print(f"   Filtered agencies: {filtered_agencies}")
        print(f"   Results: {result.total} documents found")
        return True
    else:
        print(f"❌ Query failed: {result.error}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("FEDERAL REGISTER AGENCY VALIDATION TESTS")
    print("="*80 + "\n")

    results = []

    # Test 1: Valid agencies
    results.append(await test_valid_agencies())

    # Test 2: Mix of valid and invalid
    results.append(await test_invalid_agencies_filtered())

    # Test 3: All invalid
    results.append(await test_all_invalid_agencies())

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("✅ All tests passed - Agency validation working correctly")
        return 0
    else:
        print("❌ Some tests failed - Review validation logic")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
