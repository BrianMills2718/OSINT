#!/usr/bin/env python3
"""
Live test for SEC EDGAR integration.

Tests SEC EDGAR integration with real API calls to verify:
- CIK lookup works
- Company filings retrieval works
- User-Agent header is properly configured
- Results are properly formatted
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.government.sec_edgar_integration import SECEdgarIntegration


async def main():
    print("Testing SEC EDGAR Integration...")
    print("=" * 80)

    integration = SECEdgarIntegration()

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
        ("What were Apple's recent financial results?", True),
        ("Has the CEO of Tesla been selling stock?", True),
        ("What government contracts does Lockheed Martin have?", False),  # Should use SAM.gov
        ("Is SpaceX profitable?", False),  # Private company
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What were Apple's recent 10-K filings?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Type: {query_params.get('query_type')}")
        print(f"   Company: {query_params.get('company_name')}")
        print(f"   Forms: {query_params.get('form_types')}")
        print(f"   Limit: {query_params.get('limit')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: CIK Lookup
    print("\n[TEST 4] CIK Lookup")
    print("-" * 80)

    companies = ["Apple Inc", "Microsoft Corporation", "Tesla Inc"]

    for company in companies:
        cik = await integration._search_company_cik(company)
        if cik:
            print(f"✅ {company} → CIK: {cik}")
        else:
            print(f"❌ {company} → CIK not found")

    # Test 5: Execute Search
    print("\n[TEST 5] Execute Search (Apple 10-K filings)")
    print("-" * 80)

    search_params = {
        "query_type": "company_filings",
        "company_name": "Apple Inc",
        "form_types": ["10-K"],
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
        print(f"\nFirst 3 Results:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     URL: {doc.get('url')}")
            print(f"     Snippet: {doc.get('snippet')}")
            print(f"     Metadata: {doc.get('metadata', {}).get('form_type')} | "
                  f"{doc.get('metadata', {}).get('filing_date')}")

    # Test 6: Insider Trading (Form 4)
    print("\n[TEST 6] Insider Trading Search (Tesla Form 4)")
    print("-" * 80)

    insider_params = {
        "query_type": "company_filings",
        "company_name": "Tesla Inc",
        "form_types": ["4"],
        "limit": 3
    }

    result = await integration.execute_search(insider_params, api_key=None, limit=3)

    print(f"Success: {result.success}")
    print(f"Total Results: {result.total}")

    if result.results:
        print(f"\nInsider Transactions Found:")
        for i, doc in enumerate(result.results, 1):
            print(f"  {i}. {doc.get('title')}")
            print(f"     Date: {doc.get('date')}")

    print("\n" + "=" * 80)
    print("SEC EDGAR Integration Test Complete!")


if __name__ == "__main__":
    asyncio.run(main())
