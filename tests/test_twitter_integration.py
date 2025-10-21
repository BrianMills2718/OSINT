#!/usr/bin/env python3
"""
Phase 3: TwitterIntegration End-to-End Testing

Tests all 4 methods of TwitterIntegration:
1. metadata
2. is_relevant
3. generate_query
4. execute_search
"""

import asyncio
from integrations.social.twitter_integration import TwitterIntegration
from dotenv import load_dotenv
import os

load_dotenv()

async def test_twitter_integration():
    print("=" * 80)
    print("TWITTER INTEGRATION - COMPREHENSIVE TEST")
    print("=" * 80)

    integration = TwitterIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Metadata")
    print("-" * 80)
    meta = integration.metadata
    print(f"✅ Name: {meta.name}")
    print(f"✅ ID: {meta.id}")
    print(f"✅ Category: {meta.category.value}")
    print(f"✅ Requires API key: {meta.requires_api_key}")
    print(f"✅ Cost estimate: ${meta.cost_per_query_estimate}")
    print(f"✅ Response time: {meta.typical_response_time}s")

    assert meta.id == "twitter", "ID should be 'twitter'"
    assert meta.requires_api_key == True, "Should require API key"

    # Test 2: is_relevant
    print("\n[TEST 2] Relevance Detection")
    print("-" * 80)

    relevant_questions = [
        "What's trending on Twitter about JTTF?",
        "Recent social media discussions about counterterrorism",
        "Twitter sentiment about FBI hiring"
    ]

    irrelevant_questions = [
        "Federal contracting opportunities in Virginia",
        "USAJobs positions requiring TS/SCI clearance"
    ]

    print("Testing relevant questions:")
    for q in relevant_questions:
        result = await integration.is_relevant(q)
        status = "✅" if result else "❌"
        print(f"  {status} '{q[:50]}...' -> {result}")
        assert result == True, f"Should be relevant: {q}"

    print("\nTesting irrelevant questions:")
    for q in irrelevant_questions:
        result = await integration.is_relevant(q)
        status = "✅" if not result else "❌"
        print(f"  {status} '{q[:50]}...' -> {result}")
        assert result == False, f"Should NOT be relevant: {q}"

    # Test 3: generate_query
    print("\n[TEST 3] LLM Query Generation")
    print("-" * 80)

    # Test with keyword (Boolean monitor style)
    print("Testing with simple keyword (Boolean monitor style):")
    keyword_result = await integration.generate_query("JTTF")
    print(f"  Input: 'JTTF'")
    print(f"  ✅ Query: {keyword_result['query']}")
    print(f"  ✅ Search type: {keyword_result['search_type']}")
    print(f"  ✅ Max pages: {keyword_result['max_pages']}")
    print(f"  ✅ Reasoning: {keyword_result['reasoning']}")

    assert keyword_result['query'] == "JTTF", "Should use keyword directly"
    assert keyword_result['search_type'] in ["Latest", "Top", "Media", "People"], "Invalid search_type"

    # Test with full research question
    print("\nTesting with full research question (AI Research style):")
    full_result = await integration.generate_query(
        "Recent Twitter discussions about JTTF and counterterrorism operations"
    )
    print(f"  Input: 'Recent Twitter discussions about JTTF and counterterrorism operations'")
    print(f"  ✅ Query: {full_result['query']}")
    print(f"  ✅ Search type: {full_result['search_type']}")
    print(f"  ✅ Max pages: {full_result['max_pages']}")
    print(f"  ✅ Reasoning: {full_result['reasoning']}")

    assert full_result['query'] != "", "Query should not be empty"
    assert full_result['search_type'] in ["Latest", "Top", "Media", "People"], "Invalid search_type"
    assert 1 <= full_result['max_pages'] <= 5, "Max pages should be 1-5"

    # Test irrelevant question (should return None)
    print("\nTesting with irrelevant question:")
    irrelevant_result = await integration.generate_query(
        "Federal contracting opportunities in Virginia"
    )
    print(f"  Input: 'Federal contracting opportunities in Virginia'")
    print(f"  ✅ Result: {irrelevant_result}")

    assert irrelevant_result is None, "Should return None for irrelevant question"

    # Test 4: execute_search
    print("\n[TEST 4] API Execution (Real Twitter Search)")
    print("-" * 80)

    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("❌ RAPIDAPI_KEY not found, skipping API test")
        return

    # Use a simple, guaranteed-results query
    test_query_params = {
        "query": "python programming",
        "search_type": "Latest",
        "max_pages": 1,
        "reasoning": "Test search"
    }

    print(f"Executing search with params: {test_query_params}")
    print("(This will make a real API call, ~3 seconds)")

    result = await integration.execute_search(test_query_params, api_key, limit=5)

    print(f"\n✅ Success: {result.success}")
    print(f"✅ Source: {result.source}")
    print(f"✅ Total results: {result.total}")
    print(f"✅ Results returned: {len(result.results)}")
    print(f"✅ Response time: {result.response_time_ms:.0f}ms")

    assert result.success == True, "Search should succeed"
    assert result.source == "Twitter", "Source should be Twitter"
    assert len(result.results) > 0, "Should return at least 1 result"

    # Verify field mapping
    print("\n[TEST 5] Field Mapping Validation")
    print("-" * 80)

    if result.results:
        first_result = result.results[0]
        required_fields = ["title", "url", "date", "description", "author"]

        print("Checking required SIGINT common fields:")
        for field in required_fields:
            value = first_result.get(field)
            status = "✅" if value else "❌"
            print(f"  {status} {field}: {'Present' if value else 'MISSING'}")
            assert value, f"Required field '{field}' is missing"

        # Verify URL format
        url = first_result.get("url", "")
        assert "twitter.com" in url, f"URL should contain twitter.com: {url}"
        print(f"\n✅ URL format valid: {url}")

        # Show sample tweet
        print(f"\nSample Tweet:")
        print(f"  Author: @{first_result.get('author')}")
        print(f"  Text: {first_result.get('title')}")
        print(f"  Date: {first_result.get('date')}")
        print(f"  Engagement: {first_result.get('favorites', 0)} likes, {first_result.get('retweets', 0)} RTs")
        print(f"  URL: {first_result.get('url')}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - TWITTER INTEGRATION READY")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Test via AI Research: python3 apps/ai_research.py \"Twitter JTTF activity\"")
    print("  2. Update STATUS.md with [PASS]")
    print("  3. Update REGISTRY_COMPLETE.md")
    print("  4. Update CLAUDE.md")

if __name__ == "__main__":
    asyncio.run(test_twitter_integration())
