#!/usr/bin/env python3
"""
DVIDS database integration.

Provides access to Defense Visual Information Distribution Service (DVIDS)
military media including photos, videos, and news.
"""

import json
from typing import Dict, Optional
from datetime import datetime
import requests
from llm_utils import acompletion

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from config_loader import config


class DVIDSIntegration(DatabaseIntegration):
    """
    Integration for DVIDS - Defense Visual Information Distribution Service.

    DVIDS is the official source for U.S. military media including combat footage,
    training imagery, humanitarian operations, and public affairs content.

    API Features:
    - Requires API key
    - Search by keywords
    - Filter by media type (image, video, news)
    - Filter by branch, country, location
    - Filter by date range

    Rate Limits:
    - Unknown (appears generous)
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="DVIDS",
            id="dvids",
            category=DatabaseCategory.MEDIA,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # Unknown
            description="U.S. military photos, videos, and news from Department of Defense"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - always return True, let generate_query() LLM decide.

        The LLM in generate_query() is smarter at determining relevance and avoids
        false negatives from overly restrictive keyword matching.

        Args:
            research_question: The user's research question

        Returns:
            Always True - relevance determined by generate_query()
        """
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate DVIDS query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the DVIDS API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "F-35 training",
                "media_types": ["image", "video"],
                "branches": ["Air Force"],
                "from_date": "2024-01-01",
                "to_date": None
            }
        """

        prompt = f"""Generate search parameters for DVIDS.

DVIDS provides: U.S. Department of Defense media distribution - photos, videos, and news from military operations and activities.

API Parameters:
- keywords (string, required):
    Search terms for media titles and descriptions.

- media_types (array, required):
    Types of media to search. Valid options: "image", "video", "news"

- branches (array, optional):
    Military branches to filter by. Valid options:
    "Army", "Navy", "Air Force", "Marines", "Coast Guard", "Joint"

- country (string or null, optional):
    Country name (e.g., "United States", "Germany", "Japan")

- from_date (string or null, optional):
    Start date for results in YYYY-MM-DD format.

- to_date (string or null, optional):
    End date for results in YYYY-MM-DD format.

Research Question: {research_question}

Decide whether DVIDS is relevant for this question.
If relevant, generate appropriate search parameters.

Return JSON:
{{
  "relevant": boolean,
  "keywords": string,
  "media_types": array,
  "branches": array,
  "country": string | null,
  "from_date": string | null,
  "to_date": string | null,
  "reasoning": string
}}
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {
                    "type": "boolean",
                    "description": "Whether this database is relevant to the question"
                },
                "keywords": {
                    "type": "string",
                    "description": "Search keywords for media titles and descriptions"
                },
                "media_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of media types, empty if not specified"
                },
                "branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of military branches, empty if not specified"
                },
                "country": {
                    "type": ["string", "null"],
                    "description": "Country name or null"
                },
                "from_date": {
                    "type": ["string", "null"],
                    "description": "Start date in YYYY-MM-DD format or null"
                },
                "to_date": {
                    "type": ["string", "null"],
                    "description": "End date in YYYY-MM-DD format or null"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["relevant", "keywords", "media_types", "branches", "country", "from_date", "to_date", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "dvids_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        if not result["relevant"]:
            return None

        return {
            "keywords": result["keywords"],
            "media_types": result["media_types"],
            "branches": result["branches"],
            "country": result["country"],
            "from_date": result["from_date"],
            "to_date": result["to_date"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute DVIDS search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: DVIDS API key (required)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://api.dvidshub.net/search"

        if not api_key:
            return QueryResult(
                success=False,
                source="DVIDS",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for DVIDS"
            )

        try:
            # Build request parameters
            params = {
                "api_key": api_key,
                "page": 1,
                "max_results": min(limit, 50)  # DVIDS max is 50
            }

            # Add keywords if specified
            if query_params.get("keywords"):
                params["q"] = query_params["keywords"]

            # Add media types (DVIDS uses type[] for multiple)
            if query_params.get("media_types") and len(query_params["media_types"]) > 0:
                params["type[]"] = query_params["media_types"]

            # Add branches (DVIDS uses branch parameter)
            if query_params.get("branches") and len(query_params["branches"]) > 0:
                # DVIDS accepts single branch, take first one if multiple
                params["branch"] = query_params["branches"][0]

            # Add country
            if query_params.get("country"):
                params["country"] = query_params["country"]

            # Add date filters (DVIDS uses ISO 8601 format with Z)
            if query_params.get("from_date"):
                params["from_publishdate"] = f"{query_params['from_date']}T00:00:00Z"

            if query_params.get("to_date"):
                params["to_publishdate"] = f"{query_params['to_date']}T23:59:59Z"

            # Execute API call
            response = requests.get(endpoint, params=params, timeout=config.get_database_config("dvids")["timeout"])
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            results = data.get("results", [])
            page_info = data.get("page_info", {})
            total = page_info.get("total_results", len(results))

            # Mask API key in params for logging
            log_params = params.copy()
            if "api_key" in log_params:
                log_params["api_key"] = f"{api_key[:8]}***{api_key[-4:]}"

            # Log successful request
            log_request(
                api_name="DVIDS",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=log_params
            )

            return QueryResult(
                success=True,
                source="DVIDS",
                total=total,
                results=results[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "page_info": page_info
                }
            )

        except requests.HTTPError as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="DVIDS",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="DVIDS",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="DVIDS",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="DVIDS",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
