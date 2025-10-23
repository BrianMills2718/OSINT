#!/usr/bin/env python3
"""
Contract tests for database integrations.

These tests verify that all integrations implement the DatabaseIntegration
interface correctly. They run in "cold mode" (no API keys, no network) to
validate core structure and error handling.

Contract Requirements:
1. Must implement DatabaseIntegration interface
2. metadata property must return valid DatabaseMetadata
3. is_relevant() must return bool
4. generate_query() must return Dict (not None - relevance filter removed)
5. execute_search() must return QueryResult object (not dict)
6. execute_search() must handle missing API keys gracefully (cold mode)
7. All methods must be async where specified
"""

import pytest
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Configure pytest-anyio for async testing
pytestmark = pytest.mark.anyio

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from integrations.registry import IntegrationRegistry


# Initialize registry
registry = IntegrationRegistry()


def get_all_integration_classes():
    """Get all registered integration classes for parametrized testing."""
    integration_ids = registry.list_ids()
    integration_classes = []

    for integration_id in integration_ids:
        try:
            integration_class = registry.get(integration_id)
            integration_classes.append((integration_id, integration_class))
        except Exception as e:
            print(f"Warning: Could not load integration {integration_id}: {e}")
            continue

    return integration_classes


@pytest.mark.parametrize("integration_id,integration_class", get_all_integration_classes())
class TestIntegrationContracts:
    """Contract tests for all database integrations."""

    def test_inherits_from_base(self, integration_id, integration_class):
        """Integration must inherit from DatabaseIntegration."""
        assert issubclass(integration_class, DatabaseIntegration), \
            f"{integration_id} must inherit from DatabaseIntegration"

    def test_metadata_property(self, integration_id, integration_class):
        """metadata property must return valid DatabaseMetadata."""
        instance = integration_class()
        metadata = instance.metadata

        # Must return DatabaseMetadata instance
        assert isinstance(metadata, DatabaseMetadata), \
            f"{integration_id}.metadata must return DatabaseMetadata instance"

        # Required fields must be present and valid
        assert metadata.name, f"{integration_id}.metadata.name must not be empty"
        assert metadata.id == integration_id, \
            f"{integration_id}.metadata.id must match registry ID"
        assert isinstance(metadata.category, DatabaseCategory), \
            f"{integration_id}.metadata.category must be DatabaseCategory enum"
        assert isinstance(metadata.requires_api_key, bool), \
            f"{integration_id}.metadata.requires_api_key must be bool"
        assert isinstance(metadata.cost_per_query_estimate, (int, float)), \
            f"{integration_id}.metadata.cost_per_query_estimate must be numeric"
        assert metadata.cost_per_query_estimate >= 0, \
            f"{integration_id}.metadata.cost_per_query_estimate must be non-negative"
        assert isinstance(metadata.typical_response_time, (int, float)), \
            f"{integration_id}.metadata.typical_response_time must be numeric"
        assert metadata.typical_response_time > 0, \
            f"{integration_id}.metadata.typical_response_time must be positive"
        assert metadata.description, \
            f"{integration_id}.metadata.description must not be empty"

    async def test_is_relevant_returns_bool(self, integration_id, integration_class):
        """is_relevant() must return bool."""
        instance = integration_class()
        result = await instance.is_relevant("test query")

        assert isinstance(result, bool), \
            f"{integration_id}.is_relevant() must return bool, got {type(result)}"

    async def test_generate_query_returns_dict(self, integration_id, integration_class):
        """generate_query() must return Dict (relevance filter removed)."""
        instance = integration_class()

        # Test with generic query that should work for all sources
        result = await instance.generate_query("cybersecurity intelligence")

        # MUST return Dict now (relevance filter removed)
        assert isinstance(result, dict), \
            f"{integration_id}.generate_query() must return Dict, got {type(result)}"

        # Dict should not be empty
        assert len(result) > 0, \
            f"{integration_id}.generate_query() returned empty dict"

    async def test_execute_search_returns_queryresult(self, integration_id, integration_class):
        """execute_search() must return QueryResult object (not dict)."""
        instance = integration_class()

        # Use minimal valid query params
        query_params = {"test": "test"}

        # Execute in cold mode (no API key)
        result = await instance.execute_search(
            query_params=query_params,
            api_key=None,
            limit=1
        )

        # MUST return QueryResult object, NOT dict
        assert isinstance(result, QueryResult), \
            f"{integration_id}.execute_search() must return QueryResult object, got {type(result)}"

        # QueryResult must have required attributes (not dict keys)
        assert hasattr(result, 'success'), \
            f"{integration_id} QueryResult missing 'success' attribute"
        assert hasattr(result, 'source'), \
            f"{integration_id} QueryResult missing 'source' attribute"
        assert hasattr(result, 'total'), \
            f"{integration_id} QueryResult missing 'total' attribute"
        assert hasattr(result, 'results'), \
            f"{integration_id} QueryResult missing 'results' attribute"

        # Validate attribute types
        assert isinstance(result.success, bool), \
            f"{integration_id} QueryResult.success must be bool"
        assert isinstance(result.source, str), \
            f"{integration_id} QueryResult.source must be str"
        assert isinstance(result.total, int), \
            f"{integration_id} QueryResult.total must be int"
        assert isinstance(result.results, list), \
            f"{integration_id} QueryResult.results must be list"

    async def test_execute_search_cold_mode_graceful_failure(self, integration_id, integration_class):
        """execute_search() must handle missing API key gracefully (cold mode)."""
        instance = integration_class()
        metadata = instance.metadata

        # Skip if integration doesn't require API key (e.g., Discord local search)
        if not metadata.requires_api_key:
            pytest.skip(f"{integration_id} doesn't require API key")

        # Execute with no API key
        result = await instance.execute_search(
            query_params={"test": "test"},
            api_key=None,
            limit=1
        )

        # Must return QueryResult (not crash)
        assert isinstance(result, QueryResult), \
            f"{integration_id} must return QueryResult even without API key"

        # Must indicate failure
        assert result.success is False, \
            f"{integration_id} must set success=False when API key missing"

        # Must have error message
        assert hasattr(result, 'error') and result.error, \
            f"{integration_id} must set error message when API key missing"

        # Must return empty results
        assert result.total == 0, \
            f"{integration_id} must return total=0 when API key missing"
        assert len(result.results) == 0, \
            f"{integration_id} must return empty results when API key missing"

    async def test_execute_search_structural_invariants(self, integration_id, integration_class):
        """execute_search() results must have consistent structure."""
        instance = integration_class()

        # Execute in cold mode
        result = await instance.execute_search(
            query_params={"test": "test"},
            api_key=None,
            limit=1
        )

        # If results exist, validate structure
        if result.results:
            for idx, item in enumerate(result.results):
                assert isinstance(item, dict), \
                    f"{integration_id} result[{idx}] must be dict, got {type(item)}"

                # Common fields that should exist in results
                # (Not all integrations return all fields, but these are typical)
                expected_fields = ['title', 'url', 'content']
                has_some_content = any(field in item for field in expected_fields)

                assert has_some_content, \
                    f"{integration_id} result[{idx}] should have at least one of: {expected_fields}"


