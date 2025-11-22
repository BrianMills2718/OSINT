#!/usr/bin/env python3
"""
Test integration rejection reasoning wrapper end-to-end.

Verifies that:
1. Base class wrapper extracts rejection reasoning
2. ParallelExecutor logs and displays rejection reasoning
3. Clean params are passed to execute_search() (no metadata pollution)

NOTE: This is an integration test that requires live API keys.
      Run manually with: PYTHONPATH=/home/brian/sam_gov python3 tests/test_rejection_reasoning.py
      Not run in CI (requires SAM_GOV_API_KEY environment variable)
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from core.parallel_executor import ParallelExecutor
from integrations.government.sam_integration import SAMIntegration

load_dotenv()


# Skip if no API key (CI environment)
if not os.getenv("SAM_GOV_API_KEY"):
    print("⊘ SKIPPED: SAM_GOV_API_KEY not set (integration test requires live API)")
    print("  To run: export SAM_GOV_API_KEY=<key> && PYTHONPATH=/home/brian/sam_gov python3 tests/test_rejection_reasoning.py")
    sys.exit(0)


async def test_rejection_case():
    """Test SAM.gov rejects job-related query with reasoning."""
    print("=" * 80)
    print("TEST 1: SAM.gov Rejection (Job Query)")
    print("=" * 80)
    print()

    executor = ParallelExecutor(max_concurrent=1)

    # Query that should be rejected by SAM.gov
    result = await executor.execute_all(
        research_question="What cybersecurity analyst jobs are available at the FBI?",
        databases=[SAMIntegration()],
        api_keys={"sam": os.getenv("SAM_GOV_API_KEY")},
        limit=5
    )

    print()
    print("-" * 80)
    print("RESULT:")
    print(f"  Number of results: {len(result)}")

    if "sam" in result:
        sam_result = result["sam"]
        print(f"  SAM.gov success: {sam_result.success}")
        print(f"  SAM.gov total: {sam_result.total}")
        print(f"  SAM.gov error: {sam_result.error}")
        print(f"  SAM.gov metadata: {sam_result.metadata}")

        # Verify rejection reasoning is captured
        if not sam_result.success:
            assert sam_result.error and "not relevant" in sam_result.error.lower(), \
                "Expected rejection error message"
            print("\n✓ Rejection reasoning captured in error message")
        else:
            print("\n✗ UNEXPECTED: Query was accepted (should have been rejected)")
    else:
        print("  SAM.gov not in results (query generation failed)")

    print()
    return result


async def test_acceptance_case():
    """Test SAM.gov accepts contract-related query."""
    print("=" * 80)
    print("TEST 2: SAM.gov Acceptance (Contract Query)")
    print("=" * 80)
    print()

    executor = ParallelExecutor(max_concurrent=1)

    # Query that should be accepted by SAM.gov
    result = await executor.execute_all(
        research_question="What cybersecurity contracts are available from the FBI?",
        databases=[SAMIntegration()],
        api_keys={"sam": os.getenv("SAM_GOV_API_KEY")},
        limit=5
    )

    print()
    print("-" * 80)
    print("RESULT:")
    print(f"  Number of results: {len(result)}")

    if "sam" in result:
        sam_result = result["sam"]
        print(f"  SAM.gov success: {sam_result.success}")
        print(f"  SAM.gov total: {sam_result.total}")
        print(f"  SAM.gov results count: {len(sam_result.results)}")

        if sam_result.success:
            print("\n✓ Query accepted and executed")

            # Verify query_params are clean (no metadata pollution)
            params = sam_result.query_params
            assert "relevant" not in params, "Metadata key 'relevant' should be stripped"
            assert "rejection_reason" not in params, "Metadata key 'rejection_reason' should be stripped"
            assert "suggested_reformulation" not in params, "Metadata key 'suggested_reformulation' should be stripped"
            print("✓ Query params are clean (no metadata pollution)")
        else:
            print(f"\n✗ Query rejected: {sam_result.error}")
    else:
        print("  SAM.gov not in results (query generation failed)")

    print()
    return result


async def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "REJECTION REASONING WRAPPER TEST" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Test rejection case
    await test_rejection_case()

    # Test acceptance case
    await test_acceptance_case()

    print("=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
