#!/usr/bin/env python3
"""
Phase 1 & 2 Validation Test

Tests both LLM-driven intelligence features together:
- Phase 1: Mentor-style reasoning notes in reports
- Phase 2: Source re-selection on retry based on performance

Query designed to trigger multiple retries and source adjustments.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv

load_dotenv()

async def test_phase1_phase2_validation():
    """
    Validation test for Phase 1 & 2 features.

    Query Strategy:
    - Use a query likely to trigger retries (sparse results initially)
    - Monitor for source re-selection on retry attempts
    - Verify reasoning notes appear in final report

    Success Criteria:
    Phase 1:
    - Research Process Notes section appears in report
    - Reasoning includes filtering strategy, interesting decisions, patterns
    - Reasoning is educational (not just restating decisions)

    Phase 2:
    - Source performance data collected on retry
    - LLM makes intelligent keep/drop/add decisions
    - Adjusted sources applied on next retry (skip source selection)
    """

    print("=" * 80)
    print("PHASE 1 & 2 VALIDATION TEST")
    print("=" * 80)
    print()

    # Test query: Designed to trigger retries due to initial sparse/low-quality results
    # "classified programs" is sensitive topic with limited public data
    # Should trigger source re-selection as LLM realizes need for different sources
    test_query = "What classified intelligence programs does the NSA operate?"

    print(f"Test Query: {test_query}")
    print()
    print("Configuration:")
    print("- max_tasks: 3 (keep test focused)")
    print("- max_retries_per_task: 2 (allow retry for source adjustment)")
    print("- max_time_minutes: 10 (sufficient for 3 tasks + retries)")
    print()
    print("Expected Behavior:")
    print("- Phase 1: Reasoning notes captured for each relevance evaluation")
    print("- Phase 2: Source adjustments on retry if poor performance detected")
    print()

    research = SimpleDeepResearch(
        max_tasks=3,
        max_concurrent_tasks=2,
        max_retries_per_task=2,  # Allow retries for source re-selection
        max_time_minutes=10,
        min_results_per_task=3,
        save_output=True
    )

    print("Starting deep research...")
    print()

    result = await research.research(test_query)

    print()
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()

    # Phase 1 Validation: Check for reasoning notes
    print("PHASE 1 VALIDATION: Mentor-Style Reasoning Notes")
    print("-" * 80)

    if result.get("report"):
        report = result["report"]

        # Check if Research Process Notes section exists
        if "## Research Process Notes" in report:
            print("[PASS] Research Process Notes section found in report")

            # Extract the section
            sections = report.split("## ")
            process_notes = None
            for section in sections:
                if section.startswith("Research Process Notes"):
                    process_notes = section
                    break

            if process_notes:
                # Check for key components
                has_filtering_strategy = "Filtering Strategy" in process_notes or "filtering strategy" in process_notes
                has_interesting_decisions = "Interesting Decisions" in process_notes or "interesting decisions" in process_notes
                has_patterns = "Patterns Noticed" in process_notes or "patterns noticed" in process_notes

                print(f"  - Filtering Strategy: {'[PASS]' if has_filtering_strategy else '[FAIL]'}")
                print(f"  - Interesting Decisions: {'[PASS]' if has_interesting_decisions else '[FAIL]'}")
                print(f"  - Patterns Noticed: {'[PASS]' if has_patterns else '[FAIL]'}")

                # Show a sample
                print()
                print("Sample Reasoning (first 500 chars):")
                print(process_notes[:500])
                print("...")
            else:
                print("[FAIL] Could not extract Research Process Notes section")
        else:
            print("[FAIL] Research Process Notes section NOT found in report")
    else:
        print("[FAIL] No report generated")

    print()

    # Phase 2 Validation: Check execution log for source adjustments
    print("PHASE 2 VALIDATION: Source Re-Selection on Retry")
    print("-" * 80)

    # Check output directory for execution log
    output_dir = result.get("output_directory")
    if output_dir:
        exec_log_path = Path(output_dir) / "execution_log.jsonl"
        if exec_log_path.exists():
            print(f"[PASS] Execution log found: {exec_log_path}")

            # Parse log for reformulation events
            import json
            reformulation_count = 0
            source_adjustments_found = 0

            with open(exec_log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("event") == "query_reformulation":
                            reformulation_count += 1
                            # Check if source_adjustments were made
                            if "source_adjustments" in str(entry):
                                source_adjustments_found += 1

            print(f"  - Reformulations: {reformulation_count}")
            print(f"  - Source adjustments: {source_adjustments_found}")

            if source_adjustments_found > 0:
                print("[PASS] Phase 2 source re-selection triggered")
            elif reformulation_count > 0:
                print("[INFO] Reformulations occurred but no source adjustments (LLM chose to keep all sources)")
            else:
                print("[INFO] No retries occurred (all tasks succeeded on first attempt)")
        else:
            print(f"[INFO] No execution log at {exec_log_path}")
    else:
        print("[INFO] No output directory (save_output may be disabled)")

    print()

    # Summary Statistics
    print("SUMMARY STATISTICS")
    print("-" * 80)
    print(f"Tasks Executed: {result.get('tasks_executed', 0)}")
    print(f"Tasks Completed: {len(result.get('completed_tasks', []))}")
    print(f"Tasks Failed: {len(result.get('failed_tasks', []))}")
    print(f"Total Results: {result.get('total_results', 0)}")
    print(f"Entities Discovered: {result.get('entities_discovered', 0)}")
    print(f"Runtime: {result.get('time_elapsed', 'unknown')}")

    if output_dir:
        print(f"\nOutput Directory: {output_dir}")
        print("  - report.md (final report with reasoning notes)")
        print("  - results.json (structured data)")
        print("  - metadata.json (execution metadata)")
        print("  - execution_log.jsonl (detailed event log)")

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print()

    # Return result for inspection
    return result

if __name__ == "__main__":
    print("Activating virtual environment...")
    print(f"Python: {sys.executable}")
    print()

    result = asyncio.run(test_phase1_phase2_validation())

    print()
    print("Next Steps:")
    print("1. Review the report.md file in the output directory")
    print("2. Check Research Process Notes for reasoning quality")
    print("3. Review execution_log.jsonl for source re-selection events")
    print("4. Verify reasoning is educational and transparent")
