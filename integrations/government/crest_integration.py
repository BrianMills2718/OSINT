#!/usr/bin/env python3
"""
CIA CREST (CIA Records Search Tool) database integration.

Provides access to declassified CIA documents from the CIA Reading Room.
"""

import asyncio
import json
from typing import Dict, Optional, List
from urllib.parse import quote
from llm_utils import acompletion
from core.prompt_loader import render_prompt
from core.stealth_browser import StealthBrowser

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request


class CRESTIntegration(DatabaseIntegration):
    """
    Integration for CIA CREST - CIA Records Search Tool.

    CREST is the CIA's online Freedom of Information Act (FOIA) Reading Room
    containing over 13 million pages of declassified documents dating from
    the 1940s through the 1990s.

    Features:
    - No API key required (public access)
    - Keyword search
    - Historical intelligence documents
    - Declassified operations and programs

    Limitations:
    - Web scraping only (no official API)
    - Slower than API-based sources
    - Respect crawl delays (2s between requests)
    - Documents are historical (mostly pre-2000)
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="CIA CREST",
            id="crest",
            category=DatabaseCategory.GOV_GENERAL,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=10.0,     # seconds (scraping is slow)
            description="CIA's declassified document reading room (FOIA records, 1940s-1990s)",
            requires_stealth=True,          # Akamai Bot Manager protection
            rate_limit_daily=None           # Self-imposed: be respectful
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check for CIA/intelligence-related questions.

        Always return True - let generate_query() LLM make the final call.

        Args:
            research_question: The user's research question

        Returns:
            Always True - relevance determined by generate_query()
        """
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate CREST search parameters using LLM.

        Args:
            research_question: The user's research question

        Returns:
            Dict with 'keyword' and 'max_pages', or None if not relevant
        """
        prompt = render_prompt(
            "integrations/crest_query.j2",
            research_question=research_question
        )

        schema = {
            "name": "crest_query",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {
                        "type": "boolean",
                        "description": "Is this question relevant for CIA declassified documents?"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why is/isn't this relevant for CREST?"
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword (single term or short phrase, 2-4 words max)"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Number of result pages to fetch (1-3, each page has ~20 docs)"
                    }
                },
                "required": ["relevant", "reasoning", "keyword", "max_pages"],
                "additionalProperties": False
            }
        }

        response = await acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": schema}
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        return {
            "keyword": result.get("keyword", ""),
            "max_pages": min(result.get("max_pages", 1), 3)  # Cap at 3 pages
        }

    async def execute_search(
        self,
        params: Dict,
        api_key: Optional[str] = None,
        limit: int = 20
    ) -> QueryResult:
        """
        Execute CREST search using Playwright web scraping.

        Args:
            params: Query parameters from generate_query()
            api_key: Not used (CREST is public)
            limit: Maximum results to return

        Returns:
            QueryResult with documents found
        """
        keyword = params.get("keyword", "")
        max_pages = params.get("max_pages", 1)

        if not keyword:
            return QueryResult(
                success=False,
                source="CIA CREST",
                total=0,
                results=[],
                query_params=params,
                error="No keyword provided"
            )

        # Import playwright only when needed (lazy import)
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeout
        except ImportError:
            return QueryResult(
                success=False,
                source="CIA CREST",
                total=0,
                results=[],
                query_params=params,
                error="Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        documents = []

        try:
            # Use stealth browser to bypass Akamai Bot Manager
            browser = await StealthBrowser.create_playwright_browser(headless=True)
            page = await StealthBrowser.create_stealth_page(browser)

            # Fetch multiple pages if requested
            for page_num in range(max_pages):
                if len(documents) >= limit:
                    break

                # Construct search URL
                encoded_keyword = quote(keyword)
                search_url = f"https://www.cia.gov/readingroom/advanced-search-view?keyword={encoded_keyword}&page={page_num}"

                await page.goto(search_url, timeout=30000)
                await asyncio.sleep(2)  # Be respectful

                # Wait for results table
                try:
                    await page.wait_for_selector('.views-table', timeout=10000)
                except PlaywrightTimeout:
                    # No results found
                    break

                # Extract document links from table
                doc_links = await page.evaluate("""
                    () => {
                        const results = [];
                        const table = document.querySelector('table.views-table');
                        if (!table) return results;

                        const rows = table.querySelectorAll('tr');
                        for (let i = 1; i < rows.length; i++) {  // Skip header row
                            const titleCell = rows[i].querySelector('.views-field-label');
                            if (titleCell) {
                                const link = titleCell.querySelector('a');
                                if (link && link.href.includes('/readingroom/document/')) {
                                    results.push({
                                        title: link.textContent.trim(),
                                        url: link.href
                                    });
                                }
                            }
                        }
                        return results;
                    }
                """)

                # Visit each document to get snippet (limited to limit)
                for doc_link in doc_links:
                    if len(documents) >= limit:
                        break

                    try:
                        await page.goto(doc_link['url'], timeout=30000)
                        await asyncio.sleep(2)  # Be respectful

                        # Extract document content
                        content = await page.evaluate("""
                            () => {
                                const data = {};

                                // Extract title
                                const title = document.querySelector('h1.documentFirstHeading');
                                data.title = title ? title.textContent.trim() : '';

                                // Extract metadata
                                const metadata = {};
                                const fields = document.querySelectorAll('.field-label-inline');
                                fields.forEach(field => {
                                    const label = field.querySelector('.field-label');
                                    const item = field.querySelector('.field-item');
                                    if (label && item) {
                                        const key = label.textContent.trim().replace(':', '');
                                        metadata[key] = item.textContent.trim();
                                    }
                                });
                                data.metadata = metadata;

                                // Extract body text (first 500 chars as snippet)
                                const body = document.querySelector('.field-name-body .field-item');
                                data.snippet = body ? body.textContent.trim().substring(0, 500) + '...' : '';

                                return data;
                            }
                        """)

                        # Create document dictionary
                        doc = {
                            "title": content.get('title', doc_link['title']),
                            "url": doc_link['url'],
                            "snippet": content.get('snippet', ''),
                            "metadata": content.get('metadata', {})
                        }
                        documents.append(doc)

                    except Exception as e:
                        # Skip failed documents
                        print(f"Failed to fetch document {doc_link['url']}: {e}")
                        continue

                await browser.close()

                # Log the request
                log_request(
                    source="CIA CREST",
                    query=keyword,
                    num_results=len(documents),
                    metadata={"pages_fetched": max_pages}
                )

                return QueryResult(
                    success=True,
                    source="CIA CREST",
                    total=len(documents),
                    results=documents,
                    query_params=params
                )

        except Exception as e:
            return QueryResult(
                success=False,
                source="CIA CREST",
                total=0,
                results=[],
                query_params=params,
                error=f"CREST scraping failed: {str(e)}"
            )
