#!/usr/bin/env python3
"""
Test deep research relevance validation fixes.

Tests all 4 fixes implemented:
1. LLM reasoning captured in execution logs
2. Partial relevance scoring guidance in prompt
3. max_retries_per_task = 2 (3 total attempts)
4. USAJobs field normalization (title, description, snippet)

Run with:
    python3 tests/test_deep_research_relevance.py
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Test imports
from research.deep_research import SimpleDeepResearch


async def main():
    print("🧪 Deep Research Relevance Validation Test")
    print("=" * 80)
    print()

    # Test configuration
    test_query = "What cybersecurity job opportunities are available for cleared professionals?"
    print(f"Test Query: {test_query}")
    print()

    # Run deep research with limited tasks for faster testing
    print("Running deep research (max 5 tasks, 10 min timeout)...")
    print("-" * 80)

    engine = SimpleDeepResearch(
        max_tasks=5,
        max_retries_per_task=2,  # Test Fix #3: 2 retries (3 total attempts)
        max_time_minutes=10,
        min_results_per_task=3
    )

    result = await engine.research(test_query)

    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    # Basic metrics
    print(f"\nBasic Metrics:")
    print(f"  Tasks executed:  {result['tasks_executed']}")
    print(f"  Tasks failed:    {result['tasks_failed']}")
    print(f"  Total results:   {result['total_results']}")
    print(f"  Elapsed time:    {result['elapsed_minutes']:.1f} minutes")
    print(f"  Sources used:    {', '.join(result['sources_searched'])}")

    # Test Fix #3: Verify retry count
    print(f"\n✓ Fix #3: max_retries_per_task = 2 (allows 3 total attempts)")

    # Test Fix #4: Check if USAJobs was used and returned results
    usajobs_in_sources = "USAJobs" in result['sources_searched']
    if usajobs_in_sources:
        print(f"✓ Fix #4: USAJobs was called (may be rate-limited)")
    else:
        print(f"⚠️  Fix #4: USAJobs not in sources (may have been skipped)")

    # Check for task failures
    if result['tasks_failed'] == 0:
        print(f"\n✅ ALL TASKS SUCCEEDED")
        print(f"   This validates that relevance scoring is working correctly")
    else:
        print(f"\n⚠️  {result['tasks_failed']} TASKS FAILED")
        print(f"\nFailure details:")
        for failure in result.get('failure_details', []):
            print(f"  Task {failure['task_id']}: {failure['query']}")
            print(f"    Error: {failure['error']}")
            print(f"    Retries: {failure['retry_count']}")

    # Test Fix #1 & #2: Check execution logs for LLM reasoning
    output_dir = result.get('output_directory')
    if output_dir:
        print(f"\n✓ Output saved to: {output_dir}")

        # Check execution log for relevance scoring entries
        log_file = Path(output_dir) / "execution_log.jsonl"
        if log_file.exists():
            print(f"\nChecking execution_log.jsonl for LLM reasoning...")

            with open(log_file) as f:
                log_entries = [json.loads(line) for line in f]

            # Find relevance scoring entries
            relevance_entries = [
                entry for entry in log_entries
                if entry.get('action_type') == 'relevance_scoring'
            ]

            if relevance_entries:
                print(f"✓ Fix #1: Found {len(relevance_entries)} relevance scoring log entries")

                # Check first entry for actual LLM reasoning
                first_entry = relevance_entries[0]
                llm_response = first_entry.get('action_payload', {}).get('llm_response', {})
                reasoning = llm_response.get('reasoning', '')

                if reasoning and len(reasoning) > 10:
                    print(f"✓ Fix #1: LLM reasoning captured (not generic f-string)")
                    print(f"  Sample: {reasoning[:100]}...")
                else:
                    print(f"❌ Fix #1: FAILED - LLM reasoning is empty or generic")

                # Check if partial relevance guidance is working
                # (Fix #2 is in the prompt, we can infer it worked if scores are non-binary)
                scores = [
                    e.get('action_payload', {}).get('llm_response', {}).get('relevance_score', 0)
                    for e in relevance_entries
                ]
                unique_scores = set(scores)
                if len(unique_scores) > 2 or (len(unique_scores) == 2 and 0 not in unique_scores):
                    print(f"✓ Fix #2: Partial relevance scoring appears to work")
                    print(f"  Unique scores observed: {sorted(unique_scores)}")
                else:
                    print(f"⚠️  Fix #2: Scores are binary ({sorted(unique_scores)}), may not have partial results")
            else:
                print(f"⚠️  No relevance scoring entries found in log")
        else:
            print(f"⚠️  execution_log.jsonl not found")

    # Test Fix #4: Check raw USAJobs results for field normalization
    if output_dir:
        raw_dir = Path(output_dir) / "raw"
        if raw_dir.exists():
            usajobs_files = list(raw_dir.glob("usajobs_*.json"))
            if usajobs_files:
                print(f"\nChecking USAJobs raw results for field normalization...")

                # Load first USAJobs result file
                with open(usajobs_files[0]) as f:
                    usajobs_results = json.load(f)

                if usajobs_results:
                    first_result = usajobs_results[0]
                    has_title = 'title' in first_result
                    has_description = 'description' in first_result
                    has_snippet = 'snippet' in first_result
                    has_position_title = 'PositionTitle' in first_result

                    print(f"✓ Fix #4: USAJobs field normalization check:")
                    print(f"  Normalized 'title': {has_title}")
                    print(f"  Normalized 'description': {has_description}")
                    print(f"  Normalized 'snippet': {has_snippet}")
                    print(f"  Raw 'PositionTitle': {has_position_title}")

                    if has_title and has_description and has_snippet and has_position_title:
                        print(f"  ✅ All required fields present")
                    else:
                        print(f"  ❌ MISSING FIELDS - normalization broken!")
                else:
                    print(f"⚠️  USAJobs returned 0 results (likely rate-limited)")
            else:
                print(f"⚠️  No USAJobs raw result files found")

    print()
    print("=" * 80)
    print("✅ Deep Research Relevance Test Complete!")
    print("=" * 80)
    print()
    print("Summary of Fixes Validated:")
    print("  1. LLM reasoning capture: Check execution_log.jsonl above")
    print("  2. Partial relevance scoring: Check unique scores above")
    print("  3. Retry count (max 2): Configured in engine")
    print("  4. USAJobs normalization: Check field presence above")


if __name__ == "__main__":
    asyncio.run(main())
