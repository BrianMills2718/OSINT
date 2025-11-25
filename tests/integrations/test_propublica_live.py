#!/usr/bin/env python3
"""
Live test for ProPublica Nonprofit Explorer integration.

Tests ProPublica integration with real API calls to verify:
- Relevance checking works
- Query generation works
- Nonprofit financial data is retrieved
- Results are properly formatted
- Free API access works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.nonprofit.propublica_integration import ProPublicaIntegration


async def main():
    print("Testing ProPublica Nonprofit Explorer Integration...")
    print("=" * 80)

    integration = ProPublicaIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Category: {metadata.category}")
    print(f"Requires API Key: {metadata.requires_api_key}")
    print(f"Description: {metadata.description}")

    # Test 2: Relevance Check
    print("\n[TEST 2] Relevance Check")
    print("-" * 80)

    test_questions = [
        ("What dark money groups are spending on elections?", True),
        ("How much does the Red Cross CEO make?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What are recent EPA regulations?", False),  # Should use Federal Register
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What political dark money groups are operating in New York?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Search query: {query_params.get('q')}")
        print(f"   State: {query_params.get('state_id')}")
        print(f"   NTEE category: {query_params.get('ntee_id')}")
        print(f"   Tax code: {query_params.get('c_code_id')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search - Dark Money
    print("\n[TEST 4] Execute Search (Political Nonprofits)")
    print("-" * 80)

    search_params = {
        "q": "political",
        "state_id": None,
        "ntee_id": 7,  # Public, Societal Benefit
        "c_code_id": 4  # 501(c)(4) - dark money groups
    }

    result = await integration.execute_search(search_params, api_key=None, limit=5)

    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.error:
        print(f"Error: {result.error}")

    if result.results:
        print(f"\nFirst 3 Nonprofits:")
        for i, org in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {org.get('title')}")
            print(f"     Location: {org.get('metadata', {}).get('city')}, {org.get('metadata', {}).get('state')}")
            print(f"     Tax Code: {org.get('metadata', {}).get('tax_code')}")
            revenue = org.get('metadata', {}).get('revenue_amount')
            if revenue:
                print(f"     Revenue: ${revenue:,}")
            print(f"     URL: {org.get('url')}")

    # Test 5: Execute Search - Foundations
    print("\n[TEST 5] Execute Search (Foundations)")
    print("-" * 80)

    search_params = {
        "q": "foundation",
        "state_id": None,
        "ntee_id": None,
        "c_code_id": 3  # 501(c)(3) - charitable organizations
    }

    result = await integration.execute_search(search_params, api_key=None, limit=3)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")
    print(f"Response Time: {result.response_time_ms}ms")

    if result.results:
        print(f"\nSample Foundations:")
        for org in result.results:
            print(f"  • {org.get('title')}")
            revenue = org.get('metadata', {}).get('revenue_amount')
            if revenue:
                print(f"    Revenue: ${revenue:,}")

    print("\n" + "=" * 80)
    print("ProPublica Nonprofit Explorer Integration Test Complete!")
    print("\nNOTE: ProPublica characteristics:")
    print("- Completely FREE, no API key required")
    print("- 1.8M+ IRS Form 990 filings")
    print("- Financial data, executive compensation, grants")
    print("- Perfect for investigating dark money, nonprofits, foundations")


if __name__ == "__main__":
    asyncio.run(main())
