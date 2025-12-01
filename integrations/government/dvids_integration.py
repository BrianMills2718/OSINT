#!/usr/bin/env python3
"""
DVIDS database integration.

Provides access to Defense Visual Information Distribution Service (DVIDS)
military media including photos, videos, and news.
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
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="DVIDS",
            id="dvids",
            category=DatabaseCategory.MEDIA,
            requires_api_key=True,
            api_key_env_var="DVIDS_API_KEY",
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # Unknown
            description="U.S. military photos, videos, and news from Department of Defense"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for DVIDS.

        Uses LLM to determine if Defense Visual Information Distribution Service
        (military media, photos, videos, news) might have relevant content.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt
        import json

        prompt = render_prompt(
            "integrations/dvids_relevance.j2",
            research_question=research_question
        )

        try:
            response = await acompletion(
                model=config.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)

        except Exception as e:
            logger.warning(f"DVIDS relevance check failed, defaulting to True: {e}", exc_info=True)
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

        prompt = render_prompt(
            "integrations/dvids_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
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
                    "type": "string",
                    "description": "Country name (optional)"
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (optional)"
                },
                "to_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (optional)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["media_types", "branches", "country", "from_date", "to_date", "reasoning"],
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
            # Build base request parameters (shared by all queries)
            base_params = {
                "api_key": api_key,
                "page": 1,
                "max_results": min(limit, 50)  # DVIDS max is 50
            }

            # Add media types (DVIDS uses type[] for multiple)
            if query_params.get("media_types") and len(query_params["media_types"]) > 0:
                base_params["type[]"] = query_params["media_types"]

            # Add branches (DVIDS uses branch parameter)
            # ONLY filter by branch if LLM specified a single specific branch
            # If LLM lists all branches (Army, Navy, AF, Marines, etc.), that means
            # the query is generic and we should NOT filter by branch
            if query_params.get("branches") and len(query_params["branches"]) == 1:
                base_params["branch"] = query_params["branches"][0]

            # Add country
            if query_params.get("country"):
                base_params["country"] = query_params["country"]

            # Add date filters (DVIDS uses ISO 8601 format with Z)
            # Validate dates are not string "null" (LLM sometimes returns this)
            from_date = query_params.get("from_date")
            to_date = query_params.get("to_date")

            if from_date and from_date != "null" and isinstance(from_date, str):
                base_params["from_publishdate"] = f"{from_date}T00:00:00Z"

            if to_date and to_date != "null" and isinstance(to_date, str):
                base_params["to_publishdate"] = f"{to_date}T23:59:59Z"

            # Get keywords and check for OR operators
            keywords_str = query_params.get("keywords", "")

            # Try the full OR query first
            params = base_params.copy()
            params["q"] = keywords_str

            # Add Origin/Referer headers if configured (DVIDS API keys may have origin restrictions)
            headers = {}
            dvids_config = config.get_database_config("dvids")
            if dvids_config.get("origin"):
                headers["Origin"] = dvids_config["origin"]
                headers["Referer"] = dvids_config["origin"]

            # Run blocking requests.get in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(endpoint, params=params, headers=headers, timeout=dvids_config["timeout"])
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            page_info = data.get("page_info", {})
            total = page_info.get("total_results", len(results))

            # DVIDS API quirk: Some OR combinations return 0 despite individual terms working
            # If we get 0 results with an OR query, decompose and try individual terms
            if total == 0 and " OR " in keywords_str:
                print(f"DVIDS: OR query returned 0, decomposing into individual terms...")

                # Split on " OR " to get individual terms
                individual_terms = [term.strip() for term in keywords_str.split(" OR ")]

                # Collect results from each individual term
                all_results = []
                seen_ids = set()  # Deduplicate by ID

                for term in individual_terms:
                    term_params = base_params.copy()
                    term_params["q"] = term

                    # Run in thread pool
                    term_response = await loop.run_in_executor(
                        None,
                        lambda p=term_params: requests.get(endpoint, params=p, headers=headers, timeout=dvids_config["timeout"])
                    )
                    if term_response.status_code == 200:
                        term_data = term_response.json()
                        term_results = term_data.get("results", [])

                        # Deduplicate - only add results we haven't seen
                        for result in term_results:
                            result_id = result.get("id")
                            if result_id and result_id not in seen_ids:
                                all_results.append(result)
                                seen_ids.add(result_id)

                # Update results with decomposed query results
                results = all_results
                total = len(results)
                print(f"DVIDS: Decomposed query found {total} unique results across {len(individual_terms)} terms")

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

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

            # Transform results to standardized format using defensive builder
            documents = []
            for item in results[:limit]:
                doc = (SearchResultBuilder()
                    .title(item.get("title"), default="Untitled")
                    .url(item.get("url"))
                    .snippet(item.get("description") or item.get("caption", ""))
                    .date(item.get("date"))
                    .metadata({
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "branch": item.get("branch"),
                        "date": item.get("date")
                    })
                    .build())
                documents.append(doc)

            return QueryResult(
                success=True,
                source="DVIDS",
                total=total,
                results=documents,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "page_info": page_info
                }
            )

        except requests.HTTPError as e:
            logger.error(f"DVIDS HTTP error: {e}", exc_info=True)
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
                http_code=status_code if status_code > 0 else None,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"DVIDS search failed: {e}", exc_info=True)
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
                http_code=None,  # Non-HTTP error
                response_time_ms=response_time_ms
            )
