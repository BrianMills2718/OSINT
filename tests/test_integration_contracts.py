#!/usr/bin/env python3
"""
Contract tests for integration query generation.

These tests enforce the contract that generate_query() must NEVER return:
1. None (unless truly not relevant - but we removed relevance filter)
2. Empty keywords
3. Invalid query structure

PURPOSE: Catch prompt regressions early before they reach production.
Without these tests, a bad prompt update could cause integrations to silently
return None, making them unavailable without any visibility.

CODEX RECOMMENDATION: "Fold structural invariant checks into contract tests
so we get early warning if prompts regress."
"""

import asyncio
import pytest
from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Integration imports
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.social.discord_integration import DiscordIntegration


# Diverse test queries to exercise different topics
TEST_QUERIES = [
    "SIGINT",
    "cybersecurity contracts",  # Non-military (tests DVIDS with non-military topic)
    "North Korea nuclear program",
    "intelligence analyst jobs",
    "random topic xyz123"  # Edge case - nonsense query
]


class TestDVIDSContract:
    """Contract tests for DVIDS integration."""

    @pytest.mark.asyncio
    async def test_never_returns_none(self):
        """DVIDS must never return None for any query."""
        dvids = DVIDSIntegration()

        for query in TEST_QUERIES:
            result = await dvids.generate_query(query)

            assert result is not None, (
                f"DVIDS returned None for query: '{query}'. "
                f"This violates the contract - all queries should generate parameters. "
                f"Check prompt in dvids_integration.py for regressions."
            )

    @pytest.mark.asyncio
    async def test_never_returns_empty_keywords(self):
        """DVIDS must never return empty keywords."""
        dvids = DVIDSIntegration()

        for query in TEST_QUERIES:
            result = await dvids.generate_query(query)

            assert result is not None, f"DVIDS returned None for '{query}'"

            # Must have keywords field
            assert "keywords" in result, (
                f"DVIDS missing 'keywords' field for query: '{query}'"
            )

            # Keywords must be non-empty string
            keywords = result["keywords"]
            assert isinstance(keywords, str), (
                f"DVIDS keywords must be string, got {type(keywords)} for '{query}'"
            )
            assert keywords.strip() != "", (
                f"DVIDS returned empty keywords for query: '{query}'. "
                f"This indicates a prompt regression. "
                f"Prompt should guide LLM to NEVER return empty keywords."
            )

    @pytest.mark.asyncio
    async def test_required_fields_present(self):
        """DVIDS must return all required query parameter fields."""
        dvids = DVIDSIntegration()

        required_fields = ["keywords", "media_types", "branches", "country", "from_date", "to_date"]

        result = await dvids.generate_query("SIGINT signals intelligence")

        assert result is not None, "DVIDS returned None"

        for field in required_fields:
            assert field in result, (
                f"DVIDS missing required field '{field}'. "
                f"Check schema in generate_query() method."
            )


class TestDiscordContract:
    """Contract tests for Discord integration."""

    @pytest.mark.asyncio
    async def test_never_returns_none(self):
        """Discord must never return None for any query."""
        discord = DiscordIntegration()

        for query in TEST_QUERIES:
            result = await discord.generate_query(query)

            assert result is not None, (
                f"Discord returned None for query: '{query}'. "
                f"This violates the contract - all queries should generate parameters."
            )

    @pytest.mark.asyncio
    async def test_never_returns_empty_keywords(self):
        """Discord must never return empty keywords list."""
        discord = DiscordIntegration()

        for query in TEST_QUERIES:
            result = await discord.generate_query(query)

            assert result is not None, f"Discord returned None for '{query}'"

            # Must have keywords field
            assert "keywords" in result, (
                f"Discord missing 'keywords' field for query: '{query}'"
            )

            # Keywords must be non-empty list
            keywords = result["keywords"]
            assert isinstance(keywords, list), (
                f"Discord keywords must be list, got {type(keywords)} for '{query}'"
            )
            assert len(keywords) > 0, (
                f"Discord returned empty keywords list for query: '{query}'. "
                f"This indicates a prompt regression. "
                f"LLM should NEVER return empty list - even for nonsense queries."
            )

    @pytest.mark.asyncio
    async def test_keywords_are_strings(self):
        """Discord keywords must be list of strings."""
        discord = DiscordIntegration()

        result = await discord.generate_query("SIGINT")

        assert result is not None
        keywords = result["keywords"]

        for i, keyword in enumerate(keywords):
            assert isinstance(keyword, str), (
                f"Discord keyword[{i}] must be string, got {type(keyword)}: {keyword}"
            )
            assert keyword.strip() != "", (
                f"Discord keyword[{i}] is empty string"
            )


