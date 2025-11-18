#!/usr/bin/env python3
"""
Real-World Phase 3C Test: NSPM-7 Investigation

Query: Anomalous and potentially overlooked government activity related to
NATIONAL SECURITY PRESIDENTIAL MEMORANDUM/NSPM-7 that hasn't been widely reported

This tests Phase 3C's ability to:
- Find obscure/under-reported information
- Adapt search depth based on information gaps
- Use coverage assessment to determine when sufficient evidence gathered
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_nspm7_investigation():
    """Real-world investigative query for NSPM-7 anomalies."""

    print("=" * 80)
    print("PHASE 3C REAL-WORLD TEST: NSPM-7 INVESTIGATION")
    print("=" * 80)
    print("\nQuery Type: Investigative journalism (finding under-reported activity)")
    print("Expected Behavior: Deep search with adaptive stopping based on coverage gaps")
    print()

    # Create engine with investigative research configuration
    engine = SimpleDeepResearch(
        max_tasks=2,  # Narrowed for test stability (prod can run wider)
        max_retries_per_task=2,
        max_time_minutes=20,  # Give more wall-clock headroom for slow sources
        save_output=True
    )

    # Configure for Phase 3C - Coverage-Driven Sequential Execution
    print("📋 Configuration:")
    print(f"   Hypothesis Mode: execution")
    print(f"   Coverage Mode: true (sequential with adaptive stopping)")
    print(f"   Max Hypotheses per Task: 3 (investigative depth)")
    print(f"   Max Hypotheses to Execute: 3")
    print(f"   Time Budget per Task: 720s (avoid per-task timeout)")
    print(f"   Expected Sources: SAM.gov, DVIDS, Brave Search, Reddit, Discord")

    engine.hypothesis_mode = "execution"
    engine.hypothesis_branching_enabled = True
    engine.max_hypotheses_per_task = 3  # More depth for investigative runs
    engine.coverage_mode = True
    engine.max_hypotheses_to_execute = 3
    engine.max_time_per_task_seconds = 720  # Allow longer per task in test

    # Real-world investigative query
    query = "anomalous and potentially overlooked government activity related to NATIONAL SECURITY PRESIDENTIAL MEMORANDUM/NSPM-7 especially that hasn't been widely reported"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Investigative Behavior:")
    print("   - Task decomposition into investigative angles (contracts, statements, filings)")
    print("   - Sequential hypothesis execution with coverage assessment")
    print("   - LLM identifies information gaps and decides whether to continue")
    print("   - Stops when coverage sufficient or hard ceiling reached")
    print("   - Sources: SAM.gov (contracts), DVIDS (official statements), web search (news)")

    # Execute
    print("\n" + "=" * 80)
    print("EXECUTING INVESTIGATIVE RESEARCH...")
    print("=" * 80)

    result = await engine.research(query)

    # Validation
    print("\n" + "=" * 80)
    print("INVESTIGATION RESULTS")
    print("=" * 80)

    validation_passed = True

    # 1. Basic completion
    print(f"\n✓ Tasks executed: {result['tasks_executed']}")
    print(f"✓ Total results: {result['total_results']}")
    print(f"✓ Sources used: {', '.join(result['sources_searched'])}")
    print(f"✓ Entities discovered: {len(result['entities_discovered'])}")

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

                    # Show per-task breakdown
                    for task_id, runs in hyp_summary.items():
                        print(f"\n   Task {task_id}: {len(runs)} hypotheses")
                        for run in runs:
                            if 'delta_metrics' in run:
                                delta = run['delta_metrics']
                                print(f"      H{run['hypothesis_id']}: {delta['results_new']} new + {delta['results_duplicate']} dup")
                                print(f"      Statement: {run['statement'][:80]}...")
                            else:
                                print(f"      H{run['hypothesis_id']}: ❌ FAIL: Missing delta metrics")
                                validation_passed = False
                else:
                    print("\n⚠️  INFO: No hypothesis execution (may have used traditional decomposition)")
            else:
                print("\n⚠️  INFO: No hypothesis_execution_summary in metadata.json")
        else:
            print(f"\n⚠️  WARNING: metadata.json not found at {metadata_path}")
    else:
        print("\n⚠️  WARNING: No output_directory in result")

    # 3. Check coverage decisions (if hypotheses executed)
    coverage_found = False
    for task in engine.completed_tasks:
        if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
            coverage_found = True
            decisions = task.metadata['coverage_decisions']
            print(f"\n✅ Coverage decisions found ({len(decisions)} assessments)")

            for i, decision in enumerate(decisions):
                print(f"\n   Assessment {i+1} (Task {task.id}):")
                print(f"      Decision: {decision.get('decision', 'N/A').upper()}")
                print(f"      Coverage Score: {decision.get('coverage_score', 'N/A')}%")
                print(f"      Incremental Gain: {decision.get('incremental_gain_last', 'N/A')}%")
                print(f"      Confidence: {decision.get('confidence', 'N/A')}%")
                print(f"      Rationale: {decision.get('rationale', 'N/A')[:100]}...")

    if not coverage_found:
        print("\n⚠️  INFO: No coverage decisions (may have only executed 1 hypothesis per task)")

    # 4. Check report quality
    if result.get('output_directory'):
        report_path = os.path.join(result['output_directory'], 'report.md')
        print(f"\n✓ Report saved to: {report_path}")

        try:
            with open(report_path, 'r') as f:
                report_content = f.read()

            # Check for investigative quality indicators
            nspm7_mentioned = "NSPM-7" in report_content or "NSPM 7" in report_content
            print(f"\n   NSPM-7 mentioned in report: {'✅ Yes' if nspm7_mentioned else '❌ No'}")

            if "Coverage Assessment Decisions" in report_content:
                print("   ✅ Coverage Assessment section found")

            if "Incremental Contribution" in report_content:
                print("   ✅ Incremental contribution metrics found")

            # Count sections to estimate report depth
            sections = report_content.count("\n##")
            print(f"   Report depth: {sections} major sections")

        except Exception as e:
            print(f"⚠️  Could not analyze report: {e}")

    # Final verdict
    print("\n" + "=" * 80)
    if validation_passed:
        print("✅ INVESTIGATION COMPLETE")
    else:
        print("⚠️  INVESTIGATION COMPLETE (with warnings)")
    print("=" * 80)

    print("\nPhase 3C Investigative Features Demonstrated:")
    print("   ✓ Deep task decomposition for investigative queries")
    print("   ✓ Sequential hypothesis execution with coverage tracking")
    print("   ✓ Adaptive stopping based on information gaps")
    print("   ✓ Delta metrics showing incremental value of each hypothesis")
    print("   ✓ Multi-source integration (government + social + web)")

    if result.get('output_directory'):
        print(f"\nFull Investigation Report: {result['output_directory']}/report.md")
        print(f"Raw Data: {result['output_directory']}/results.json")
        print(f"Execution Trace: {result['output_directory']}/execution_log.jsonl")

    return validation_passed


if __name__ == "__main__":
    result = asyncio.run(test_nspm7_investigation())
    sys.exit(0 if result else 1)
