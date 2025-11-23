#!/usr/bin/env python3
"""
Live test for Discord integration.

Tests Discord integration with local file search to verify:
- Relevance checking works
- Query generation works
- Discord messages are retrieved from exports
- Results are properly formatted
- Local file search works
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.social.discord_integration import DiscordIntegration


async def main():
    print("Testing Discord Integration...")
    print("=" * 80)

    integration = DiscordIntegration()

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
        ("What are OSINT experts saying about Ukraine?", True),
        ("What discussions are happening in defense communities?", True),
        ("What contracts does Lockheed have?", False),  # Should use SAM.gov
        ("What are Tesla's financial results?", False),  # Should use SEC EDGAR
    ]

    for question, expected in test_questions:
        relevant = await integration.is_relevant(question)
        status = "✅" if relevant == expected else "❌"
        print(f"{status} '{question}' → {relevant} (expected {expected})")

    # Test 3: Query Generation
    print("\n[TEST 3] Query Generation")
    print("-" * 80)

    test_query = "What are OSINT communities saying about satellite imagery?"
    print(f"Question: {test_query}")

    query_params = await integration.generate_query(test_query)

    if query_params:
        print(f"✅ Query generated:")
        print(f"   Keywords: {query_params.get('keywords')}")
        print(f"   Channels: {query_params.get('channels')}")
        print(f"   Date Range Days: {query_params.get('date_range_days')}")
    else:
        print("❌ Query generation returned None (not relevant)")

    # Test 4: Execute Search
    print("\n[TEST 4] Execute Search (OSINT satellite discussions)")
    print("-" * 80)
    print("NOTE: Searches local Discord export files in data/discord/")

    search_params = {
        "keywords": ["satellite", "imagery", "OSINT"],
        "channels": [],
        "date_range_days": 90,
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
        print(f"\nFirst 3 Discord Messages:")
        for i, doc in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {doc.get('title')}")
            print(f"     Channel: {doc.get('metadata', {}).get('channel')}")
            print(f"     Author: {doc.get('metadata', {}).get('author')}")
            print(f"     Date: {doc.get('date')}")
            print(f"     Snippet: {doc.get('snippet', '')[:150]}...")
    else:
        print("ℹ️  No results found - this requires Discord exports in data/discord/")

    print("\n" + "=" * 80)
    print("Discord Integration Test Complete!")
    print("\nNOTE: Discord characteristics:")
    print("- Completely FREE, no API key required")
    print("- Searches local Discord export files")
    print("- Requires Discord exports in data/discord/")
    print("- Very fast (local file search)")


if __name__ == "__main__":
    asyncio.run(main())
