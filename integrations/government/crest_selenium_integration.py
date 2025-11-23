#!/usr/bin/env python3
"""
CIA CREST database integration using Selenium/undetected-chromedriver.

Alternative implementation using undetected-chromedriver instead of Playwright
for better Akamai Bot Manager evasion.
"""

import json
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
        return DatabaseMetadata(
            name="CIA CREST (Selenium)",
            id="crest_selenium",
            category=DatabaseCategory.GOV_GENERAL,
            requires_api_key=False,
            cost_per_query_estimate=0.001,
            typical_response_time=15.0,  # Slower due to visible browser
            description="CIA's declassified document reading room (Selenium/undetected-chromedriver)",
            requires_stealth=True,
            rate_limit_daily=None
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Always return True - let LLM decide in generate_query()."""
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Generate CREST search parameters using LLM."""
        prompt = render_prompt(
            "integrations/crest_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword for CIA documents"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum pages to scrape (1-5)",
                    "minimum": 1,
                    "maximum": 5
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of query strategy"
                }
            },
            "required": ["keyword", "max_pages", "reasoning"],
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

        return {
            "keyword": result["keyword"],
            "max_pages": min(result["max_pages"], 3)  # Limit to 3 pages max
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
            # Create undetected Chrome driver (visible browser)
            driver = StealthBrowser.create_selenium_browser(headless=False)

            # Fetch multiple pages
            for page_num in range(max_pages):
                if len(documents) >= limit:
                    break

                # Construct search URL
                encoded_keyword = quote(keyword)
                search_url = f"https://www.cia.gov/readingroom/advanced-search-view?keyword={encoded_keyword}&page={page_num}"

                driver.get(search_url)
                time.sleep(3)  # Wait for page load and be respectful

                # Check if we got the results table (not redirected to homepage)
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC

                    # Wait for results table
                    table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.views-table"))
                    )
                except Exception:
                    # No results or redirected
                    break

                # Extract document links from table
                rows = driver.find_elements(By.CSS_SELECTOR, "table.views-table tr")
                doc_links = []

                for row in rows[1:]:  # Skip header row
                    try:
                        title_cell = row.find_element(By.CSS_SELECTOR, ".views-field-label")
                        link = title_cell.find_element(By.TAG_NAME, "a")
                        href = link.get_attribute("href")

                        if href and "/readingroom/document/" in href:
                            doc_links.append({
                                "title": link.text.strip(),
                                "url": href
                            })
                    except Exception:
                        continue

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
                        except:
                            title = doc_link['title']

                        try:
                            body = driver.find_element(By.CSS_SELECTOR, ".field-name-body .field-item")
                            snippet = body.text.strip()[:500] + "..."
                        except:
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
                                except:
                                    continue
                        except:
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
                        print(f"Failed to fetch document {doc_link['url']}: {e}")
                        continue

            # Close browser
            if driver:
                driver.quit()

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log successful request
            log_request(
                api_name="CREST (Selenium)",
                endpoint="https://www.cia.gov/readingroom/advanced-search-view",
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
                    "pages_scraped": page_num + 1,
                    "method": "selenium_undetected_chromedriver"
                }
            )

        except Exception as e:
            if driver:
                driver.quit()

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            log_request(
                api_name="CREST (Selenium)",
                endpoint="https://www.cia.gov/readingroom/advanced-search-view",
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
