"""
Pytest configuration for system tests.

System tests include unit tests (fast) and integration tests (API calls).
Tests are marked based on their content:
- @pytest.mark.api: Tests that hit external APIs
- @pytest.mark.integration: Multi-component integration tests

To run only fast unit tests:
    pytest tests/system/ -m "not api"

To run all system tests:
    pytest tests/system/
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Mark tests based on content and naming."""
    for item in items:
        if "/tests/system/" in str(item.fspath):
            # Tests with 'live' or 'e2e' in name use real APIs
            test_name = str(item.fspath).lower()
            if "_live" in test_name or "_e2e" in test_name or "all_integrations" in test_name:
                item.add_marker(pytest.mark.api)
                item.add_marker(pytest.mark.integration)
