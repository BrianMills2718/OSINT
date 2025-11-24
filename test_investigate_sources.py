#!/usr/bin/env python3
"""Quick investigation of Brave Search and Congress.gov 0 results."""

import asyncio
import os
from dotenv import load_dotenv

from integrations.social.brave_search_integration import BraveSearchIntegration
from integrations.government.congress_integration import CongressIntegration

load_dotenv()

async def test_brave_search():
    """Test Brave Search with GAO-related query."""
    print("=" * 80)
    print("BRAVE SEARCH TEST")
    print("=" * 80)

    brave = BraveSearchIntegration()

    # Test relevance
    question = "GAO reports on defense spending waste"
    is_relevant = await brave.is_relevant(question)
    print(f"Is relevant: {is_relevant}")

    # Generate query
    query_params = await brave.generate_query(question)
    print(f"\nGenerated query: {query_params}")

    if query_params:
        # Execute search
        api_key = os.getenv('BRAVE_SEARCH_API_KEY')
        if api_key:
            result = await brave.execute_search(query_params, api_key, limit=5)
            print(f"\nResult success: {result.success}")
            print(f"Total results: {result.total}")
            print(f"Returned: {len(result.results)}")
            if result.error:
                print(f"Error: {result.error}")
            if result.results:
                print(f"\nFirst result: {result.results[0].get('title', 'NO TITLE')[:80]}")
        else:
            print("\n✗ No BRAVE_SEARCH_API_KEY")
    print()


async def test_congress():
    """Test Congress.gov with GAO-related query."""
    print("=" * 80)
    print("CONGRESS.GOV TEST")
    print("=" * 80)

    congress = CongressIntegration()

    # Test relevance
    question = "GAO reports on defense spending waste"
    is_relevant = await congress.is_relevant(question)
    print(f"Is relevant: {is_relevant}")

    # Generate query
    query_params = await congress.generate_query(question)
    print(f"\nGenerated query: {query_params}")

    if query_params:
        # Execute search
        api_key = os.getenv('CONGRESS_API_KEY') or os.getenv('DATA_GOV_API_KEY')
        if api_key:
            result = await congress.execute_search(query_params, api_key, limit=5)
            print(f"\nResult success: {result.success}")
            print(f"Total results: {result.total}")
            print(f"Returned: {len(result.results)}")
            if result.error:
                print(f"Error: {result.error}")
            if result.results:
                print(f"\nFirst result: {result.results[0].get('title', 'NO TITLE')[:80]}")
        else:
            print("\n✗ No CONGRESS_API_KEY or DATA_GOV_API_KEY")
    print()


async def main():
    await test_brave_search()
    await test_congress()


if __name__ == "__main__":
    asyncio.run(main())
