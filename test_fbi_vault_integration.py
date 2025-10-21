#!/usr/bin/env python3
"""
Test FBI Vault integration with Cloudflare bypass.
"""

import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from integrations.government.fbi_vault import FBIVaultIntegration


async def test_fbi_vault():
    """Test FBI Vault integration end-to-end."""
    print("=" * 80)
    print("FBI VAULT INTEGRATION TEST (with Cloudflare bypass)")
    print("=" * 80)

    integration = FBIVaultIntegration()

    # Test query
    research_question = "domestic terrorism investigations"

    print(f"\nResearch Question: {research_question}")
    print(f"\nMetadata: {integration.metadata.name}")
    print(f"Category: {integration.metadata.category}")

    # Test relevance
    print("\nTesting relevance...")
    is_relevant = await integration.is_relevant(research_question)
    print(f"Is relevant: {is_relevant}")

    if not is_relevant:
        print("❌ Question not relevant to FBI Vault")
        return

    # Generate query
    print("\nGenerating query...")
    query_params = await integration.generate_query(research_question)
    print(f"Query parameters: {query_params}")

    if not query_params:
        print("❌ No query generated")
        return

    # Execute search
    print("\nExecuting search (this may take 10-15 seconds for Cloudflare bypass)...")
    result = await integration.execute_search(query_params, limit=5)

    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Success: {result.success}")
    print(f"Total results: {result.total}")
    print(f"Response time: {result.response_time_ms:.0f}ms")

    if result.error:
        print(f"❌ Error: {result.error}")
        return

    if result.success and result.results:
        print(f"\nFirst {min(len(result.results), 5)} results:")
        for i, item in enumerate(result.results[:5], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   URL: {item['url']}")
            print(f"   Type: {item['metadata']['document_type']}")
            if item.get('snippet'):
                snippet = item['snippet'][:200]
                print(f"   Snippet: {snippet}...")

        print(f"\n✅ FBI VAULT INTEGRATION WORKING with Cloudflare bypass!")
        print(f"   Scraping method: {result.metadata.get('scraping_method')}")
    else:
        print(f"\n⚠️ No results found")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_fbi_vault())
