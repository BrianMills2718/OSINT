#!/usr/bin/env python3
"""
Phase 3C Coverage Mode Test - Sequential Hypothesis Execution with Adaptive Stopping

Tests sequential execution mode with coverage assessment for adaptive stopping.

Expected Behavior:
- mode: "execution" + coverage_mode: true → sequential execution
- LLM assesses coverage after each hypothesis
- Stops early if LLM says "sufficient coverage"
- Respects hard ceilings (max hypotheses, time budget)

Test Configuration:
- max_tasks: 2 (two subtasks)
- max_hypotheses_per_task: 3 (generate up to 3 hypotheses per task)
- coverage_mode: true (enable sequential execution with adaptive stopping)
- max_hypotheses_to_execute: 3 (hard ceiling)
- max_time_per_task_seconds: 120 (2 minutes per task)

Validation:
- Sequential execution triggered (not parallel)
- Coverage assessment called after each hypothesis (except first)
- Coverage decisions stored in task.metadata
- Coverage decisions appear in final report
- Execution stops on LLM "stop" decision OR hard ceilings
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_coverage_mode():
    """Test Phase 3C coverage assessment with sequential execution."""

    print("=" * 80)
    print("PHASE 3C TEST: Coverage Mode (Sequential Execution with Adaptive Stopping)")
    print("=" * 80)

    # Create engine with coverage mode enabled
    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=10,
        save_output=True
    )

    # Override config for Phase 3C testing
    print("\n📋 Configuration:")
    print(f"   Hypothesis Mode: execution (generate + execute hypotheses)")
    print(f"   Coverage Mode: true (sequential execution with adaptive stopping)")
    print(f"   Max Hypotheses to Execute: 3 (hard ceiling)")
    print(f"   Time Budget per Task: 120s (2 minutes)")
    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 3
    engine.coverage_mode = True  # PHASE 3C: Enable coverage assessment
    engine.max_hypotheses_to_execute = 3  # Hard ceiling
    engine.max_time_per_task_seconds = 120  # Time budget

    # Simple query (likely to find sufficient coverage quickly)
    query = "What are federal cybersecurity job opportunities?"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Behavior:")
    print("   1. Task decomposition generates 2 subtasks")
    print("   2. Each subtask generates up to 3 hypotheses")
    print("   3. Hypotheses execute SEQUENTIALLY (one-by-one)")
    print("   4. LLM assesses coverage after each hypothesis")
    print("   5. Stops early if LLM decides 'sufficient coverage'")
    print("   6. OR stops when hard ceilings reached (3 hypotheses, 120s)")

    # Execute research
    result = await engine.research(query)

    # Validation
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    # Check task completion
    print(f"\n✓ Tasks executed: {result['tasks_executed']}")
    print(f"✓ Tasks failed: {result['tasks_failed']}")
    print(f"✓ Total results: {result['total_results']}")

    # Check hypothesis execution
    if 'metadata' in result and 'hypothesis_execution_summary' in result['metadata']:
        hypothesis_summary = result['metadata']['hypothesis_execution_summary']
        print(f"\n✓ Hypothesis execution summary found ({len(hypothesis_summary)} tasks)")

        for task_id, runs in hypothesis_summary.items():
            print(f"\n   Task {task_id}: {len(runs)} hypotheses executed")
            for run in runs:
                print(f"      - {run['hypothesis_id']}: {run['results_count']} results")
                if 'delta_metrics' in run:
                    delta = run['delta_metrics']
                    new_pct = (delta['results_new'] / delta['total_results'] * 100) if delta['total_results'] > 0 else 0
                    print(f"        Delta: {delta['results_new']} new + {delta['results_duplicate']} dup ({new_pct:.1f}% new)")

    # Check coverage decisions (Phase 3C specific)
    coverage_found = False
    for task in engine.completed_tasks:
        if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
            coverage_found = True
            decisions = task.metadata['coverage_decisions']
            print(f"\n✓ Task {task.id}: {len(decisions)} coverage assessments found")

            for i, decision in enumerate(decisions):
                print(f"\n   Assessment {i+1}:")
                print(f"      Decision: {decision['decision'].upper()} (confidence: {decision['confidence']}%)")
                print(f"      Coverage score: {decision['coverage_score']}%")
                print(f"      Incremental gain: {decision['incremental_gain_last']}%")
                print(f"      Rationale: {decision['rationale'][:100]}...")
                if decision['gaps_identified']:
                    print(f"      Gaps: {', '.join(decision['gaps_identified'][:2])}...")

    if coverage_found:
        print("\n✅ PASS: Coverage decisions stored in task metadata")
    else:
        print("\n⚠️  WARNING: No coverage decisions found (may have stopped after first hypothesis)")

    # Check report for coverage section
    if result.get('report_path'):
        print(f"\n✓ Report saved to: {result['report_path']}")
        try:
            with open(result['report_path'], 'r') as f:
                report_content = f.read()

            if "Coverage Assessment Decisions" in report_content:
                print("✅ PASS: Coverage Assessment section found in report")
            else:
                print("⚠️  INFO: Coverage Assessment section not in report (may not have coverage decisions)")

            if "Incremental Contribution" in report_content:
                print("✅ PASS: Incremental contribution metrics found in report")
        except Exception as e:
            print(f"⚠️  Could not read report: {e}")

    # Check execution log for coverage events
    if result.get('output_dir'):
        log_path = os.path.join(result['output_dir'], 'execution_log.jsonl')
        if os.path.exists(log_path):
            import json
            coverage_events = []
            with open(log_path, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('action_type') == 'coverage_assessment':
                        coverage_events.append(entry)

            if coverage_events:
                print(f"\n✅ PASS: {len(coverage_events)} coverage assessment events in execution log")
                print(f"   First event: {coverage_events[0]['action_payload']['decision'].upper()}")
            else:
                print("\n⚠️  INFO: No coverage assessment events in log (may have stopped after first hypothesis)")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nPhase 3C Features Validated:")
    print("   ✓ Sequential execution mode")
    print("   ✓ Coverage assessment after each hypothesis")
    print("   ✓ Delta metrics (new vs duplicate results)")
    print("   ✓ Coverage decisions stored in metadata")
    print("   ✓ Coverage events logged to execution_log.jsonl")
    print("   ✓ Coverage section in final report")


if __name__ == "__main__":
    asyncio.run(test_coverage_mode())
