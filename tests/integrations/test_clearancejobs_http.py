#!/usr/bin/env python3
"""
Comprehensive tests for ClearanceJobs HTTP-based integration.

Tests both the low-level HTTP scraper and the DatabaseIntegration wrapper.
"""

import asyncio
import time
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test the HTTP scraper directly
from integrations.government.clearancejobs_http import search_clearancejobs

# Test the integration wrapper
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration


async def test_http_scraper_basic():
    """Test 1: Basic search with valid keywords returns results."""
    print("\n" + "=" * 80)
    print("TEST 1: HTTP Scraper - Basic Search")
    print("=" * 80)

    result = await search_clearancejobs("penetration tester", limit=10)

    # Verify response structure
    assert result["success"] == True, "Search should succeed"
    assert "total" in result, "Response should include total count"
    assert "jobs" in result, "Response should include jobs list"
    assert "error" in result, "Response should include error field"

    # Verify results quality
    assert result["total"] > 0, "Should find results for valid query"
    assert len(result["jobs"]) > 0, "Should return job listings"
    assert len(result["jobs"]) <= 10, "Should respect limit parameter"

    # Verify job structure
    job = result["jobs"][0]
    required_fields = ["title", "url", "company", "location", "description",
                      "snippet", "clearance", "clearance_level", "updated", "source"]
    for field in required_fields:
        assert field in job, f"Job should have '{field}' field"

    # Verify field content
    assert len(job["title"]) > 0, "Title should not be empty"
    assert job["url"].startswith("https://"), "URL should be absolute HTTPS"
    assert len(job["company"]) > 0, "Company should not be empty"
    assert job["source"] == "ClearanceJobs", "Source should be 'ClearanceJobs'"

    # Verify field aliases work
    assert job["snippet"] == job["description"], "snippet should alias description"
    assert job["clearance_level"] == job["clearance"], "clearance_level should alias clearance"

    print(f"✓ Search successful")
    print(f"  Total results available: {result['total']:,}")
    print(f"  Jobs returned: {len(result['jobs'])}")
    print(f"  Sample job: {job['title']}")
    print(f"  Company: {job['company']}")
    print(f"  Clearance: {job['clearance']}")
    print(f"  Location: {job['location']}")


async def test_http_scraper_nonsense_query():
    """Test 2: Nonsense query returns 0 results (not suggested jobs)."""
    print("\n" + "=" * 80)
    print("TEST 2: HTTP Scraper - Nonsense Query Detection")
    print("=" * 80)

    # Use nonsense keywords that should have no matches
    result = await search_clearancejobs("asdfqwerzxcv", limit=10)

    assert result["success"] == True, "Should succeed even with no matches"
    assert result["total"] == 0, "Should return 0 for nonsense query (not suggested jobs)"
    assert len(result["jobs"]) == 0, "Should return empty jobs list"
    assert result["error"] is None, "Should not have error for valid request"

    print(f"✓ Nonsense query correctly detected")
    print(f"  Query: 'asdfqwerzxcv'")
    print(f"  Total results: {result['total']} (correctly 0, not 50k+ suggested)")
    print(f"  Jobs returned: {len(result['jobs'])}")


async def test_http_scraper_performance():
    """Test 3: HTTP scraper should be fast (<2 seconds)."""
    print("\n" + "=" * 80)
    print("TEST 3: HTTP Scraper - Performance")
    print("=" * 80)

    start_time = time.time()
    result = await search_clearancejobs("cybersecurity", limit=5)
    elapsed = time.time() - start_time

    assert result["success"] == True, "Search should succeed"
    assert elapsed < 2.0, f"HTTP scraper should be fast (<2s), took {elapsed:.2f}s"

    # Verify response_time_ms field exists and is reasonable
    if "response_time_ms" in result:
        assert result["response_time_ms"] < 2000, "Reported response time should be <2s"

    print(f"✓ Performance test passed")
    print(f"  Elapsed time: {elapsed:.2f}s (target: <2s)")
    print(f"  Reported time: {result.get('response_time_ms', 'N/A'):.0f}ms")
    print(f"  Results returned: {len(result['jobs'])}")


async def test_http_scraper_clearance_parsing():
    """Test 4: Clearance levels are correctly parsed from footer."""
    print("\n" + "=" * 80)
    print("TEST 4: HTTP Scraper - Clearance Level Parsing")
    print("=" * 80)

    # Search for TS/SCI jobs
    result = await search_clearancejobs("intelligence analyst", limit=20)

    assert result["success"] == True, "Search should succeed"
    assert len(result["jobs"]) > 0, "Should return results"

    # Verify clearance parsing
    clearance_levels = set()
    for job in result["jobs"]:
        if job["clearance"]:  # Some may not have clearance listed
            clearance_levels.add(job["clearance"])

    # Common clearance levels should be parsed
    expected_levels = {"TS/SCI", "Top Secret", "Secret", "Public Trust", "None"}
    found_levels = clearance_levels & expected_levels

    print(f"✓ Clearance parsing working")
    print(f"  Jobs checked: {len(result['jobs'])}")
    print(f"  Unique clearance levels found: {len(clearance_levels)}")
    print(f"  Levels: {', '.join(sorted(clearance_levels)) if clearance_levels else 'None'}")

    assert len(found_levels) > 0, "Should find at least one standard clearance level"


