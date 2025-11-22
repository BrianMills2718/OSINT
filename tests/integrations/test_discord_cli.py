#!/usr/bin/env python3
"""
Simple CLI test for Discord integration.
Tests the integration through the registry system.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from integrations.registry import registry
from dotenv import load_dotenv

load_dotenv()


async def test_discord_search(query: str):
    """Test Discord integration via registry."""

    print("="*80)
    print("DISCORD INTEGRATION TEST")
    print("="*80)
    print(f"Query: {query}")
    print()

    # Get Discord integration from registry
    discord_class = registry.get('discord')
    if not discord_class:
        print("❌ Discord integration not found in registry!")
        return

    print("✓ Discord integration found in registry")

    # Create instance
    discord = discord_class()

    # Show metadata
    print(f"\nMetadata:")
    print(f"  Name: {discord.metadata.name}")
    print(f"  ID: {discord.metadata.id}")
    print(f"  Category: {discord.metadata.category.value}")
    print(f"  Requires API key: {discord.metadata.requires_api_key}")
    print(f"  Exports directory: {discord.exports_dir}")
    print(f"  Exports exist: {discord.exports_dir.exists()}")

    # Check relevance
    print(f"\nChecking relevance...")
    is_relevant = await discord.is_relevant(query)
    print(f"  Relevant: {is_relevant}")

    if not is_relevant:
        print("  Query not relevant for Discord")
        return

    # Generate query
    print(f"\nGenerating query...")
    query_params = await discord.generate_query(query)
    if not query_params:
        print("  Could not generate query parameters")
        return

    print(f"  Query params: {query_params}")

    # Execute search
    print(f"\nExecuting search...")
    result = await discord.execute_search(query_params, limit=5)

    print(f"\nResults:")
    print(f"  Success: {result.success}")
    print(f"  Total: {result.total}")
    print(f"  Response time: {result.response_time_ms:.2f}ms")

    if result.error:
        print(f"  Error: {result.error}")

    if result.success and result.results:
        print(f"\n  First 3 results:")
        for i, msg in enumerate(result.results[:3], 1):
            print(f"\n  {i}. {msg.get('title', 'No title')}")
            print(f"     Server: {msg.get('server', 'Unknown')}")
            print(f"     Channel: {msg.get('channel', 'Unknown')}")
            print(f"     Author: {msg.get('author', 'Unknown')}")
            print(f"     Content: {msg.get('content', '')[:100]}...")
            print(f"     Matched keywords: {msg.get('matched_keywords', [])}")
            print(f"     Score: {msg.get('score', 0):.2f}")

    print("\n" + "="*80)
    if result.success and result.total > 0:
        print("✓ DISCORD INTEGRATION TEST PASSED")
    else:
        print("✗ DISCORD INTEGRATION TEST FAILED")
    print("="*80)


if __name__ == "__main__":
    # Default query
    query = "ukraine intelligence analysis"

    # Allow command-line override
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])

    asyncio.run(test_discord_search(query))
