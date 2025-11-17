#!/usr/bin/env python3
"""
Quick verification that test_phase3c_minimal_e2e.py validation logic works
against the validated artifact from 2025-11-16.

This proves the test script assertions are correct before running a full new E2E.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_artifact(output_dir):
    """Verify Phase 3C artifact using same logic as test_phase3c_minimal_e2e.py"""

    print("=" * 80)
    print("PHASE 3C ARTIFACT VERIFICATION")
    print("=" * 80)
    print(f"\nArtifact: {output_dir}")

    validation_passed = True

    # 1. Check metadata.json exists
    metadata_path = os.path.join(output_dir, 'metadata.json')
    if not os.path.exists(metadata_path):
        print(f"\n❌ FAIL: metadata.json not found at {metadata_path}")
        return False

    print(f"\n✓ Found metadata.json")

    # 2. Load and check hypothesis_execution_summary
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    if 'hypothesis_execution_summary' not in metadata:
        print("\n❌ FAIL: No hypothesis_execution_summary in metadata.json")
        return False

    hyp_summary = metadata['hypothesis_execution_summary']
    if not hyp_summary:
        print("\n❌ FAIL: hypothesis_execution_summary is empty")
        return False

    total_hypotheses = sum(len(runs) for runs in hyp_summary.values())
    print(f"\n✓ Hypothesis execution: {total_hypotheses} total hypotheses across {len(hyp_summary)} tasks")

    # 3. Check delta metrics for all tasks
    for task_id, runs in hyp_summary.items():
        print(f"\n   Task {task_id}:")
        for run in runs:
            if 'delta_metrics' not in run:
                print(f"      H{run['hypothesis_id']}: ❌ FAIL: Missing delta metrics")
                validation_passed = False
            else:
                delta = run['delta_metrics']
                print(f"      H{run['hypothesis_id']}: {delta['results_new']} new + {delta['results_duplicate']} dup")
                print(f"      ✅ PASS: Delta metrics present")

    # 4. Check report.md exists and has coverage section
    report_path = os.path.join(output_dir, 'report.md')
    if not os.path.exists(report_path):
        print(f"\n❌ FAIL: report.md not found at {report_path}")
        validation_passed = False
    else:
        print(f"\n✓ Found report.md")

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

    # 5. Check execution_log.jsonl
    log_path = os.path.join(output_dir, 'execution_log.jsonl')
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
            required_fields = ['decision', 'coverage_score', 'time_elapsed_seconds', 'hypotheses_remaining']
            missing_fields = [f for f in required_fields if f not in payload]

            if missing_fields:
                print(f"   ❌ FAIL: Missing event fields: {missing_fields}")
                validation_passed = False
            else:
                print(f"   ✅ PASS: Event has all required fields")
        else:
            print("\n⚠️  INFO: No coverage events in log (may have only executed 1 hypothesis)")
    else:
        print(f"\n⚠️  WARNING: Execution log not found at {log_path}")

    # Final verdict
    print("\n" + "=" * 80)
    if validation_passed:
        print("✅ VALIDATION PASSED")
    else:
        print("❌ VALIDATION FAILED - See errors above")
    print("=" * 80)

    return validation_passed


if __name__ == "__main__":
    # Test against the provided artifact or default
    if len(sys.argv) > 1:
        artifact_dir = sys.argv[1]
    else:
        artifact_dir = "data/research_output/2025-11-16_04-55-21_what_is_gs_2210_job_series"

    if not os.path.exists(artifact_dir):
        print(f"❌ ERROR: Artifact directory not found: {artifact_dir}")
        sys.exit(1)

    result = verify_artifact(artifact_dir)
    sys.exit(0 if result else 1)
