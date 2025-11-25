"""
Pytest configuration for feature tests.

Feature tests may use LLM APIs for query generation and are marked accordingly.
Tests that require external APIs are marked with @pytest.mark.api.

To run only fast unit tests (excluding API/LLM tests):
    pytest -m "not api and not llm"

To run feature tests only:
    pytest tests/features/
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Mark tests based on naming conventions and API usage."""
    for item in items:
        if "/tests/features/" in str(item.fspath):
            # Deep research tests use LLM and external APIs
            if "deep_research" in str(item.fspath):
                item.add_marker(pytest.mark.llm)
                item.add_marker(pytest.mark.api)
            # E2E tests are integration tests
            if "_e2e" in str(item.fspath) or "full" in str(item.fspath):
                item.add_marker(pytest.mark.integration)
