#!/usr/bin/env python3
"""
Test Deep Research with MCP Integration

Quick test to verify MCP tools work with Deep Research engine.
Uses simple query with low task limits to complete quickly.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch, ResearchProgress


def show_progress(progress: ResearchProgress):
    """Display progress updates."""
    event_emoji = {
        "research_started": "🚀",
        "decomposition_complete": "📋",
        "task_started": "▶️",
        "task_completed": "✅",
        "task_failed": "❌",
        "task_retry": "🔄",
        "synthesis_complete": "📝"
    }

    emoji = event_emoji.get(progress.event, "ℹ️")
    print(f"{emoji} [{progress.event.upper()}] {progress.message}")

    # Show data for key events
    if progress.event in ["task_completed", "task_failed"] and progress.data:
        if "total_results" in progress.data:
            print(f"    Results: {progress.data['total_results']}")
        if "entities" in progress.data:
            print(f"    Entities: {', '.join(progress.data['entities'][:3])}...")
        if "error" in progress.data:
            print(f"    Error: {progress.data['error']}")


async def test_mcp_integration():
    """Test Deep Research with MCP tools."""

    print("\n" + "="*80)
    print("MCP INTEGRATION TEST")
    print("="*80)

    # Create engine with low limits for quick test
    engine = SimpleDeepResearch(
        max_tasks=5,              # Only 5 tasks max
        max_retries_per_task=1,   # Only 1 retry
        max_time_minutes=10,      # 10 minute limit
        min_results_per_task=3,   # Need at least 3 results
        max_concurrent_tasks=2,   # 2 tasks in parallel
        progress_callback=show_progress
    )

    # Simple test query (should find results in government DBs)
    question = "military cybersecurity training"

    print(f"\nQuery: {question}")
    print(f"Config: max_tasks={engine.max_tasks}, parallel={engine.max_concurrent_tasks}\n")

    # Execute research
    result = await engine.research(question)

    # Display results
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)

    print(f"\nTasks Executed: {result['tasks_executed']}")
    print(f"Tasks Failed: {result['tasks_failed']}")
    print(f"Total Results: {result['total_results']}")
    print(f"Entities Discovered: {len(result['entities_discovered'])}")
    print(f"Sources Searched: {', '.join(result['sources_searched'])}")
    print(f"Elapsed Time: {result['elapsed_minutes']:.1f} minutes")

    if result['entities_discovered']:
        print(f"\nSample Entities: {', '.join(result['entities_discovered'][:5])}")

    if result.get('failure_details'):
        print(f"\nFailed Tasks: {len(result['failure_details'])}")
        for failure in result['failure_details'][:2]:
            print(f"  - {failure['query']}: {failure['error']}")

    print("\n" + "="*80)
    print("REPORT PREVIEW (first 500 chars)")
    print("="*80)
    print(result['report'][:500] + "...")

    # Validation
    print("\n" + "="*80)
    print("VALIDATION")
    print("="*80)

    success = True

    if result['tasks_executed'] > 0:
        print("✅ Tasks executed successfully")
    else:
        print("❌ No tasks completed")
        success = False

    if result['total_results'] > 0:
        print("✅ Results returned from MCP tools")
    else:
        print("❌ No results returned")
        success = False

    if len(result['sources_searched']) > 0:
        print(f"✅ Sources searched: {', '.join(result['sources_searched'])}")
    else:
        print("❌ No sources searched")
        success = False

    if result['entities_discovered']:
        print(f"✅ Entities extracted: {len(result['entities_discovered'])}")
    else:
        print("⚠️  No entities extracted (may be normal for simple queries)")

    return success


async def main():
    """Run test."""
    try:
        success = await test_mcp_integration()

        if success:
            print("\n" + "="*80)
            print("✅ MCP INTEGRATION TEST PASSED")
            print("="*80 + "\n")
            sys.exit(0)
        else:
            print("\n" + "="*80)
            print("❌ MCP INTEGRATION TEST FAILED")
            print("="*80 + "\n")
            sys.exit(1)

    except Exception as e:
        import traceback
        print("\n" + "="*80)
        print("❌ TEST EXCEPTION")
        print("="*80)
        print(f"\nError: {type(e).__name__}: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        print("\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
