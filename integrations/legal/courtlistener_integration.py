#!/usr/bin/env python3
"""
CourtListener database integration.

Provides access to federal and state court opinions, RECAP filings,
judicial financial disclosures, and oral arguments via the Free Law Project API.
"""

import json
import logging
import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
import requests
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()


class CourtListenerIntegration(DatabaseIntegration):
    """
    Integration for CourtListener - Free Law Project's legal database.

    CourtListener provides free access to millions of legal opinions, court filings,
    and judicial data from federal and state courts.

    API Features:
    - Requires free API token from courtlistener.com
    - Search opinions by full-text keyword
    - Filter by court, date range, case name
    - Access RECAP federal court filings
    - Judicial financial disclosure reports
    - Oral argument audio recordings

    Rate Limits:
    - 5,000 requests per hour (authenticated)
    - 100 requests per day (unauthenticated)

    Data Coverage:
    - Federal Courts: Supreme Court, Circuit Courts, District Courts, Bankruptcy
    - State Courts: All appellate courts, many trial courts
    - Historical: Opinions back to 1754
    - RECAP: Federal district and bankruptcy filings (PACER mirror)

    API Documentation:
    - https://www.courtlistener.com/help/api/rest/
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="CourtListener",
            id="courtlistener",
            category=DatabaseCategory.RESEARCH,
            requires_api_key=True,
            api_key_env_var="COURTLISTENER_API_KEY",
            cost_per_query_estimate=0.001,  # LLM cost only (API is free)
            typical_response_time=2.0,      # seconds
            rate_limit_daily=120000,        # 5000/hour * 24 hours
            description="Federal and state court opinions, RECAP filings, judicial disclosures",

            # Rate Limit Recovery - CourtListener has 5,000 requests/hour (authenticated)
            # Source: https://www.courtlistener.com/help/api/rest/
            rate_limit_recovery_seconds=60,  # Wait 1 min, quota partially refills
            retry_on_rate_limit_within_session=True  # Worth retrying - hourly limit rolls
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for CourtListener.

        Uses LLM to determine if court opinions, legal filings, or judicial
        decisions might have relevant information for the research question.

        Args:
            research_question: The user's research question

        Returns:
            True if CourtListener might have relevant information, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv
        import json

        load_dotenv()

        prompt = f"""Is CourtListener relevant for researching this question?

RESEARCH QUESTION:
{research_question}

COURTLISTENER CHARACTERISTICS:
Strengths:
- Federal and state court opinions (Supreme Court, Circuit Courts, District Courts)
- RECAP filings (PACER documents)
- Judicial financial disclosures
- Legal precedent and case law
- Litigation history and rulings
- Patent, trademark, copyright cases
- Antitrust, securities fraud, class action lawsuits
- Contract disputes and business litigation
- FEDERAL LAWSUITS against companies or individuals

Limitations:
- Only judicial branch documents (not legislative or executive)
- No proposed regulations or agency rules
- No contractor databases or procurement records
- Limited to legal proceedings and court documents

CRITICAL - PARTIAL RELEVANCE RULE:
If a research question mentions MULTIPLE topics and ANY ONE of them relates to lawsuits, litigation, court cases, legal disputes, or judicial proceedings, return relevant=true. Do NOT reject just because the question also asks about topics CourtListener doesn't cover (like contracts or funding).

Example: "contractors who received funding AND face federal lawsuits" → relevant=TRUE (CourtListener handles the "federal lawsuits" part; other sources handle the funding part)

DECISION CRITERIA:
- Is relevant: If seeking court opinions, litigation history, legal precedent, judicial decisions, lawsuits, or legal disputes
- Is relevant: If the question mentions "lawsuits", "litigation", "court", "enforcement actions", or "legal"
- NOT relevant ONLY if: The question has ZERO legal/judicial/lawsuit component

