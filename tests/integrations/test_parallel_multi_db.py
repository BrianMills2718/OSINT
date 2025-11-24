#!/usr/bin/env python3
"""
Integration tests for parallel execution across multiple databases.

Tests the full flow: relevance checking → query generation → parallel execution
with real APIs and real queries.

These tests validate that:
1. Multiple databases can execute in parallel without conflicts
2. Error handling works when some integrations fail
3. Results are properly aggregated and returned
4. Performance is acceptable (<60s for 8 integrations)
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
class TestParallelMultiDB:
    """Integration tests for parallel multi-database execution."""

    @pytest.fixture
    def executor(self):
        """Create parallel executor for tests."""
        return ParallelExecutor(max_concurrent=10)

    @pytest.fixture
    def all_integrations(self):
        """Get all enabled integrations from registry."""
        return list(registry.get_all_enabled().values())

    @pytest.fixture
    def api_keys(self):
        """Load API keys from environment."""
        return {
            "sam": os.getenv("SAM_GOV_API_KEY"),
            "usajobs": os.getenv("USAJOBS_API_KEY"),
            "dvids": os.getenv("DVIDS_API_KEY"),
            "twitter": os.getenv("RAPIDAPI_KEY"),
            "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
        }

    @pytest.mark.asyncio
    async def test_all_integrations_parallel_happy_path(self, executor, all_integrations, api_keys):
        """
        Test: All 8 integrations execute in parallel successfully.

        Success criteria:
        - At least 3 integrations return results
        - Execution time < 60s
        - No crashes or exceptions
        """
        start_time = datetime.now()

        result_dict = await executor.execute_all(
            research_question="cybersecurity threat intelligence",
            databases=all_integrations,
            api_keys=api_keys,
            limit=5
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Assertions
        assert len(result_dict) > 0, "Should return at least some results"
        assert duration < 60, f"Should complete in <60s, took {duration:.1f}s"

        # Count successful vs failed
        successful = [r for r in result_dict.values() if r.success]
        failed = [r for r in result_dict.values() if not r.success]

        print(f"\n{'='*60}")
        print(f"Parallel Execution Results:")
        print(f"  Total integrations: {len(result_dict)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Duration: {duration:.1f}s")
        print(f"{'='*60}\n")

        # Should have at least 3 successful integrations
        assert len(successful) >= 3, f"Expected >=3 successful, got {len(successful)}"

        # Verify result structure
        for db_id, result in result_dict.items():
            assert hasattr(result, 'success'), f"{db_id}: Missing 'success' attribute"
            assert hasattr(result, 'source'), f"{db_id}: Missing 'source' attribute"
            assert hasattr(result, 'total'), f"{db_id}: Missing 'total' attribute"
            assert hasattr(result, 'results'), f"{db_id}: Missing 'results' attribute"
            assert isinstance(result.results, list), f"{db_id}: 'results' must be a list"

    @pytest.mark.asyncio
    async def test_mixed_relevant_irrelevant(self, executor, all_integrations, api_keys):
        """
        Test: Query that's only relevant to some databases.

        Success criteria:
        - Some integrations marked as not relevant
        - Relevant ones return results
        - Irrelevant ones either skip or return 0 results
        """
        # Use a very specific query that won't be relevant to all DBs
        result_dict = await executor.execute_all(
            research_question="federal job openings for intelligence analysts",
            databases=all_integrations,
            api_keys=api_keys,
            limit=5
        )

        # USAJobs should be relevant
        if "usajobs" in result_dict:
            usajobs_result = result_dict["usajobs"]
            print(f"\nUSAJobs result: success={usajobs_result.success}, total={usajobs_result.total}")

        # SAM.gov (contracts) might not be relevant
        if "sam" in result_dict:
            sam_result = result_dict["sam"]
            print(f"SAM.gov result: success={sam_result.success}, total={sam_result.total}")

        # At least one integration should have results
        total_results = sum(r.total for r in result_dict.values() if r.success)
        assert total_results > 0, "Should get some results from relevant databases"

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_api_key(self, executor, all_integrations):
        """
        Test: One integration has invalid API key, others should still work.

        Success criteria:
        - Invalid key integration fails gracefully
        - Other integrations continue working
        - No crashes or exceptions propagating
        """
        # Use invalid API keys for some integrations
        bad_api_keys = {
            "sam": "INVALID_KEY",
            "usajobs": os.getenv("USAJOBS_API_KEY"),  # Valid
            "dvids": os.getenv("DVIDS_API_KEY"),      # Valid
        }

        result_dict = await executor.execute_all(
            research_question="test query",
            databases=all_integrations,
            api_keys=bad_api_keys,
            limit=5
        )

        # Should get results from at least some integrations
        assert len(result_dict) > 0, "Should return results despite one failure"

        # SAM should fail (invalid key), but gracefully
        if "sam" in result_dict:
            sam_result = result_dict["sam"]
            # Should either fail gracefully or skip
            print(f"\nSAM (invalid key): success={sam_result.success}, error={sam_result.error}")

        # DVIDS/USAJobs should work
        successful = [r for r in result_dict.values() if r.success and r.total > 0]
        print(f"Successful integrations despite SAM failure: {len(successful)}")

        # Should have at least one success
        assert len(successful) >= 1, "At least one integration should succeed"

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, executor, api_keys):
        """
        Test: Integration handles rate limits gracefully.

        Success criteria:
        - Rate limited requests return error (not crash)
        - Error message indicates rate limit
        - Other integrations unaffected
        """
        # SAM.gov is known to have rate limits
        from integrations.government.sam_integration import SAMIntegration
        sam = SAMIntegration()

        result_dict = await executor.execute_all(
            research_question="test query",
            databases=[sam],
            api_keys=api_keys,
            limit=5
        )

        if "sam" in result_dict:
            result = result_dict["sam"]
            print(f"\nSAM rate limit test: success={result.success}")
            if not result.success:
                print(f"Error: {result.error}")
                # Should mention rate limit or 429 if hit
                if result.error:
                    assert "429" in result.error or "rate" in result.error.lower(), \
                           "Error should mention rate limiting"

    @pytest.mark.asyncio
    async def test_performance_8_integrations_under_60s(self, executor, all_integrations, api_keys):
        """
        Test: 8 integrations execute in parallel in <60s.

        Success criteria:
        - Total execution time < 60s
        - All integrations attempted (success or graceful failure)
        """
        start_time = datetime.now()

        result_dict = await executor.execute_all(
            research_question="military intelligence operations",
            databases=all_integrations,
            api_keys=api_keys,
            limit=10
        )

        duration = (datetime.now() - start_time).total_seconds()

        print(f"\nPerformance test results:")
        print(f"  Integrations tested: {len(result_dict)}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Average per integration: {duration/len(result_dict):.1f}s")

        # Performance assertion
        assert duration < 60, f"Should complete in <60s, took {duration:.1f}s"

        # Should attempt all integrations
        assert len(result_dict) == len(all_integrations), \
               f"Should attempt all {len(all_integrations)} integrations"


if __name__ == "__main__":
    """Run tests directly."""
    print("=" * 80)
    print("PARALLEL MULTI-DB INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "-s"])

    sys.exit(exit_code)
