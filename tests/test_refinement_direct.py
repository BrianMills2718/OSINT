#!/usr/bin/env python3
"""
Direct test of agentic refinement by simulating a zero-result scenario.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

from core.agentic_executor import AgenticExecutor
from core.database_integration_base import DatabaseIntegration, DatabaseMetadata, DatabaseCategory, QueryResult


class MockDatabase(DatabaseIntegration):
    """Mock database that returns zero results on first call, then more on refinement."""

    def __init__(self):
        self.call_count = 0

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="MockDB",
            id="mockdb",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.0,
            typical_response_time=0.1,
            rate_limit_daily=None,
            description="Mock database for testing refinement"
        )

    async def is_relevant(self, research_question: str) -> bool:
        return True

    async def generate_query(self, research_question: str) -> dict:
        # Always generates a query
        return {"keywords": "test", "narrow": True}

    async def execute_search(self, query_params: dict, api_key=None, limit=10) -> QueryResult:
        self.call_count += 1

        if self.call_count == 1:
            # First call: zero results (triggers refinement)
            print(f"  🔴 MockDB Call #{self.call_count}: Returning 0 results (triggers refinement)")
            return QueryResult(
                success=True,
                source="MockDB",
                total=0,
                results=[],
                query_params=query_params,
                response_time_ms=100
            )
        else:
            # Refined call: more results
            print(f"  🟢 MockDB Call #{self.call_count}: Returning 100 results (after refinement)")
            return QueryResult(
                success=True,
                source="MockDB",
                total=100,
                results=[{"job_id": i, "title": f"Job {i}"} for i in range(limit)],
                query_params=query_params,
                response_time_ms=100
            )


async def test_refinement():
    print("=" * 80)
    print("DIRECT REFINEMENT TEST - Mock Database")
    print("=" * 80)

    mock_db = MockDatabase()
    executor = AgenticExecutor(max_concurrent=5, max_refinements=2)

    print("\nRunning agentic search (should trigger refinement)...\n")

    results = await executor.execute_all(
        research_question="test query",
        databases=[mock_db],
        api_keys={},
        limit=5
    )

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    for db_id, result in results.items():
        print(f"\n{result.source}:")
        print(f"  Success: {result.success}")
        print(f"  Total: {result.total}")
        print(f"  Returned: {len(result.results)}")
        print(f"  Query params: {result.query_params}")

    print(f"\nTotal MockDB API calls: {mock_db.call_count}")

    if mock_db.call_count > 1:
        print("\n✅ SUCCESS: Refinement triggered!")
        print(f"   - Initial call returned 0 results")
        print(f"   - Refined call returned {results['mockdb'].total} results")
    else:
        print("\n❌ FAILED: Refinement did not trigger")


if __name__ == "__main__":
    asyncio.run(test_refinement())
