#!/usr/bin/env python3
"""
Validation tests for Deep Research Fix 3 (Critical Source Warnings).

Tests that warnings appear in all 4 channels when critical sources fail:
1. Console (print with ⚠️)
2. Logging (logging.warning)
3. Progress events (_emit_progress)
4. Report ("Research Limitations" section)
"""

import asyncio
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from io import StringIO
import sys

# Add parent directory to path
sys.path.insert(0, '/home/brian/sam_gov')

from research.deep_research import SimpleDeepResearch


async def test_fix3_critical_source_failure():
    """Test that critical source failures emit warnings in all 4 channels."""

    print("\n" + "="*80)
    print("TEST 1: Critical Source Failure → Warnings Should Appear")
    print("="*80)

    # Capture console output
    console_output = StringIO()

    # Capture logging output
    log_capture = StringIO()
    log_handler = logging.StreamHandler(log_capture)
    log_handler.setLevel(logging.WARNING)
    logging.getLogger().addHandler(log_handler)

    # Capture progress events
    progress_events = []
    def capture_progress(event):
        progress_events.append(event)

    # Mock MCP client to force SAM.gov failure
    with patch('research.deep_research.Client') as mock_client_class:
        # Mock the async context manager
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock call_tool to return failure for SAM.gov
        async def mock_call_tool(tool_name, args):
            # Create mock result with content attribute
            mock_result = MagicMock()

            if tool_name == "search_sam":
                # SAM.gov fails (critical source)
                mock_result.content = [MagicMock(text='{"success": false, "source": "SAM.gov", "total": 0, "results": [], "error": "Rate limited"}')]
            elif tool_name == "search_dvids":
                # DVIDS succeeds (non-critical for contract query)
                mock_result.content = [MagicMock(text='{"success": true, "source": "DVIDS", "total": 5, "results": [{"title": "Test", "snippet": "Test"}]}')]
            else:
                # Other tools succeed with minimal results
                source_name = tool_name.replace("search_", "").title()
                mock_result.content = [MagicMock(text=f'{{"success": true, "source": "{source_name}", "total": 0, "results": []}}')]

            return mock_result

        mock_client.call_tool = AsyncMock(side_effect=mock_call_tool)

        # Create engine with progress callback
        engine = SimpleDeepResearch(
            max_tasks=3,
            max_retries_per_task=1,
            max_time_minutes=5,
            min_results_per_task=3,
            progress_callback=capture_progress
        )

        # Redirect stdout to capture console output
        old_stdout = sys.stdout
        sys.stdout = console_output

        try:
            # Run query with "contract" keyword (triggers SAM.gov as critical)
            result = await engine.research("What contracts has NSA awarded?")
        finally:
            sys.stdout = old_stdout

        # Remove log handler
        logging.getLogger().removeHandler(log_handler)

    # Get captured outputs
    console_text = console_output.getvalue()
    log_text = log_capture.getvalue()
    report_text = result["report"]

    print("\n--- VALIDATION RESULTS ---\n")

    # Channel 1: Console (⚠️ warning)
    has_console_warning = "⚠️" in console_text and "SAM.gov" in console_text
    print(f"✓ Channel 1 (Console): {'PASS' if has_console_warning else 'FAIL'}")
    if has_console_warning:
        # Extract warning line
        for line in console_text.split('\n'):
            if "⚠️" in line and "SAM.gov" in line:
                print(f"  Found: {line.strip()}")
                break
    else:
        print(f"  Expected: ⚠️ WARNING: SAM.gov returned 0 results")
        print(f"  Actual: Not found in console output")

    # Channel 2: Logging (warning level)
    has_log_warning = "WARNING" in log_text and "SAM.gov" in log_text
    print(f"✓ Channel 2 (Logging): {'PASS' if has_log_warning else 'FAIL'}")
    if has_log_warning:
        for line in log_text.split('\n'):
            if "WARNING" in line and "SAM.gov" in line:
                print(f"  Found: {line.strip()}")
                break
    else:
        print(f"  Expected: WARNING level log with 'SAM.gov'")
        print(f"  Actual: Not found in logs")

    # Channel 3: Progress events (critical_source_failure)
    critical_failure_events = [e for e in progress_events if e.event == "critical_source_failure"]
    has_progress_event = len(critical_failure_events) > 0
    print(f"✓ Channel 3 (Progress Events): {'PASS' if has_progress_event else 'FAIL'}")
    if has_progress_event:
        for event in critical_failure_events:
            print(f"  Found: {event.event} - {event.message}")
    else:
        print(f"  Expected: critical_source_failure event")
        print(f"  Actual: No such events found")

    # Channel 4: Report ("Research Limitations" section)
    has_limitations_section = "Research Limitations" in report_text and "SAM.gov" in report_text
    print(f"✓ Channel 4 (Report): {'PASS' if has_limitations_section else 'FAIL'}")
    if has_limitations_section:
        # Extract section
        lines = report_text.split('\n')
        for i, line in enumerate(lines):
            if "Research Limitations" in line:
                print(f"  Found section starting at line {i}")
                # Print next 5 lines
                for j in range(i, min(i+5, len(lines))):
                    print(f"    {lines[j]}")
                break
    else:
        print(f"  Expected: 'Research Limitations' section mentioning SAM.gov")
        print(f"  Actual: Not found in report")

    # Channel 5: State tracking (critical_source_failures list)
    has_state_tracking = "SAM.gov" in engine.critical_source_failures
    print(f"✓ Channel 5 (State): {'PASS' if has_state_tracking else 'FAIL'}")
    if has_state_tracking:
        print(f"  Found: {engine.critical_source_failures}")
    else:
        print(f"  Expected: ['SAM.gov'] in critical_source_failures")
        print(f"  Actual: {engine.critical_source_failures}")

    # Overall result
    all_channels_pass = all([
        has_console_warning,
        has_log_warning,
        has_progress_event,
        has_limitations_section,
        has_state_tracking
    ])

    print("\n" + "="*80)
    if all_channels_pass:
        print("✅ TEST PASSED: All 5 channels working correctly")
    else:
        print("❌ TEST FAILED: Some channels not working")
        print(f"   Console: {has_console_warning}")
        print(f"   Logging: {has_log_warning}")
        print(f"   Progress: {has_progress_event}")
        print(f"   Report: {has_limitations_section}")
        print(f"   State: {has_state_tracking}")
    print("="*80)

    return all_channels_pass


