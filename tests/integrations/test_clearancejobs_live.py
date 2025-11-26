#!/usr/bin/env python3
"""
Live test for ClearanceJobs integration.

Tests ClearanceJobs integration with real Playwright browser automation to verify:
- Relevance checking works
- Query generation works
- Clearance job postings are retrieved via browser automation
- Results are properly formatted
- Playwright automation works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')
from dotenv import load_dotenv
load_dotenv()

from integrations.government.clearancejobs_integration import ClearanceJobsIntegration


async def main():
    print("Testing ClearanceJobs Integration...")
    print("=" * 80)

    integration = ClearanceJobsIntegration()

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
        ("What Top Secret jobs are available in cybersecurity?", True),
        ("Are there any TS/SCI cleared positions at defense contractors?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What is NASA's budget?", False),  # Should use USASpending
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What Top Secret cybersecurity jobs are available?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Clearance Level: {query_params.get('clearance_level')}")
        print(f"   Location: {query_params.get('location')}")
        print(f"   Limit: {query_params.get('limit')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search (Playwright)
    print("\n[TEST 4] Execute Search (Top Secret cybersecurity jobs)")
    print("-" * 80)
    print("NOTE: This uses Playwright browser automation - may take 10-15 seconds")

    search_params = {
        "keywords": "cybersecurity",
        "clearance_level": "Top Secret",
        "location": None,
        "limit": 5
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Clearance Jobs:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Company: {doc.get('metadata', {}).get('company')}")
            print(f"     Clearance: {doc.get('metadata', {}).get('clearance')}")
            print(f"     Location: {doc.get('metadata', {}).get('location')}")
            print(f"     URL: {doc.get('url')}")

    print("\n" + "=" * 80)
    print("ClearanceJobs Integration Test Complete!")
    print("\nNOTE: ClearanceJobs characteristics:")
    print("- Uses Playwright browser automation (slower)")
    print("- No API key required")
    print("- Searches for jobs requiring security clearances")
    print("- Typical response time: 10-15 seconds")


if __name__ == "__main__":
    asyncio.run(main())
