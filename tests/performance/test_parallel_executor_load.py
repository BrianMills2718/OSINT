#!/usr/bin/env python3
"""
Performance tests for parallel executor under load.

Tests system behavior under production-like loads:
- 50+ concurrent queries
- 8 integrations in parallel
- Memory usage and leaks
- Thread safety of cached instances

These tests validate that the system scales to production loads
(100+ monitors executing searches).
"""

import asyncio
import sys
import os
from datetime import datetime
import tracemalloc
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.parallel_executor import ParallelExecutor
from integrations.registry import registry
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.performance
@pytest.mark.api
class TestParallelExecutorLoad:
    """Performance tests for parallel executor under high load."""

    @pytest.fixture
    def executor(self):
        """Create parallel executor for tests."""
        return ParallelExecutor(max_concurrent=10)

    @pytest.fixture
    def all_integrations(self):
        """Get all enabled integrations from registry."""
        return list(registry.get_all_enabled().values())

    @pytest.fixture
    def api_keys(self):
        """Load API keys from environment."""
        return {
            "sam": os.getenv("SAM_GOV_API_KEY"),
            "usajobs": os.getenv("USAJOBS_API_KEY"),
            "dvids": os.getenv("DVIDS_API_KEY"),
            "twitter": os.getenv("RAPIDAPI_KEY"),
            "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
        }

    @pytest.mark.asyncio
    async def test_50_concurrent_queries_no_degradation(self, executor, all_integrations, api_keys):
        """
        Test: 50 concurrent queries complete without performance degradation.

        Success criteria:
        - All 50 queries complete
        - Average time < 30s per query
        - No timeouts or crashes
        - Results are valid
        """
        num_queries = 50
        queries = [
            "cybersecurity threat intelligence",
            "military operations",
            "federal contract opportunities",
            "intelligence analysis jobs",
            "defense procurement",
        ] * 10  # Cycle through 5 queries, 10 times each

        print(f"\n{'='*60}")
        print(f"LOAD TEST: {num_queries} concurrent queries")
        print(f"{'='*60}\n")

        start_time = datetime.now()
        tracemalloc.start()

        # Execute all queries concurrently
        tasks = []
        for i, query in enumerate(queries):
            task = executor.execute_all(
                research_question=query,
                databases=all_integrations[:4],  # Test on subset for speed
                api_keys=api_keys,
                limit=5
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = (datetime.now() - start_time).total_seconds()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        print(f"Results:")
        print(f"  Total queries: {num_queries}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Avg time per query: {duration/num_queries:.1f}s")
        print(f"  Peak memory: {peak / 1024 / 1024:.1f} MB")

        # Assertions
        assert len(successful) == num_queries, f"Expected {num_queries} successful, got {len(successful)}"
        assert duration / num_queries < 30, f"Avg time {duration/num_queries:.1f}s exceeds 30s threshold"

        # Verify results are valid
        for result in successful:
            assert isinstance(result, dict), "Each result should be a dict"
            for db_id, query_result in result.items():
                assert hasattr(query_result, 'success'), f"{db_id}: Missing 'success' attribute"
                assert hasattr(query_result, 'results'), f"{db_id}: Missing 'results' attribute"

        print(f"\n✓ Load test PASSED: {num_queries} queries in {duration:.1f}s")
        print(f"{'='*60}\n")

    @pytest.mark.asyncio
    async def test_memory_usage_stable_under_load(self, executor, all_integrations, api_keys):
        """
        Test: Memory usage remains stable under repeated queries.

        Success criteria:
        - Memory usage doesn't grow unbounded
        - No memory leaks detected
        - Peak memory < 500MB
        """
        num_rounds = 10
        queries_per_round = 5

        print(f"\n{'='*60}")
        print(f"MEMORY TEST: {num_rounds} rounds × {queries_per_round} queries")
        print(f"{'='*60}\n")

        tracemalloc.start()
        memory_samples = []

        for round_num in range(num_rounds):
            # Execute batch of queries
            tasks = []
            for _ in range(queries_per_round):
                task = executor.execute_all(
                    research_question="test query",
                    databases=all_integrations[:2],  # Small subset for speed
                    api_keys=api_keys,
                    limit=3
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

            # Sample memory after each round
            current, peak = tracemalloc.get_traced_memory()
            memory_samples.append(current)
            print(f"  Round {round_num+1}: {current / 1024 / 1024:.1f} MB")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"\nMemory Usage:")
        print(f"  Starting: {memory_samples[0] / 1024 / 1024:.1f} MB")
        print(f"  Final: {memory_samples[-1] / 1024 / 1024:.1f} MB")
        print(f"  Peak: {peak / 1024 / 1024:.1f} MB")
        print(f"  Growth: {(memory_samples[-1] - memory_samples[0]) / 1024 / 1024:.1f} MB")

        # Assertions
        # Memory shouldn't grow more than 100MB over the test
        memory_growth = memory_samples[-1] - memory_samples[0]
        assert memory_growth < 100 * 1024 * 1024, \
               f"Memory grew by {memory_growth / 1024 / 1024:.1f} MB (threshold: 100 MB)"

        # Peak memory shouldn't exceed 500MB
        assert peak < 500 * 1024 * 1024, \
               f"Peak memory {peak / 1024 / 1024:.1f} MB exceeds 500 MB threshold"

        print(f"\n✓ Memory test PASSED: Stable usage, no leaks detected")
        print(f"{'='*60}\n")

    @pytest.mark.asyncio
    async def test_concurrent_access_thread_safety(self, executor, all_integrations, api_keys):
        """
        Test: Concurrent queries don't cause race conditions.

        Success criteria:
        - All queries complete without errors
        - No corrupted results
        - No deadlocks or hangs
        """
        num_concurrent = 20

        print(f"\n{'='*60}")
        print(f"CONCURRENCY TEST: {num_concurrent} simultaneous queries")
        print(f"{'='*60}\n")

        start_time = datetime.now()

        # Launch all queries simultaneously
        tasks = [
            executor.execute_all(
                research_question=f"test query {i}",
                databases=all_integrations[:3],
                api_keys=api_keys,
                limit=3
            )
            for i in range(num_concurrent)
        ]

        # Wait for all with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=120  # 2 minutes max
            )
        except asyncio.TimeoutError:
            pytest.fail(f"Concurrent queries timed out after 120s")

        duration = (datetime.now() - start_time).total_seconds()

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        print(f"Results:")
        print(f"  Total queries: {num_concurrent}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Duration: {duration:.1f}s")

        # All should succeed
        assert len(successful) == num_concurrent, \
               f"Expected {num_concurrent} successful, got {len(successful)}"

        # Verify no result corruption
        for i, result in enumerate(successful):
            assert isinstance(result, dict), f"Query {i}: Result should be dict"
            assert len(result) > 0, f"Query {i}: Result should not be empty"

        print(f"\n✓ Concurrency test PASSED: {num_concurrent} queries completed safely")
        print(f"{'='*60}\n")

    @pytest.mark.asyncio
    async def test_rate_limit_backoff_handling(self, executor, all_integrations, api_keys):
        """
        Test: System handles rate limits gracefully with backoff.

        Success criteria:
        - Rate limited requests retry with backoff
        - Eventually succeed or fail gracefully
        - Don't crash or hang
        """
        # Fire off rapid queries to trigger rate limits
        num_rapid_queries = 30

        print(f"\n{'='*60}")
        print(f"RATE LIMIT TEST: {num_rapid_queries} rapid queries")
        print(f"{'='*60}\n")

        start_time = datetime.now()

        tasks = [
            executor.execute_all(
                research_question="test query",
                databases=all_integrations[:2],  # Use subset likely to rate limit
                api_keys=api_keys,
                limit=5
            )
            for _ in range(num_rapid_queries)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = (datetime.now() - start_time).total_seconds()

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        print(f"Results:")
        print(f"  Total queries: {num_rapid_queries}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Duration: {duration:.1f}s")

        # At least some should succeed (system handles rate limits)
        assert len(successful) > 0, "Should handle rate limits and complete some queries"

        # System shouldn't crash
        assert all(not isinstance(r, Exception) or isinstance(r, dict)
                   for r in results), "No exceptions should propagate"

        print(f"\n✓ Rate limit test PASSED: System handled rapid queries gracefully")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    """Run tests directly."""
    print("=" * 80)
    print("PARALLEL EXECUTOR LOAD TESTS")
    print("=" * 80)
    print()

    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "-s"])

    sys.exit(exit_code)
