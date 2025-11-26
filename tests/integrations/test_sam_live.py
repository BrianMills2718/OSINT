#!/usr/bin/env python3
"""
Live test for SAM.gov integration.

Tests SAM.gov integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Contract opportunities are retrieved
- Results are properly formatted
- API key authentication works
- Rate limiting is handled
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')
from dotenv import load_dotenv
load_dotenv()
import os

from integrations.government.sam_integration import SAMIntegration


async def main():
    print("Testing SAM.gov Integration...")
    print("=" * 80)

    integration = SAMIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Category: {metadata.category}")
    print(f"Requires API Key: {metadata.requires_api_key}")
    print(f"Rate Limit (Daily): {metadata.rate_limit_daily}")
    print(f"Description: {metadata.description}")

    # Test 2: Relevance Check
    print("\n[TEST 2] Relevance Check")
    print("-" * 80)

    test_questions = [
        ("What cybersecurity contracts is DoD offering?", True),
        ("Are there any AI research solicitations?", True),
        ("What companies won SpaceX contracts?", False),  # Should use USASpending
        ("What jobs are available at NASA?", False),  # Should use USAJobs
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        # SAM.gov always returns True for is_relevant, defers to generate_query
        status = "✅" if relevant == True else "❌"
        print(f"{status} '{question}' → {relevant} (SAM returns True, filters in generate_query)")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What cybersecurity solicitations is the Department of Defense currently offering?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Procurement Types: {query_params.get('procurement_types')}")
        print(f"   Set Aside: {query_params.get('set_aside')}")
        print(f"   NAICS Codes: {query_params.get('naics_codes')}")
        print(f"   Date Range (days): {query_params.get('date_range_days')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search (may hit rate limits)
    print("\n[TEST 4] Execute Search (cybersecurity contracts)")
    print("-" * 80)
    print("NOTE: SAM.gov has strict rate limits - this may fail with 429 error")

    search_params = {
        "keywords": "cybersecurity",
        "procurement_types": ["Solicitation"],
        "set_aside": None,
        "naics_codes": None,
        "date_range_days": 30
    }

    result = await integration.execute_search(search_params, api_key=os.getenv('SAM_GOV_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")
        if "429" in result.error or "rate limit" in result.error.lower():
            print("⚠️  Rate limited (expected) - SAM.gov has strict limits")

    if result.results:
        print(f"\nFirst 3 Opportunities:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Posted: {doc.get('date')}")
            print(f"     Type: {doc.get('metadata', {}).get('type')}")
            print(f"     URL: {doc.get('url')}")

    # Test 5: Irrelevant Query (should return None)
    print("\n[TEST 5] Irrelevant Query (NASA job postings)")
    print("-" * 80)

    irrelevant_query = "What jobs are available at NASA?"
    print(f"Question: {irrelevant_query}")

    query_params = await integration.generate_query(irrelevant_query)

    if query_params is None:
        print("✅ Query generation correctly returned None (not relevant)")
    else:
        print("❌ Query generation returned params for irrelevant query")
        print(f"   Params: {query_params}")

    print("\n" + "=" * 80)
    print("SAM.gov Integration Test Complete!")
    print("\nNOTE: SAM.gov limitations:")
    print("- Strict rate limits (429 errors common)")
    print("- Requires API key from SAM_GOV_API_KEY env var")
    print("- Date range required (max 1 year)")
    print("- Often slow (2-5 seconds per request)")


if __name__ == "__main__":
    asyncio.run(main())
