#!/usr/bin/env python3
"""
Tests for Jina Reader integration.

Tests:
- Single page fetch
- Multiple page fetch with rate limiting
- Error handling (timeouts, bad URLs)
- Content enrichment helper
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.jina_reader import (
    fetch_page_content,
    fetch_multiple_pages,
    enrich_search_results,
    PageContent
)


class TestJinaReader:
    """Test suite for Jina Reader functionality."""

    @pytest.mark.asyncio
    async def test_fetch_single_page(self):
        """Test fetching a single page."""
        result = await fetch_page_content("https://example.com", timeout=15)

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.content_length > 0
        assert result.fetch_time_ms > 0
        assert result.error is None
        print(f"[PASS] Single page fetch: {result.content_length} chars in {result.fetch_time_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_fetch_bad_url(self):
        """Test handling of invalid URL."""
        result = await fetch_page_content("https://this-domain-does-not-exist-12345.com", timeout=5)

        assert result.success is False
        assert result.error is not None
        print(f"[PASS] Bad URL handled: {result.error}")

    @pytest.mark.asyncio
    async def test_fetch_multiple_pages(self):
        """Test fetching multiple pages with rate limiting."""
        urls = [
            "https://example.com",
            "https://httpbin.org/html",
        ]

        results = await fetch_multiple_pages(urls, max_concurrent=2, timeout=15)

        assert len(results) == 2
        successful = sum(1 for r in results if r.success)
        print(f"[PASS] Multiple pages: {successful}/{len(urls)} succeeded")

    def test_enrich_search_results(self):
        """Test enriching search results with fetched content."""
        search_results = [
            {"title": "Test 1", "url": "http://example.com/1", "snippet": "Snippet 1"},
            {"title": "Test 2", "url": "http://example.com/2", "snippet": "Snippet 2"},
            {"title": "Test 3", "url": "http://example.com/3", "snippet": "Snippet 3"},
        ]

        page_contents = [
            PageContent(url="http://example.com/1", success=True, content="Full content 1", content_length=14, fetch_time_ms=100),
            PageContent(url="http://example.com/3", success=True, content="Full content 3", content_length=14, fetch_time_ms=150),
        ]

        enriched = enrich_search_results(search_results, page_contents)

        assert len(enriched) == 3
        assert enriched[0].get("full_content") == "Full content 1"
        assert enriched[1].get("full_content") is None  # URL 2 wasn't fetched
        assert enriched[2].get("full_content") == "Full content 3"
        print(f"[PASS] Search results enriched correctly")


class TestContentEnrichmentMixin:
    """Test the content enrichment mixin integration."""

    @pytest.mark.asyncio
    async def test_mixin_available(self):
        """Test that mixin methods are available on SimpleDeepResearch."""
        from research.deep_research import SimpleDeepResearch

        research = SimpleDeepResearch(max_tasks=1, max_time_minutes=1)

        assert hasattr(research, '_enrich_results_with_content')
        assert hasattr(research, '_select_urls_for_content_fetch')
        print("[PASS] Content enrichment methods available")


if __name__ == "__main__":
    # Run quick smoke test
    async def smoke_test():
        print("Running Jina Reader smoke tests...\n")

        # Test 1: Single page
        print("Test 1: Single page fetch")
        result = await fetch_page_content("https://example.com", timeout=15)
        assert result.success, f"Single page fetch failed: {result.error}"
        print(f"  [PASS] {result.content_length} chars fetched\n")

        # Test 2: Mixin available
        print("Test 2: Mixin integration")
        from research.deep_research import SimpleDeepResearch
        research = SimpleDeepResearch(max_tasks=1, max_time_minutes=1)
        assert hasattr(research, '_enrich_results_with_content')
        print("  [PASS] Methods available\n")

        # Test 3: Config accessible
        print("Test 3: Config option")
        from config_loader import config
        max_fetches = config.get_raw_config().get("research", {}).get("max_full_page_fetches", 0)
        print(f"  [PASS] max_full_page_fetches = {max_fetches}\n")

        print("All smoke tests passed!")

    asyncio.run(smoke_test())
