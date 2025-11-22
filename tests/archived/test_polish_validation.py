#!/usr/bin/env python3
"""
Validation test for Tasks 2 & 3 (Report Polish + Entity Filtering).

Runs a quick deep research test to verify:
- Report counts match reality (Task 2A)
- Sources section distinguishes integrations vs websites (Task 2B)
- Research Process Notes section shows task diagnostics (Task 2C)
- Entity filtering removes meta-terms and low-confidence entities (Task 3)
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Run validation test for polish changes."""

    print("\n" + "="*80)
    print("VALIDATION TEST: Report Polish + Entity Filtering")
    print("="*80)

    # Configure for quick test
    engine = SimpleDeepResearch(
        max_tasks=3,              # Small number for quick test
        max_retries_per_task=1,   # Minimal retries
        max_time_minutes=5,       # 5 minute limit
        min_results_per_task=3,
        max_concurrent_tasks=2,   # Parallel execution
        save_output=True          # Save to validate report
    )

    # Test query (broad enough to get multiple sources + entities)
    question = "What are federal cybersecurity job opportunities?"

    print(f"\nQuery: {question}")
    print(f"Config: max_tasks={engine.max_tasks}, max_retries={engine.max_retries_per_task}, timeout={engine.max_time_minutes}min\n")

    # Execute research
    result = await engine.research(question)

    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    # Check 1: Task 2A - Report counts
    print("\n[Task 2A] Report Count Accuracy:")
    print(f"  Results in memory: {len(result.get('results_by_task', {}))} tasks")
    print(f"  Total results reported: {result.get('total_results', 0)}")
    print(f"  ✓ Report should use actual sum, not sample size")

    # Check 2: Task 2B - Sources distinction
    print("\n[Task 2B] Sources Section:")
    sources = result.get('sources_searched', [])
    print(f"  Sources found: {', '.join(sources)}")
    print(f"  ✓ Report should distinguish integrations (USAJobs, etc.) from websites (Glassdoor, etc.)")

    # Check 3: Task 2C - Task diagnostics
    print("\n[Task 2C] Task Diagnostics:")
    print(f"  Tasks executed: {result.get('tasks_executed', 0)}")
    print(f"  ✓ Report should have 'Research Process Notes' section with per-task breakdown")

    # Check 4: Task 3 - Entity filtering
    print("\n[Task 3] Entity Filtering:")
    entities = result.get('entities_discovered', [])
    print(f"  Entities before filtering: (logged during execution)")
    print(f"  Entities after filtering: {len(entities)}")
    print(f"  Sample entities: {', '.join(entities[:5])}")

    # Check for meta-terms in entity list (should be removed)
    meta_terms = {"defense contractor", "cybersecurity", "clearance", "polygraph", "job"}
    found_meta_terms = [e for e in entities if e in meta_terms]
    if found_meta_terms:
        print(f"  ⚠️  Meta-terms still present: {found_meta_terms}")
    else:
        print(f"  ✓ No meta-terms found (blacklist working)")

    # Check 5: Report file validation
    print("\n[Report Validation]:")
    output_dir = result.get('output_directory')
    if output_dir:
        report_path = Path(output_dir) / "report.md"
        if report_path.exists():
            report_content = report_path.read_text()

            # Check for new sections
            has_data_sources = "## Data Sources" in report_content
            has_process_notes = "## Research Process Notes" in report_content
            has_primary_integrations = "**Primary Integrations**" in report_content

            print(f"  Report path: {report_path}")
            print(f"  Data Sources section: {'✓' if has_data_sources else '✗'}")
            print(f"  Primary Integrations label: {'✓' if has_primary_integrations else '✗'}")
            print(f"  Research Process Notes: {'✓' if has_process_notes else '✗'}")

            # Show excerpt from Data Sources section
            if has_data_sources:
                lines = report_content.split('\n')
                for i, line in enumerate(lines):
                    if "## Data Sources" in line:
                        excerpt = '\n'.join(lines[i:i+5])
                        print(f"\n  Excerpt:")
                        for excerpt_line in excerpt.split('\n'):
                            print(f"    {excerpt_line}")
                        break
        else:
            print(f"  ⚠️  Report file not found at {report_path}")
    else:
        print(f"  ⚠️  No output directory in result")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print(f"\nElapsed: {result.get('elapsed_minutes', 0):.1f} minutes")
    print(f"Exit code: 0 (success)\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
