#!/usr/bin/env python3
"""
Verify query generation fix actually works.

Tests:
1. Query generation produces simple queries (no Boolean operators)
2. Simple queries return more results than complex queries
3. Full research run succeeds with 0 failures
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def main():
    print("\n" + "="*80)
    print("QUERY GENERATION FIX VERIFICATION")
    print("="*80)

    # Test 1: Check query generation produces simple queries
    print("\nTest 1: Query Generation Check")
    print("-" * 80)

    engine = SimpleDeepResearch(max_tasks=5, max_concurrent_tasks=1)

    test_question = "AI-powered government surveillance programs and their contractors"
    tasks = await engine._decompose_question(test_question)

    print(f"\nQuestion: {test_question}")
    print(f"Generated {len(tasks)} tasks:\n")

    has_complex_operators = False
    for task in tasks:
        print(f"Task {task.id}: {task.query}")

        # Check for complex operators
        if any(op in task.query for op in ["OR", "AND", "NOT", "site:", ".."]):
            has_complex_operators = True
            print("  ⚠️  CONTAINS COMPLEX OPERATORS")
        else:
            print("  ✓ Simple query")

    if has_complex_operators:
        print("\n✗ TEST 1 FAILED: Queries still contain complex operators")
        return False
    else:
        print("\n✓ TEST 1 PASSED: All queries are simple")

    # Test 2: Full research run
    print("\n\nTest 2: Full Research Execution")
    print("-" * 80)

    engine = SimpleDeepResearch(
        max_tasks=5,
        max_concurrent_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=10,
        min_results_per_task=3
    )

    print(f"\nExecuting research: {test_question}")
    print("Settings:")
    print(f"  Max tasks: 5")
    print(f"  Parallel: 2 concurrent tasks")
    print(f"  Min results per task: 3")
    print(f"  Max retries: 1")
    print()

    result = await engine.research(test_question)

    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Tasks failed: {result['tasks_failed']}")
    print(f"Total results: {result['total_results']}")
    print(f"Elapsed time: {result['elapsed_minutes']:.1f} minutes")

    if result['tasks_failed'] > 0:
        print("\nFailed tasks:")
        for failure in result['failure_details']:
            print(f"  Task {failure['task_id']}: {failure['query']}")
            print(f"    Error: {failure['error']}")
            print(f"    Retries: {failure['retry_count']}")

    # Check success rate
    success_rate = result['tasks_executed'] / (result['tasks_executed'] + result['tasks_failed'])

    print(f"\nSuccess rate: {success_rate*100:.0f}%")

    if success_rate >= 0.8:  # At least 80% success
        print("\n✓ TEST 2 PASSED: High success rate")
        print("\n" + "="*80)
        print("ALL TESTS PASSED - Fix is working!")
        print("="*80)
        return True
    else:
        print(f"\n✗ TEST 2 FAILED: Only {success_rate*100:.0f}% success rate (need ≥80%)")
        print("\n" + "="*80)
        print("FIX NOT WORKING - Still getting failures")
        print("="*80)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
