#!/usr/bin/env python3
"""
Federal Register database integration.

Provides access to Federal Register documents including rules, proposed rules,
notices, and presidential documents.
"""

import json
from typing import Dict, Optional
from datetime import datetime
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


class FederalRegisterIntegration(DatabaseIntegration):
    """
    Integration for FederalRegister.gov.

    The Federal Register is the official daily publication for rules,
    proposed rules, and notices of Federal agencies and organizations,
    as well as executive orders and other presidential documents.

    API Features:
    - NO API key required
    - Free, open access
    - Search by term/keywords
    - Filter by document type
    - Filter by agency
    - Filter by date range
    - Returns JSON or CSV

    Rate Limits:
    - No official limit documented
    - Recommendation: Be respectful, 1 request per second

    Limitations:
    - Can only paginate through first 2000 results
    - Use date range filters to get more results if needed
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Federal Register",
            id="federal_register",
            category=DatabaseCategory.GOV_FEDERAL_REGISTER,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.5,      # seconds
            rate_limit_daily=None,          # No official limit
            description="Official daily publication of U.S. federal rules, proposed rules, and notices"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check - does question relate to federal regulations/rules?

        We check for regulation/rule-related keywords to avoid wasting LLM calls
        on questions that clearly aren't about federal regulatory activity.

        Args:
            research_question: The user's research question

        Returns:
            True if question might be about regulations, False otherwise
        """
        regulation_keywords = [
            "regulation", "regulations", "regulatory", "rule", "rules", "rulemaking",
            "notice", "notices", "federal register", "agency", "agencies",
            "policy", "policies", "compliance", "requirement", "requirements",
            "standard", "standards", "law", "laws", "legal", "cfr", "code of federal",
            "proposed", "final rule", "interim", "directive", "directives",
            "executive order", "presidential", "department of", "epa", "fda", "sec",
            "dhs", "homeland security", "defense", "treasury", "commerce"
        ]

        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in regulation_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Federal Register query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the Federal Register API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "term": "cybersecurity",
                "document_types": ["RULE", "PRORULE"],
                "agencies": ["homeland-security-department"],
                "date_range_days": 90
            }
        """

        prompt = render_prompt(
            "integrations/federal_register_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                                "term": {
                    "type": "string",
                    "description": "Search term for document titles and text"
                },
                "document_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of document types, empty for all"
                },
                "agencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of agency slugs, empty if not specified"
                },
                "date_range_days": {
                    "type": "integer",
                    "description": "Days back to search, 1-730",
                    "minimum": 1,
                    "maximum": 730
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["term", "document_types", "agencies", "date_range_days", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "federal_register_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # RELEVANCE FILTER REMOVED - Always generate query
        # if not result["relevant"]:
        #     return None

        return {
            "term": result["term"],
            "document_types": result["document_types"],
            "agencies": result["agencies"],
            "date_range_days": result["date_range_days"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute Federal Register search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: Not required (Federal Register API is free)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://www.federalregister.gov/api/v1/documents.json"

        try:
            # Build request parameters
            params = {
                "per_page": min(limit, 1000),  # Max 1000 per request
                "order": "newest",  # Most recent first
            }

            # Add search term if specified
            if query_params.get("term"):
                params["conditions[term]"] = query_params["term"]

            # Add document types if specified
            if query_params.get("document_types") and len(query_params["document_types"]) > 0:
                for doc_type in query_params["document_types"]:
                    params["conditions[type][]"] = doc_type

            # Add agencies if specified
            if query_params.get("agencies") and len(query_params["agencies"]) > 0:
                for agency in query_params["agencies"]:
                    params["conditions[agencies][]"] = agency

            # Add date range (publication_date)
            if query_params.get("date_range_days"):
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=query_params["date_range_days"])
                params["conditions[publication_date][gte]"] = start_date.strftime("%Y-%m-%d")
                params["conditions[publication_date][lte]"] = end_date.strftime("%Y-%m-%d")

            # Execute API call
            response = requests.get(
                endpoint,
                params=params,
                headers={"Accept": "application/json"},
                timeout=15  # 15 second timeout
            )
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse response
            data = response.json()
            documents = data.get("results", [])
            total = data.get("count", len(documents))

            # Log successful request
            log_request(
                api_name="Federal Register",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=params
            )

            return QueryResult(
                success=True,
                source="Federal Register",
                total=total,
                results=documents[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "next_page_url": data.get("next_page_url"),
                    "total_pages": data.get("total_pages", 1)
                }
            )

        except requests.HTTPError as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="Federal Register",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=f"HTTP {status_code}",
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Federal Register",
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
                api_name="Federal Register",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="Federal Register",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
