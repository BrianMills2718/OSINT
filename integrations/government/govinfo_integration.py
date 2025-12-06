#!/usr/bin/env python3
"""
GovInfo.gov database integration.

Provides access to the U.S. Government Publishing Office's digital repository
including GAO reports, Inspector General reports, Congressional reports,
hearings, court opinions, and federal regulations.
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio
import requests
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.result_builder import SearchResultBuilder
from core.api_request_tracker import log_request
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class GovInfoIntegration(DatabaseIntegration):
    """
    Integration for GovInfo.gov - U.S. Government Publishing Office.

    GovInfo provides official publications from all three branches of the
    Federal Government, including oversight reports, audits, investigations,
    and regulatory documents.

    API Features:
    - Requires API key from api.data.gov
    - Search across 150+ collections
    - Access GAO reports, IG reports, Congressional documents
    - Federal Register, CFR, court opinions
    - Full-text search with metadata filtering

    Key Collections:
    - **GAOREPORTS**: Government Accountability Office audits
    - **CRPT**: Congressional committee reports
    - **CHRG**: Congressional hearings transcripts
    - **USCOURTS**: Federal court opinions
    - **CFR**: Code of Federal Regulations
    - **PLAW**: Public and Private Laws
    - **CREC**: Congressional Record (daily proceedings)
    - **FR**: Federal Register (we have separate integration)

    Rate Limits:
    - 5,000 requests per hour (api.data.gov standard)
    - 1,000 requests per 5 minutes

    API Documentation:
    - https://api.govinfo.gov/docs/
    - https://github.com/usgpo/api
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="GovInfo",
            id="govinfo",
            category=DatabaseCategory.GOV_GENERAL,
            description="Government publications: GAO reports (historical through 2008), Congressional hearings, court opinions, federal regulations. Note: Recent GAO reports may require gao.gov directly.",

            requires_api_key=True,
            api_key_env_var="DATA_GOV_API_KEY",

            cost_per_query_estimate=0.001,
            typical_response_time=2.0,
            rate_limit_daily=120000,
            default_result_limit=30,

            # Rate Limit Recovery - GovInfo uses api.data.gov (default 1,000/hour, some APIs get 5,000)
            # Source: https://api.data.gov/docs/developer-manual/
            rate_limit_recovery_seconds=60,  # Wait 1 min, quota partially refills
            retry_on_rate_limit_within_session=True,  # Worth retrying - hourly limit rolls

            query_strategies=[
                'collection_specific',
                'keyword_search',
                'agency_oversight',
                'congressional_activity',
                'court_opinions',
                'regulatory_documents',
                'date_range_filter',
                'topic_investigation'
            ],
            characteristics={
                'official_publications': True,
                'oversight_reports': True,
                'audit_reports': True,
                'congressional_documents': True,
                'court_opinions': True,
                'federal_regulations': True,
                'public_laws': True,
                'full_text_search': True,
                'structured_data': True,
                'rich_metadata': True,
                '150_plus_collections': True,
                'requires_verification': False,
                'date_filtering': True
            },
            typical_result_count=30,
            max_queries_recommended=6
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - always return True, let generate_query() decide.

        GovInfo covers such a broad range of government documents that
        keyword filtering would cause false negatives. Let the LLM in
        generate_query() make the intelligent decision.

        Args:
            research_question: The user's research question

        Returns:
            Always True - relevance determined by generate_query()
        """
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate GovInfo search parameters using LLM.

        Uses LLM to understand the research question and generate appropriate
        search query with collection filters for the GovInfo API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query": "defense contracting fraud",
                "collections": ["GAOREPORTS", "CRPT"],
                "date_range_years": 5,
                "sort_by": "publishdate"
            }
        """

        prompt = render_prompt(
            "integrations/govinfo_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether GovInfo is relevant for this research question"
                },
                "query": {
                    "type": "string",
                    "description": "Search keywords for GovInfo full-text search"
                },
                "collections": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "GAOREPORTS",   # GAO audits and reports
                            "CRPT",         # Congressional committee reports
                            "CHRG",         # Congressional hearings
                            "USCOURTS",     # Federal court opinions
                            "CFR",          # Code of Federal Regulations
                            "PLAW",         # Public Laws
                            "CREC",         # Congressional Record
                            "CDIR",         # Congressional Directory
                            "BILLS",        # Congressional bills (use Congress.gov instead)
                            "BILLSTATUS"    # Bill status (use Congress.gov instead)
                        ]
                    },
                    "description": "Which GovInfo collections to search (1-3 most relevant)"
                },
                "date_range_years": {
                    "type": "integer",
                    "description": "How many years back to search (1-10, optional)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["publishdate", "lastModified", "score"],
                    "description": "How to sort results"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of query strategy"
                }
            },
            "required": ["relevant", "query", "collections", "sort_by", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "govinfo_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Return None if not relevant
        if not result.get("relevant", False):
            return None

        # Return query parameters (excluding metadata)
        return {
            "query": result["query"],
            "collections": result["collections"],
            "date_range_years": result["date_range_years"],
            "sort_by": result["sort_by"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute GovInfo search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: api.data.gov API key (required)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()

        # Check for API key
        if not api_key:
            return QueryResult(
                success=False,
                source="GovInfo",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for GovInfo (api.data.gov key)",
                http_code=None  # Non-HTTP error
            )

        try:
            # Extract parameters
            search_terms = query_params.get("query", "")
            collections = query_params.get("collections", [])
            date_range_years = query_params.get("date_range_years")

            # Calculate start date
            from datetime import timedelta
            if date_range_years:
                cutoff_date = datetime.now() - timedelta(days=365 * date_range_years)
            else:
                cutoff_date = datetime.now() - timedelta(days=365 * 5)  # Default 5 years

            # Use collections API only if NO search terms and single collection
            # Otherwise use search API for better keyword matching
            if len(collections) == 1 and not search_terms:
                # Collections API: https://api.govinfo.gov/collections/{collectionCode}/{startDate}
                collection_code = collections[0]
                start_date_iso = cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                endpoint = f"https://api.govinfo.gov/collections/{collection_code}/{start_date_iso}"

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(
                        endpoint,
                        params={
                            "api_key": api_key,
                            "offset": 0,
                            "pageSize": min(limit, 100)
                        },
                        timeout=30
                    )
                )
                response.raise_for_status()
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                data = response.json()
                raw_results = data.get("packages", [])
                total = data.get("count", len(raw_results))

                # Filter by search terms if provided
                if search_terms:
                    search_lower = search_terms.lower()
                    filtered_results = [
                        doc for doc in raw_results
                        if search_lower in doc.get("title", "").lower()
                    ]
                    raw_results = filtered_results

            else:
                # Use Search API for keyword queries
                # Ref: https://www.govinfo.gov/features/search-service-overview
                endpoint = "https://api.govinfo.gov/search"

                # Build query using correct syntax: collection:CODE (not collection:(CODE))
                query_parts = []
                if search_terms:
                    query_parts.append(search_terms)

                # Add collection filter(s)
                if collections:
                    if len(collections) == 1:
                        query_parts.append(f"collection:{collections[0]}")
                    else:
                        # Multiple collections: collection:(CODE1 OR CODE2)
                        collection_filter = " OR ".join(collections)
                        query_parts.append(f"collection:({collection_filter})")

                # Add date range using lastModified (publishdate range doesn't work reliably)
                # Note: GAOREPORTS collection only has historical data through 2008
                # For recent data, consider FR, BILLS, CFR collections instead
                if date_range_years:
                    cutoff_iso = cutoff_date.strftime("%Y-%m-%dT00:00:00Z")
                    query_parts.append(f"lastModified:range({cutoff_iso},)")

                full_query = " ".join(query_parts)

                payload = {
                    "query": full_query,
                    "pageSize": min(limit, 100),
                    "offsetMark": "*",
                    "sorts": [
                        {
                            "field": query_params.get("sort_by", "publishdate"),
                            "sortOrder": "DESC"
                        }
                    ]
                }

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(
                        endpoint,
                        params={"api_key": api_key},
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                )
                response.raise_for_status()
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                data = response.json()
                raw_results = data.get("results", [])
                total = data.get("count", len(raw_results))

            # Transform to standardized format
            transformed_results = []
            for doc in raw_results[:limit]:
                # Extract fields from GovInfo response
                package_id = doc.get("packageId", "")

                # Build GovInfo URL
                # Collections API uses packageLink, search API uses resultLink
                url = doc.get("packageLink") or doc.get("resultLink", "")
                if not url and package_id:
                    url = f"https://www.govinfo.gov/app/details/{package_id}"

                # Get snippet/summary
                snippet = doc.get("summary", "")
                if not snippet:
                    snippet = doc.get("abstract", "")

                # Handle date field (collections API uses dateIssued, search API uses publishDate)
                date_value = doc.get("dateIssued") or doc.get("publishDate")

                # Three-tier model: preserve full content with build_with_raw()
                transformed = (SearchResultBuilder()
                    .title(SearchResultBuilder.safe_text(doc.get("title"), default="Untitled Document"))
                    .url(url)
                    .snippet(SearchResultBuilder.safe_text(snippet, max_length=500))
                    .raw_content(snippet)  # Full content, never truncated
                    .date(SearchResultBuilder.safe_date(date_value))
                    .api_response(doc)  # Preserve complete API response
                    .metadata({
                        "package_id": package_id,
                        "collection": doc.get("collectionCode"),
                        "collection_name": doc.get("collectionName"),
                        "publish_date": date_value,
                        "last_modified": doc.get("lastModified"),
                        "doc_class": doc.get("docClass"),
                        "government_author": doc.get("governmentAuthor1") or doc.get("governmentAuthor")
                    })
                    .build_with_raw())
                transformed_results.append(transformed)

            # Log successful request
            log_request(
                api_name="GovInfo",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="GovInfo",
                total=total,
                results=transformed_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "search_terms": search_terms,
                    "collections_searched": collections
                }
            )

        except requests.HTTPError as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="GovInfo",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="GovInfo",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e)}",
                http_code=status_code,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="GovInfo",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="GovInfo",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                http_code=None,  # Non-HTTP error
                response_time_ms=response_time_ms
            )
