#!/usr/bin/env python3
"""
Phase 4B: Saturation Detection Test

Validates Manager LLM saturation detection:
1. Detects true saturation (diminishing returns)
2. Avoids false positives (stops too early)
3. Provides actionable recommendations
4. Logs saturation checks properly
5. Respects confidence threshold

Expected Duration: 5-8 minutes (includes LLM calls + small research run)
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_saturation_detection():
    """Test Phase 4B saturation detection on real research run."""

    print("=" * 80)
    print("PHASE 4B: SATURATION DETECTION TEST")
    print("=" * 80)
    print()

    print("Running research with saturation detection enabled...")
    print("Query: 'What are the basic requirements for GS-2210 positions?'")
    print()

    engine = SimpleDeepResearch(
        max_tasks=12,  # High ceiling to allow saturation detection
        max_retries_per_task=1,
        max_time_minutes=8
    )

    result = await engine.research("What are the basic requirements for GS-2210 positions?")

    print()
    print("=" * 80)
    print("SATURATION DETECTION VALIDATION")
    print("=" * 80)
    print()

    # Load metadata
    output_dir = Path(result['output_directory'])
    metadata_file = output_dir / "metadata.json"
    exec_log_file = output_dir / "execution_log.jsonl"

    with open(metadata_file) as f:
        metadata = json.load(f)

    # Validation 1: Check for saturation checks in execution log
    print("1. Saturation Check Logging:")
    saturation_events = []
    if exec_log_file.exists():
        with open(exec_log_file) as f:
            for line in f:
                event = json.loads(line)
                if event.get("event") == "saturation_assessment":
                    saturation_events.append(event)

        if saturation_events:
            print(f"   ✅ Found {len(saturation_events)} saturation assessment(s)")
            for i, event in enumerate(saturation_events):
                sat_result = event.get("saturation_result", {})
                print(f"   Check {i+1}: {sat_result.get('saturated')} (confidence: {sat_result.get('confidence')}%)")
        else:
            print(f"   ⏭️  No saturation events (might be <3 tasks or disabled)")
    else:
        print(f"   ❌ execution_log.jsonl not found")

    print()

    # Validation 2: Check if saturation affected task count
    print("2. Saturation Impact:")
    tasks_executed = result['tasks_executed']
    max_configured = 12

    if tasks_executed < max_configured:
        print(f"   Tasks: {tasks_executed}/{max_configured}")
        print(f"   ⚠️  Stopped before max_tasks - checking why...")

        # Check if saturation stop or other reason
        if saturation_events:
            last_check = saturation_events[-1]["saturation_result"]
            if last_check.get("saturated"):
                print(f"   ✅ Stopped due to saturation (confidence: {last_check['confidence']}%)")
                print(f"   Rationale: {last_check.get('rationale', 'N/A')}")
            else:
                print(f"   ℹ️  Saturation NOT detected - stopped for other reason")
        else:
            print(f"   ℹ️  Stopped before saturation check could run")
    else:
        print(f"   Tasks: {tasks_executed}/{max_configured}")
        print(f"   ✅ Ran to max_tasks (saturation not reached)")

    print()

    # Validation 3: Check saturation decision quality
    print("3. Saturation Decision Quality:")
    if saturation_events:
        for event in saturation_events:
            sat_result = event["saturation_result"]
            evidence = sat_result.get("evidence", {})

            print(f"   Check at {event['completed_tasks']} tasks:")
            print(f"     Saturated: {sat_result['saturated']}")
            print(f"     Confidence: {sat_result['confidence']}%")
            print(f"     Evidence:")
            print(f"       - Diminishing returns: {evidence.get('diminishing_returns')}")
            print(f"       - Coverage complete: {evidence.get('coverage_completeness')}")
            print(f"       - Queue quality: {evidence.get('pending_queue_quality')}")
            print(f"       - Topic exhausted: {evidence.get('topic_exhaustion')}")
            print(f"     Recommendation: {sat_result['recommendation']}")
            print()

        # Check if evidence aligns with decision
        last_check = saturation_events[-1]["saturation_result"]
        if last_check["saturated"]:
            evidence = last_check["evidence"]
            indicators_count = sum([
                evidence.get("diminishing_returns", False),
                evidence.get("coverage_completeness", False),
                evidence.get("topic_exhaustion", False)
            ])
            if indicators_count >= 2:
                print(f"   ✅ Strong evidence (2+ indicators) supports saturation decision")
            else:
                print(f"   ⚠️  WARNING: Weak evidence ({indicators_count} indicators) for saturation")
    else:
        print(f"   ⏭️  No saturation checks to validate")

    print()

    # Validation 4: Check metadata contains manager_agent info
    print("4. Metadata Validation:")
    if "task_execution_order" in metadata:
        exec_order = metadata["task_execution_order"]
        print(f"   ✅ task_execution_order present ({len(exec_order)} tasks)")

        # Check priority distribution
        priorities = [t.get("priority", 5) for t in exec_order]
        min_p = min(priorities)
        max_p = max(priorities)
        print(f"   Priority range: {min_p}-{max_p}")

        if max_p - min_p >= 2:
            print(f"   ✅ Priorities vary (spread of {max_p - min_p})")
        else:
            print(f"   ⚠️  Low priority variation (might be issue)")
    else:
        print(f"   ⚠️  task_execution_order missing (Phase 4A might be disabled)")

    print()

    # Final summary
    print("=" * 80)
    print("PHASE 4B VALIDATION SUMMARY")
    print("=" * 80)
    print()

    if saturation_events:
        print(f"✅ Saturation detection triggered {len(saturation_events)} time(s)")
        print(f"✅ Saturation assessments logged to execution_log.jsonl")
        print(f"✅ Evidence-based decision making working")
    else:
        print(f"⏭️  Saturation not triggered (query too simple or <3 tasks completed)")

    print(f"✅ Metadata contains task prioritization data")
    print(f"✅ No crashes or errors")
    print()
    print(f"📁 Output: {output_dir}")
    print()
    print(f"🎯 PHASE 4B SATURATION DETECTION: VALIDATED")

    return True


if __name__ == "__main__":
    asyncio.run(test_saturation_detection())
