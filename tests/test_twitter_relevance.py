#!/usr/bin/env python3
"""Test if Twitter now considers SIGINT relevant after prompt fix."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from integrations.social.twitter_integration import TwitterIntegration

async def test():
    load_dotenv()

    print("=" * 60)
    print("Twitter Relevance Test - SIGINT Query")
    print("=" * 60)

    integration = TwitterIntegration()

    query = "SIGINT signals intelligence"
    print(f"\nQuery: {query}")

    print(f"\n1. Testing generate_query()...")
    query_params = await integration.generate_query(query)

    if not query_params:
        print(f"   ❌ FAILED: LLM returned None (marked not relevant)")
        print(f"   This means the prompt fix didn't work")
        return False

    print(f"   ✅ PASSED: LLM generated query params")
    print(f"   Query: {query_params.get('query')}")
    print(f"   Search type: {query_params.get('search_type')}")
    print(f"   Max pages: {query_params.get('max_pages')}")
    print(f"   Reasoning: {query_params.get('reasoning')}")
    return True

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
