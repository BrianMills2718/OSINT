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

from database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from api_request_tracker import log_request


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
        Quick relevance check - does question relate to military media?

        We check for military/media-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about military content or media.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about military media, False otherwise
        """
        media_keywords = [
            "photo", "photos", "image", "images", "video", "videos", "media",
            "footage", "picture", "pictures", "visual", "news",
            "military", "defense", "dod", "army", "navy", "air force", "marine",
            "coast guard", "dvids", "combat", "training", "deployment",
            "humanitarian", "exercise", "operation"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in media_keywords)

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

        prompt = f"""You are a search query generator for DVIDS, the U.S. military's media distribution service.

Research Question: {research_question}

Generate search parameters for the DVIDS API:
- keywords: Search terms for media titles/descriptions (string, keep concise)
- media_types: Types of media to search (array from: "image", "video", "news")
- branches: Military branches (array from: "Army", "Navy", "Air Force", "Marines", "Coast Guard", "Joint")
- country: Country if specified (string, e.g., "United States", "Germany", "Japan")
- from_date: Start date if recency mentioned (YYYY-MM-DD format, or null)
- to_date: End date if specified (YYYY-MM-DD format, or null)

Guidelines:
- keywords: Use military-specific terms, avoid very long queries
- media_types: Include all types unless specifically requested (e.g., "photos only" → ["image"])
- branches: Only specify if the question mentions specific branches
- dates: Only filter by date if recency is mentioned (e.g., "recent", "2024", "last month")
- country: Only specify if the question mentions a specific country or location

If this question is not about military media or content, return relevant: false.

Return JSON with these exact fields. Use empty arrays for optional list fields and null for optional date fields.

Example 1:
Question: "Show me recent F-35 training photos from the Air Force"
Response:
{{
  "relevant": true,
  "keywords": "F-35 training",
  "media_types": ["image"],
  "branches": ["Air Force"],
  "country": null,
  "from_date": "2024-10-01",
  "to_date": null,
  "reasoning": "Recent Air Force F-35 training imagery"
}}

Example 2:
Question: "What videos are available about humanitarian operations?"
Response:
{{
  "relevant": true,
  "keywords": "humanitarian operations",
  "media_types": ["video"],
  "branches": [],
  "country": null,
  "from_date": null,
  "to_date": null,
  "reasoning": "Video content about humanitarian missions"
}}

Example 3:
Question: "What government contracts are available?"
Response:
{{
  "relevant": false,
  "keywords": "",
  "media_types": [],
  "branches": [],
  "country": null,
  "from_date": null,
  "to_date": null,
  "reasoning": "Question is about contracts, not military media"
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
            model="gpt-5-mini",
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
            response = requests.get(endpoint, params=params, timeout=20)
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