class TestClearanceJobsContract:
    """Contract tests for ClearanceJobs integration."""

    @pytest.mark.asyncio
    async def test_never_returns_none(self):
        """ClearanceJobs must never return None for any query."""
        cj = ClearanceJobsIntegration()

        for query in TEST_QUERIES:
            result = await cj.generate_query(query)

            assert result is not None, (
                f"ClearanceJobs returned None for query: '{query}'. "
                f"This violates the contract - all queries should generate parameters."
            )

    @pytest.mark.asyncio
    async def test_never_returns_empty_keywords(self):
        """ClearanceJobs must never return empty keywords."""
        cj = ClearanceJobsIntegration()

        for query in TEST_QUERIES:
            result = await cj.generate_query(query)

            assert result is not None, f"ClearanceJobs returned None for '{query}'"

            # Must have keywords field
            assert "keywords" in result, (
                f"ClearanceJobs missing 'keywords' field for query: '{query}'"
            )

            # Keywords must be non-empty string
            keywords = result["keywords"]
            assert isinstance(keywords, str), (
                f"ClearanceJobs keywords must be string, got {type(keywords)} for '{query}'"
            )
            assert keywords.strip() != "", (
                f"ClearanceJobs returned empty keywords for query: '{query}'. "
                f"This indicates a prompt regression."
            )

    @pytest.mark.asyncio
    async def test_keywords_reasonable_length(self):
        """ClearanceJobs keywords should be focused (not too long)."""
        cj = ClearanceJobsIntegration()

        # Test that prompt guidance prevents excessively long queries
        result = await cj.generate_query("cybersecurity analyst")

        assert result is not None
        keywords = result["keywords"]

        # Should be focused (< 100 chars for typical queries)
        # Not a hard limit, but a guideline check
        assert len(keywords) < 500, (
            f"ClearanceJobs keywords very long ({len(keywords)} chars): '{keywords}'. "
            f"Prompt guidance may not be working. "
            f"Expected focused query (e.g., 'cybersecurity analyst OR SOC analyst')."
        )


async def test_contract_suite():
    """Run all contract tests manually."""
    print("Running Integration Contract Tests...")
    print("=" * 60)

    # DVIDS tests
    print("\n[DVIDS Contract Tests]")
    dvids_tests = TestDVIDSContract()
    try:
        await dvids_tests.test_never_returns_none()
        print("  ✓ Never returns None")
    except AssertionError as e:
        print(f"  ✗ Never returns None: {e}")

    try:
        await dvids_tests.test_never_returns_empty_keywords()
        print("  ✓ Never returns empty keywords")
    except AssertionError as e:
        print(f"  ✗ Never returns empty keywords: {e}")

    try:
        await dvids_tests.test_required_fields_present()
        print("  ✓ Required fields present")
    except AssertionError as e:
        print(f"  ✗ Required fields present: {e}")

    # Discord tests
    print("\n[Discord Contract Tests]")
    discord_tests = TestDiscordContract()
    try:
        await discord_tests.test_never_returns_none()
        print("  ✓ Never returns None")
    except AssertionError as e:
        print(f"  ✗ Never returns None: {e}")

    try:
        await discord_tests.test_never_returns_empty_keywords()
        print("  ✓ Never returns empty keywords")
    except AssertionError as e:
        print(f"  ✗ Never returns empty keywords: {e}")

    try:
        await discord_tests.test_keywords_are_strings()
        print("  ✓ Keywords are strings")
    except AssertionError as e:
        print(f"  ✗ Keywords are strings: {e}")

    # ClearanceJobs tests
    print("\n[ClearanceJobs Contract Tests]")
    cj_tests = TestClearanceJobsContract()
    try:
        await cj_tests.test_never_returns_none()
        print("  ✓ Never returns None")
    except AssertionError as e:
        print(f"  ✗ Never returns None: {e}")

    try:
        await cj_tests.test_never_returns_empty_keywords()
        print("  ✓ Never returns empty keywords")
    except AssertionError as e:
        print(f"  ✗ Never returns empty keywords: {e}")

    try:
        await cj_tests.test_keywords_reasonable_length()
        print("  ✓ Keywords reasonable length")
    except AssertionError as e:
        print(f"  ✗ Keywords reasonable length: {e}")

    print("\n" + "=" * 60)
    print("Contract tests complete!")


# Main test runner
if __name__ == "__main__":
    """Run contract tests directly for quick validation."""
    asyncio.run(test_contract_suite())
