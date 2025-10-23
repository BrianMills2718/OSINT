#!/usr/bin/env python3
"""Test Discord integration after fixing ANY-match bug."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.social.discord_integration import DiscordIntegration

async def test():
    print("=" * 60)
    print("Discord Test After ANY-Match Fix")
    print("=" * 60)

    integration = DiscordIntegration()

    # Test with SIGINT query (should find results now)
    query = "SIGINT signals intelligence"
    print(f"\nTest: {query}")

    query_params = await integration.generate_query(query)
    print(f"Query params: {query_params}")

    if query_params:
        result = await integration.execute_search(
            query_params=query_params,
            limit=10
        )
        print(f"Success: {result.success}")
        print(f"Total: {result.total}")

        if result.total > 0:
            print(f"\n✅ FIX WORKING - Found {result.total} results!")
            print(f"\nFirst 3 results:")
            for i, msg in enumerate(result.results[:3], 1):
                print(f"\n  Result {i}:")
                print(f"    Server: {msg.get('server')}")
                print(f"    Channel: {msg.get('channel')}")
                print(f"    Author: {msg.get('author')}")
                print(f"    Content: {msg.get('content')[:100]}...")
                print(f"    Matched keywords: {msg.get('matched_keywords')}")
                print(f"    Score: {msg.get('score'):.2f}")
        else:
            print(f"⚠️  Still 0 results - fix may not be working")
    else:
        print("❌ Query generation returned None (not relevant)")

if __name__ == "__main__":
    asyncio.run(test())
