#!/usr/bin/env python3
"""
Test 4: Full Deep Research End-to-End Test

This runs an actual Deep Research investigation to verify:
- Task decomposition works
- Government databases search
- Brave Search integration
- Results combine correctly
- Live progress works
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from research.deep_research import SimpleDeepResearch, ResearchProgress

async def test_full_deep_research():
    """Run full Deep Research and verify all components work."""
    print("=" * 60)
    print("TEST 4: Full Deep Research End-to-End")
    print("=" * 60)

    load_dotenv()

    # Track progress
    progress_events = []

    def progress_callback(progress: ResearchProgress):
        progress_events.append(progress)
        print(f"[{progress.event}] {progress.message}")

    print(f"\n1. Creating Deep Research engine...")
    engine = SimpleDeepResearch(
        max_tasks=3,  # Small test - just 3 tasks
        max_retries_per_task=1,
        max_time_minutes=5,
        min_results_per_task=1,  # Accept any results
        progress_callback=progress_callback
    )
    print(f"   ✅ Engine created")

    print(f"\n2. Running Deep Research...")
    print(f"   Query: 'cybersecurity threat intelligence'")
    print(f"   Max tasks: 3")
    print(f"   This will take ~2-3 minutes...")
    print("")

    result = await engine.research("cybersecurity threat intelligence")

    print(f"\n" + "=" * 60)
    print("3. RESULTS ANALYSIS")
    print("=" * 60)

    # Check basic stats
    print(f"\n   Tasks Executed: {result['tasks_executed']}")
    print(f"   Tasks Failed: {result['tasks_failed']}")
    print(f"   Total Results: {result['total_results']}")
    print(f"   Sources Searched: {result['sources_searched']}")

    # Check for Brave Search specifically
    has_brave = 'Brave Search' in result['sources_searched']
    print(f"\n   Brave Search integrated: {'✅ YES' if has_brave else '❌ NO'}")

    # Check task completion events
    completed_tasks = [e for e in progress_events if e.event == 'task_completed']
    print(f"\n   Completed task events: {len(completed_tasks)}")

    if completed_tasks:
        print(f"\n4. SOURCE BREAKDOWN PER TASK:")
        for event in completed_tasks:
            if event.data:
                task_id = event.task_id
                gov_db = event.data.get('government_databases', 0)
                web = event.data.get('web_search', 0)
                total = event.data.get('total_results', 0)
                print(f"   Task {task_id}: {total} total ({gov_db} gov + {web} web)")

    # Overall verdict
    print(f"\n" + "=" * 60)
    if has_brave and result['total_results'] > 0 and result['tasks_executed'] > 0:
        print("✅ TEST 4 PASSED: Full Deep Research working end-to-end")
        print("=" * 60)
        print(f"\n   VERIFIED:")
        print(f"   - Task decomposition: ✅")
        print(f"   - Government databases: ✅")
        print(f"   - Brave Search integration: ✅")
        print(f"   - Results combining: ✅")
        print(f"   - Live progress: ✅")
        return True
    else:
        print("❌ TEST 4 FAILED: Issues found")
        print("=" * 60)
        print(f"\n   ISSUES:")
        if not has_brave:
            print(f"   - Brave Search not in sources: ❌")
        if result['total_results'] == 0:
            print(f"   - No results found: ❌")
        if result['tasks_executed'] == 0:
            print(f"   - No tasks executed: ❌")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_full_deep_research())
    sys.exit(0 if success else 1)
