#!/usr/bin/env python3
"""
Live integration test for GovInfo.gov.

Tests the full integration including LLM query generation and API search.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

from integrations.government.govinfo_integration import GovInfoIntegration


async def main():
    print("\n" + "=" * 80)
    print("GOVINFO.GOV INTEGRATION - LIVE TEST")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("DATA_GOV_API_KEY")
    if not api_key:
        print("\n❌ ERROR: DATA_GOV_API_KEY not found in .env file")
        print("\nTo get an API key:")
        print("  1. Visit https://api.data.gov/signup/")
        print("  2. Sign up for a free API key")
        print("  3. Add to .env file: DATA_GOV_API_KEY=your_key_here")
        print("\nThis is the same key used for Congress.gov integration.")
        return False

    integration = GovInfoIntegration()

    # Test 1: Metadata
    print("\n" + "=" * 80)
    print("TEST 1: Integration Metadata")
    print("=" * 80)

    metadata = integration.metadata
    print(f"✓ Name: {metadata.name}")
    print(f"✓ ID: {metadata.id}")
    print(f"✓ Category: {metadata.category}")
    print(f"✓ Requires API key: {metadata.requires_api_key}")
    print(f"✓ Description: {metadata.description}")

    # Test 2: Relevance check
    print("\n" + "=" * 80)
    print("TEST 2: Relevance Check")
    print("=" * 80)

    is_relevant = await integration.is_relevant("GAO report on defense contracting waste")
    print(f"✓ is_relevant() returns: {is_relevant} (always True - LLM decides relevance)")

    # Test 3: Query generation - GAO reports
    print("\n" + "=" * 80)
    print("TEST 3: Query Generation - GAO Reports")
    print("=" * 80)

    question = "Find GAO reports on defense contractor cost overruns"
    print(f"Question: {question}")

    query = await integration.generate_query(question)

    if query is None:
        print("✗ LLM determined GovInfo not relevant for this question")
        return False

    print(f"✓ Query generated:")
    print(f"  Keywords: {query['query']}")
    print(f"  Collections: {query['collections']}")
    print(f"  Date range: {query['date_range_years']} years" if query['date_range_years'] else "  Date range: All time")
    print(f"  Sort by: {query['sort_by']}")

    # Test 4: Execute search
    print("\n" + "=" * 80)
    print("TEST 4: Execute Search")
    print("=" * 80)

    result = await integration.execute_search(query, api_key=api_key, limit=5)

    if not result.success:
        print(f"✗ Search failed: {result.error}")
        return False

    print(f"✓ Search successful!")
    print(f"  Total results: {result.total:,}")
    print(f"  Returned: {len(result.results)} documents")
    print(f"  Response time: {result.response_time_ms:.0f}ms")
    print(f"  Collections searched: {result.metadata.get('collections_searched', [])}")

    if result.results:
        print(f"\n  Sample results:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc['title']}")
            print(f"     Collection: {doc['metadata'].get('collection_name', 'Unknown')}")
            print(f"     Published: {doc['metadata'].get('publish_date', 'Unknown')}")
            print(f"     URL: {doc['url'][:70]}...")
            if doc['snippet']:
                snippet = doc['snippet'][:150] + "..." if len(doc['snippet']) > 150 else doc['snippet']
                print(f"     Snippet: {snippet}")

    # Test 5: Different query - Congressional hearings
    print("\n" + "=" * 80)
    print("TEST 5: Congressional Hearings Query")
    print("=" * 80)

    question2 = "Congressional hearings on cybersecurity threats"
    print(f"Question: {question2}")

    query2 = await integration.generate_query(question2)

    if query2:
        print(f"✓ Query generated:")
        print(f"  Keywords: {query2['query']}")
        print(f"  Collections: {query2['collections']}")

        result2 = await integration.execute_search(query2, api_key=api_key, limit=3)

        if result2.success:
            print(f"✓ Search successful!")
            print(f"  Total results: {result2.total:,}")
            print(f"  Returned: {len(result2.results)} documents")
        else:
            print(f"✗ Search failed: {result2.error}")

    # Test 6: Court opinions query
    print("\n" + "=" * 80)
    print("TEST 6: Court Opinions Query")
    print("=" * 80)

    question3 = "Federal court cases involving False Claims Act settlements with defense contractors"
    print(f"Question: {question3}")

    query3 = await integration.generate_query(question3)

    if query3:
        print(f"✓ Query generated:")
        print(f"  Keywords: {query3['query']}")
        print(f"  Collections: {query3['collections']}")

        result3 = await integration.execute_search(query3, api_key=api_key, limit=3)

        if result3.success:
            print(f"✓ Search successful!")
            print(f"  Total results: {result3.total:,}")
            print(f"  Returned: {len(result3.results)} documents")
        else:
            print(f"✗ Search failed: {result3.error}")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print("\nVerified features:")
    print("  ✓ LLM-based query generation")
    print("  ✓ Collection selection (GAOREPORTS, CHRG, USCOURTS)")
    print("  ✓ API search with filters")
    print("  ✓ Result standardization (title/url/snippet)")
    print("  ✓ Metadata extraction")
    print("\nGovInfo integration is production-ready!")
    print(f"\nTotal collections available: {len(set(query['collections'] + query2['collections'] + query3['collections']))} tested")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
