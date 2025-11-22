#!/usr/bin/env python3
"""
Test the new multi-database architecture with ClearanceJobs.

This is a simple test to verify the base classes and parallel executor
work correctly with the first refactored database.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key for LiteLLM
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

from database_registry import registry
from core.parallel_executor import ParallelExecutor
from integrations.clearancejobs_integration import ClearanceJobsIntegration


async def test_single_database():
    """Test with just ClearanceJobs to verify architecture works."""

    print("=" * 80)
    print("TESTING NEW MULTI-DATABASE ARCHITECTURE")
    print("=" * 80)

    # Register ClearanceJobs
    print("\n1. Registering databases...")
    registry.register(ClearanceJobsIntegration())

    stats = registry.get_stats()
    print(f"   Registered: {stats['total']} databases")
    print(f"   Categories: {stats['by_category']}")

    # Get available databases (no API keys needed for ClearanceJobs)
    available = registry.list_available({})
    print(f"\n2. Available databases: {len(available)}")
    for db in available:
        print(f"   - {db.metadata.name} ({db.metadata.category.value})")

    # Test queries
    test_questions = [
        "What cybersecurity jobs are available?",
        "Recent counterterrorism analyst positions with TS/SCI clearance",
        "What government contracts are available?",  # Should be not relevant
    ]

    executor = ParallelExecutor(max_concurrent=5)

    for question in test_questions:
        print(f"\n{'=' * 80}")
        print(f"Question: {question}")
        print('=' * 80)

        results = await executor.execute_all(
            research_question=question,
            databases=available,
            api_keys={},
            limit=5
        )

        print(f"\nResults:")
        for db_id, result in results.items():
            if result.success:
                print(f"\n  ✓ {result.source}:")
                print(f"    Total available: {result.total}")
                print(f"    Returned: {len(result.results)}")
                print(f"    Response time: {result.response_time_ms:.0f}ms")
                print(f"    Query params: {result.query_params}")

                if result.results:
                    print(f"\n    First result:")
                    first = result.results[0]
                    print(f"      Title: {first.get('job_name', 'N/A')}")
                    print(f"      Company: {first.get('company_name', 'N/A')}")
                    locations = first.get('locations', [])
                    if locations:
                        print(f"      Location: {locations[0].get('location', 'N/A')}")
                    print(f"      Clearance: {first.get('clearance', 'N/A')}")
            else:
                print(f"\n  ✗ {result.source}: {result.error}")

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(test_single_database())
