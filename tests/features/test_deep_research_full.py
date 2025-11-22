#!/usr/bin/env python3
"""
Test deep research with comprehensive logging and saved output.

This test:
1. Runs deep research on a test query
2. Logs all progress to console and files
3. Saves complete output to data/research_output/
4. Prints summary at the end
"""

import asyncio
import json
import sys
import os

# Add parent directory to path so imports work from tests/ subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch, ResearchProgress


def show_progress(progress: ResearchProgress):
    """Display progress updates in real-time."""
    print(f"\n{'='*80}")
    print(f"[{progress.timestamp}] {progress.event.upper()}")
    print(f"Message: {progress.message}")
    if progress.task_id is not None:
        print(f"Task ID: {progress.task_id}")
    if progress.data:
        print(f"Data: {json.dumps(progress.data, indent=2)[:500]}...")  # Truncate long data
    print('='*80)


async def main():
    """Run deep research test."""

    # Test queries (pick one)
    test_queries = [
        "What cybersecurity job opportunities are available for cleared professionals?",
        "What are the latest DoD contracts for AI and machine learning?",
        "What are current OSINT techniques discussed in the intelligence community?",
    ]

    # Use first query
    question = test_queries[0]

    print(f"\n{'#'*80}")
    print(f"# DEEP RESEARCH TEST - JINJA2 VALIDATION")
    print(f"# Question: {question}")
    print(f"# Output will be saved to: data/research_output/")
    print(f"{'#'*80}\n")

    # Create engine with conservative settings for testing
    engine = SimpleDeepResearch(
        max_tasks=5,                    # Limit to 5 tasks for faster testing
        max_retries_per_task=1,         # 1 retry per task
        max_time_minutes=30,            # 30 minute timeout
        min_results_per_task=3,         # Min 3 results
        max_concurrent_tasks=2,         # 2 tasks in parallel
        progress_callback=show_progress,  # Real-time progress
        save_output=True,               # Auto-save to files
        output_dir="data/research_output"
    )

    # Execute research
    print("\n🚀 Starting deep research...\n")
    result = await engine.research(question)

    # Display final report
    print("\n" + "="*80)
    print("FINAL REPORT")
    print("="*80)
    print(result['report'])

    # Display statistics
    print("\n" + "="*80)
    print("RESEARCH STATISTICS")
    print("="*80)
    print(f"Tasks Executed: {result['tasks_executed']}")
    print(f"Tasks Failed: {result['tasks_failed']}")
    if result.get('failure_details'):
        print(f"\nFailure Details:")
        for failure in result['failure_details']:
            print(f"  - Task {failure['task_id']}: {failure['query']}")
            print(f"    Error: {failure['error']}")
            print(f"    Retries: {failure['retry_count']}")
    print(f"\nTotal Results: {result['total_results']}")
    print(f"Entities Discovered: {len(result['entities_discovered'])}")
    print(f"Entity Relationships: {len(result['entity_relationships'])}")
    print(f"Sources Searched: {', '.join(result['sources_searched'])}")
    print(f"Elapsed Time: {result['elapsed_minutes']:.1f} minutes")

    # Output directory info
    if result.get('output_directory'):
        print(f"\n💾 All output saved to: {result['output_directory']}")
        print(f"   - results.json: Complete structured data")
        print(f"   - report.md: Human-readable report")
        print(f"   - metadata.json: Research parameters")
        print(f"   - execution_log.jsonl: Detailed execution log")

    # Entity network
    if result['entity_relationships']:
        print("\n" + "="*80)
        print("ENTITY NETWORK (Top 10)")
        print("="*80)
        for entity, related in list(result['entity_relationships'].items())[:10]:
            print(f"{entity}:")
            print(f"  → {', '.join(related[:5])}")

    print("\n✅ Deep research test complete!")
    print(f"Review saved output at: {result.get('output_directory', 'data/research_output/')}")


if __name__ == "__main__":
    asyncio.run(main())
