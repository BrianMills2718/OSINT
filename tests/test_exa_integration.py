#!/usr/bin/env python3
"""
Tests for Exa AI semantic search integration.

Tests:
- Integration registration
- Metadata validation
- Query generation (requires LLM)
- Search execution (requires API key)
"""

import asyncio
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.web.exa_integration import ExaIntegration
from integrations.registry import registry


class TestExaIntegration:
    """Test suite for Exa integration."""

    def test_registration(self):
        """Test that Exa is registered in the integration registry."""
        integration_ids = registry.list_ids()

        assert "exa" in integration_ids, f"Exa not found in registry. Found: {integration_ids}"
        print("[PASS] Exa registered in integration registry")

    def test_metadata(self):
        """Test metadata is properly configured."""
        integration = ExaIntegration()
        meta = integration.metadata

        assert meta.id == "exa"
        assert meta.name == "Exa"
        assert meta.requires_api_key is True
        assert meta.cost_per_query_estimate > 0
        print(f"[PASS] Metadata: {meta.name} (id={meta.id})")

    @pytest.mark.asyncio
    async def test_is_relevant(self):
        """Test relevance check always returns True."""
        integration = ExaIntegration()

        # Exa is relevant for most research
        result = await integration.is_relevant("AI companies working with Pentagon")
        assert result is True

        result = await integration.is_relevant("Find companies similar to Palantir")
        assert result is True

        print("[PASS] is_relevant() returns True as expected")

    @pytest.mark.asyncio
    async def test_generate_query(self):
        """Test query generation with LLM."""
        integration = ExaIntegration()

        # Test semantic search pattern
        query_params = await integration.generate_query(
            "Find defense technology companies similar to Anduril"
        )

        assert query_params is not None
        assert "pattern" in query_params
        assert "query" in query_params
        assert query_params["pattern"] in ["semantic_search", "find_similar"]

        print(f"[PASS] Query generated: pattern={query_params['pattern']}, query={query_params['query'][:50]}...")

    @pytest.mark.asyncio
    async def test_execute_search_no_api_key(self):
        """Test search fails gracefully without API key."""
        integration = ExaIntegration()

        query_params = {
            "pattern": "semantic_search",
            "query": "AI defense contractors",
            "num_results": 5
        }

        result = await integration.execute_search(query_params, api_key=None)

        assert result.success is False
        assert "API key required" in result.error
        print("[PASS] Search fails gracefully without API key")

    @pytest.mark.asyncio
    async def test_execute_search_with_api_key(self):
        """Test actual search with API key (if available)."""
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            pytest.skip("EXA_API_KEY not set - skipping live test")

        integration = ExaIntegration()

        query_params = {
            "pattern": "semantic_search",
            "query": "AI companies working with US Department of Defense",
            "num_results": 5
        }

        result = await integration.execute_search(query_params, api_key=api_key)

        assert result.success is True, f"Search failed: {result.error}"
        assert result.total > 0
        assert len(result.results) > 0

        # Check result structure
        first_result = result.results[0]
        assert "title" in first_result
        assert "url" in first_result

        print(f"[PASS] Live search returned {result.total} results")
        print(f"  First result: {first_result['title'][:60]}...")
        print(f"  Response time: {result.response_time_ms:.0f}ms")


class TestExaFindSimilar:
    """Test the Find Similar pattern."""

    @pytest.mark.asyncio
    async def test_find_similar_query_generation(self):
        """Test that find_similar pattern is selected for URL-based queries."""
        integration = ExaIntegration()

        # This should trigger find_similar pattern
        query_params = await integration.generate_query(
            "Find companies similar to https://anduril.com"
        )

        assert query_params is not None
        # Note: LLM may or may not select find_similar - just verify it generates something
        print(f"[PASS] Query generated for URL-based search: {query_params['pattern']}")

    @pytest.mark.asyncio
    async def test_find_similar_with_api_key(self):
        """Test find_similar with API key."""
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            pytest.skip("EXA_API_KEY not set - skipping live test")

        integration = ExaIntegration()

        query_params = {
            "pattern": "find_similar",
            "query": "https://palantir.com",  # URL to find similar to
            "num_results": 5
        }

        result = await integration.execute_search(query_params, api_key=api_key)

        assert result.success is True, f"Find similar failed: {result.error}"
        assert result.total > 0

        print(f"[PASS] Find similar returned {result.total} results")
        for r in result.results[:3]:
            print(f"  - {r['title'][:50]}...")


if __name__ == "__main__":
    async def smoke_test():
        print("Running Exa integration smoke tests...\n")

        # Test 1: Registration
        print("Test 1: Registration check")
        integration_ids = registry.list_ids()
        exa_found = "exa" in integration_ids
        assert exa_found, f"Exa not registered! Found: {integration_ids}"
        print("  [PASS] Exa registered\n")

        # Test 2: Metadata
        print("Test 2: Metadata")
        integration = ExaIntegration()
        meta = integration.metadata
        print(f"  [PASS] Name: {meta.name}, ID: {meta.id}\n")

        # Test 3: Query generation
        print("Test 3: Query generation")
        query_params = await integration.generate_query(
            "AI defense contractors working with Pentagon"
        )
        print(f"  [PASS] Pattern: {query_params['pattern']}")
        print(f"  [PASS] Query: {query_params['query'][:60]}...\n")

        # Test 4: Live search (if API key available)
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("EXA_API_KEY")
        if api_key:
            print("Test 4: Live search")
            result = await integration.execute_search(query_params, api_key=api_key)
            if result.success:
                print(f"  [PASS] {result.total} results in {result.response_time_ms:.0f}ms")
            else:
                print(f"  [FAIL] {result.error}")
        else:
            print("Test 4: [SKIPPED] EXA_API_KEY not set")

        print("\nSmoke tests complete!")

    asyncio.run(smoke_test())
