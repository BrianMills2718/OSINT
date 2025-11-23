#!/usr/bin/env python3
"""
ICIJ Offshore Leaks Database integration.

Provides access to the International Consortium of Investigative Journalists'
offshore leaks database including Panama Papers, Paradise Papers, Pandora Papers,
and other major financial leak investigations.
"""

import json
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
from core.api_request_tracker import log_request
from config_loader import config


class ICIJOffshoreLeaksIntegration(DatabaseIntegration):
    """
    Integration for ICIJ Offshore Leaks Database.

    The Offshore Leaks Database contains information on more than 810,000 offshore
    entities uncovered through major leak investigations by the International
    Consortium of Investigative Journalists (ICIJ).

    Database Features:
    - NO API key required (public database)
    - Free access for journalists and researchers
    - 810,000+ offshore entities
    - Multiple leak investigations included
    - Reconciliation API for entity matching

    Data Coverage:
    - **Pandora Papers** (2021) - 11.9M documents
    - **Paradise Papers** (2017) - 13.4M documents
    - **Panama Papers** (2016) - 11.5M documents
    - **Bahamas Leaks** (2016)
    - **Offshore Leaks** (2013)

    Entity Types:
    - Officers: People associated with offshore entities
    - Entities: Companies, trusts, foundations
    - Addresses: Offshore addresses
    - Intermediaries: Law firms, banks that set up structures

    Rate Limits:
    - No official limit documented
    - Recommendation: Be respectful, 1 request per second

    API Documentation:
    - https://offshoreleaks.icij.org/
    - Uses OpenRefine Reconciliation API standard
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="ICIJ Offshore Leaks",
            id="icij_offshore_leaks",
            category=DatabaseCategory.RESEARCH,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,      # seconds
            rate_limit_daily=None,          # No official limit
            description="Panama Papers, Paradise Papers, Pandora Papers - offshore entities and shell companies"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to offshore finance/leaks?

        Args:
            research_question: The user's research question

        Returns:
            True if question relates to offshore entities, False otherwise
        """
        offshore_keywords = [
            "offshore", "panama papers", "paradise papers", "pandora papers",
            "bahamas leaks", "tax haven", "shell company", "shell companies",
            "offshore entity", "offshore entities", "tax avoidance", "tax evasion",
            "hidden assets", "hidden ownership", "beneficial owner", "nominee",
            "british virgin islands", "bvi", "cayman islands", "bermuda",
            "panama", "seychelles", "cyprus", "luxembourg", "switzerland",
            "icij", "leaked", "leak", "leaks", "financial secrecy",
            "offshore account", "offshore banking", "offshore trust",
            "mossack fonseca", "appleby", "portcullis", "trustnet"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in offshore_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate ICIJ query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the ICIJ Reconciliation API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "search_name": "Vladimir Putin",
                "entity_type": "Officer",
                "jurisdiction": "",
                "leak_source": "Panama Papers"
            }
        """

        prompt = render_prompt(
            "integrations/icij_offshore_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "search_name": {
                    "type": "string",
                    "description": "Name to search (person, company, or intermediary)"
                },
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity to search for",
                    "enum": ["Officer", "Entity", "Address", "Intermediary", "All"]
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Country/jurisdiction to filter by (empty for all)"
                },
                "leak_source": {
                    "type": "string",
                    "description": "Specific leak to search (empty for all leaks)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["search_name", "entity_type", "jurisdiction", "leak_source", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "icij_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "search_name": result["search_name"],
            "entity_type": result["entity_type"],
            "jurisdiction": result["jurisdiction"],
            "leak_source": result["leak_source"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute ICIJ Offshore Leaks search using Reconciliation API.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not required (ICIJ database is free)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://offshoreleaks.icij.org/api/v1/reconcile"

        search_name = query_params.get("search_name", "")
        entity_type = query_params.get("entity_type", "All")

        if not search_name:
            return QueryResult(
                success=False,
                source="ICIJ Offshore Leaks",
                total=0,
                results=[],
                query_params=query_params,
                error="Search name is required"
            )

        try:
            # Build Reconciliation API query
            # Format: {"q0": {"query": "search term", "type": "Entity", "limit": 10}}
            queries = {
                "q0": {
                    "query": search_name,
                    "limit": min(limit, 100)
                }
            }

            # Add type filter if specified
            if entity_type != "All":
                queries["q0"]["type"] = entity_type

            # Make request (Reconciliation API uses POST or GET with queries parameter)
            params = {
                "queries": json.dumps(queries)
            }

            # Execute API call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(endpoint, params=params, timeout=30)
            )
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            response.raise_for_status()
            data = response.json()

            # Parse Reconciliation API response
            # Format: {"q0": {"result": [{"id": "...", "name": "...", "score": 100, ...}]}}
            q0_results = data.get("q0", {}).get("result", [])
            total = len(q0_results)

            # Log successful request
            log_request(
                api_name="ICIJ Offshore Leaks",
                endpoint=endpoint,
                status_code=200,
                response_time_ms=response_time_ms,
                result_count=total,
                request_params=params
            )

            # Transform results to standardized format
            transformed_results = []
            for entity in q0_results[:limit]:
                entity_id = entity.get("id", "")
                name = entity.get("name", "Unknown Entity")
                score = entity.get("score", 0)
                match = entity.get("match", False)

                # Extract metadata from entity object
                entity_type_info = entity.get("type", [])
                if entity_type_info and len(entity_type_info) > 0:
                    entity_type_name = entity_type_info[0].get("name", "Unknown")
                else:
                    entity_type_name = "Unknown"

                # Extract additional metadata (jurisdiction, leak source, etc.)
                # Note: Full details require a second API call to the entity endpoint
                # For now, we'll use what's in the reconciliation response
                jurisdiction = entity.get("jurisdiction", "")
                countries = entity.get("countries", "")
                sourceID = entity.get("sourceID", "")

                # Build entity URL
                url = f"https://offshoreleaks.icij.org/nodes/{entity_id}" if entity_id else ""

                # Build snippet with key info
                snippet_parts = []
                snippet_parts.append(f"Type: {entity_type_name}")
                if jurisdiction:
                    snippet_parts.append(f"Jurisdiction: {jurisdiction}")
                if countries:
                    snippet_parts.append(f"Countries: {countries}")
                if sourceID:
                    snippet_parts.append(f"Source: {sourceID}")
                snippet_parts.append(f"Match Score: {score}")

                snippet = " | ".join(snippet_parts)

                transformed = {
                    "title": name,
                    "url": url,
                    "snippet": snippet[:500] if snippet else "",
                    "date": None,  # Leak databases don't have a single publication date
                    "metadata": {
                        "entity_id": entity_id,
                        "entity_type": entity_type_name,
                        "jurisdiction": jurisdiction,
                        "countries": countries,
                        "leak_source": sourceID,
                        "match_score": score,
                        "exact_match": match
                    }
                }
                transformed_results.append(transformed)

            return QueryResult(
                success=True,
                source="ICIJ Offshore Leaks",
                total=total,
                results=transformed_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "search_name": search_name,
                    "entity_type": entity_type
                }
            )

        except requests.exceptions.HTTPError as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="ICIJ Offshore Leaks",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=f"HTTP {status_code}",
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="ICIJ Offshore Leaks",
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
                api_name="ICIJ Offshore Leaks",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="ICIJ Offshore Leaks",
                total=0,
                results=[],
                query_params=query_params,
                error=f"ICIJ API error: {str(e)}",
                response_time_ms=response_time_ms
            )
