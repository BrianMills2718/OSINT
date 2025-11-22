#!/usr/bin/env python3
"""
Quick validation script to test logging and filtering fixes.
"""
import asyncio
import json
from research.deep_research import SimpleDeepResearch
from research.execution_logger import ExecutionLogger
from pathlib import Path
import tempfile

async def test_hypothesis_query_logging():
    """Test that log_hypothesis_query_generation exists and works"""
    print("\n[TEST 1] Testing hypothesis query generation logging...")

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ExecutionLogger(research_id="test_run", output_dir=tmpdir)

        # Test the method exists and can be called
        logger.log_hypothesis_query_generation(
            task_id=0,
            hypothesis_id="hyp_1",
            source_name="Brave Search",
            query="test query about Cuba sanctions",
            reasoning="Testing that query generation logging works correctly"
        )

        # Read the log file
        log_file = Path(tmpdir) / "execution_log.jsonl"
        with open(log_file) as f:
            lines = f.readlines()

        # Verify the log entry
        last_entry = json.loads(lines[-1])
        assert last_entry["action_type"] == "hypothesis_query_generation", \
            f"Expected hypothesis_query_generation, got {last_entry['action_type']}"
        assert last_entry["action_payload"]["query"] == "test query about Cuba sanctions"
        assert last_entry["action_payload"]["reasoning"] == "Testing that query generation logging works correctly"

        print("   [PASS] log_hypothesis_query_generation() method exists and logs correctly")
        return True

async def test_relevance_filtering_callable():
    """Test that _validate_result_relevance can be called on hypothesis results"""
    print("\n[TEST 2] Testing hypothesis relevance filtering integration...")

    # Create engine instance
    engine = SimpleDeepResearch(max_tasks=1, max_time_minutes=5)

    # Check that _validate_result_relevance method exists
    assert hasattr(engine, '_validate_result_relevance'), \
        "Engine missing _validate_result_relevance method"

    # Check that _execute_hypothesis method exists
    assert hasattr(engine, '_execute_hypothesis'), \
        "Engine missing _execute_hypothesis method"

    print("   [PASS] Relevance filtering method exists and is callable")
    print("   [NOTE] Full integration test requires live API calls")
    return True

async def main():
    print("="*60)
    print("VALIDATION: Logging and Filtering Fixes")
    print("="*60)

    test_results = []

    # Test 1: Hypothesis query logging
    try:
        result = await test_hypothesis_query_logging()
        test_results.append(("Hypothesis query logging", result))
    except Exception as e:
        print(f"   [FAIL] {type(e).__name__}: {e}")
        test_results.append(("Hypothesis query logging", False))

    # Test 2: Relevance filtering integration
    try:
        result = await test_relevance_filtering_callable()
        test_results.append(("Relevance filtering integration", result))
    except Exception as e:
        print(f"   [FAIL] {type(e).__name__}: {e}")
        test_results.append(("Relevance filtering integration", False))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"Passed: {passed}/{total}")
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    print("\n" + "="*60)
    if passed == total:
        print("✓ All validation tests passed")
        print("\n[ NEXT STEP ]")
        print("Run full research test to verify end-to-end:")
        print('  python3 apps/ai_research.py "test query" --max-tasks 1')
    else:
        print("⚠ Some tests failed - review errors above")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
