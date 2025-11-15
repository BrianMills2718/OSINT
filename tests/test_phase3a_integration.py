#!/usr/bin/env python3
"""
Phase 3A Integration Test

Tests that hypothesis branching integration works correctly:
1. Config reading: enabled: true triggers hypothesis generation
2. Workflow integration: hypotheses generated after task decomposition
3. Metadata persistence: hypotheses stored in metadata.json
4. Report display: "Suggested Investigative Angles" section appears in report
5. Disabled mode: enabled: false doesn't impact traditional workflow
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv
from config_loader import Config

load_dotenv()


async def test_integration():
    """Test Phase 3A integration with hypothesis branching enabled."""

    print("\n" + "="*80)
    print("PHASE 3A INTEGRATION TEST")
    print("="*80)
    print()

    # Test 1: Verify config reading
    print("TEST 1: Config Reading")
    print("-"*80)

    # Create engine with hypothesis branching enabled (via config.yaml)
    # NOTE: This test assumes config.yaml has hypothesis_branching.enabled: true
    # If using config_default.yaml (enabled: false), this will test disabled mode

    config = Config()
    raw_config = config.get_raw_config()
    hypothesis_enabled = raw_config.get("research", {}).get("hypothesis_branching", {}).get("enabled", False)

    if hypothesis_enabled:
        print("✓ Hypothesis branching ENABLED in config")
    else:
        print("⚠️  Hypothesis branching DISABLED in config")
        print("   NOTE: To test enabled mode, set hypothesis_branching.enabled: true in config.yaml")

    print()

    # Test 2: Simple research query (2 tasks, 1 minute timeout)
    print("TEST 2: Integration Test - Simple Query")
    print("-"*80)
    print("Query: 'What is the GS-2210 job series?'")
    print(f"Config: hypothesis_branching.enabled = {hypothesis_enabled}")
    print()

    research = SimpleDeepResearch(
        max_tasks=2,  # Quick test - only 2 tasks
        max_retries_per_task=1,
        max_time_minutes=2,  # 2 minute timeout
        save_output=True
    )

    result = await research.research("What is the GS-2210 job series?")

    print()
    print("="*80)
    print("TEST RESULTS")
    print("="*80)

    # Validate results
    print(f"\n1. Tasks Executed: {result['tasks_executed']}")
    print(f"2. Total Results: {result['total_results']}")
    print(f"3. Entities Discovered: {len(result.get('entities_discovered', []))}")

    # Test 3: Check metadata.json for hypotheses
    if result.get('output_directory'):
        output_path = Path(result['output_directory'])
        metadata_file = output_path / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Check config persisted
            engine_config = metadata.get('engine_config', {})
            print(f"\n4. Metadata - hypothesis_branching_enabled: {engine_config.get('hypothesis_branching_enabled', 'NOT FOUND')}")

            # Check hypotheses persisted
            hypotheses_by_task = metadata.get('hypotheses_by_task', {})
            if hypotheses_by_task:
                print(f"5. Metadata - hypotheses_by_task: {len(hypotheses_by_task)} tasks with hypotheses")
                for task_id, hyp_data in hypotheses_by_task.items():
                    print(f"   Task {task_id}: {len(hyp_data['hypotheses'])} hypothesis/hypotheses generated")
            else:
                print("5. Metadata - hypotheses_by_task: NOT FOUND (expected if disabled)")

        # Test 4: Check report for "Suggested Investigative Angles" section
        report_file = output_path / "report.md"
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = f.read()

            if "## Suggested Investigative Angles" in report_content:
                print("\n6. Report - 'Suggested Investigative Angles' section: PRESENT")
            else:
                print("\n6. Report - 'Suggested Investigative Angles' section: NOT FOUND (expected if disabled)")

        print(f"\n7. Output saved to: {output_path}")

    print()
    print("="*80)

    # Success criteria
    if hypothesis_enabled:
        print("\nEXPECTED BEHAVIOR (enabled: true):")
        print("- [✓] Config reading: hypothesis_branching_enabled should be true")
        print("- [✓] Metadata: hypotheses_by_task should contain 2 tasks")
        print("- [✓] Report: 'Suggested Investigative Angles' section should appear")
        print("- [✓] Console: Should see '🔬 Hypothesis branching enabled...' message")
    else:
        print("\nEXPECTED BEHAVIOR (enabled: false):")
        print("- [✓] Config reading: hypothesis_branching_enabled should be false")
        print("- [✓] Metadata: hypotheses_by_task should NOT exist")
        print("- [✓] Report: 'Suggested Investigative Angles' section should NOT appear")
        print("- [✓] Console: Should NOT see hypothesis generation messages")
        print("- [✓] Traditional workflow unchanged (no performance impact)")

    print()
    print("="*80)
    print("\nTo test ENABLED mode:")
    print("1. Create config.yaml (copy from config_default.yaml)")
    print("2. Set hypothesis_branching.enabled: true")
    print("3. Run this test again")
    print()
    print("To test DISABLED mode:")
    print("1. Use config_default.yaml (default: enabled: false)")
    print("2. OR set hypothesis_branching.enabled: false in config.yaml")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_integration())
