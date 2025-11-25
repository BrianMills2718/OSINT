#!/usr/bin/env python3
"""
USAspending.gov database integration.

Provides access to U.S. federal spending data including awarded contracts,
grants, loans, and other financial assistance from USAspending.gov.
"""

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
import asyncio
import aiohttp
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config

logger = logging.getLogger(__name__)


class USASpendingIntegration(DatabaseIntegration):
    """
    Integration for USAspending.gov - Official U.S. federal spending data.

    USAspending.gov is the official open data source of federal spending information
    including contract awards, grants, loans, and other financial assistance.

    API Features:
    - No API key required (public access)
    - Complex filter structure for advanced search
    - Historical spending data (post-award)
    - Recipient information, budget data, geographic analysis
    - Supports pagination for large result sets

    Data Coverage:
    - Contract awards (A, B, C, D types)
    - Grants and cooperative agreements
    - Direct payments
    - Loans
    - Agency budgets and federal accounts

    NOT suitable for:
    - Future contracting opportunities (use SAM.gov)
    - Pre-award solicitations

    Rate Limits:
    - None documented - public API
    """

    BASE_URL = "https://api.usaspending.gov"

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="USAspending",
            id="usaspending",
            category=DatabaseCategory.CONTRACTS,
            description="Historical federal spending data: awarded contracts, grants, loans, budget information",

            requires_api_key=False,
            api_key_env_var=None,

            cost_per_query_estimate=0.001,
            typical_response_time=1.5,
            rate_limit_daily=None,
            default_result_limit=100,

            query_strategies=[
                'recipient_name_search',
                'agency_spending_analysis',
                'award_amount_filter',
                'time_period_comparison',
                'award_type_filter',
                'keyword_description_search',
                'geographic_spending',
                'disaster_emergency_tracking'
            ],
            characteristics={
                'historical_spending': True,
                'post_award_data': True,
                'structured_data': True,
                'rich_metadata': True,
                'budget_data': True,
                'recipient_tracking': True,
                'geographic_data': True,
                'time_series': True,
                'award_amounts': True,
                'date_format': 'YYYY-MM-DD',
                'requires_verification': False
            },
            typical_result_count=100,
            max_queries_recommended=7
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for USAspending data.

        USAspending is relevant for questions about:
        - Historical spending and awarded contracts
        - Budget analysis and trends
        - Recipient analysis (which companies/orgs received funding)
        - Geographic spending distribution
        - Award amounts and timelines

        NOT relevant for:
        - Future opportunities or solicitations (use SAM.gov)
        - Job postings (use USAJobs)

        Args:
            research_question: The user's research question

        Returns:
            True if USAspending can provide relevant data
        """

        prompt = render_prompt(
            "integrations/usaspending_relevance.j2",
            research_question=research_question
            # current_date automatically injected by prompt_loader
        )

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default True on parsing failure

        except Exception as e:
            # Fallback on LLM failure - acceptable to default to True
            # This lets query generation and filtering handle the decision
            logger.warning(f"USAspending relevance check failed: {e}, defaulting to True", exc_info=True)
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate USAspending API query using LLM.

        Uses LLM to understand the research question and generate appropriate
        filter object and field selection for the USAspending API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with 'filters' and 'fields', or None if not relevant

        Example Return:
            {
                "filters": {
                    "keywords": ["cybersecurity"],
                    "award_type_codes": ["A", "B", "C"],
                    "time_period": [{"start_date": "2022-10-01", "end_date": "2023-09-30"}],
                    "agencies": [{"type": "awarding", "tier": "toptier", "name": "Department of Defense"}]
                },
                "fields": ["Award ID", "Recipient Name", "Award Amount", "Start Date", "Description"],
                "limit": 100
            }
        """

        prompt = render_prompt(
            "integrations/usaspending_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether USAspending is relevant for this question"
                },
                "filters": {
                    "type": "object",
                    "description": "USAspending API filter object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Search keywords"
                        },
                        "award_type_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": "Award type codes (REQUIRED: at least 1 code). Use ['A','B','C','D'] for contracts if not specified."
                        },
                        "time_period": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "start_date": {"type": "string"},
                                    "end_date": {"type": "string"}
                                }
                            },
                            "description": "Time period filters (YYYY-MM-DD)"
                        },
                        "agencies": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "tier": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            },
                            "description": "Agency filters"
                        },
                        "recipient_search_text": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recipient company/org names"
                        },
                        "award_amounts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "lower_bound": {"type": "number"},
                                    "upper_bound": {"type": "number"}
                                }
                            },
                            "description": "Award amount ranges"
                        }
                    }
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to return in response"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (1-500)",
                    "minimum": 1,
                    "maximum": 500
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of query strategy"
                }
            },
            "required": ["relevant", "filters", "fields", "limit", "reasoning"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "usaspending_query",
                        "schema": schema,
                        "strict": True
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)

            # Note: LLM cost tracking handled by llm_utils.acompletion()

            if not result.get("relevant", False):
                print(f"[INFO] USAspending not relevant: {result.get('reasoning', 'No reason provided')}")
                return None

            # Return query parameters
            return {
                "filters": result["filters"],
                "fields": result["fields"],
                "limit": result.get("limit", 100),
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            # Catch-all for query generation failures at integration boundary
            # This is acceptable - return None instead of crashing
            logger.error(f"USAspending query generation failed: {e}", exc_info=True)
            return None

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        """
        Execute search against USAspending API.

        Args:
            query_params: Query parameters from generate_query()
            api_key: Not used (USAspending is public)
            limit: Maximum results (overrides query_params['limit'] if provided)

        Returns:
            QueryResult with normalized spending data
        """

        # Build request body (filter out empty arrays - API rejects them)
        # Also: keywords filter requires minimum 3 items per API spec
        filters = query_params.get("filters", {})
        cleaned_filters = {}
        for k, v in filters.items():
            if v is None:
                continue
            if isinstance(v, list) and len(v) == 0:
                continue
            # API requires minimum 3 keywords - drop filter if fewer
            if k == "keywords" and isinstance(v, list) and len(v) < 3:
                logger.debug(f"Dropping keywords filter (only {len(v)} items, API requires 3+)")
                continue
            cleaned_filters[k] = v

        request_body = {
            "filters": cleaned_filters,
            "fields": query_params.get("fields", [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Start Date",
                "End Date",
                "Awarding Agency",
                "Description"
            ]),
            "limit": limit or query_params.get("limit", 100),
            "page": 1,
            "sort": "Award Amount",
            "order": "desc"
        }

        endpoint = f"{self.BASE_URL}/api/v2/search/spending_by_award/"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=request_body,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        return QueryResult(
                            success=False,
                            source="USAspending",
                            total=0,
                            results=[],
                            query_params=query_params,
                            error=f"HTTP {response.status}: {error_text}"
                        )

                    data = await response.json()

                    # Normalize results
                    results = []
                    for award in data.get("results", []):
                        # Build title with fallback chain (handle None values)
                        title = award.get("Description") or award.get("Award ID") or "USAspending Award"

                        # Build normalized result
                        normalized = {
                            "title": title,
                            "url": self._build_award_url(award.get("Award ID", "")),
                            "snippet": self._build_snippet(award),
                            "metadata": award,  # Full award data
                            "source": "USAspending"
                        }
                        results.append(normalized)

                    # Track API request
                    log_request(
                        api_name="USAspending",
                        endpoint=endpoint,
                        status_code=response.status,
                        response_time_ms=0,  # aiohttp doesn't provide this easily
                        error_message=None,
                        request_params={"filters": query_params.get("filters", {}), "limit": limit}
                    )

                    return QueryResult(
                        success=True,
                        source="USAspending",
                        total=len(results),
                        results=results,
                        query_params=query_params,
                        response_time_ms=0,
                        metadata={
                            "page_metadata": data.get("page_metadata", {}),
                            "request_filters": query_params.get("filters", {}),
                            "spending_level": data.get("spending_level", "awards")
                        }
                    )

        except asyncio.TimeoutError:
            return QueryResult(
                success=False,
                source="USAspending",
                total=0,
                results=[],
                query_params=query_params,
                error="Request timeout after 30 seconds"
            )
        except Exception as e:
            # Catch-all for unexpected errors at integration boundary
            # This is acceptable - return error instead of crashing
            logger.error(f"USAspending search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="USAspending",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Search failed: {str(e)}"
            )

    def _build_award_url(self, award_id: str) -> str:
        """Build URL to award detail page on USAspending.gov"""
        if not award_id:
            return "https://www.usaspending.gov/"

        # URL encode award ID
        from urllib.parse import quote
        encoded_id = quote(award_id, safe='')
        return f"https://www.usaspending.gov/award/{encoded_id}"

    def _build_snippet(self, award: Dict) -> str:
        """Build informative snippet from award data"""
        parts = []

        # Recipient
        recipient = award.get("Recipient Name", "Unknown Recipient")
        parts.append(f"Recipient: {recipient}")

        # Amount
        amount = award.get("Award Amount")
        if amount:
            parts.append(f"Amount: ${amount:,.2f}")

        # Dates
        start_date = award.get("Start Date")
        end_date = award.get("End Date")
        if start_date and end_date:
            parts.append(f"Period: {start_date} to {end_date}")
        elif start_date:
            parts.append(f"Start: {start_date}")

        # Agency
        agency = award.get("Awarding Agency")
        if agency:
            parts.append(f"Agency: {agency}")

        return " | ".join(parts)
