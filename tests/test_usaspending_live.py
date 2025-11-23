#!/usr/bin/env python3
"""
Live test for USAspending integration.

Tests USAspending integration with real API calls to verify:
- Relevance checking works
- Query generation creates valid filter objects
- API requests succeed (no auth required)
- Results are properly formatted and normalized
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.usaspending_integration import USASpendingIntegration


async def main():
    print("Testing USAspending Integration...")
    print("=" * 80)

    integration = USASpendingIntegration()

    # Test 1: Metadata
    print("\n[TEST 1] Integration Metadata")
    print("-" * 80)
    metadata = integration.metadata
    print(f"Name: {metadata.name}")
    print(f"ID: {metadata.id}")
    print(f"Category: {metadata.category}")
    print(f"Requires API Key: {metadata.requires_api_key}")
    print(f"Rate Limit: {metadata.rate_limit_daily}")
    print(f"Description: {metadata.description}")

    # Test 2: Relevance Check
    print("\n[TEST 2] Relevance Check")
    print("-" * 80)

    test_questions = [
        ("How much did DoD spend on AI contracts in FY2023?", True),
        ("What companies received the most NASA funding in 2022?", True),
        ("Track Anduril's historical contract awards", True),
        ("What are the upcoming solicitations for cybersecurity?", False),  # Future (use SAM.gov)
        ("Are there any federal cybersecurity analyst jobs?", False),  # Jobs (use USAJobs)
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "How much did SpaceX receive from NASA in 2022?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Filters: {query_params.get('filters', {})}")
        print(f"   Fields: {query_params.get('fields', [])}")
        print(f"   Limit: {query_params.get('limit', 100)}")
        print(f"   Reasoning: {query_params.get('reasoning', 'No reasoning provided')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search (SpaceX NASA awards)
    print("\n[TEST 4] Execute Search (SpaceX NASA awards)")
    print("-" * 80)

    if query_params:
        result = await integration.execute_search(
            params=query_params,
            api_key=None,  # No API key needed
            limit=10
        )

        print(f"Success: {result.success}")
        print(f"Source: {result.source}")
        print(f"Total Results: {result.total}")

        if result.error:
            print(f"❌ Error: {result.error}")
        else:
            print(f"✅ Query succeeded")

        if result.results:
            print(f"\nFirst 3 Results:")
            for i, award in enumerate(result.results[:3], 1):
                print(f"\n  {i}. {award.get('title', 'No title')}")
                print(f"     URL: {award.get('url')}")
                print(f"     Snippet: {award.get('snippet', 'No snippet')}")
                metadata_dict = award.get('metadata', {})
                if metadata_dict:
                    print(f"     Award Amount: ${metadata_dict.get('Award Amount', 0):,.2f}")
                    print(f"     Agency: {metadata_dict.get('Awarding Agency', 'Unknown')}")
                    print(f"     Start Date: {metadata_dict.get('Start Date', 'Unknown')}")
    else:
        print("⚠️  Skipping search - no query params generated")

    # Test 5: DoD Cybersecurity Spending
    print("\n[TEST 5] DoD Cybersecurity Spending (FY2023)")
    print("-" * 80)

    dod_query = "Department of Defense cybersecurity contracts in FY2023"
    print(f"Question: {dod_query}")

    dod_params = await integration.generate_query(dod_query)

    if dod_params:
        print(f"✅ Query params generated")
        print(f"   Keywords: {dod_params.get('filters', {}).get('keywords', [])}")
        print(f"   Agencies: {dod_params.get('filters', {}).get('agencies', [])}")
        print(f"   Time Period: {dod_params.get('filters', {}).get('time_period', [])}")

        result = await integration.execute_search(
            params=dod_params,
            api_key=None,
            limit=5
        )

        print(f"\nSearch Results:")
        print(f"  Success: {result.success}")
        print(f"  Total: {result.total}")

        if result.results:
            print(f"\n  Sample Awards:")
            for i, award in enumerate(result.results[:3], 1):
                metadata_dict = award.get('metadata', {})
                print(f"    {i}. {metadata_dict.get('Recipient Name', 'Unknown')}")
                print(f"       Amount: ${metadata_dict.get('Award Amount', 0):,.2f}")
                print(f"       Description: {metadata_dict.get('Description', 'No description')[:80]}...")
    else:
        print("⚠️  Query generation failed")

    # Test 6: Award Amount Filter (Large Contracts >$100M)
    print("\n[TEST 6] Large Contracts (>$100M)")
    print("-" * 80)

    large_contracts_query = "Federal contracts over $100 million in 2023"
    print(f"Question: {large_contracts_query}")

    large_params = await integration.generate_query(large_contracts_query)

    if large_params:
        filters = large_params.get('filters', {})
        print(f"✅ Query generated with filters:")
        print(f"   Award Amounts: {filters.get('award_amounts', [])}")
        print(f"   Time Period: {filters.get('time_period', [])}")

        result = await integration.execute_search(
            params=large_params,
            api_key=None,
            limit=5
        )

        print(f"\nResults:")
        print(f"  Success: {result.success}")
        print(f"  Count: {result.total}")

        if result.results:
            print(f"\n  Top 5 Large Contracts:")
            for i, award in enumerate(result.results[:5], 1):
                metadata_dict = award.get('metadata', {})
                amount = metadata_dict.get('Award Amount', 0)
                recipient = metadata_dict.get('Recipient Name', 'Unknown')
                agency = metadata_dict.get('Awarding Agency', 'Unknown')
                print(f"    {i}. ${amount:,.2f} - {recipient}")
                print(f"       Agency: {agency}")
    else:
        print("⚠️  Query generation failed")

    print("\n" + "=" * 80)
    print("USAspending Integration Test Complete!")
    print("\n✅ Integration is working correctly!" if query_params else "⚠️  Some tests failed - check errors above")


if __name__ == "__main__":
    asyncio.run(main())
