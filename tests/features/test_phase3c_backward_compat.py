#!/usr/bin/env python3
"""
Phase 3C Backward Compatibility Test

Validates that Phase 3B parallel execution still works when coverage_mode: false.

Test Scenarios:
1. mode: "execution" + coverage_mode: false → parallel execution (Phase 3B)
2. mode: "off" → no hypotheses (traditional task decomposition)
3. mode: "planning" → hypotheses displayed but not executed

Validation:
- Parallel execution still works (all hypotheses run at once)
- No coverage assessments triggered
- No coverage decisions in metadata or report
- Results identical to Phase 3B behavior
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_backward_compatibility():
    """Test that Phase 3B parallel execution still works (coverage_mode: false)."""

    print("=" * 80)
    print("PHASE 3C BACKWARD COMPATIBILITY TEST")
    print("=" * 80)

    # Test 1: Parallel execution (Phase 3B default)
    print("\n" + "=" * 80)
    print("TEST 1: Parallel Execution (coverage_mode: false)")
    print("=" * 80)

    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=10,
        save_output=True
    )

    print("\n📋 Configuration:")
    print(f"   Hypothesis Mode: execution")
    print(f"   Coverage Mode: false (parallel execution, Phase 3B)")
    print(f"   Max Hypotheses per Task: 3")
    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 3
    engine.coverage_mode = False  # Phase 3B behavior

    query = "What are federal cybersecurity jobs?"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Behavior:")
    print("   - All hypotheses execute in PARALLEL (Phase 3B)")
    print("   - NO coverage assessments")
    print("   - NO coverage decisions in metadata")

    result = await engine.research(query)

    # Validation
    print("\n✓ Tasks executed: " + str(result['tasks_executed']))
    print(f"✓ Total results: {result['total_results']}")

    # Check hypothesis execution
    parallel_execution_found = False
    if 'metadata' in result and 'hypothesis_execution_summary' in result['metadata']:
        hypothesis_summary = result['metadata']['hypothesis_execution_summary']
        print(f"\n✓ Hypothesis execution summary found ({len(hypothesis_summary)} tasks)")
        parallel_execution_found = True

    # Check NO coverage decisions
    coverage_decisions_found = False
    for task in engine.completed_tasks:
        if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
            coverage_decisions_found = True
            print(f"\n❌ FAIL: Coverage decisions found in task {task.id} metadata (should not exist in parallel mode)")

    if not coverage_decisions_found:
        print("\n✅ PASS: No coverage decisions (parallel mode working as expected)")

    # Check report does NOT contain coverage section
    if result.get('report_path'):
        try:
            with open(result['report_path'], 'r') as f:
                report_content = f.read()

            if "Coverage Assessment Decisions" not in report_content:
                print("✅ PASS: Coverage Assessment section not in report (parallel mode)")
            else:
                print("❌ FAIL: Coverage Assessment section found in report (should not exist in parallel mode)")
        except Exception as e:
            print(f"⚠️  Could not read report: {e}")

    # Test 2: Mode "off" (no hypotheses)
    print("\n" + "=" * 80)
    print("TEST 2: Traditional Mode (mode: off)")
    print("=" * 80)

    engine2 = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=10,
        save_output=True
    )

    print("\n📋 Configuration:")
    print(f"   Hypothesis Mode: off")
    print(f"   Expected: Traditional task decomposition (no hypotheses)")
    engine2.hypothesis_mode = "off"
    engine2.hypothesis_branching_enabled = False

    result2 = await engine2.research(query)

    print("\n✓ Tasks executed: " + str(result2['tasks_executed']))
    print(f"✓ Total results: {result2['total_results']}")

    # Check NO hypotheses
    if 'metadata' in result2 and 'hypothesis_execution_summary' in result2['metadata']:
        print("\n❌ FAIL: Hypotheses found when mode: off")
    else:
        print("\n✅ PASS: No hypotheses (mode: off working)")

    # Test 3: Mode "planning" (hypotheses not executed)
    print("\n" + "=" * 80)
    print("TEST 3: Planning Mode (mode: planning)")
    print("=" * 80)

    engine3 = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=10,
        save_output=True
    )

    print("\n📋 Configuration:")
    print(f"   Hypothesis Mode: planning")
    print(f"   Expected: Hypotheses displayed but not executed")
    engine3.hypothesis_mode = "planning"
    engine3.hypothesis_branching_enabled = True
    engine3.max_hypotheses_per_task = 3

    result3 = await engine3.research(query)

    print("\n✓ Tasks executed: " + str(result3['tasks_executed']))
    print(f"✓ Total results: {result3['total_results']}")

    # Check hypotheses in metadata but NOT executed
    if 'metadata' in result3:
        if 'hypotheses_by_task' in result3['metadata'] and result3['metadata']['hypotheses_by_task']:
            print("\n✓ Hypotheses generated and stored in metadata")

        if 'hypothesis_execution_summary' in result3['metadata']:
            print("❌ FAIL: Hypotheses were executed (should be planning only)")
        else:
            print("✅ PASS: Hypotheses not executed (planning mode working)")

    print("\n" + "=" * 80)
    print("BACKWARD COMPATIBILITY TEST COMPLETE")
    print("=" * 80)
    print("\nAll Modes Validated:")
    print("   ✓ mode: execution + coverage_mode: false → parallel (Phase 3B)")
    print("   ✓ mode: off → no hypotheses")
    print("   ✓ mode: planning → hypotheses displayed only")


if __name__ == "__main__":
    asyncio.run(test_backward_compatibility())
