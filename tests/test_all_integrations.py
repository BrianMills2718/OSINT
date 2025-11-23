#!/usr/bin/env python3
"""
Comprehensive regression test suite for all integrations.

Runs all integration tests and reports:
- Pass/fail status for each integration
- Total coverage (16/16 integrations tested)
- Summary statistics
- Exit code for CI/CD (0 = all passed, 1 = some failed)

Usage:
    python3 tests/test_all_integrations.py
"""

import asyncio
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, '/home/brian/sam_gov')

from integrations.registry import registry


# All integration test files
INTEGRATION_TESTS = [
    # Government sources (9 tests)
    ("SAM.gov", "tests/test_sam_live.py"),
    ("DVIDS", "tests/test_dvids_live.py"),
    ("USAJobs", "tests/test_usajobs_live.py"),
    ("USASpending", "tests/test_usaspending_live.py"),
    ("ClearanceJobs", "tests/test_clearancejobs_live.py"),
    ("FBI Vault", "tests/test_fbi_vault_live.py"),
    ("Federal Register", "tests/test_federal_register_live.py"),
    ("Congress.gov", "tests/test_congress_live.py"),
    ("CIA CREST", "tests/test_crest_live.py"),

    # Social media sources (3 tests)
    ("Discord", "tests/test_discord_live.py"),
    ("Twitter", "tests/test_twitter_live.py"),
    ("Reddit", "tests/test_reddit_live.py"),

    # Web search & news (3 tests)
    ("Brave Search", "tests/test_brave_search_live.py"),
    ("NewsAPI", "tests/test_newsapi_live.py"),

    # Archive sources (2 tests)
    ("SEC EDGAR", "tests/test_sec_edgar_live.py"),
    ("Wayback Machine", "tests/test_wayback_live.py"),
]


async def main():
    print("=" * 80)
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 80)
    print(f"Testing {len(INTEGRATION_TESTS)} integrations...")
    print()

    # Check that all enabled integrations have tests
    print("Integration Coverage:")
    print("-" * 80)
    enabled = registry.list_enabled_ids()
    test_files = {test_file for _, test_file in INTEGRATION_TESTS}

    for integration_id in sorted(enabled):
        instance = registry.get_instance(integration_id)
        if instance:
            expected_test = f"tests/test_{integration_id}_live.py"
            # Handle naming mismatches
            if integration_id == "wayback_machine":
                expected_test = "tests/test_wayback_live.py"

            has_test = expected_test in test_files or f"tests/test_{integration_id.replace('_', '')}_live.py" in test_files
            status = "✅" if has_test else "❌"
            print(f"{status} {instance.metadata.name:25s} ({integration_id})")

    print(f"\nTotal: {len(enabled)} integrations, {len(INTEGRATION_TESTS)} tests")
    print()

    # Run all tests
    print("=" * 80)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 80)
    print()

    results = []
    for name, test_file in INTEGRATION_TESTS:
        print(f"[TEST] {name}...")
        print("-" * 80)

        # Check if test file exists
        if not Path(test_file).exists():
            print(f"❌ FAIL - Test file not found: {test_file}")
            results.append((name, False, "File not found"))
            print()
            continue

        try:
            # Run test with timeout
            result = subprocess.run(
                ["python3", test_file],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout per test
            )

            # Check if test passed (exit code 0 and no errors)
            passed = result.returncode == 0

            # Extract key info from output
            if passed:
                print(f"✅ PASS")
                results.append((name, True, "Success"))
            else:
                print(f"❌ FAIL - Exit code: {result.returncode}")
                # Show first error if available
                if result.stderr:
                    error_lines = result.stderr.strip().split('\n')
                    print(f"   Error: {error_lines[0]}")
                results.append((name, False, f"Exit code {result.returncode}"))

        except subprocess.TimeoutExpired:
            print(f"❌ FAIL - Timeout (>60 seconds)")
            results.append((name, False, "Timeout"))

        except Exception as e:
            print(f"❌ FAIL - Exception: {str(e)}")
            results.append((name, False, str(e)))

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    passed = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    print(f"Passed: {len(passed)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    print()

    if failed:
        print("Failed Tests:")
        for name, _, reason in failed:
            print(f"  ❌ {name}: {reason}")
        print()

    # Coverage stats
    coverage_pct = (len(results) / len(enabled)) * 100
    print(f"Coverage: {len(results)}/{len(enabled)} integrations ({coverage_pct:.0f}%)")
    print()

    # Final result
    if len(failed) == 0:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"❌ {len(failed)} TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
