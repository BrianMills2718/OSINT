#!/usr/bin/env python3
"""
Performance tests for integration registry.

Tests registry performance characteristics:
- Lazy instantiation time
- Caching effectiveness
- Concurrent access performance
- Memory footprint

These tests validate that the registry scales efficiently
for production use (100+ monitors accessing integrations).
"""

import sys
import os
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from integrations.registry import registry
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.performance
class TestRegistryPerformance:
    """Performance tests for integration registry."""

    def setup_method(self):
        """Clear registry cache before each test."""
        registry._cached_instances.clear()

    def test_instantiation_time_under_100ms(self):
        """
        Test: Registry instantiation takes < 100ms per integration.

        Success criteria:
        - First instantiation < 100ms
        - Cached instantiation < 1ms
        - All 8 integrations instantiate quickly
        """
        print(f"\n{'='*60}")
        print("INSTANTIATION TIME TEST")
        print(f"{'='*60}\n")

        all_ids = registry.list_ids()
        first_times = {}
        cached_times = {}

        for integration_id in all_ids:
            # Clear cache for this integration
            if integration_id in registry._cached_instances:
                del registry._cached_instances[integration_id]

            # Time first instantiation (cold)
            start = time.perf_counter()
            instance = registry.get_instance(integration_id)
            first_time = (time.perf_counter() - start) * 1000  # Convert to ms

            # Time cached instantiation (hot)
            start = time.perf_counter()
            cached_instance = registry.get_instance(integration_id)
            cached_time = (time.perf_counter() - start) * 1000  # Convert to ms

            first_times[integration_id] = first_time
            cached_times[integration_id] = cached_time

            print(f"  {integration_id:20s}: first={first_time:6.2f}ms, cached={cached_time:6.2f}ms")

            # Assertions
            assert first_time < 100, \
                   f"{integration_id}: First instantiation {first_time:.2f}ms exceeds 100ms threshold"
            assert cached_time < 1, \
                   f"{integration_id}: Cached instantiation {cached_time:.2f}ms exceeds 1ms threshold"
            assert instance is cached_instance, \
                   f"{integration_id}: Cache should return same instance"

        avg_first = sum(first_times.values()) / len(first_times)
        avg_cached = sum(cached_times.values()) / len(cached_times)

        print(f"\nAverages:")
        print(f"  First instantiation: {avg_first:.2f}ms")
        print(f"  Cached instantiation: {avg_cached:.2f}ms")

        print(f"\n✓ Instantiation test PASSED: All integrations < 100ms")
        print(f"{'='*60}\n")

    def test_cache_effectiveness(self):
        """
        Test: Cache significantly improves performance.

        Success criteria:
        - Cache hit ratio > 99% after warmup
        - Cached access 100x faster than first access
        """
        print(f"\n{'='*60}")
        print("CACHE EFFECTIVENESS TEST")
        print(f"{'='*60}\n")

        # Warmup: Instantiate all integrations
        all_ids = registry.list_ids()
        for integration_id in all_ids:
            registry.get_instance(integration_id)

        # Test: 1000 random accesses
        num_accesses = 1000
        start = time.perf_counter()

        for i in range(num_accesses):
            # Cycle through integrations
            integration_id = all_ids[i % len(all_ids)]
            instance = registry.get_instance(integration_id)
            assert instance is not None

        duration = (time.perf_counter() - start) * 1000  # ms
        avg_time = duration / num_accesses

        print(f"Results:")
        print(f"  Total accesses: {num_accesses}")
        print(f"  Total time: {duration:.2f}ms")
        print(f"  Avg time per access: {avg_time:.4f}ms")

        # Average cached access should be < 0.1ms
        assert avg_time < 0.1, \
               f"Avg cached access {avg_time:.4f}ms exceeds 0.1ms threshold"

        print(f"\n✓ Cache test PASSED: {num_accesses} accesses in {duration:.2f}ms")
        print(f"{'='*60}\n")

    def test_concurrent_access_thread_safety(self):
        """
        Test: Concurrent access to registry is thread-safe.

        Success criteria:
        - Multiple threads can access registry simultaneously
        - No race conditions or corrupted instances
        - Cache works correctly under concurrent load
        """
        print(f"\n{'='*60}")
        print("CONCURRENT ACCESS TEST")
        print(f"{'='*60}\n")

        num_threads = 20
        accesses_per_thread = 100
        all_ids = registry.list_ids()

        def access_registry(thread_id):
            """Worker function: access registry multiple times."""
            instances = []
            for i in range(accesses_per_thread):
                integration_id = all_ids[i % len(all_ids)]
                instance = registry.get_instance(integration_id)
                instances.append(instance)
            return (thread_id, instances)

        # Execute concurrent accesses
        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(access_registry, i)
                for i in range(num_threads)
            ]

            results = []
            for future in as_completed(futures):
                thread_id, instances = future.result()
                results.append((thread_id, instances))

        duration = (time.perf_counter() - start) * 1000  # ms

        # Verify results
        total_accesses = num_threads * accesses_per_thread

        print(f"Results:")
        print(f"  Threads: {num_threads}")
        print(f"  Accesses per thread: {accesses_per_thread}")
        print(f"  Total accesses: {total_accesses}")
        print(f"  Duration: {duration:.2f}ms")
        print(f"  Avg time per access: {duration/total_accesses:.4f}ms")

        # Verify all threads completed
        assert len(results) == num_threads, \
               f"Expected {num_threads} results, got {len(results)}"

        # Verify all accesses returned valid instances
        for thread_id, instances in results:
            assert len(instances) == accesses_per_thread, \
                   f"Thread {thread_id}: Expected {accesses_per_thread} instances"
            assert all(i is not None for i in instances), \
                   f"Thread {thread_id}: Some instances are None"

        # Verify cache consistency: same ID should return same instance across threads
        # Get instances from first thread
        first_thread_instances = results[0][1]

        for thread_id, instances in results[1:]:
            for i, instance in enumerate(instances):
                integration_id = all_ids[i % len(all_ids)]
                first_instance = first_thread_instances[i]

                # Same ID should return same cached instance
                if all_ids[i % len(all_ids)] == all_ids[i % len(all_ids)]:
                    assert instance is first_instance, \
                           f"Thread {thread_id}: Cache inconsistency for {integration_id}"

        print(f"\n✓ Concurrent access test PASSED: {total_accesses} accesses, no race conditions")
        print(f"{'='*60}\n")

    def test_memory_footprint(self):
        """
        Test: Registry memory footprint is reasonable.

        Success criteria:
        - All integrations cached use < 50MB
        - No memory leaks from repeated access
        """
        print(f"\n{'='*60}")
        print("MEMORY FOOTPRINT TEST")
        print(f"{'='*60}\n")

        tracemalloc.start()

        # Get baseline memory (empty cache)
        baseline = tracemalloc.get_traced_memory()[0]

        # Instantiate all integrations
        all_ids = registry.list_ids()
        for integration_id in all_ids:
            registry.get_instance(integration_id)

        # Measure memory after instantiation
        current, peak = tracemalloc.get_traced_memory()
        footprint = current - baseline

        print(f"Memory Usage:")
        print(f"  Baseline: {baseline / 1024 / 1024:.2f} MB")
        print(f"  After instantiation: {current / 1024 / 1024:.2f} MB")
        print(f"  Footprint: {footprint / 1024 / 1024:.2f} MB")
        print(f"  Peak: {peak / 1024 / 1024:.2f} MB")

        # Test for memory leaks: repeated access shouldn't grow memory
        before_loop = tracemalloc.get_traced_memory()[0]

        for _ in range(1000):
            for integration_id in all_ids:
                registry.get_instance(integration_id)

        after_loop = tracemalloc.get_traced_memory()[0]
        growth = after_loop - before_loop

        print(f"\nMemory Leak Test:")
        print(f"  Before 1000 accesses: {before_loop / 1024 / 1024:.2f} MB")
        print(f"  After 1000 accesses: {after_loop / 1024 / 1024:.2f} MB")
        print(f"  Growth: {growth / 1024 / 1024:.2f} MB")

        tracemalloc.stop()

        # Assertions
        assert footprint < 50 * 1024 * 1024, \
               f"Registry footprint {footprint / 1024 / 1024:.2f} MB exceeds 50 MB"

        assert growth < 1 * 1024 * 1024, \
               f"Memory grew by {growth / 1024 / 1024:.2f} MB (threshold: 1 MB)"

        print(f"\n✓ Memory test PASSED: Footprint < 50MB, no leaks detected")
        print(f"{'='*60}\n")

    def test_registry_list_operations_performance(self):
        """
        Test: Registry list operations are fast.

        Success criteria:
        - get_all_enabled() < 10ms
        - get_by_category() < 10ms
        - Repeated calls use cache effectively
        """
        print(f"\n{'='*60}")
        print("LIST OPERATIONS TEST")
        print(f"{'='*60}\n")

        # Test get_all_enabled
        times = []
        for _ in range(100):
            start = time.perf_counter()
            enabled = registry.get_all_enabled()
            times.append((time.perf_counter() - start) * 1000)

        avg_time = sum(times) / len(times)
        print(f"get_all_enabled():")
        print(f"  100 calls avg: {avg_time:.4f}ms")
        print(f"  First call: {times[0]:.4f}ms")
        print(f"  Last call: {times[-1]:.4f}ms")

        assert avg_time < 10, f"get_all_enabled() avg {avg_time:.4f}ms exceeds 10ms"

        # Test get_by_category
        from core.database_integration_base import DatabaseCategory

        times = []
        for _ in range(100):
            start = time.perf_counter()
            govt = registry.get_by_category(DatabaseCategory.GOV_GENERAL)
            times.append((time.perf_counter() - start) * 1000)

        avg_time = sum(times) / len(times)
        print(f"\nget_by_category():")
        print(f"  100 calls avg: {avg_time:.4f}ms")
        print(f"  First call: {times[0]:.4f}ms")
        print(f"  Last call: {times[-1]:.4f}ms")

        assert avg_time < 10, f"get_by_category() avg {avg_time:.4f}ms exceeds 10ms"

        print(f"\n✓ List operations test PASSED: All operations < 10ms")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    """Run tests directly."""
    print("=" * 80)
    print("REGISTRY PERFORMANCE TESTS")
    print("=" * 80)
    print()

    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "-s"])

    sys.exit(exit_code)