Return JSON with your decision:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why CourtListener is/isn't relevant for this question"
}}"""

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default to True if parsing fails

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            # On error, default to True (let query generation and filtering handle it)
            print(f"[WARN] CourtListener relevance check failed: {e}, defaulting to True")
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate CourtListener query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the CourtListener API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "q": "antitrust google microsoft",
                "type": "o",  # Opinion
                "court": "scotus ca9",  # Supreme Court + 9th Circuit
                "filed_after": "2020-01-01",
                "filed_before": "2025-01-01"
            }
        """

        prompt = render_prompt(
            "integrations/courtlistener_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Search query for case names, parties, and full-text opinion search"
                },
                "type": {
                    "type": "string",
                    "description": "Result type: 'o' (opinions), 'r' (RECAP), 'p' (dockets), 'oa' (oral arguments)",
                    "enum": ["o", "r", "p", "oa"]
                },
                "court": {
                    "type": "string",
                    "description": "Court ID(s) separated by spaces (e.g., 'scotus ca9' for Supreme Court + 9th Circuit), empty for all courts"
                },
                "filed_after": {
                    "type": ["string", "null"],
                    "description": "Start date for filing date range (YYYY-MM-DD) or null"
                },
                "filed_before": {
                    "type": ["string", "null"],
                    "description": "End date for filing date range (YYYY-MM-DD) or null"
                },
                "case_name": {
                    "type": "string",
                    "description": "Filter by case name (e.g., 'United States v.')"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["q", "type", "court", "filed_after", "filed_before", "case_name", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "courtlistener_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "q": result["q"],
            "type": result["type"],
            "court": result["court"],
            "filed_after": result["filed_after"],
            "filed_before": result["filed_before"],
            "case_name": result["case_name"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute CourtListener search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: CourtListener API token (from courtlistener.com account)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://www.courtlistener.com/api/rest/v3/search/"

        if not api_key:
            # Try loading from environment variable
            api_key = os.getenv("COURTLISTENER_API_KEY")

        if not api_key:
            return QueryResult(
                success=False,
                source="CourtListener",
                total=0,
                results=[],
                query_params=query_params,
                error="CourtListener API key not found. Get one at: https://www.courtlistener.com/sign-in/register/"
            )

        try:
            # Build request parameters
            params = {
                "format": "json",
                "order_by": "score desc",  # Best matches first
            }

            # Add search query
            if query_params.get("q"):
                params["q"] = query_params["q"]

            # Add result type (opinions, RECAP, etc.)
            if query_params.get("type"):
                params["type"] = query_params["type"]

            # Add court filter
            if query_params.get("court"):
                params["court"] = query_params["court"]

            # Add date range filters
            if query_params.get("filed_after"):
                params["filed_after"] = query_params["filed_after"]
            if query_params.get("filed_before"):
                params["filed_before"] = query_params["filed_before"]

            # Add case name filter
            if query_params.get("case_name"):
                params["case_name"] = query_params["case_name"]

            # Execute API call with authentication
            headers = {
                "Authorization": f"Token {api_key}",
                "Accept": "application/json"
            }

            # Run blocking requests in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(endpoint, params=params, headers=headers, timeout=30)
            )
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            response.raise_for_status()

            # Parse response
            data = response.json()
            results = data.get("results", [])
            total = data.get("count", len(results))

            # Log successful request
            log_request(
                api_name="CourtListener",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=params
            )

            # Transform results to standardized format
            transformed_results = []
            for result in results[:limit]:
                # Different result types have different structures
                result_type = query_params.get("type", "o")

                if result_type == "o":  # Opinion
                    # Extract court and case name
                    court_name = result.get("court", "") or result.get("court_citation_string", "")
                    case_name = result.get("caseName", "") or result.get("case_name", "")
                    date_filed = result.get("dateFiled", "") or result.get("date_filed", "")

                    # Build snippet from summary or text
                    snippet_parts = []
                    if court_name:
                        snippet_parts.append(f"Court: {court_name}")
                    if date_filed:
                        snippet_parts.append(f"Filed: {date_filed}")
                    if result.get("status"):
                        snippet_parts.append(f"Status: {result['status']}")

                    # Add text excerpt if available
                    text_snippet = result.get("snippet", "") or result.get("text", "")[:200]
                    if text_snippet:
                        snippet_parts.append(text_snippet)

                    snippet = " | ".join(snippet_parts) if snippet_parts else "Court opinion"

                    url = result.get("absolute_url") or f"https://www.courtlistener.com{result.get('url', '')}"
                    transformed = (SearchResultBuilder()
                        .title(case_name, default="Untitled Case")
                        .url(url)
                        .snippet(snippet[:500] if snippet else "")
                        .date(date_filed)
                        .metadata({
                            "court": court_name,
                            "date_filed": date_filed,
                            "docket_number": result.get("docketNumber", "") or result.get("docket_number", ""),
                            "citation": result.get("citation", []),
                            "status": result.get("status", ""),
                            "result_type": "opinion"
                        })
                        .build())

                elif result_type == "r":  # RECAP
                    docket = result.get("docket", {})
                    case_name = SearchResultBuilder.safe_text(docket.get("case_name"))
                    court = SearchResultBuilder.safe_text(result.get("court"))
                    date_filed = result.get("date_filed", "")
                    description = SearchResultBuilder.safe_text(result.get("description"))

                    snippet = f"Court: {court} | Filed: {date_filed} | {description[:200]}"
                    url = result.get("absolute_url") or f"https://www.courtlistener.com{result.get('url', '')}"

                    transformed = (SearchResultBuilder()
                        .title(case_name, default="Untitled Filing")
                        .url(url)
                        .snippet(snippet[:500] if snippet else "")
                        .date(date_filed)
                        .metadata({
                            "court": court,
                            "date_filed": date_filed,
                            "document_number": result.get("document_number", ""),
                            "description": description,
                            "result_type": "recap"
                        })
                        .build())

                else:  # Other types (dockets, oral arguments, etc.)
                    title = SearchResultBuilder.safe_text(result.get("case_name") or result.get("title"))
                    url = result.get("absolute_url") or f"https://www.courtlistener.com{result.get('url', '')}"
                    date = result.get("date_filed", "") or result.get("date_created", "")

                    transformed = (SearchResultBuilder()
                        .title(title, default="Untitled Result")
                        .url(url)
                        .snippet(str(result)[:500])
                        .date(date)
                        .metadata({
                            "result_type": result_type,
                            "raw_result": result
                        })
                        .build())

                transformed_results.append(transformed)

            return QueryResult(
                success=True,
                source="CourtListener",
                total=total,
                results=transformed_results,
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    "next": data.get("next"),
                    "previous": data.get("previous")
                }
            )

        except requests.exceptions.HTTPError as e:
            # CourtListener HTTP error
            logger.error(f"CourtListener HTTP error: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            error_msg = f"HTTP {status_code}: {e.response.reason}"
            if status_code == 401:
                error_msg = "Invalid API token. Get one at: https://www.courtlistener.com/sign-in/register/"
            elif status_code == 429:
                error_msg = "Rate limit exceeded (5000/hour). Wait before retrying."

            # Log failed request
            log_request(
                api_name="CourtListener",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=error_msg,
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="CourtListener",
                total=0,
                results=[],
                query_params=query_params,
                error=error_msg,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Exception in integration - log with full trace
            logger.error(f"Operation failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="CourtListener",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="CourtListener",
                total=0,
                results=[],
                query_params=query_params,
                error=f"CourtListener API error: {str(e)}",
                response_time_ms=response_time_ms
            )
