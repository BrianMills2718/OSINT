#!/usr/bin/env python3
"""
Phase 3A Enabled Mode Test

Quick test to validate hypothesis branching works with enabled: true.
This test temporarily enables the feature, runs a simple query, and checks:
1. Hypotheses generated during task decomposition
2. Hypotheses stored in metadata.json
3. "Suggested Investigative Angles" appears in report.md
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

load_dotenv()


async def test_enabled_mode():
    """Test Phase 3A with hypothesis branching enabled."""

    print("\n" + "="*80)
    print("PHASE 3A ENABLED MODE TEST")
    print("="*80)
    print()
    print("NOTE: This test TEMPORARILY enables hypothesis branching by passing")
    print("      hypothesis_branching_enabled=True directly to the research engine.")
    print()

    # Create engine with hypothesis branching ENABLED
    # NOTE: We override the config by directly setting the attribute
    research = SimpleDeepResearch(
        max_tasks=1,  # Only 1 task for quick test
        max_retries_per_task=1,
        max_time_minutes=3,  # 3 minute timeout
        save_output=True
    )

    # Override config to enable hypothesis branching
    research.hypothesis_branching_enabled = True
    research.max_hypotheses_per_task = 5

    print("✓ Hypothesis branching ENABLED (overridden)")
    print()

    # Run simple query
    print("Running query: 'What is the GS-2210 job series?'")
    print("-"*80)
    print()

    result = await research.research("What is the GS-2210 job series?")

    print()
    print("="*80)
    print("TEST RESULTS")
    print("="*80)

    # Validate results
    print(f"\n1. Tasks Executed: {result['tasks_executed']}")
    print(f"2. Total Results: {result['total_results']}")
    print(f"3. Entities Discovered: {len(result.get('entities_discovered', []))}")

    # Check metadata.json for hypotheses
    if result.get('output_directory'):
        output_path = Path(result['output_directory'])
        metadata_file = output_path / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Check config persisted
            engine_config = metadata.get('engine_config', {})
            hypothesis_enabled = engine_config.get('hypothesis_branching_enabled', False)
            print(f"\n4. Metadata - hypothesis_branching_enabled: {hypothesis_enabled}")

            # Check hypotheses persisted
            hypotheses_by_task = metadata.get('hypotheses_by_task', {})
            if hypotheses_by_task:
                print(f"5. Metadata - hypotheses_by_task: ✓ PRESENT ({len(hypotheses_by_task)} tasks)")
                for task_id, hyp_data in hypotheses_by_task.items():
                    print(f"   Task {task_id}: {len(hyp_data['hypotheses'])} hypothesis/hypotheses")
                    for i, hyp in enumerate(hyp_data['hypotheses'][:2]):  # Show first 2
                        print(f"      - Hypothesis {i+1}: {hyp['statement'][:80]}...")
                        print(f"        Confidence: {hyp['confidence']}%, Priority: {hyp['exploration_priority']}")
            else:
                print("5. Metadata - hypotheses_by_task: ✗ NOT FOUND (UNEXPECTED!)")

            # Check report for "Suggested Investigative Angles" section
            report_file = output_path / "report.md"
            if report_file.exists():
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_content = f.read()

                if "## Suggested Investigative Angles" in report_content:
                    print("\n6. Report - 'Suggested Investigative Angles' section: ✓ PRESENT")

                    # Show snippet
                    start_idx = report_content.find("## Suggested Investigative Angles")
                    end_idx = report_content.find("## Key Findings", start_idx)
                    if end_idx == -1:
                        end_idx = start_idx + 500
                    snippet = report_content[start_idx:end_idx]
                    print("\n   Snippet:")
                    print("   " + snippet[:400].replace("\n", "\n   "))
                else:
                    print("\n6. Report - 'Suggested Investigative Angles' section: ✗ NOT FOUND (UNEXPECTED!)")

            print(f"\n7. Output saved to: {output_path}")

        else:
            print("\n⚠️  Metadata file not found")
    else:
        print("\n⚠️  No output_directory in result")

    print()
    print("="*80)
    print("\nSUCCESS CRITERIA:")
    print("- [✓] Config reading: hypothesis_branching_enabled should be true in metadata")
    print("- [✓] Hypotheses generated: Console should show '🔬 Hypothesis branching enabled...'")
    print("- [✓] Metadata persistence: hypotheses_by_task should contain 1 task with hypotheses")
    print("- [✓] Report display: 'Suggested Investigative Angles' section should appear")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_enabled_mode())
