#!/usr/bin/env python3
"""
CIA CREST database integration using Selenium/undetected-chromedriver.

Alternative implementation using undetected-chromedriver instead of Playwright
for better Akamai Bot Manager evasion.
"""

import json
import logging
from typing import Dict, Optional, List
from urllib.parse import quote
import time
from datetime import datetime
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
from config_loader import config


class CRESTSeleniumIntegration(DatabaseIntegration):
    """
    Alternative CREST integration using Selenium/undetected-chromedriver.

    Uses undetected-chromedriver which is often more effective against
    Akamai Bot Manager than Playwright stealth patches.
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="CIA CREST (Selenium)",
            id="crest_selenium",
            category=DatabaseCategory.GOV_GENERAL,
            requires_api_key=False,
            cost_per_query_estimate=0.001,
            typical_response_time=27.0,  # Slower: visible browser + form interaction
            description="CIA's declassified document reading room (Selenium/undetected-chromedriver)",
            requires_stealth=True,
            stealth_method="selenium",  # Selenium required - Playwright blocked by Akamai
            rate_limit_daily=None
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Always return True - let LLM decide in generate_query()."""
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Generate CREST search parameters using LLM."""
        prompt = render_prompt(
            "integrations/crest_query.j2",
            research_question=research_question
        )

        schema = {
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

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "crest_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        return {
            "keyword": result.get("keyword", ""),
            "max_pages": min(result.get("max_pages", 1), 3)  # Cap at 3 pages
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute CREST search using Selenium/undetected-chromedriver.

        This method runs synchronously (blocking) since Selenium is sync.
        """
        start_time = datetime.now()
        keyword = query_params.get("keyword", "")
        max_pages = query_params.get("max_pages", 1)

        if not keyword:
            return QueryResult(
                success=False,
                source="CIA CREST (Selenium)",
                total=0,
                results=[],
                query_params=query_params,
                error="No keyword provided"
            )

        documents = []
        driver = None

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Create undetected Chrome driver (visible browser)
            driver = StealthBrowser.create_selenium_browser(headless=False)

            # Step 1: Visit homepage (more human-like)
            driver.get("https://www.cia.gov/readingroom/")
            time.sleep(3)

            # Step 2: Use search form
            search_input = driver.find_element(By.NAME, "search_block_form")
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.RETURN)
            time.sleep(4)  # Wait for search results

            # Extract document links from search results
            # CREST uses .search-result items, not table.views-table
            doc_links = []

            try:
                # Find all document links in search results
                result_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/document/"]')

                for link in result_links[:limit]:  # Limit to requested number
                    href = link.get_attribute("href")
                    if href and "/readingroom/document/" in href:
                        doc_links.append({
                            "title": link.text.strip(),
                            "url": href
                        })

            except Exception as e:
                # Catch-all at integration boundary - acceptable to return error instead of crashing
                logger.error(f"CREST Selenium operation failed: {e}", exc_info=True)
                print(f"Error extracting search results: {e}")

            # Visit each document to get snippet (limited to limit)
            for doc_link in doc_links:
                if len(documents) >= limit:
                    break

                try:
                    driver.get(doc_link['url'])
                    time.sleep(2)  # Be respectful

                    # Extract document content
                    title = ""
                    snippet = ""
                    metadata = {}

                    try:
                        title_elem = driver.find_element(By.CSS_SELECTOR, "h1.documentFirstHeading")
                        title = title_elem.text.strip()
                    except Exception as e:
                        # Element not found - use fallback title
                        logger.warning(f"CREST: Title element not found, using fallback: {e}", exc_info=True)
                        title = doc_link['title']

                    try:
                        body = driver.find_element(By.CSS_SELECTOR, ".field-name-body .field-item")
                        snippet = body.text.strip()[:500] + "..."
                    except Exception as e:
                        # Body element not found - acceptable to continue without snippet
                        logger.warning(f"CREST: Body element not found: {e}", exc_info=True)
                        snippet = ""

                    # Extract metadata fields
                    try:
                        fields = driver.find_elements(By.CSS_SELECTOR, ".field-label-inline")
                        for field in fields:
                            try:
                                label = field.find_element(By.CSS_SELECTOR, ".field-label")
                                item = field.find_element(By.CSS_SELECTOR, ".field-item")
                                key = label.text.strip().replace(':', '')
                                metadata[key] = item.text.strip()
                            except Exception as e:
                                # Individual field parsing failed - skip this field
                                logger.debug(f"CREST: Failed to parse metadata field: {e}", exc_info=True)
                                continue
                    except Exception as e:
                        # Metadata extraction failed - acceptable to continue without metadata
                        logger.warning(f"CREST: Metadata extraction failed: {e}", exc_info=True)
                        pass

                    # Create document dictionary
                    doc = {
                        "title": title or doc_link['title'],
                        "url": doc_link['url'],
                        "snippet": snippet,
                        "metadata": metadata
                    }
                    documents.append(doc)

                except Exception as e:
                    # Catch-all at integration boundary - acceptable to return error instead of crashing
                    logger.error(f"CREST Selenium operation failed: {e}", exc_info=True)
                    print(f"Failed to fetch document {doc_link['url']}: {e}")
                    continue

            # Close browser
            if driver:
                driver.quit()

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log successful request
            log_request(
                api_name="CREST (Selenium)",
                endpoint=f"https://www.cia.gov/readingroom/search/site/{keyword}",
                status_code=200 if documents else 0,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="CIA CREST (Selenium)",
                total=len(documents),
                results=documents,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "method": "selenium_undetected_chromedriver",
                    "bot_detection": "bypassed_via_search_form"
                }
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"CREST Selenium operation failed: {e}", exc_info=True)
            if driver:
                driver.quit()

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            log_request(
                api_name="CREST (Selenium)",
                endpoint=f"https://www.cia.gov/readingroom/search/site/{keyword}",
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="CIA CREST (Selenium)",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Selenium scraping failed: {str(e)}",
                response_time_ms=response_time_ms
            )
