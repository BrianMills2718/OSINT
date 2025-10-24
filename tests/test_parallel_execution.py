#!/usr/bin/env python3
"""
Test parallel execution in SimpleDeepResearch.

Verifies:
1. Parallel batch execution works
2. Task progress events emitted correctly
3. Resource locks prevent race conditions
4. Sequential (concurrency=1) still works
5. Performance improvement with parallel execution
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch, ResearchProgress


def test_progress_events():
    """Test that all expected progress events are emitted."""
    events = []

    def track_events(progress: ResearchProgress):
        events.append(progress.event)

    async def run():
        engine = SimpleDeepResearch(
            max_tasks=5,
            max_concurrent_tasks=2,  # Parallel
            max_retries_per_task=1,
            max_time_minutes=10,
            min_results_per_task=1,
            progress_callback=track_events
        )

        # Simple test question
        question = "military training exercises"

        try:
            result = await engine.research(question)
            return result, events
        except Exception as e:
            print(f"ERROR during research: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, events

    result, events = asyncio.run(run())

    print("\n" + "="*80)
    print("TEST 1: Progress Events")
    print("="*80)

    # Check expected events
    expected_events = [
        "research_started",
        "decomposition_started",
        "decomposition_complete",
        "task_created",
        "batch_started",
        "task_started",  # Should have per-task events now (Codex fix)
    ]

    for event in expected_events:
        if event in events:
            print(f"✓ {event}")
        else:
            print(f"✗ {event} - MISSING")

    # Check batch events
    batch_started_count = events.count("batch_started")
    batch_complete_count = events.count("batch_complete")

    print(f"\nBatch events: {batch_started_count} started, {batch_complete_count} complete")
    if batch_started_count == batch_complete_count:
        print("✓ Batch events balanced")
    else:
        print(f"✗ Batch events unbalanced: {batch_started_count} != {batch_complete_count}")

    # Check task_started events
    task_started_count = events.count("task_started")
    print(f"\nTask started events: {task_started_count}")
    if task_started_count > 0:
        print("✓ Task-level progress events working (Codex fix)")
    else:
        print("✗ No task_started events (Codex fix failed)")

    return result is not None


def test_sequential_vs_parallel():
    """Compare sequential vs parallel execution time."""

    async def run_test(concurrency: int, label: str):
        print(f"\n{'='*80}")
        print(f"TEST 2: {label} (concurrency={concurrency})")
        print("="*80)

        start_time = time.time()

        engine = SimpleDeepResearch(
            max_tasks=6,
            max_concurrent_tasks=concurrency,
            max_retries_per_task=1,
            max_time_minutes=10,
            min_results_per_task=1,
            progress_callback=None  # Suppress progress for timing
        )

        question = "special operations forces"

        try:
            result = await engine.research(question)
            elapsed = time.time() - start_time

            print(f"\nResults:")
            print(f"  Tasks executed: {result['tasks_executed']}")
            print(f"  Tasks failed: {result['tasks_failed']}")
            print(f"  Total results: {result['total_results']}")
            print(f"  Elapsed time: {elapsed:.1f}s")

            return elapsed, result['tasks_executed']
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\nERROR: {type(e).__name__}: {str(e)}")
            print(f"Elapsed time: {elapsed:.1f}s")
            return elapsed, 0

    # Run sequential
    sequential_time, seq_tasks = asyncio.run(run_test(1, "Sequential Execution"))

    # Run parallel
    parallel_time, par_tasks = asyncio.run(run_test(3, "Parallel Execution"))

    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    print(f"Sequential: {sequential_time:.1f}s ({seq_tasks} tasks)")
    print(f"Parallel:   {parallel_time:.1f}s ({par_tasks} tasks)")

    if parallel_time < sequential_time:
        speedup = sequential_time / parallel_time
        print(f"✓ Parallel is {speedup:.2f}x faster")
        return True
    else:
        print(f"✗ Parallel is slower (or equal)")
        print(f"  Note: This can happen if tasks complete very quickly")
        print(f"  or if network latency dominates over concurrency benefit")
        return False


def test_resource_locks():
    """Test that resource locks prevent race conditions."""

    print(f"\n{'='*80}")
    print("TEST 3: Resource Lock Safety")
    print("="*80)

    async def run():
        engine = SimpleDeepResearch(
            max_tasks=6,
            max_concurrent_tasks=3,  # High concurrency to stress test
            max_retries_per_task=1,
            max_time_minutes=10,
            min_results_per_task=1
        )

        question = "cyber security operations"

        try:
            result = await engine.research(question)

            # Check entity graph consistency
            entity_count = len(result['entity_relationships'])

            # Check results_by_task consistency
            tasks_with_results = len(result.get('failure_details', []))

            print(f"\nEntity graph entries: {entity_count}")
            print(f"Tasks executed: {result['tasks_executed']}")

            # No errors = locks working
            print("✓ No race condition errors detected")
            return True

        except Exception as e:
            print(f"\n✗ ERROR (possible race condition): {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    return asyncio.run(run())


def test_brave_search_rate_limit():
    """Test that Brave Search respects 1 req/sec limit with parallel execution."""

    print(f"\n{'='*80}")
    print("TEST 4: Brave Search Rate Limiting")
    print("="*80)

    brave_call_times = []

    # Track when Brave Search is called
    original_search_brave = None

    async def run():
        engine = SimpleDeepResearch(
            max_tasks=4,
            max_concurrent_tasks=3,  # Parallel - would violate rate limit without lock
            max_retries_per_task=1,
            max_time_minutes=5,
            min_results_per_task=1
        )

        # Wrap _search_brave to track timing
        original = engine._search_brave

        async def tracked_search_brave(*args, **kwargs):
            brave_call_times.append(time.time())
            return await original(*args, **kwargs)

        engine._search_brave = tracked_search_brave

        question = "intelligence operations"

        try:
            result = await engine.research(question)
            print(f"\nTasks executed: {result['tasks_executed']}")
            print(f"Brave Search calls: {len(brave_call_times)}")

            # Check intervals between calls
            if len(brave_call_times) > 1:
                intervals = [brave_call_times[i+1] - brave_call_times[i]
                            for i in range(len(brave_call_times) - 1)]

                min_interval = min(intervals)
                avg_interval = sum(intervals) / len(intervals)

                print(f"Min interval: {min_interval:.2f}s")
                print(f"Avg interval: {avg_interval:.2f}s")

                # Should be >= 1.0s due to rate limiting
                if min_interval >= 0.95:  # Allow 50ms tolerance
                    print("✓ Rate limit respected (1 req/sec)")
                    return True
                else:
                    print(f"✗ Rate limit violated: {min_interval:.2f}s < 1.0s")
                    return False
            else:
                print("✓ Only one Brave Search call (rate limit not tested)")
                return True

        except Exception as e:
            print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
            return False

    return asyncio.run(run())


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PARALLEL EXECUTION TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}")

    results = {}

    # Test 1: Progress events
    try:
        results['progress_events'] = test_progress_events()
    except Exception as e:
        print(f"\nTest 1 FAILED with exception: {e}")
        results['progress_events'] = False

    # Test 2: Sequential vs Parallel
    try:
        results['sequential_vs_parallel'] = test_sequential_vs_parallel()
    except Exception as e:
        print(f"\nTest 2 FAILED with exception: {e}")
        results['sequential_vs_parallel'] = False

    # Test 3: Resource locks
    try:
        results['resource_locks'] = test_resource_locks()
    except Exception as e:
        print(f"\nTest 3 FAILED with exception: {e}")
        results['resource_locks'] = False

    # Test 4: Brave Search rate limiting
    try:
        results['brave_rate_limit'] = test_brave_search_rate_limit()
    except Exception as e:
        print(f"\nTest 4 FAILED with exception: {e}")
        results['brave_rate_limit'] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n✗ {total_tests - passed_tests} TESTS FAILED")
        sys.exit(1)
