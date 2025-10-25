#!/usr/bin/env python3
"""Quick test with simple non-sensitive query to check API key status."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.government.dvids_integration import DVIDSIntegration

async def test_simple():
    integration = DVIDSIntegration()
    api_key = os.getenv("DVIDS_API_KEY")

    # Simple, non-sensitive query
    params = await integration.generate_query("Air Force training exercises")
    result = await integration.execute_search(params, api_key, limit=5)

    print(f"Query: Air Force training exercises")
    print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
    if result.success:
        print(f"  Total: {result.total} results")
    else:
        print(f"  Error: {result.error}")

    return result.success

if __name__ == "__main__":
    success = asyncio.run(test_simple())
    exit(0 if success else 1)
