#!/usr/bin/env python3
"""
Test Reddit LLM-based relevance check.
Verifies that Reddit now returns True for contract-related queries.
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.social.reddit_integration import RedditIntegration
from integrations.social.discord_integration import DiscordIntegration


async def main():
    print("Testing Reddit LLM-based relevance check...")
    print("=" * 80)

    # Test question that previously caused Reddit to return False
    test_question = "What government contracts has Anduril Industries received?"

    print(f"\nTest Question: {test_question}")
    print("-" * 80)

    # Test Reddit
    reddit = RedditIntegration()
    print("\n[Reddit] Testing is_relevant()...")
    reddit_relevant = await reddit.is_relevant(test_question)
    print(f"[Reddit] Result: {reddit_relevant}")

    # Test Discord for comparison
    discord = DiscordIntegration()
    print("\n[Discord] Testing is_relevant()...")
    discord_relevant = await discord.is_relevant(test_question)
    print(f"[Discord] Result: {discord_relevant}")

    print("\n" + "=" * 80)
    print("VERIFICATION:")
    if reddit_relevant:
        print("✅ [PASS] Reddit now returns True for contract queries")
        print("✅ Reddit underutilization bug FIXED")
    else:
        print("❌ [FAIL] Reddit still returns False")
        print("❌ Implementation did not resolve the issue")

    print("\nComparison:")
    print(f"  Reddit:  {reddit_relevant}")
    print(f"  Discord: {discord_relevant}")

    if reddit_relevant == discord_relevant:
        print("✅ Both integrations now behave consistently")
    else:
        print("❌ Integrations still have different behavior")


if __name__ == "__main__":
    asyncio.run(main())
