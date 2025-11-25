#!/usr/bin/env python3
"""
Test Telegram integration with live API.

FIRST RUN ONLY: This will prompt for an SMS code sent to your phone.
After first authentication, a session file is saved and no SMS code is needed.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from integrations.social.telegram_integration import TelegramIntegration


async def test_telegram_channel_messages():
    """Test getting messages from Bellingcat's Telegram channel."""
    print("\n" + "="*80)
    print("TEST 1: Get messages from @bellingcat channel")
    print("="*80)

    integration = TelegramIntegration()

    # Check relevance
    question = "What is Bellingcat saying about Ukraine?"
    print(f"\nQuestion: {question}")

    is_relevant = await integration.is_relevant(question)
    print(f"Is relevant: {is_relevant}")

    if not is_relevant:
        print("⚠️  Telegram not relevant for this query")
        return

    # Generate query
    print("\nGenerating query parameters...")
    query_params = await integration.generate_query(question)

    if not query_params:
        print("❌ Query generation failed")
        return

    print(f"Pattern: {query_params.get('pattern')}")
    print(f"Params: {query_params.get('params')}")
    print(f"Reasoning: {query_params.get('reasoning')}")

    # Execute search
    print("\nExecuting search (this will authenticate on first run)...")
    result = await integration.execute_search(
        query_params=query_params,
        api_key=None,
        limit=5
    )

    # Display results
    if result.success:
        print(f"\n✅ SUCCESS: Got {result.total} results")
        for i, item in enumerate(result.results[:3], 1):
            print(f"\n[Result {i}]")
            print(f"  Title: {item['title'][:100]}")
            print(f"  URL: {item.get('url', 'N/A')}")
            print(f"  Date: {item.get('date', 'N/A')}")
    else:
        print(f"\n❌ FAILED: {result.error}")


async def test_telegram_channel_search():
    """Test searching for OSINT-related channels."""
    print("\n" + "="*80)
    print("TEST 2: Search for OSINT channels")
    print("="*80)

    integration = TelegramIntegration()

    query_params = {
        "pattern": "channel_search",
        "params": {
            "query": "OSINT intelligence",
            "limit": 5
        },
        "reasoning": "Finding OSINT-focused channels"
    }

    print(f"Pattern: {query_params['pattern']}")
    print(f"Query: {query_params['params']['query']}")

    result = await integration.execute_search(
        query_params=query_params,
        api_key=None,
        limit=5
    )

    if result.success:
        print(f"\n✅ SUCCESS: Found {result.total} channels")
        for i, item in enumerate(result.results, 1):
            print(f"\n[Channel {i}]")
            print(f"  Title: {item['title']}")
            print(f"  URL: {item.get('url', 'N/A')}")
            print(f"  Members: {item.get('metadata', {}).get('members', 'Unknown')}")
    else:
        print(f"\n❌ FAILED: {result.error}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TELEGRAM INTEGRATION TEST SUITE")
    print("="*80)
    print("\nNOTE: First run will prompt for SMS code sent to your phone.")
    print("After authentication, a session file is saved for future use.")
    print("\nPress Ctrl+C to cancel if you don't want to authenticate now.")
    print("="*80)

    try:
        await test_telegram_channel_messages()
        print("\n" + "-"*80)
        await test_telegram_channel_search()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETE")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
