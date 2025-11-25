"""
Pytest configuration for integration tests.

All tests in this directory hit real external APIs and are automatically marked:
- @pytest.mark.api: Requires external API access (keys, network)
- @pytest.mark.integration: Multi-component integration tests

To run only fast unit tests (excluding API tests):
    pytest -m "not api"

To run only integration tests:
    pytest -m api tests/integrations/
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in this directory as 'api' tests."""
    for item in items:
        # Check if test is in the integrations directory
        if "/tests/integrations/" in str(item.fspath):
            item.add_marker(pytest.mark.api)
            item.add_marker(pytest.mark.integration)
