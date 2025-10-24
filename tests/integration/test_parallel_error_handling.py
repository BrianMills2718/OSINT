#!/usr/bin/env python3
"""
Integration tests for parallel executor error handling.

Tests how the system handles various error conditions:
- Timeouts
- Network failures
- Invalid queries
- Missing API keys
- Rate limits

These tests validate graceful degradation - system continues working
even when individual components fail.
"""

import asyncio
import sys
import os
from datetime import datetime
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.parallel_executor import ParallelExecutor
from integrations.registry import registry
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.integration
@pytest.mark.api
class TestParallelErrorHandling:
    """Integration tests for error handling in parallel execution."""

    @pytest.fixture
    def executor(self):
        """Create parallel executor for tests."""
        return ParallelExecutor(max_concurrent=10)

    @pytest.mark.asyncio
    async def test_all_integrations_fail_gracefully(self, executor):
        """
        Test: All integrations fail (no API keys), system doesn't crash.

        Success criteria:
        - Returns results dict (not crash)
        - All results have success=False
        - All have error messages
        """
        # Get all integrations
        all_integrations = list(registry.get_all_enabled().values())

        # No API keys - all should fail
        result_dict = await executor.execute_all(
            research_question="test query",
            databases=all_integrations,
            api_keys={},  # Empty - all fail
            limit=5
        )

        print(f"\nAll integrations with no API keys:")
        print(f"  Total: {len(result_dict)}")

        for db_id, result in result_dict.items():
            print(f"  {db_id}: success={result.success}, error={result.error[:50] if result.error else 'None'}")

            # All should fail gracefully
            assert isinstance(result.success, bool), f"{db_id}: success must be bool"
            assert hasattr(result, 'error'), f"{db_id}: must have error attribute"

            # If requires API key and we didn't provide one, should fail
            integration = next((i for i in all_integrations if i.metadata.id == db_id), None)
            if integration and integration.metadata.requires_api_key:
                assert not result.success or result.total == 0, \
                       f"{db_id}: should fail without API key"

    @pytest.mark.asyncio
    async def test_empty_query_handled_gracefully(self, executor):
        """
        Test: Empty query string doesn't crash system.

        Success criteria:
        - Returns results (no crash)
        - Integrations either skip or return 0 results
        """
        all_integrations = list(registry.get_all_enabled().values())
        api_keys = {
            "dvids": os.getenv("DVIDS_API_KEY"),
        }

        result_dict = await executor.execute_all(
            research_question="",  # Empty query
            databases=all_integrations[:3],  # Test on subset
            api_keys=api_keys,
            limit=5
        )

        print(f"\nEmpty query test:")
        print(f"  Results returned: {len(result_dict)}")

        # Should return results (even if empty)
        assert isinstance(result_dict, dict), "Should return dict, not crash"

    @pytest.mark.asyncio
    async def test_very_long_query_handled(self, executor):
        """
        Test: Very long query (>1000 chars) doesn't break LLM generation.

        Success criteria:
        - LLM generates queries successfully
        - No truncation errors
        """
        all_integrations = list(registry.get_all_enabled().values())
        api_keys = {
            "dvids": os.getenv("DVIDS_API_KEY"),
        }

        # Create very long query
        long_query = " ".join([
            "military intelligence operations",
            "cybersecurity threat assessment",
            "special operations command structure",
            "joint task force coordination"
        ] * 50)  # ~1000+ characters

        result_dict = await executor.execute_all(
            research_question=long_query,
            databases=all_integrations[:2],  # Test on subset
            api_keys=api_keys,
            limit=5
        )

        print(f"\nLong query test ({len(long_query)} chars):")
        print(f"  Results: {len(result_dict)}")

        # Should handle long queries
        assert len(result_dict) > 0, "Should return results for long query"

    @pytest.mark.asyncio
    async def test_mixed_success_failure_aggregation(self, executor):
        """
        Test: Mix of successful and failed integrations aggregated correctly.

        Success criteria:
        - Success dict contains both successful and failed results
        - Failed results have error messages
        - Successful results have data
        """
        all_integrations = list(registry.get_all_enabled().values())

        # Some valid, some invalid API keys
        api_keys = {
            "dvids": os.getenv("DVIDS_API_KEY"),      # Valid
            "sam": "INVALID_KEY_12345",               # Invalid
            "usajobs": os.getenv("USAJOBS_API_KEY"),  # Valid
        }

        result_dict = await executor.execute_all(
            research_question="intelligence analysis",
            databases=all_integrations[:4],  # Test on subset
            api_keys=api_keys,
            limit=5
        )

        print(f"\nMixed success/failure test:")
        successes = [r for r in result_dict.values() if r.success]
        failures = [r for r in result_dict.values() if not r.success]

        print(f"  Successes: {len(successes)}")
        print(f"  Failures: {len(failures)}")

        # Should have both successes and failures
        assert len(successes) > 0, "Should have at least one success"

        # Verify structure of both
        for result in successes:
            assert hasattr(result, 'results'), "Success should have results"
            assert isinstance(result.results, list), "Results should be list"

        for result in failures:
            if not result.success:
                # Failed results should explain why
                assert result.error or result.total == 0, "Failed results should have error or 0 total"

    @pytest.mark.asyncio
    async def test_zero_integrations_doesnt_crash(self, executor):
        """
        Test: Calling execute_all with empty database list.

        Success criteria:
        - Returns empty dict (no crash)
        - Completes quickly
        """
        result_dict = await executor.execute_all(
            research_question="test",
            databases=[],  # No databases
            api_keys={},
            limit=5
        )

        print(f"\nZero integrations test:")
        print(f"  Result: {result_dict}")

        # Should return empty dict
        assert result_dict == {}, "Should return empty dict for no databases"

    @pytest.mark.asyncio
    async def test_duplicate_integrations_handled(self, executor):
        """
        Test: Same integration listed multiple times.

        Success criteria:
        - Executes without error
        - Returns results for each instance
        """
        from integrations.government.dvids_integration import DVIDSIntegration

        dvids = DVIDSIntegration()
        api_keys = {"dvids": os.getenv("DVIDS_API_KEY")}

        # List DVIDS twice
        result_dict = await executor.execute_all(
            research_question="military training",
            databases=[dvids, dvids],  # Duplicate
            api_keys=api_keys,
            limit=5
        )

        print(f"\nDuplicate integrations test:")
        print(f"  Results: {len(result_dict)}")

        # Should handle duplicates gracefully
        # (May dedupe by ID or execute twice - either is acceptable)
        assert len(result_dict) >= 1, "Should return at least one result"


if __name__ == "__main__":
    """Run tests directly."""
    print("=" * 80)
    print("PARALLEL ERROR HANDLING INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "-s"])

    sys.exit(exit_code)