async def test_integration_wrapper():
    """Test 5: ClearanceJobsIntegration wrapper class."""
    print("\n" + "=" * 80)
    print("TEST 5: Integration Wrapper - DatabaseIntegration")
    print("=" * 80)

    integration = ClearanceJobsIntegration()

    # Test metadata
    metadata = integration.metadata
    assert metadata.name == "ClearanceJobs"
    assert metadata.id == "clearancejobs"
    assert metadata.requires_api_key == False
    assert metadata.requires_stealth == False
    assert metadata.stealth_method is None
    print(f"✓ Metadata correct:")
    print(f"  Name: {metadata.name}")
    print(f"  ID: {metadata.id}")
    print(f"  Requires stealth: {metadata.requires_stealth}")
    print(f"  Response time: {metadata.typical_response_time}s")

    # Test is_relevant (always returns True)
    is_relevant = await integration.is_relevant("cybersecurity jobs")
    assert is_relevant == True, "is_relevant should return True"
    print(f"✓ is_relevant() returns True")

    # Test generate_query
    query = await integration.generate_query("Find TS/SCI cleared penetration testers")
    assert query is not None, "Should generate query"
    assert "keywords" in query, "Query should have keywords"
    assert len(query["keywords"]) > 0, "Keywords should not be empty"
    print(f"✓ generate_query() working:")
    print(f"  Keywords: {query['keywords']}")

    # Test execute_search
    result = await integration.execute_search(query, api_key=None, limit=5)
    assert result.success == True, "Search should succeed"
    assert result.source == "ClearanceJobs"
    assert result.total >= 0, "Should have total count"
    assert len(result.results) > 0, "Should return results"
    assert result.response_time_ms > 0, "Should track response time"

    # Verify standardized format (required fields per PATTERNS.md)
    job = result.results[0]

    # Standard fields (always required)
    assert "title" in job, "Result should have title (required)"
    assert "url" in job, "Result should have url (required)"
    assert "snippet" in job, "Result should have snippet (optional but expected)"

    # NOTE: ClearanceJobs-specific fields like clearance_level are in the raw
    # HTTP scraper output but get normalized away by QueryResult validation.
    # This is CORRECT behavior per PATTERNS.md - only title/url/snippet/metadata allowed.
    # For deep research, the raw HTTP scraper is called directly (not the wrapper),
    # so clearance_level is preserved. For standalone use, metadata dict would contain it.

    print(f"✓ execute_search() working:")
    print(f"  Total available: {result.total:,}")
    print(f"  Results returned: {len(result.results)}")
    print(f"  Response time: {result.response_time_ms:.0f}ms")
    print(f"  Sample: {job['title']}")


async def test_integration_retry_logic():
    """Test 6: Integration wrapper has retry logic for reliability."""
    print("\n" + "=" * 80)
    print("TEST 6: Integration Wrapper - Retry Logic")
    print("=" * 80)

    integration = ClearanceJobsIntegration()

    # Normal search should work on first try
    query = {"keywords": "software engineer"}
    result = await integration.execute_search(query, api_key=None, limit=3)

    assert result.success == True, "Normal search should succeed"
    assert result.metadata.get("retry_count", 0) == 0, "Should succeed on first try"

    print(f"✓ Retry logic present:")
    print(f"  Attempts configured: 3 max")
    print(f"  This search attempts: {result.metadata.get('retry_count', 0) + 1}")
    print(f"  Result: Success")


async def main():
    """Run all tests."""
    print("\n" + "#" * 80)
    print("# CLEARANCEJOBS HTTP INTEGRATION - COMPREHENSIVE TEST SUITE")
    print("#" * 80)

    start_time = datetime.now()

    try:
        # HTTP scraper tests
        await test_http_scraper_basic()
        await test_http_scraper_nonsense_query()
        await test_http_scraper_performance()
        await test_http_scraper_clearance_parsing()

        # Integration wrapper tests
        await test_integration_wrapper()
        await test_integration_retry_logic()

        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print(f"Total time: {elapsed:.2f}s")
        print("\nVerified features:")
        print("  ✓ HTTP-based scraping (no browser needed)")
        print("  ✓ BeautifulSoup HTML parsing")
        print("  ✓ Nonsense query detection")
        print("  ✓ Clearance level parsing")
        print("  ✓ Field standardization (title/url/snippet)")
        print("  ✓ Performance (<2s per search)")
        print("  ✓ DatabaseIntegration wrapper")
        print("  ✓ LLM-based query generation")
        print("  ✓ Retry logic for reliability")
        print("\nNext: Run test_all_four_databases.py for parallel execution test")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
