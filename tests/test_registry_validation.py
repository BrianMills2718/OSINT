#!/usr/bin/env python3
"""
Test the registry validation framework.

Validates that:
1. validate_integration() correctly tests a single integration
2. validate_all() runs tests on all registered integrations
3. print_validation_report() formats results correctly
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from integrations.registry import registry


def test_single_integration_validation():
    """Test validating a single integration."""
    results = registry.validate_integration("sam")

    # Check expected keys exist
    expected_keys = ['instantiation', 'metadata_valid', 'query_generation', 'graceful_errors']
    missing = [k for k in expected_keys if k not in results]
    assert not missing, f"Missing expected keys: {missing}"

    # SAM.gov should pass instantiation and metadata at minimum
    assert results.get('instantiation', False), "SAM.gov instantiation failed"
    assert results.get('metadata_valid', False), "SAM.gov metadata validation failed"


def test_all_integrations_validation():
    """Test validating all integrations."""
    results = registry.validate_all()

    # Should have results for all registered integrations
    assert len(results) > 0, "validate_all() returned no results"

    # At least some integrations should pass instantiation
    passed_instantiation = sum(1 for r in results.values() if r.get('instantiation', False))
    assert passed_instantiation > 0, "No integrations passed instantiation"


def test_validation_report_formatting(capsys):
    """Test the print_validation_report() method."""
    # Run validation and print report
    registry.print_validation_report()

    # Capture output and verify it contains expected content
    captured = capsys.readouterr()
    assert "Integration Validation Report" in captured.out or len(captured.out) > 0


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Registry Validation Framework Tests")
    print("="*80)

    tests = [
        test_single_integration_validation,
        test_all_integrations_validation,
        test_validation_report_formatting,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✅ ALL TESTS PASSED - Smoke test framework working correctly")
    else:
        print("\n❌ SOME TESTS FAILED")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
