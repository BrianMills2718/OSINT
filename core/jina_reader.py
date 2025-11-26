#!/usr/bin/env python3
"""
Jina Reader - Web content fetcher for LLM-friendly markdown extraction.

Converts any URL to clean markdown suitable for LLM analysis.
Uses Jina AI's Reader API: https://jina.ai/reader/

Usage:
    from core.jina_reader import fetch_page_content, fetch_multiple_pages

    # Single page
    content = await fetch_page_content("https://example.com/article")

    # Multiple pages (with rate limiting)
    contents = await fetch_multiple_pages(urls, max_concurrent=5)

Rate Limits (Jina Reader):
    - Without API key: 20 requests/minute
    - With free API key: 200 requests/minute
    - Paid tiers for higher limits

API Key:
    Set JINA_API_KEY in .env for higher rate limits (optional)
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Jina Reader configuration
JINA_READER_BASE = "https://r.jina.ai/"
JINA_API_KEY = os.getenv("JINA_API_KEY")  # Optional - increases rate limit

# Rate limiting
REQUESTS_PER_MINUTE = 200 if JINA_API_KEY else 20
REQUEST_DELAY = 60.0 / REQUESTS_PER_MINUTE  # Seconds between requests


@dataclass
class PageContent:
    """Result of fetching a single page."""
    url: str
    success: bool
    content: Optional[str] = None  # Markdown content
    title: Optional[str] = None
    error: Optional[str] = None
    fetch_time_ms: float = 0.0
    content_length: int = 0


async def fetch_page_content(
    url: str,
    timeout: int = 30,
    max_content_length: int = 50000
) -> PageContent:
    """
    Fetch a single URL and convert to markdown using Jina Reader.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        max_content_length: Maximum content length to return (chars)

    Returns:
        PageContent with markdown content or error
    """
    start_time = datetime.now()
    jina_url = f"{JINA_READER_BASE}{url}"

    headers = {
        "Accept": "text/markdown",
    }

    # Add API key if available for higher rate limits
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                jina_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                fetch_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                if response.status != 200:
                    return PageContent(
                        url=url,
                        success=False,
                        error=f"HTTP {response.status}: {response.reason}",
                        fetch_time_ms=fetch_time_ms
                    )

                content = await response.text()

                # Extract title from first markdown heading if present
                title = None
                lines = content.split('\n')
                for line in lines[:10]:  # Check first 10 lines
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break

                # Truncate if too long
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "\n\n[Content truncated...]"

                return PageContent(
                    url=url,
                    success=True,
                    content=content,
                    title=title,
                    fetch_time_ms=fetch_time_ms,
                    content_length=len(content)
                )

    except asyncio.TimeoutError:
        fetch_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return PageContent(
            url=url,
            success=False,
            error="Request timed out",
            fetch_time_ms=fetch_time_ms
        )
    except Exception as e:
        fetch_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"Jina Reader fetch failed for {url}: {e}", exc_info=True)
        return PageContent(
            url=url,
            success=False,
            error=str(e),
            fetch_time_ms=fetch_time_ms
        )


async def fetch_multiple_pages(
    urls: List[str],
    max_concurrent: int = 5,
    timeout: int = 30,
    max_content_length: int = 50000
) -> List[PageContent]:
    """
    Fetch multiple URLs with rate limiting and concurrency control.

    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests
        timeout: Request timeout per URL in seconds
        max_content_length: Maximum content length per page (chars)

    Returns:
        List of PageContent results (same order as input URLs)
    """
    if not urls:
        return []

    logger.info(f"Fetching {len(urls)} pages via Jina Reader (max_concurrent={max_concurrent})")

    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def fetch_with_semaphore(url: str, index: int) -> tuple:
        async with semaphore:
            # Rate limiting delay
            if index > 0:
                await asyncio.sleep(REQUEST_DELAY)

            result = await fetch_page_content(url, timeout, max_content_length)
            return index, result

    # Create tasks for all URLs
    tasks = [
        fetch_with_semaphore(url, i)
        for i, url in enumerate(urls)
    ]

    # Execute with progress logging
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # Sort by original index and extract results
    sorted_results = sorted(
        [(idx, res) for idx, res in completed if not isinstance(res, Exception)],
        key=lambda x: x[0]
    )

    results = [res for _, res in sorted_results]

    # Log summary
    successful = sum(1 for r in results if r.success)
    total_chars = sum(r.content_length for r in results if r.success)
    logger.info(f"Jina Reader: {successful}/{len(urls)} pages fetched, {total_chars:,} chars total")

    return results


def enrich_search_results(
    search_results: List[Dict],
    page_contents: List[PageContent]
) -> List[Dict]:
    """
    Enrich search results with full page content.

    Matches PageContent to search results by URL and adds
    'full_content' field to results that were successfully fetched.

    Args:
        search_results: Original search results with 'url' field
        page_contents: Fetched page contents

    Returns:
        Search results with 'full_content' added where available
    """
    # Create URL -> content mapping
    content_map = {
        pc.url: pc for pc in page_contents if pc.success
    }

    enriched = []
    for result in search_results:
        result_copy = result.copy()
        url = result.get('url')

        if url and url in content_map:
            pc = content_map[url]
            result_copy['full_content'] = pc.content
            result_copy['full_content_length'] = pc.content_length
            result_copy['content_fetch_time_ms'] = pc.fetch_time_ms

        enriched.append(result_copy)

    return enriched
