#!/usr/bin/env python3
"""
Traditional Deep Research Test: NSPM-7 Investigation

Same query as Phase 3C test, but using traditional approach:
- No hypothesis branching (hypothesis_mode: "off")
- Parallel task execution (coverage_mode: False)
- Single query per task, no adaptive depth

This allows direct comparison with Phase 3C results.
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


async def test_nspm7_traditional():
    """Traditional deep research for NSPM-7 (no hypothesis branching)."""

    print("=" * 80)
    print("TRADITIONAL DEEP RESEARCH: NSPM-7 INVESTIGATION")
    print("=" * 80)
    print("\nMode: Traditional task decomposition (NO hypothesis branching)")
    print("Expected: Single query per task, parallel execution, no adaptive depth")
    print()

    # Create engine with same basic config
    engine = SimpleDeepResearch(
        max_tasks=5,
        max_retries_per_task=2,
        max_time_minutes=15,
        save_output=True
    )

    # Configure for TRADITIONAL mode (no hypothesis branching)
    print("📋 Configuration:")
    print(f"   Hypothesis Mode: off (traditional task decomposition)")
    print(f"   Coverage Mode: false (parallel execution, no coverage assessment)")
    print(f"   Expected: Single query per task, no adaptive stopping")

    engine.hypothesis_mode = "off"  # Traditional mode
    engine.hypothesis_branching_enabled = False
    engine.coverage_mode = False  # Parallel execution

    # SAME QUERY as Phase 3C test
    query = "anomalous and potentially overlooked government activity related to NATIONAL SECURITY PRESIDENTIAL MEMORANDUM/NSPM-7 especially that hasn't been widely reported"

    print(f"\n🔍 Query: {query}")
    print("\nExpected Traditional Behavior:")
    print("   - Task decomposition into subtasks")
    print("   - Single query per task (no hypothesis exploration)")
    print("   - Parallel execution (all tasks at once)")
    print("   - No coverage assessment or adaptive stopping")
    print("   - Fixed depth (no iterative refinement)")

    # Execute
    print("\n" + "=" * 80)
    print("EXECUTING TRADITIONAL RESEARCH...")
    print("=" * 80)

    result = await engine.research(query)

    # Validation
    print("\n" + "=" * 80)
    print("TRADITIONAL RESULTS")
    print("=" * 80)

    # 1. Basic completion
    print(f"\n✓ Tasks executed: {result['tasks_executed']}")
    print(f"✓ Total results: {result['total_results']}")
    print(f"✓ Sources used: {', '.join(result['sources_searched'])}")
    print(f"✓ Entities discovered: {len(result['entities_discovered'])}")

    # 2. Check for hypothesis execution (should be NONE in traditional mode)
    if result.get('output_directory'):
        metadata_path = os.path.join(result['output_directory'], 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            if 'hypothesis_execution_summary' in metadata and metadata['hypothesis_execution_summary']:
                print("\n⚠️  WARNING: Hypothesis execution found (should be NONE in traditional mode)")
            else:
                print("\n✓ Confirmed: No hypothesis execution (traditional mode)")

    # 3. Report quality
    if result.get('output_directory'):
        report_path = os.path.join(result['output_directory'], 'report.md')
        print(f"\n✓ Report saved to: {report_path}")

        try:
            with open(report_path, 'r') as f:
                report_content = f.read()

            nspm7_mentioned = "NSPM-7" in report_content or "NSPM 7" in report_content
            print(f"\n   NSPM-7 mentioned in report: {'✅ Yes' if nspm7_mentioned else '❌ No'}")

            sections = report_content.count("\n##")
            print(f"   Report depth: {sections} major sections")

        except Exception as e:
            print(f"⚠️  Could not analyze report: {e}")

    print("\n" + "=" * 80)
    print("✅ TRADITIONAL RESEARCH COMPLETE")
    print("=" * 80)

    print("\nTraditional Features:")
    print("   ✓ Task decomposition")
    print("   ✓ Parallel execution (no sequential hypothesis testing)")
    print("   ✓ Single query per task (no adaptive depth)")
    print("   ✓ No coverage assessment")
    print("   ✓ Fixed search depth")

    if result.get('output_directory'):
        print(f"\nFull Report: {result['output_directory']}/report.md")
        print(f"Raw Data: {result['output_directory']}/results.json")

    print("\n" + "=" * 80)
    print("COMPARISON WITH PHASE 3C:")
    print("=" * 80)
    print("\nPhase 3C (Hypothesis Branching):")
    print("   - 124 unique results")
    print("   - 5 hypotheses executed with adaptive stopping")
    print("   - Coverage assessment guided depth")
    print("   - Found specific Treasury/IRS directives, FARA shifts")
    print("\nTraditional (this run):")
    print(f"   - {result['total_results']} results")
    print(f"   - {result['tasks_executed']} tasks (single query each)")
    print("   - No adaptive depth or coverage assessment")

    return True


if __name__ == "__main__":
    result = asyncio.run(test_nspm7_traditional())
    sys.exit(0 if result else 1)
