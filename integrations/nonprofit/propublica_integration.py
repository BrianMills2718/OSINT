#!/usr/bin/env python3
"""
ProPublica Nonprofit Explorer database integration.

Provides access to IRS Form 990 data for nonprofit organizations including
revenue, expenses, executive compensation, and organizational details.
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


class ProPublicaIntegration(DatabaseIntegration):
    """
    Integration for ProPublica Nonprofit Explorer.

    Provides access to IRS Form 990 tax filings for nonprofit organizations,
    including financial data, executive compensation, and organizational details.

    API Features:
    - NO API key required
    - Free, open access
    - Search by keyword, state, category, tax code
    - Get detailed org data by EIN
    - Multiple years of Form 990 filings

    Rate Limits:
    - No official limit documented
    - PDF downloads are rate limited (not used here)
    - Recommendation: Be respectful, 1 request per second

    Data Sources:
    - IRS Exempt Organizations Business Master File
    - IRS Annual Extract of Tax-Exempt Organization Financial Data
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="ProPublica Nonprofit Explorer",
            id="propublica",
            category=DatabaseCategory.RESEARCH,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.0,      # seconds
            rate_limit_daily=None,          # No official limit
            description="IRS Form 990 data for nonprofits: revenue, expenses, executive compensation"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Use LLM to determine if this question relates to nonprofit organizations.

        We use LLM instead of keyword matching because nonprofit-related questions
        can be phrased in many ways (e.g., "dark money groups", "501(c)(4) spending",
        "foundation grants", etc.)

        Args:
            research_question: The user's research question

        Returns:
            True if question might relate to nonprofits, False otherwise
        """
        prompt = render_prompt(
            "integrations/propublica_relevance.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether this relates to nonprofit organizations"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation"
                }
            },
            "required": ["relevant", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("relevance"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "propublica_relevance",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)
        return result["relevant"]

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate ProPublica search parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the ProPublica API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "q": "dark money political spending",
                "state_id": null,
                "ntee_id": 7,  # Public, Societal Benefit
                "c_code_id": 4  # 501(c)(4)
            }
        """

        prompt = render_prompt(
            "integrations/propublica_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Search query string"
                },
                "state_id": {
                    "type": "string",
                    "description": "Two-letter state code (optional)"
                },
                "ntee_id": {
                    "type": "integer",
                    "description": "NTEE category 1-10 (optional)",
                    "minimum": 1,
                    "maximum": 10
                },
                "c_code_id": {
                    "type": "integer",
                    "description": "501(c) subsection code (optional)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["q", "state_id", "ntee_id", "c_code_id", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "propublica_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "q": result["q"],
            "state_id": result["state_id"],
            "ntee_id": result["ntee_id"],
            "c_code_id": result["c_code_id"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute ProPublica search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not required (ProPublica API is free)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://projects.propublica.org/nonprofits/api/v2/search.json"

        try:
            # Build request parameters
            params = {}

            # Add search query
            if query_params.get("q"):
                params["q"] = query_params["q"]

            # Add state filter
            if query_params.get("state_id"):
                params["state[id]"] = query_params["state_id"]

            # Add NTEE category filter
            if query_params.get("ntee_id"):
                params["ntee[id]"] = query_params["ntee_id"]

            # Add 501(c) code filter
            if query_params.get("c_code_id"):
                params["c_code[id]"] = query_params["c_code_id"]

            # Pagination - always start at page 0
            params["page"] = 0

            # Execute API call
            # Run blocking requests in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(endpoint, params=params, headers={"Accept": "application/json"}, timeout=15)
            )

            # ProPublica API quirk: Returns 404 for 0 results (with valid JSON)
            # Don't raise_for_status() - check JSON first
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            organizations = data.get("organizations", [])
            total = data.get("total_results", len(organizations))

            # Log successful request
            log_request(
                api_name="ProPublica",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=params
            )

            # Transform results to standardized format
            transformed_orgs = []
            for org in organizations[:limit]:
                # Build organization URL
                ein = org.get("ein")
                url = f"https://projects.propublica.org/nonprofits/organizations/{ein}" if ein else ""

                # Build snippet from key financial data if available
                snippet_parts = []
                if org.get("name"):
                    snippet_parts.append(org["name"])
                if org.get("city") and org.get("state"):
                    snippet_parts.append(f"({org['city']}, {org['state']})")

                # Add latest filing data if available
                if org.get("revenue_amount"):
                    revenue = org["revenue_amount"]
                    if revenue:
                        snippet_parts.append(f"Revenue: ${revenue:,}")

                snippet = " • ".join(snippet_parts) if snippet_parts else "Nonprofit organization"

                # Extract tax code description
                strein = org.get("strein", "")
                tax_code = None
                if strein:
                    # strein format like "501(c)(3)" or "4947(a)(1)"
                    tax_code = strein

                transformed = (SearchResultBuilder()
                    .title(org.get("name"), default="Unnamed Organization")
                    .url(url)
                    .snippet(snippet[:500] if snippet else "")
                    .date(None)  # ProPublica doesn't have a single publication date
                    .metadata({
                        "ein": ein,
                        "city": org.get("city"),
                        "state": org.get("state"),
                        "zipcode": org.get("zipcode"),
                        "tax_code": tax_code,
                        "ntee_code": org.get("ntee_code"),
                        "revenue_amount": org.get("revenue_amount"),
                        "asset_amount": org.get("asset_amount"),
                        "filing_date": org.get("filing_date"),
                        "subsection_code": org.get("subseccd")
                    })
                    .build())
                transformed_orgs.append(transformed)

            return QueryResult(
                success=True,
                source="ProPublica Nonprofit Explorer",
                total=total,
                results=transformed_orgs,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "num_pages": data.get("num_pages", 1),
                    "per_page": data.get("per_page", 25)
                }
            )

        except requests.HTTPError as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="ProPublica",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=f"HTTP {status_code}",
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="ProPublica Nonprofit Explorer",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e,
                http_code=status_code)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="ProPublica",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="ProPublica Nonprofit Explorer",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                http_code=None,  # Non-HTTP error
                response_time_ms=response_time_ms
            )
