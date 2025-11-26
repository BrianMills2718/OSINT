#!/usr/bin/env python3
"""
Live test for USAJobs integration.

Tests USAJobs integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Federal job postings are retrieved
- Results are properly formatted
- API key authentication works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')
from dotenv import load_dotenv
load_dotenv()
import os

from integrations.government.usajobs_integration import USAJobsIntegration


async def main():
    print("Testing USAJobs Integration...")
    print("=" * 80)

    integration = USAJobsIntegration()

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
        ("What cybersecurity jobs are available at NASA?", True),
        ("Are there any AI research positions at DoD?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What is the latest news?", False),  # Should use NewsAPI
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What cybersecurity analyst jobs are available at NASA?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Organization: {query_params.get('organization')}")
        print(f"   Location: {query_params.get('location')}")
        print(f"   Limit: {query_params.get('limit')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (cybersecurity jobs)")
    print("-" * 80)

    search_params = {
        "keywords": "cybersecurity",
        "organization": None,
        "location": None,
        "limit": 5
    }

    result = await integration.execute_search(search_params, api_key=os.getenv('USAJOBS_API_KEY'), limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Job Postings:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Agency: {doc.get('metadata', {}).get('agency')}")
            print(f"     Location: {doc.get('metadata', {}).get('location')}")
            print(f"     Salary: {doc.get('metadata', {}).get('salary')}")
            print(f"     URL: {doc.get('url')}")

    # Test 5: NASA-specific Search
    print("\n[TEST 5] NASA Job Search")
    print("-" * 80)

    nasa_params = {
        "keywords": "engineer",
        "organization": "National Aeronautics and Space Administration",
        "location": None,
        "limit": 3
    }

    result = await integration.execute_search(nasa_params, api_key=os.getenv('USAJOBS_API_KEY'), limit=3)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nNASA Engineering Jobs:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')}")
            print(f"     {doc.get('metadata', {}).get('agency')}")

    print("\n" + "=" * 80)
    print("USAJobs Integration Test Complete!")
    print("\nNOTE: USAJobs requirements:")
    print("- Requires API key from USAJOBS_API_KEY env var")
    print("- Requires User-Agent header with email")
    print("- Fast API (typically <1 second)")


if __name__ == "__main__":
    asyncio.run(main())