@pytest.mark.parametrize("integration_id,integration_class", get_all_integration_classes())
class TestIntegrationQueryGeneration:
    """Test query generation across different query types."""

    async def test_generate_query_military_topic(self, integration_id, integration_class):
        """Test query generation for military topics."""
        instance = integration_class()
        result = await instance.generate_query("F-35 fighter jet training exercises")

        assert isinstance(result, dict), \
            f"{integration_id} must return dict for military query"
        assert len(result) > 0, \
            f"{integration_id} returned empty dict for military query"

    async def test_generate_query_intelligence_topic(self, integration_id, integration_class):
        """Test query generation for intelligence topics."""
        instance = integration_class()
        result = await instance.generate_query("SIGINT signals intelligence collection")

        assert isinstance(result, dict), \
            f"{integration_id} must return dict for intelligence query"
        assert len(result) > 0, \
            f"{integration_id} returned empty dict for intelligence query"

    async def test_generate_query_contract_topic(self, integration_id, integration_class):
        """Test query generation for contract/procurement topics."""
        instance = integration_class()
        result = await instance.generate_query("cybersecurity contracts federal government")

        assert isinstance(result, dict), \
            f"{integration_id} must return dict for contract query"
        assert len(result) > 0, \
            f"{integration_id} returned empty dict for contract query"

    async def test_generate_query_job_topic(self, integration_id, integration_class):
        """Test query generation for job listing topics."""
        instance = integration_class()
        result = await instance.generate_query("intelligence analyst jobs clearance")

        assert isinstance(result, dict), \
            f"{integration_id} must return dict for job query"
        assert len(result) > 0, \
            f"{integration_id} returned empty dict for job query"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