async def test_fix3_critical_source_success():
    """Test that critical source success does NOT emit false warnings."""

    print("\n" + "="*80)
    print("TEST 2: Critical Source Success → No False Warnings")
    print("="*80)

    # Capture console output
    console_output = StringIO()

    # Capture progress events
    progress_events = []
    def capture_progress(event):
        progress_events.append(event)

    # Mock MCP client with SAM.gov succeeding
    with patch('research.deep_research.Client') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def mock_call_tool(tool_name, args):
            mock_result = MagicMock()

            if tool_name == "search_sam":
                # SAM.gov SUCCEEDS with results
                mock_result.content = [MagicMock(text='{"success": true, "source": "SAM.gov", "total": 10, "results": [{"title": "Contract 1", "snippet": "NSA contract"}]}')]
            else:
                source_name = tool_name.replace("search_", "").title()
                mock_result.content = [MagicMock(text=f'{{"success": true, "source": "{source_name}", "total": 5, "results": [{{"title": "Test", "snippet": "Test"}}]}}')]

            return mock_result

        mock_client.call_tool = AsyncMock(side_effect=mock_call_tool)

        engine = SimpleDeepResearch(
            max_tasks=3,
            max_retries_per_task=1,
            max_time_minutes=5,
            min_results_per_task=3,
            progress_callback=capture_progress
        )

        old_stdout = sys.stdout
        sys.stdout = console_output

        try:
            result = await engine.research("What contracts has NSA awarded?")
        finally:
            sys.stdout = old_stdout

    console_text = console_output.getvalue()
    report_text = result["report"]

    print("\n--- VALIDATION RESULTS ---\n")

    # Should NOT have warnings
    has_console_warning = "⚠️" in console_text and "SAM.gov" in console_text
    has_limitations_section = "Research Limitations" in report_text
    critical_failure_events = [e for e in progress_events if e.event == "critical_source_failure"]
    has_progress_event = len(critical_failure_events) > 0
    has_state_tracking = "SAM.gov" in engine.critical_source_failures

    no_false_warnings = not any([
        has_console_warning,
        has_limitations_section,
        has_progress_event,
        has_state_tracking
    ])

    print(f"✓ No Console Warning: {'PASS' if not has_console_warning else 'FAIL (false positive)'}")
    print(f"✓ No Report Limitations: {'PASS' if not has_limitations_section else 'FAIL (false positive)'}")
    print(f"✓ No Progress Events: {'PASS' if not has_progress_event else 'FAIL (false positive)'}")
    print(f"✓ No State Tracking: {'PASS' if not has_state_tracking else 'FAIL (false positive)'}")

    print("\n" + "="*80)
    if no_false_warnings:
        print("✅ TEST PASSED: No false warnings when critical source succeeds")
    else:
        print("❌ TEST FAILED: False warnings detected")
        if has_console_warning:
            print("   ⚠️ Console warning appeared (should not)")
        if has_limitations_section:
            print("   ⚠️ Report limitations section appeared (should not)")
        if has_progress_event:
            print("   ⚠️ Progress events emitted (should not)")
        if has_state_tracking:
            print(f"   ⚠️ State tracking populated: {engine.critical_source_failures}")
    print("="*80)

    return no_false_warnings


async def main():
    """Run both validation tests."""
    print("\n" + "="*80)
    print("DEEP RESEARCH FIX 3 VALIDATION TESTS")
    print("="*80)

    # Test 1: Failure case (warnings should appear)
    test1_pass = await test_fix3_critical_source_failure()

    # Test 2: Success case (no false warnings)
    test2_pass = await test_fix3_critical_source_success()

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Test 1 (Failure → Warnings): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (Success → No Warnings): {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print("="*80)

    if test1_pass and test2_pass:
        print("\n✅ FIX 3 VALIDATED - Ready for production")
        return 0
    else:
        print("\n❌ FIX 3 NOT VALIDATED - Issues found")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
