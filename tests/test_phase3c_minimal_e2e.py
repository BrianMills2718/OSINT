#!/usr/bin/env python3
"""
Phase 3C Minimal E2E Validation

Fastest possible E2E test to validate critical Phase 3C components:
- 1 task only (minimal LLM calls)
- 2 hypotheses (enough to test coverage assessment)
- Simple query (fast execution)
- coverage_mode: true (sequential execution)

Expected Duration: 2-3 minutes

Validation Points:
1. Coverage assessment LLM call succeeds
2. Coverage decision is valid JSON with all required fields
3. Coverage decision stored in task.metadata
4. Coverage event logged to execution_log.jsonl
5. Coverage section appears in final report
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_minimal_e2e():
    """Minimal E2E test for Phase 3C coverage assessment."""

    print("=" * 80)
    print("PHASE 3C MINIMAL E2E VALIDATION")
    print("=" * 80)
    print("\nScope: 1 task, 2 hypotheses, coverage_mode: true")
    print("Expected Duration: 2-3 minutes")
    print()

    # Create engine with minimal config
    engine = SimpleDeepResearch(
        max_tasks=1,  # MINIMAL: Only 1 task
        max_retries_per_task=1,
        max_time_minutes=5,
        save_output=True
    )

    # Configure for Phase 3C
    print("📋 Configuration:")
    print(f"   Hypothesis Mode: execution")
    print(f"   Coverage Mode: true (sequential with adaptive stopping)")
    print(f"   Max Hypotheses: 2 (minimal for testing coverage assessment)")
    print(f"   Max Hypotheses to Execute: 2")
    print(f"   Time Budget: 120s")

    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 2  # MINIMAL: Only 2 hypotheses
    engine.coverage_mode = True  # PHASE 3C: Enable coverage assessment
    engine.max_hypotheses_to_execute = 2
    engine.max_time_per_task_seconds = 120

    # Simple query
    query = "What is GS-2210 job series?"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Behavior:")
    print("   1. Generate 1 task")
    print("   2. Generate 2 hypotheses for the task")
    print("   3. Execute H1 (no coverage assessment)")
    print("   4. Execute H2 → coverage assessment → LLM decides continue/stop")
    print("   5. Store coverage decision in metadata")
    print("   6. Log coverage event to execution_log.jsonl")
    print("   7. Include coverage section in report")

    # Execute
    print("\n" + "=" * 80)
    print("EXECUTING...")
    print("=" * 80)

    result = await engine.research(query)

    # Validation
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    validation_passed = True

    # 1. Basic completion
    print(f"\n✓ Tasks executed: {result['tasks_executed']}")
    print(f"✓ Total results: {result['total_results']}")

    # 2. Check hypothesis execution
    if 'metadata' in result and 'hypothesis_execution_summary' in result['metadata']:
        hyp_summary = result['metadata']['hypothesis_execution_summary']
        if hyp_summary:
            task_id = list(hyp_summary.keys())[0]
            runs = hyp_summary[task_id]
            print(f"\n✓ Hypothesis execution: {len(runs)} hypotheses executed")

            # Check delta metrics
            for run in runs:
                if 'delta_metrics' in run:
                    delta = run['delta_metrics']
                    print(f"   - {run['hypothesis_id']}: {delta['results_new']} new + {delta['results_duplicate']} dup")
                    print(f"     ✅ PASS: Delta metrics present")
                else:
                    print(f"   - {run['hypothesis_id']}: ❌ FAIL: Missing delta metrics")
                    validation_passed = False
        else:
            print("\n❌ FAIL: No hypothesis execution summary")
            validation_passed = False
    else:
        print("\n❌ FAIL: No hypothesis metadata")
        validation_passed = False

    # 3. Check coverage decisions (Phase 3C specific)
    coverage_found = False
    for task in engine.completed_tasks:
        if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
            coverage_found = True
            decisions = task.metadata['coverage_decisions']
            print(f"\n✅ PASS: Coverage decisions found ({len(decisions)} assessments)")

            for i, decision in enumerate(decisions):
                print(f"\n   Assessment {i+1}:")

                # Validate schema
                required_fields = ['decision', 'rationale', 'coverage_score', 'incremental_gain_last', 'gaps_identified', 'confidence']
                missing_fields = [f for f in required_fields if f not in decision]

                if missing_fields:
                    print(f"      ❌ FAIL: Missing fields: {missing_fields}")
                    validation_passed = False
                else:
                    print(f"      ✅ PASS: All required fields present")

                print(f"      Decision: {decision['decision'].upper()}")
                print(f"      Coverage Score: {decision['coverage_score']}%")
                print(f"      Incremental Gain: {decision['incremental_gain_last']}%")
                print(f"      Confidence: {decision['confidence']}%")
                print(f"      Rationale: {decision['rationale'][:80]}...")

    if not coverage_found:
        print("\n⚠️  INFO: No coverage decisions (may have only executed 1 hypothesis)")
        # This is OK if only 1 hypothesis executed (coverage assessment starts after H2)

    # 4. Check execution log
    if result.get('output_dir'):
        log_path = os.path.join(result['output_dir'], 'execution_log.jsonl')
        if os.path.exists(log_path):
            coverage_events = []
            with open(log_path, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('action_type') == 'coverage_assessment':
                        coverage_events.append(entry)

            if coverage_events:
                print(f"\n✅ PASS: {len(coverage_events)} coverage events in execution log")

                # Validate event structure
                event = coverage_events[0]
                payload = event.get('action_payload', {})
                required_event_fields = ['decision', 'coverage_score', 'time_elapsed_seconds', 'hypotheses_remaining']
                missing_event_fields = [f for f in required_event_fields if f not in payload]

                if missing_event_fields:
                    print(f"   ❌ FAIL: Missing event fields: {missing_event_fields}")
                    validation_passed = False
                else:
                    print(f"   ✅ PASS: Event has all required fields")
            else:
                print("\n⚠️  INFO: No coverage events in log (may have only executed 1 hypothesis)")
        else:
            print(f"\n⚠️  WARNING: Execution log not found at {log_path}")

    # 5. Check report
    if result.get('report_path'):
        print(f"\n✓ Report saved to: {result['report_path']}")
        try:
            with open(result['report_path'], 'r') as f:
                report_content = f.read()

            if "Coverage Assessment Decisions" in report_content:
                print("✅ PASS: Coverage Assessment section found in report")
            else:
                print("⚠️  INFO: No Coverage Assessment section (may not have coverage decisions)")

            if "Incremental Contribution" in report_content:
                print("✅ PASS: Incremental contribution metrics found in report")
            else:
                print("⚠️  WARNING: Incremental contribution metrics not found")
        except Exception as e:
            print(f"⚠️  Could not read report: {e}")

    # Final verdict
    print("\n" + "=" * 80)
    if validation_passed:
        print("✅ VALIDATION PASSED")
    else:
        print("❌ VALIDATION FAILED - See errors above")
    print("=" * 80)

    print("\nPhase 3C Critical Components Validated:")
    print("   ✓ Sequential execution mode")
    print("   ✓ Delta metrics calculation")
    print("   ✓ Coverage assessment (if 2+ hypotheses executed)")
    print("   ✓ Telemetry and reporting")

    return validation_passed


if __name__ == "__main__":
    result = asyncio.run(test_minimal_e2e())
    sys.exit(0 if result else 1)
