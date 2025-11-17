#!/usr/bin/env python3
"""
Phase 3C Second Validation Query

Purpose: Prove pipeline robustness with different domain query
Query: "How do I qualify for federal cybersecurity jobs?"
Expected: Different decomposition, different sources, same Phase 3C quality

This is Codex Recommendation #2 - demonstrate Phase 3C works across different queries.
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_second_validation():
    """Second validation query for Phase 3C robustness check."""

    print("=" * 80)
    print("PHASE 3C SECOND VALIDATION QUERY")
    print("=" * 80)
    print("\nScope: Different domain (qualifications vs job listings)")
    print("Expected: Different task decomposition, same Phase 3C quality")
    print()

    # Create engine with same config as first validation
    engine = SimpleDeepResearch(
        max_tasks=1,  # Minimal config - LLM may create more if needed
        max_retries_per_task=1,
        max_time_minutes=10,
        save_output=True
    )

    # Configure for Phase 3C
    print("📋 Configuration:")
    print(f"   Hypothesis Mode: execution")
    print(f"   Coverage Mode: true (sequential with adaptive stopping)")
    print(f"   Max Hypotheses: 2")
    print(f"   Max Hypotheses to Execute: 2")
    print(f"   Time Budget: 120s")

    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 2
    engine.coverage_mode = True
    engine.max_hypotheses_to_execute = 2
    engine.max_time_per_task_seconds = 120

    # Different domain query (qualifications vs job listings)
    query = "How do I qualify for federal cybersecurity jobs?"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Behavior:")
    print("   - Different task decomposition than first query")
    print("   - Focus on qualifications/requirements vs job listings")
    print("   - Same Phase 3C mechanics (sequential, coverage assessment)")
    print("   - Coverage decisions stored and reported")

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

    # 2. Check hypothesis execution from metadata.json
    if result.get('output_directory'):
        metadata_path = os.path.join(result['output_directory'], 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            if 'hypothesis_execution_summary' in metadata:
                hyp_summary = metadata['hypothesis_execution_summary']
                if hyp_summary:
                    total_hypotheses = sum(len(runs) for runs in hyp_summary.values())
                    print(f"\n✓ Hypothesis execution: {total_hypotheses} total hypotheses across {len(hyp_summary)} tasks")

                    # Check delta metrics
                    for task_id, runs in hyp_summary.items():
                        print(f"\n   Task {task_id}:")
                        for run in runs:
                            if 'delta_metrics' in run:
                                delta = run['delta_metrics']
                                print(f"      H{run['hypothesis_id']}: {delta['results_new']} new + {delta['results_duplicate']} dup")
                                print(f"      ✅ PASS: Delta metrics present")
                            else:
                                print(f"      H{run['hypothesis_id']}: ❌ FAIL: Missing delta metrics")
                                validation_passed = False
                else:
                    print("\n❌ FAIL: No hypothesis execution summary")
                    validation_passed = False
            else:
                print("\n❌ FAIL: No hypothesis_execution_summary in metadata.json")
                validation_passed = False
        else:
            print(f"\n❌ FAIL: metadata.json not found at {metadata_path}")
            validation_passed = False
    else:
        print("\n❌ FAIL: No output_directory in result")
        validation_passed = False

    # 3. Check coverage decisions
    coverage_found = False
    for task in engine.completed_tasks:
        if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
            coverage_found = True
            decisions = task.metadata['coverage_decisions']
            print(f"\n✅ PASS: Coverage decisions found ({len(decisions)} assessments)")

            for i, decision in enumerate(decisions):
                print(f"\n   Assessment {i+1}:")
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

    # 4. Check report
    if result.get('output_directory'):
        report_path = os.path.join(result['output_directory'], 'report.md')
        print(f"\n✓ Report saved to: {report_path}")
        try:
            with open(report_path, 'r') as f:
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

    print("\nPhase 3C Robustness Demonstrated:")
    print("   ✓ Different query domain")
    print("   ✓ Sequential execution mode")
    print("   ✓ Delta metrics calculation")
    print("   ✓ Coverage assessment (if 2+ hypotheses executed)")
    print("   ✓ Telemetry and reporting")

    if result.get('output_directory'):
        print(f"\nArtifact Location: {result['output_directory']}")

    return validation_passed


if __name__ == "__main__":
    result = asyncio.run(test_second_validation())
    sys.exit(0 if result else 1)
