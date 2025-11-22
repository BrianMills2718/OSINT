#!/usr/bin/env python3
"""Quick query generation test with just 3 diverse queries."""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.registry import registry

# Just 3 diverse queries for quick testing
TEST_QUERIES = [
    "SIGINT signals intelligence",  # Intelligence topic
    "cybersecurity contracts",      # Contract topic
    "intelligence analyst jobs",    # Job topic
]


async def test_query(query: str):
    """Test one query across all sources."""
    print(f"\n{'='*100}")
    print(f"QUERY: {query}")
    print(f"{'='*100}\n")

    all_sources = registry.get_all()

    for source_id, source_class in all_sources.items():
        print(f"\n{source_id}:")
        print(f"  ", end="", flush=True)

        try:
            integration = source_class()
            query_params = await integration.generate_query(query)

            if not query_params:
                print(f"❌ NOT RELEVANT")
                continue

            print(f"✅ Generated: {json.dumps(query_params, separators=(',', ':'))} ")

        except Exception as e:
            print(f"❌ ERROR: {e}")


async def main():
    print(f"Quick Query Analysis - {len(TEST_QUERIES)} queries across all sources\n")

    for query in TEST_QUERIES:
        await test_query(query)

    print(f"\n{'='*100}")
    print("Quick analysis complete!")
    print("Run test_query_generation_analysis.py for full analysis with search execution.")


if __name__ == "__main__":
    asyncio.run(main())
