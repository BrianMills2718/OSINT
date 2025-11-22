#!/usr/bin/env python3
"""
Validation test for Deep Research per-task timeout.

Tests that tasks exceeding 180 seconds are terminated with proper error handling.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, '/home/brian/sam_gov')

from research.deep_research import SimpleDeepResearch


async def test_per_task_timeout():
    """Test that tasks exceeding 180s timeout are properly handled."""

    print("\n" + "="*80)
    print("TEST: Per-Task Timeout (180 seconds)")
    print("="*80)

    # Capture progress events
    progress_events = []
    def capture_progress(event):
        progress_events.append(event)

    # Mock MCP client with one tool that hangs for >180s
    with patch('research.deep_research.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def mock_call_tool(tool_name, args):
            mock_result = MagicMock()

            if tool_name == "search_sam":
                # SAM.gov hangs for 200 seconds (exceeds 180s timeout)
                print(f"  Mock: {tool_name} will hang for 200 seconds...")
                await asyncio.sleep(200)
                # Should never reach here due to timeout
                mock_result.content = [MagicMock(text='{"success": true, "source": "SAM.gov", "total": 10, "results": []}')]
            else:
                # Other tools return quickly
                source_name = tool_name.replace("search_", "").title()
                mock_result.content = [MagicMock(text=f'{{"success": true, "source": "{source_name}", "total": 5, "results": [{{"title": "Test", "snippet": "Test"}}]}}')]

            return mock_result

        mock_client.call_tool = AsyncMock(side_effect=mock_call_tool)

        # Create engine with short task timeout for testing
        # Note: Using actual 180s timeout from code, but we'll verify the mechanism works
        engine = SimpleDeepResearch(
            max_tasks=3,
            max_retries_per_task=1,
            max_time_minutes=5,
            min_results_per_task=3,
            progress_callback=capture_progress
        )

        print("\nStarting research with hanging SAM.gov (will timeout after 180s)...")
        print("Note: Test will wait for timeout to trigger - this takes 3 minutes")

        try:
            # Run query that triggers SAM.gov (contains "contract")
            result = await engine.research("What contracts has NSA awarded?")
        except Exception as e:
            print(f"\n⚠️ Exception during research: {type(e).__name__}: {e}")
            result = None

    print("\n--- VALIDATION RESULTS ---\n")

    # Check for timeout-related progress events
    timeout_events = [e for e in progress_events if "timeout" in e.event.lower() or "timeout" in e.message.lower()]
    has_timeout_event = len(timeout_events) > 0

    print(f"✓ Timeout Event Emitted: {'PASS' if has_timeout_event else 'FAIL'}")
    if has_timeout_event:
        for event in timeout_events:
            print(f"  Found: {event.event} - {event.message}")
    else:
        print(f"  Expected: task_timeout or similar event")
        print(f"  Actual: No timeout events found")

    # Check for failed tasks
    if result:
        tasks_failed = result.get("tasks_failed", 0)
        has_failed_tasks = tasks_failed > 0
        print(f"✓ Tasks Failed: {'PASS' if has_failed_tasks else 'FAIL'}")
        print(f"  Failed: {tasks_failed}")

        # Check failure details
        failure_details = result.get("failure_details", [])
        timeout_failures = [f for f in failure_details if "timeout" in str(f.get("error", "")).lower()]
        has_timeout_error = len(timeout_failures) > 0
        print(f"✓ Timeout in Failure Details: {'PASS' if has_timeout_error else 'FAIL'}")
        if has_timeout_error:
            for failure in timeout_failures:
                print(f"  Task {failure['task_id']}: {failure['error']}")
        else:
            print(f"  Expected: Error message containing 'timeout'")
            if failure_details:
                print(f"  Actual errors: {[f.get('error') for f in failure_details]}")
    else:
        print("✗ No result returned (research may have thrown exception)")
        has_failed_tasks = False
        has_timeout_error = False

    # Check engine state
    has_failed_task_state = len(engine.failed_tasks) > 0
    print(f"✓ Failed Tasks in State: {'PASS' if has_failed_task_state else 'FAIL'}")
    if has_failed_task_state:
        print(f"  Failed tasks: {len(engine.failed_tasks)}")
        for task in engine.failed_tasks:
            if task.error:
                print(f"    Task {task.id}: {task.error[:100]}")

    # Overall validation
    all_checks_pass = all([
        has_timeout_event,
        has_failed_tasks if result else True,  # Allow missing result
        has_timeout_error if result else True,
        has_failed_task_state
    ])

    print("\n" + "="*80)
    if all_checks_pass:
        print("✅ TEST PASSED: Per-task timeout working correctly")
        print("   - Tasks exceeding 180s are terminated")
        print("   - Timeout events emitted")
        print("   - Failed tasks tracked with error messages")
    else:
        print("❌ TEST FAILED: Per-task timeout not working as expected")
        print(f"   Timeout event: {has_timeout_event}")
        print(f"   Failed tasks: {has_failed_tasks if result else 'N/A'}")
        print(f"   Timeout errors: {has_timeout_error if result else 'N/A'}")
        print(f"   Failed state: {has_failed_task_state}")
    print("="*80)

    return all_checks_pass


async def test_per_task_timeout_fast():
    """Fast test: Mock timeout to avoid waiting 180 seconds."""

    print("\n" + "="*80)
    print("TEST: Per-Task Timeout (Fast Mock - 2 seconds)")
    print("="*80)

    progress_events = []
    def capture_progress(event):
        progress_events.append(event)

    # Patch asyncio.wait_for to use shorter timeout
    original_wait_for = asyncio.wait_for

    async def fast_wait_for(coro, timeout):
        # Use 2 second timeout instead of 180
        return await original_wait_for(coro, timeout=2)

    with patch('research.deep_research.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def mock_call_tool(tool_name, args):
            mock_result = MagicMock()

            if tool_name == "search_sam":
                # SAM.gov hangs for 5 seconds (exceeds 2s mock timeout)
                print(f"  Mock: {tool_name} will hang for 5 seconds (exceeds 2s timeout)...")
                await asyncio.sleep(5)
                mock_result.content = [MagicMock(text='{"success": true, "source": "SAM.gov", "total": 10, "results": []}')]
            else:
                source_name = tool_name.replace("search_", "").title()
                mock_result.content = [MagicMock(text=f'{{"success": true, "source": "{source_name}", "total": 5, "results": [{{"title": "Test", "snippet": "Test"}}]}}')]

            return mock_result

        mock_client.call_tool = AsyncMock(side_effect=mock_call_tool)

        # Patch asyncio.wait_for in deep_research module
        with patch('research.deep_research.asyncio.wait_for', fast_wait_for):
            engine = SimpleDeepResearch(
                max_tasks=3,
                max_retries_per_task=1,
                max_time_minutes=5,
                min_results_per_task=3,
                progress_callback=capture_progress
            )

            print("\nStarting research (will timeout after 2s mock timeout)...")

            try:
                result = await engine.research("What contracts has NSA awarded?")
            except Exception as e:
                print(f"\n⚠️ Exception: {type(e).__name__}: {e}")
                result = None

    print("\n--- VALIDATION RESULTS ---\n")

    # Check results
    timeout_events = [e for e in progress_events if "timeout" in e.event.lower() or "timeout" in e.message.lower()]
    has_timeout_event = len(timeout_events) > 0

    print(f"✓ Timeout Event: {'PASS' if has_timeout_event else 'FAIL'}")
    if timeout_events:
        for event in timeout_events:
            print(f"  {event.event}: {event.message}")

    has_failed_task_state = len(engine.failed_tasks) > 0
    print(f"✓ Failed Tasks: {'PASS' if has_failed_task_state else 'FAIL'} ({len(engine.failed_tasks)} failed)")
    if engine.failed_tasks:
        for task in engine.failed_tasks:
            print(f"  Task {task.id}: {task.error}")

    all_checks_pass = has_timeout_event and has_failed_task_state

    print("\n" + "="*80)
    if all_checks_pass:
        print("✅ FAST TEST PASSED: Per-task timeout mechanism working")
    else:
        print("❌ FAST TEST FAILED")
    print("="*80)

    return all_checks_pass


async def main():
    """Run timeout validation tests."""
    print("\n" + "="*80)
    print("PER-TASK TIMEOUT VALIDATION")
    print("="*80)

    # Run fast test first (2 seconds)
    print("\nRunning FAST test (2s mock timeout)...")
    fast_pass = await test_per_task_timeout_fast()

    # Optionally run real timeout test (180 seconds = 3 minutes)
    print("\n" + "="*80)
    print("Do you want to run the REAL timeout test (takes 3 minutes)?")
    print("The fast test already validates the mechanism works.")
    print("="*80)
    print("\nSkipping real timeout test - fast test sufficient for validation")
    real_pass = None  # Can enable if needed

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Fast Test (2s mock): {'✅ PASS' if fast_pass else '❌ FAIL'}")
    if real_pass is not None:
        print(f"Real Test (180s actual): {'✅ PASS' if real_pass else '❌ FAIL'}")
    else:
        print(f"Real Test (180s actual): ⏭️  SKIPPED (fast test sufficient)")
    print("="*80)

    if fast_pass:
        print("\n✅ PER-TASK TIMEOUT VALIDATED - Ready for production")
        print("   Mechanism verified with fast mock test")
        return 0
    else:
        print("\n❌ PER-TASK TIMEOUT NOT VALIDATED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
