#!/usr/bin/env python3
"""
Live test suite for FEC integration.

Tests:
1. Metadata check
2. Relevance filtering (campaign finance ✓, contracts ✗)
3. Query generation (candidate search)
4. Live API search - candidates endpoint
5. Live API search - contributions endpoint
6. Result validation

REQUIRES: CONGRESS_API_KEY (or FEC_API_KEY) in .env
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.government.fec_integration import FECIntegration


async def test_metadata():
    """Test 1: Check integration metadata."""
    print("\n" + "="*60)
    print("TEST 1: Metadata Check")
    print("="*60)

    integration = FECIntegration()
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

    integration = FECIntegration()

    test_cases = [
        ("Who donated to Bernie Sanders?", True),
        ("How much has Biden raised?", True),
        ("What PACs support environmental causes?", True),
        ("Has Elon Musk donated to campaigns?", True),
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

    integration = FECIntegration()
    question = "How much money has Elizabeth Warren raised for her Senate campaign?"

    print(f"Research Question: {question}")
    print("Generating query parameters...")

    query_params = await integration.generate_query(question)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Endpoint: {query_params.get('endpoint')}")
        print(f"   Candidate: {query_params.get('candidate_name')}")
        print(f"   Office: {query_params.get('office')}")
        print(f"   State: {query_params.get('state')}")
        print(f"   Cycle: {query_params.get('cycle')}")
        print(f"   Party: {query_params.get('party')}")
        return True
    else:
        print("❌ Query generation returned None")
        return False


async def test_api_candidates():
    """Test 4: Live API search - candidates endpoint."""
    print("\n" + "="*60)
    print("TEST 4: Live API Search - Candidates")
    print("="*60)

    # Load API key
    load_dotenv()
    api_key = os.getenv("CONGRESS_API_KEY") or os.getenv("FEC_API_KEY")

    if not api_key:
        print("❌ API key not found (CONGRESS_API_KEY or FEC_API_KEY)")
        print("   Get one at: https://api.data.gov/signup/")
        return False

    print(f"✅ API key loaded: {api_key[:10]}...{api_key[-4:]}")

    integration = FECIntegration()

    # Test query: search for Sanders
    search_params = {
        "endpoint": "candidates",
        "candidate_name": "Sanders",
        "committee_name": "",
        "contributor_name": "",
        "office": "S",  # Senate
        "state": "VT",  # Vermont
        "cycle": 2024,
        "party": "IND"  # Independent
    }

    print(f"\nExecuting search:")
    print(f"   Candidate: Sanders")
    print(f"   Office: Senate")
    print(f"   State: Vermont")
    print(f"   Cycle: 2024")

    result = await integration.execute_search(search_params, api_key, limit=5)

    if result.success:
        print(f"✅ Search successful")
        print(f"   Total results: {result.total}")
        print(f"   Results returned: {len(result.results)}")
        print(f"   Response time: {result.response_time_ms:.0f}ms")

        if result.results:
            print(f"\n   Sample results:")
            for i, candidate in enumerate(result.results[:3], 1):
                print(f"   {i}. {candidate.get('title', 'Untitled')}")
                print(f"      Office: {candidate.get('metadata', {}).get('office_full', 'N/A')}")
                print(f"      State: {candidate.get('metadata', {}).get('state', 'N/A')}")
                print(f"      Party: {candidate.get('metadata', {}).get('party_full', 'N/A')}")

        return True
    else:
        print(f"❌ Search failed: {result.error}")
        return False


async def test_api_contributions():
    """Test 5: Live API search - contributions endpoint."""
    print("\n" + "="*60)
    print("TEST 5: Live API Search - Contributions")
    print("="*60)

    load_dotenv()
    api_key = os.getenv("CONGRESS_API_KEY") or os.getenv("FEC_API_KEY")

    if not api_key:
        print("⚠️  Skipping (no API key)")
        return True

    integration = FECIntegration()

    # Test query: search for contributions from tech executives
    search_params = {
        "endpoint": "contributions",
        "candidate_name": "",
        "committee_name": "",
        "contributor_name": "Zuckerberg",  # Example tech exec
        "office": None,
        "state": None,
        "cycle": 2024,
        "party": None
    }

    print(f"\nExecuting search:")
    print(f"   Contributor: Zuckerberg")
    print(f"   Cycle: 2024")

    result = await integration.execute_search(search_params, api_key, limit=5)

    if result.success:
        print(f"✅ Search successful")
        print(f"   Total results: {result.total}")
        print(f"   Results returned: {len(result.results)}")
        print(f"   Response time: {result.response_time_ms:.0f}ms")

        if result.results:
            print(f"\n   Sample contributions:")
            for i, contrib in enumerate(result.results[:3], 1):
                print(f"   {i}. {contrib.get('title', 'Untitled')}")
                metadata = contrib.get('metadata', {})
                print(f"      Amount: ${metadata.get('amount', 0):,.2f}")
                print(f"      Date: {metadata.get('date', 'N/A')}")
                print(f"      Recipient: {metadata.get('recipient_committee', 'N/A')}")

        return True
    else:
        print(f"❌ Search failed: {result.error}")
        return False


async def test_result_validation():
    """Test 6: Validate SearchResult format."""
    print("\n" + "="*60)
    print("TEST 6: Result Validation (Pydantic Schema)")
    print("="*60)

    load_dotenv()
    api_key = os.getenv("CONGRESS_API_KEY") or os.getenv("FEC_API_KEY")

    if not api_key:
        print("⚠️  Skipping (no API key)")
        return True

    integration = FECIntegration()

    # Simple candidate search
    search_params = {
        "endpoint": "candidates",
        "candidate_name": "Warren",
        "committee_name": "",
        "contributor_name": "",
        "office": "S",
        "state": "MA",
        "cycle": 2024,
        "party": None
    }

    result = await integration.execute_search(search_params, api_key, limit=3)

    if not result.success:
        print(f"❌ Search failed: {result.error}")
        return False

    print(f"✅ Retrieved {len(result.results)} results")

    # Validate each result has required fields
    required_fields = ['title', 'url', 'snippet', 'date', 'metadata']

    for i, candidate in enumerate(result.results, 1):
        print(f"\n   Result {i}:")
        for field in required_fields:
            if field in candidate:
                value = candidate[field]
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
    print("FEC Integration - Live Test Suite")
    print("="*60)

    tests = [
        ("Metadata", test_metadata),
        ("Relevance Filtering", test_relevance),
        ("Query Generation", test_query_generation),
        ("Live API - Candidates", test_api_candidates),
        ("Live API - Contributions", test_api_contributions),
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
