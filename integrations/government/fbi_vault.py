#!/usr/bin/env python3
"""
FBI Vault database integration.

Provides access to FBI's FOIA Vault - document releases and investigation files.
Note: FBI Vault doesn't have a public search API, so this uses web scraping
with SeleniumBase UC Mode to bypass Cloudflare protection.
"""

import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import quote_plus
from functools import partial

# Lazy imports to avoid dependency issues at module load time
# from seleniumbase import SB  # Imported only when needed
# from bs4 import BeautifulSoup  # Imported only when needed

from llm_utils import acompletion

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config


class FBIVaultIntegration(DatabaseIntegration):
    """
    Integration for FBI Vault - FOIA document releases.

    FBI Vault is the FBI's FOIA Library containing documents released
    under the Freedom of Information Act.

    Note: FBI Vault doesn't have a public API, so this implementation
    uses their search interface (https://vault.fbi.gov/search).

    Search capabilities:
    - Keyword search across documents
    - Results include investigation files, memos, reports
    - No authentication required
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="FBI Vault",
            id="fbi_vault",
            category=DatabaseCategory.GOV_FBI,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only, scraping is free
            typical_response_time=3.0,
            rate_limit_daily=None,  # Unknown, be respectful
            description="FBI FOIA document releases and investigation files"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - FBI Vault is relevant for government investigations,
        FOIA requests, law enforcement topics, and domestic security issues.

        Args:
            research_question: The user's research question

        Returns:
            True if question might relate to FBI investigations/documents
        """
        fbi_keywords = [
            "fbi", "investigation", "foia", "classified", "declassified",
            "law enforcement", "domestic", "terrorism", "extremism",
            "intelligence", "security clearance", "whistleblow",
            "surveillance", "document", "report", "memo"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in fbi_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate FBI Vault search parameters using LLM.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "domestic terrorism threat assessment",
                "filters": {}
            }
        """

        prompt = f"""You are a search query generator for FBI Vault, the FBI's FOIA document library.

Research Question: {research_question}

Generate search parameters for FBI Vault:
- query: Search terms for documents (string)
- reasoning: Brief explanation of the search strategy

Guidelines:
- Be SPECIFIC with multi-word phrases (e.g., "domestic terrorism threat assessment")
- Focus on investigation names, document types, or specific topics
- Use FBI terminology when applicable
- Keep queries focused on topics likely to have FBI documentation

If this question is not relevant to FBI investigations or documents, return relevant: false.

Return JSON with these exact fields.

Example 1:
Question: "What documents exist about domestic terrorism threats?"
Response:
{{
  "relevant": true,
  "query": "domestic terrorism threat assessment",
  "reasoning": "Searching for FBI threat assessments on domestic terrorism"
}}

Example 2:
Question: "FBI investigation into January 6"
Response:
{{
  "relevant": true,
  "query": "January 6 Capitol investigation",
  "reasoning": "Looking for FBI documents related to January 6th investigation"
}}

Example 3:
Question: "How do I apply for a job?"
Response:
{{
  "relevant": false,
  "query": "",
  "reasoning": "Question is about employment, not FBI documents"
}}
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether this database is relevant to the question"
                },
                "query": {
                    "type": "string",
                    "description": "Search query for FBI Vault documents"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "query", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "fbi_vault_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        if not result["relevant"]:
            return None

        return {
            "query": result["query"]
        }

    def _scrape_fbi_vault_sync(self, search_url: str, query: str, limit: int) -> tuple:
        """
        Synchronous function to scrape FBI Vault with SeleniumBase.
        This runs in a thread pool to avoid blocking the async event loop.

        Returns:
            tuple: (results_list, page_source) or raises Exception
        """
        # Import here to avoid dependency issues at module load time
        from seleniumbase import SB
        from bs4 import BeautifulSoup
        import os
        from pathlib import Path

        # Find Chrome binary (Puppeteer/Playwright version in WSL/Linux)
        chrome_binary = None
        puppeteer_chrome = Path.home() / ".cache/puppeteer/chrome"
        if puppeteer_chrome.exists():
            # Find the latest Chrome version
            chrome_dirs = sorted(puppeteer_chrome.glob("*/chrome-linux64/chrome"), reverse=True)
            if chrome_dirs:
                chrome_binary = str(chrome_dirs[0])

        # Use SeleniumBase UC Mode to bypass Cloudflare
        # NOTE: This uses xvfb (virtual display) on Linux to avoid headless detection
        sb_kwargs = {
            "uc": True,
            "xvfb": True,
            "test": True,
            "headless2": False
        }
        if chrome_binary:
            sb_kwargs["binary_location"] = chrome_binary

        with SB(**sb_kwargs) as sb:
            # Navigate using uc_open_with_reconnect for Cloudflare bypass
            sb.driver.uc_open_with_reconnect(search_url, reconnect_time=4)

            # Wait a moment for page to fully load
            sb.sleep(2)

            # Get page source
            page_source = sb.get_page_source()

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find search results - FBI Vault uses <dt> elements with contenttype classes
        results = []
        result_items = soup.select('dt.contenttype-folder, dt.contenttype-file')

        for item in result_items[:limit]:
            try:
                # Extract title and URL
                title_elem = item.select_one('a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')

                # Make URL absolute if relative
                if url and not url.startswith('http'):
                    url = f"https://vault.fbi.gov{url}"

                # Extract description/snippet from next <dd> sibling
                snippet = ""
                dd_elem = item.find_next_sibling('dd')
                if dd_elem:
                    desc_text = dd_elem.get_text(strip=True)
                    snippet = desc_text[:500] if desc_text else ""

                # Extract date if available
                date_elem = item.select_one('.documentPublished') or item.select_one('time')
                date = date_elem.get_text(strip=True) if date_elem else None

                # Determine document type from class
                doc_type = "Folder" if "contenttype-folder" in item.get('class', []) else "File"

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "date": date,
                    "source": "FBI Vault",
                    "metadata": {
                        "document_type": doc_type,
                        "query": query
                    }
                })

            except Exception as e:
                # Skip malformed results
                print(f"    Warning: Skipping malformed result: {e}")
                continue

        return (results, page_source)

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute FBI Vault search using SeleniumBase UC Mode to bypass Cloudflare.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not used (FBI Vault doesn't require auth)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://vault.fbi.gov/search"

        try:
            query = query_params.get("query", "")

            if not query:
                return QueryResult(
                    success=False,
                    source="FBI Vault",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="No query provided for search"
                )

            # FBI Vault search URL
            search_url = f"https://vault.fbi.gov/search?SearchableText={quote_plus(query)}"

            # Run synchronous SeleniumBase scraping in thread pool
            loop = asyncio.get_event_loop()
            results, page_source = await loop.run_in_executor(
                None,  # Uses default ThreadPoolExecutor
                partial(self._scrape_fbi_vault_sync, search_url, query, limit)
            )

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log the request
            log_request(
                api_name="FBI Vault",
                endpoint=endpoint,
                status_code=200,  # SeleniumBase succeeded
                response_time_ms=response_time_ms,
                error_message=None,
                request_params={"query": query, "limit": limit}
            )

            return QueryResult(
                success=True,
                source="FBI Vault",
                total=len(results),
                results=results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "scraping_method": "SeleniumBase UC Mode (Cloudflare bypass)",
                    "search_url": search_url
                }
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="FBI Vault",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="FBI Vault",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Cloudflare bypass failed: {str(e)}",
                response_time_ms=response_time_ms
            )
