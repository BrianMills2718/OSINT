#!/usr/bin/env python3
"""
FBI Vault database integration.

Provides access to FBI's FOIA Vault - document releases and investigation files.
Note: FBI Vault doesn't have a public search API, so this uses web scraping
of their search interface.
"""

import json
import httpx
from typing import Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

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

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute FBI Vault search by scraping their search interface.

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
            search_url = f"https://vault.fbi.gov/search?SearchableText={query}"

            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    search_url,
                    timeout=30.0,
                    headers={
                        "User-Agent": "SigInt Research Platform/1.0 (Educational/Research)"
                    }
                )

                response.raise_for_status()

                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find search results
                # FBI Vault uses a specific structure - adjust selectors as needed
                results = []

                # Look for search result items
                result_items = soup.select('.searchResult') or soup.select('.documentFirstHeading')

                for item in result_items[:limit]:
                    try:
                        # Extract title
                        title_elem = item.select_one('a') or item.select_one('.documentFirstHeading a')
                        title = title_elem.get_text(strip=True) if title_elem else "Untitled Document"
                        url = title_elem.get('href', '') if title_elem else ""

                        # Make URL absolute if relative
                        if url and not url.startswith('http'):
                            url = f"https://vault.fbi.gov{url}"

                        # Extract description/snippet
                        desc_elem = item.select_one('.description') or item.select_one('p')
                        snippet = desc_elem.get_text(strip=True) if desc_elem else ""

                        # Extract date if available
                        date_elem = item.select_one('.documentPublished') or item.select_one('time')
                        date = date_elem.get_text(strip=True) if date_elem else None

                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet[:500],
                            "date": date,
                            "source": "FBI Vault",
                            "metadata": {
                                "document_type": "FOIA Release",
                                "query": query
                            }
                        })

                    except Exception as e:
                        # Skip malformed results
                        print(f"    Warning: Skipping malformed result: {e}")
                        continue

                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Log the request
                log_request(
                    api_name="FBI Vault",
                    endpoint=endpoint,
                    status_code=response.status_code,
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
                        "scraping_method": "BeautifulSoup",
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
                error=str(e),
                response_time_ms=response_time_ms
            )
