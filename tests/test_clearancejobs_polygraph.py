#!/usr/bin/env python3
"""
Test ClearanceJobs clearance extraction with TS/SCI + Polygraph query.

This validates Codex Fix #1: Clearance extraction Unicode punctuation normalization.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch


async def main():
    print("="*80)
    print("CLEARANCEJOBS VALIDATION TEST: TS/SCI + Polygraph Clearance Extraction")
    print("="*80)
    print()
    print("Configuration:")
    print("  - Model: gemini/gemini-2.5-flash (from config_default.yaml)")
    print("  - Max Tasks: 2")
    print("  - Max Retries: 1")
    print("  - Timeout: 5 minutes")
    print("  - Query: 'What TS/SCI cybersecurity jobs require polygraph clearance?'")
    print()
    print("Expected Behavior:")
    print("  - LLM should select ClearanceJobs as relevant source")
    print("  - Clearance levels should be extracted correctly:")
    print("    - TS/SCI with Poly (most specific)")
    print("    - TS/SCI (if poly not mentioned)")
    print("    - Top Secret (fallback)")
    print()
    print("="*80)
    print()

    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=5,
        save_output=True,
        output_dir='data/research_output'
    )

    result = await engine.research('What TS/SCI cybersecurity jobs require polygraph clearance?')

    print()
    print("="*80)
    print("CLEARANCEJOBS VALIDATION RESULTS")
    print("="*80)
    print()

    # Check if ClearanceJobs was used
    sources = result.get('sources_searched', [])
    clearancejobs_used = any('ClearanceJobs' in s for s in sources)

    print(f"[{'PASS' if clearancejobs_used else 'FAIL'}] ClearanceJobs selected: {clearancejobs_used}")
    if not clearancejobs_used:
        print("  Available sources:", sources)
        print("  WARNING: ClearanceJobs not selected by LLM - cannot validate clearance extraction")

    # Extract ClearanceJobs results
    clearancejobs_results = []
    for task_results in result.get('results_by_task', {}).values():
        for r in task_results.get('results', []):
            if r.get('source') == 'ClearanceJobs':
                clearancejobs_results.append(r)

    print(f"\nClearanceJobs Results: {len(clearancejobs_results)} jobs found")

    if clearancejobs_results:
        print("\nClearance Extraction Validation:")

        # Count clearance levels
        clearance_counts = {}
        missing_clearance = []

        for i, job in enumerate(clearancejobs_results[:10], 1):  # Check first 10
            clearance = job.get('clearance_level') or job.get('clearance', '')
            title = job.get('title', 'Unknown')
            company = job.get('company', 'Unknown')

            if clearance:
                clearance_counts[clearance] = clearance_counts.get(clearance, 0) + 1
            else:
                missing_clearance.append(f"{i}. {title} ({company})")

        # Display clearance distribution
        print("\nClearance Level Distribution:")
        for level, count in sorted(clearance_counts.items(), key=lambda x: -x[1]):
            print(f"  {level}: {count} jobs")

        if missing_clearance:
            print(f"\n[WARN] {len(missing_clearance)} jobs missing clearance_level field:")
            for job in missing_clearance[:5]:  # Show first 5
                print(f"  {job}")

        # Validate expected clearances are present
        has_poly = any('Poly' in c for c in clearance_counts.keys())
        has_ts_sci = any('TS/SCI' in c for c in clearance_counts.keys())

        print(f"\n[{'PASS' if has_poly else 'WARN'}] Polygraph clearances found: {has_poly}")
        print(f"[{'PASS' if has_ts_sci else 'WARN'}] TS/SCI clearances found: {has_ts_sci}")

        # Sample jobs
        print("\nSample ClearanceJobs Results (first 3):")
        for i, job in enumerate(clearancejobs_results[:3], 1):
            print(f"\n{i}. {job.get('title', 'Unknown')}")
            print(f"   Company: {job.get('company', 'Unknown')}")
            print(f"   Clearance: {job.get('clearance_level') or job.get('clearance', 'MISSING')}")
            print(f"   Location: {job.get('location', 'Unknown')}")
    else:
        print("[WARN] No ClearanceJobs results found - cannot validate clearance extraction")

    # Deduplication stats
    print(f"\n[INFO] Deduplication Stats:")
    print(f"  Total results: {result.get('total_results', 0)}")
    print(f"  Duplicates removed: {result.get('duplicates_removed', 'N/A')}")
    print(f"  Results before dedup: {result.get('results_before_dedup', 'N/A')}")

    # Entity normalization check
    entities = result.get('entities_discovered', [])
    print(f"\n[INFO] Entity Extraction:")
    print(f"  Total entities: {len(entities)}")
    print(f"  Entities: {', '.join(entities[:10])}")

    print()
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    asyncio.run(main())
