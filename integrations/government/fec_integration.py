#!/usr/bin/env python3
"""
FEC (Federal Election Commission) database integration.

Provides access to official campaign finance data including contributions,
expenditures, candidate financials, and committee information.
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime
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
from core.api_request_tracker import log_request
from config_loader import config

# Load environment variables
load_dotenv()


class FECIntegration(DatabaseIntegration):
    """
    Integration for FEC (Federal Election Commission) campaign finance data.

    The FEC API provides access to official campaign finance records including
    contributions, expenditures, candidate financials, PAC/Super PAC data, and
    independent expenditures.

    API Features:
    - Requires free API key from api.data.gov (same as Congress.gov)
    - Search candidates by name, office, state, party
    - Get itemized contributions (Schedule A filings)
    - Track PAC and Super PAC spending
    - Committee financial information
    - Independent expenditures (outside spending)
    - Election results

    Rate Limits:
    - 1,000 requests per hour
    - Default: 20 results, max 100 per page

    Data Coverage:
    - Federal elections: President, Senate, House
    - Data back to 1980s (varies by endpoint)
    - Real-time updates (filings appear within days)

    API Documentation:
    - https://api.open.fec.gov/developers/
    - Interactive API explorer available
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="FEC",
            id="fec",
            category=DatabaseCategory.GOV_GENERAL,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.5,      # seconds
            rate_limit_daily=24000,         # 1000/hour * 24 hours
            description="Federal Election Commission campaign finance data: contributions, expenditures, PACs"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for FEC.

        Uses LLM to determine if Federal Election Commission data (campaign
        finance, political donations, PACs, lobbying) might have relevant information.

        Args:
            research_question: The user's research question

        Returns:
            True if FEC might have relevant information, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv
        import json

        load_dotenv()

        prompt = f"""Is the Federal Election Commission (FEC) database relevant for researching this question?

RESEARCH QUESTION:
{research_question}

FEC CHARACTERISTICS:
Strengths:
- Campaign contributions and donors
- PAC (Political Action Committee) donations
- Super PAC expenditures
- Individual and corporate political donations
- Campaign finance disclosures
- Lobbying activities and expenditures
- Political fundraising data
- Candidate financial reports
- Money in politics tracking

Limitations:
- Only election and campaign finance data
- No policy positions or voting records
- No legislation or bills
- No government contracts or procurement
- Limited to federal elections (not state/local)

DECISION CRITERIA:
- Is relevant: If seeking campaign finance, political donations, PAC funding, lobbying, or money in politics
- NOT relevant: If ONLY seeking legislation, voting records, contracts, or non-financial political information

Return JSON with your decision:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why FEC is/isn't relevant for this question"
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
            # On error, default to True (let query generation and filtering handle it)
            print(f"[WARN] FEC relevance check failed: {e}, defaulting to True")
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate FEC query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for the FEC API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "endpoint": "candidates",
                "candidate_name": "Warren",
                "office": "S",
                "state": "MA",
                "cycle": 2024,
                "include_contributions": true
            }
        """

        prompt = render_prompt(
            "integrations/fec_query_generation.j2",
            research_question=research_question
        )

        schema = {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "FEC API endpoint to use",
                    "enum": ["candidates", "contributions", "committees", "independent_expenditures"]
                },
                "candidate_name": {
                    "type": "string",
                    "description": "Candidate name to search (last name or full name)"
                },
                "committee_name": {
                    "type": "string",
                    "description": "Committee/PAC name to search"
                },
                "contributor_name": {
                    "type": "string",
                    "description": "Contributor/donor name to search"
                },
                "office": {
                    "type": ["string", "null"],
                    "description": "Office sought: 'P' (President), 'S' (Senate), 'H' (House), or null"
                },
                "state": {
                    "type": ["string", "null"],
                    "description": "Two-letter state code or null"
                },
                "cycle": {
                    "type": "integer",
                    "description": "Election cycle year (2024, 2022, 2020, etc.)"
                },
                "party": {
                    "type": ["string", "null"],
                    "description": "Party code: 'DEM', 'REP', 'IND', etc. or null"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the query strategy"
                }
            },
            "required": ["endpoint", "candidate_name", "committee_name", "contributor_name",
                        "office", "state", "cycle", "party", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "fec_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "endpoint": result["endpoint"],
            "candidate_name": result["candidate_name"],
            "committee_name": result["committee_name"],
            "contributor_name": result["contributor_name"],
            "office": result["office"],
            "state": result["state"],
            "cycle": result["cycle"],
            "party": result["party"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 20) -> QueryResult:
        """
        Execute FEC API search with generated parameters.

        Args:
            query_params: Parameters from generate_query()
            api_key: FEC API key (from api.data.gov, same as Congress.gov)
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()

        if not api_key:
            # Try loading from environment variable (same key as Congress.gov)
            api_key = os.getenv("CONGRESS_API_KEY") or os.getenv("FEC_API_KEY")

        if not api_key:
            return QueryResult(
                success=False,
                source="FEC",
                total=0,
                results=[],
                query_params=query_params,
                error="FEC API key not found. Get one at: https://api.data.gov/signup/"
            )

        endpoint_type = query_params.get("endpoint", "candidates")

        try:
            # Route to appropriate endpoint
            if endpoint_type == "candidates":
                return await self._search_candidates(query_params, api_key, limit, start_time)
            elif endpoint_type == "contributions":
                return await self._search_contributions(query_params, api_key, limit, start_time)
            elif endpoint_type == "committees":
                return await self._search_committees(query_params, api_key, limit, start_time)
            elif endpoint_type == "independent_expenditures":
                return await self._search_independent_expenditures(query_params, api_key, limit, start_time)
            else:
                return QueryResult(
                    success=False,
                    source="FEC",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"Unknown endpoint type: {endpoint_type}"
                )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=False,
                source="FEC",
                total=0,
                results=[],
                query_params=query_params,
                error=f"FEC API error: {str(e)}",
                response_time_ms=response_time_ms
            )

    async def _search_candidates(self, query_params: Dict, api_key: str,
                                limit: int, start_time: datetime) -> QueryResult:
        """Search for candidates and their financial summaries."""
        base_url = "https://api.open.fec.gov/v1/candidates/search/"

        params = {
            "api_key": api_key,
            "per_page": min(limit, 100),
            "sort": "-receipts",  # Sort by most fundraising
        }

        # Add search filters
        if query_params.get("candidate_name"):
            params["q"] = query_params["candidate_name"]
        if query_params.get("office"):
            params["office"] = query_params["office"]
        if query_params.get("state"):
            params["state"] = query_params["state"]
        if query_params.get("party"):
            params["party"] = query_params["party"]
        if query_params.get("cycle"):
            params["cycle"] = query_params["cycle"]

        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(base_url, params=params, timeout=30)
        )
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        total = data.get("pagination", {}).get("count", len(results))

        # Log request
        log_request(
            api_name="FEC",
            endpoint=base_url,
            status_code=200,
            response_time_ms=response_time_ms,
            result_count=len(results),
            request_params=params
        )

        # Transform results
        transformed_results = []
        for candidate in results[:limit]:
            name = candidate.get("name", "Unknown Candidate")
            office_full = candidate.get("office_full", "")
            state = candidate.get("state", "")
            party_full = candidate.get("party_full", "")
            candidate_id = candidate.get("candidate_id", "")

            # Build profile URL
            url = f"https://www.fec.gov/data/candidate/{candidate_id}/" if candidate_id else ""

            # Build snippet with financial summary if available
            snippet_parts = []
            if office_full and state:
                snippet_parts.append(f"{office_full} - {state}")
            if party_full:
                snippet_parts.append(f"Party: {party_full}")

            # Add cycle info
            cycles = candidate.get("cycles", [])
            if cycles:
                snippet_parts.append(f"Cycles: {', '.join(map(str, cycles))}")

            snippet = " | ".join(snippet_parts) if snippet_parts else "Federal candidate"

            transformed = {
                "title": name,
                "url": url,
                "snippet": snippet[:500],
                "date": None,  # Candidates don't have a single date
                "metadata": {
                    "candidate_id": candidate_id,
                    "office": candidate.get("office"),
                    "office_full": office_full,
                    "state": state,
                    "district": candidate.get("district"),
                    "party": candidate.get("party"),
                    "party_full": party_full,
                    "cycles": cycles,
                    "incumbent_challenge": candidate.get("incumbent_challenge_full"),
                    "candidate_status": candidate.get("candidate_status")
                }
            }
            transformed_results.append(transformed)

        return QueryResult(
            success=True,
            source="FEC",
            total=total,
            results=transformed_results,
            query_params=query_params,
            response_time_ms=response_time_ms,
            metadata={
                "api_url": base_url,
                "pagination": data.get("pagination", {})
            }
        )

    async def _search_contributions(self, query_params: Dict, api_key: str,
                                   limit: int, start_time: datetime) -> QueryResult:
        """Search itemized contributions (Schedule A)."""
        base_url = "https://api.open.fec.gov/v1/schedules/schedule_a/"

        params = {
            "api_key": api_key,
            "per_page": min(limit, 100),
            "sort": "-contribution_receipt_amount",
        }

        # Add search filters
        if query_params.get("contributor_name"):
            params["contributor_name"] = query_params["contributor_name"]
        if query_params.get("cycle"):
            params["two_year_transaction_period"] = query_params["cycle"]

        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(base_url, params=params, timeout=30)
        )
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        total = data.get("pagination", {}).get("count", len(results))

        # Log request
        log_request(
            api_name="FEC",
            endpoint=base_url,
            status_code=200,
            response_time_ms=response_time_ms,
            result_count=len(results),
            request_params=params
        )

        # Transform results
        transformed_results = []
        for contrib in results[:limit]:
            contributor = contrib.get("contributor_name", "Unknown Contributor")
            amount = contrib.get("contribution_receipt_amount", 0)
            recipient = contrib.get("committee", {}).get("name", "Unknown Committee")
            date = contrib.get("contribution_receipt_date", "")

            title = f"${amount:,.2f} from {contributor} to {recipient}"
            url = f"https://www.fec.gov/data/receipts/?data_type=processed"

            snippet = f"Amount: ${amount:,.2f} | Date: {date} | Employer: {contrib.get('contributor_employer', 'N/A')}"

            transformed = {
                "title": title,
                "url": url,
                "snippet": snippet[:500],
                "date": date,
                "metadata": {
                    "contributor_name": contributor,
                    "contributor_employer": contrib.get("contributor_employer"),
                    "contributor_occupation": contrib.get("contributor_occupation"),
                    "amount": amount,
                    "date": date,
                    "recipient_committee": recipient,
                    "recipient_committee_id": contrib.get("committee_id"),
                    "transaction_id": contrib.get("transaction_id")
                }
            }
            transformed_results.append(transformed)

        return QueryResult(
            success=True,
            source="FEC",
            total=total,
            results=transformed_results,
            query_params=query_params,
            response_time_ms=response_time_ms,
            metadata={
                "api_url": base_url,
                "pagination": data.get("pagination", {})
            }
        )

    async def _search_committees(self, query_params: Dict, api_key: str,
                                limit: int, start_time: datetime) -> QueryResult:
        """Search committees (PACs, Super PACs, campaigns)."""
        base_url = "https://api.open.fec.gov/v1/committees/"

        params = {
            "api_key": api_key,
            "per_page": min(limit, 100),
            "sort": "-receipts",
        }

        # Add search filters
        if query_params.get("committee_name"):
            params["q"] = query_params["committee_name"]
        if query_params.get("cycle"):
            params["cycle"] = query_params["cycle"]

        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(base_url, params=params, timeout=30)
        )
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        total = data.get("pagination", {}).get("count", len(results))

        # Log request
        log_request(
            api_name="FEC",
            endpoint=base_url,
            status_code=200,
            response_time_ms=response_time_ms,
            result_count=len(results),
            request_params=params
        )

        # Transform results
        transformed_results = []
        for committee in results[:limit]:
            name = committee.get("name", "Unknown Committee")
            committee_id = committee.get("committee_id", "")
            committee_type = committee.get("committee_type_full", "")

            url = f"https://www.fec.gov/data/committee/{committee_id}/" if committee_id else ""

            snippet = f"Type: {committee_type} | Party: {committee.get('party_full', 'N/A')}"

            transformed = {
                "title": name,
                "url": url,
                "snippet": snippet[:500],
                "date": None,
                "metadata": {
                    "committee_id": committee_id,
                    "committee_type": committee.get("committee_type"),
                    "committee_type_full": committee_type,
                    "party": committee.get("party"),
                    "designation": committee.get("designation_full"),
                    "treasurer_name": committee.get("treasurer_name")
                }
            }
            transformed_results.append(transformed)

        return QueryResult(
            success=True,
            source="FEC",
            total=total,
            results=transformed_results,
            query_params=query_params,
            response_time_ms=response_time_ms,
            metadata={
                "api_url": base_url,
                "pagination": data.get("pagination", {})
            }
        )

    async def _search_independent_expenditures(self, query_params: Dict, api_key: str,
                                              limit: int, start_time: datetime) -> QueryResult:
        """Search independent expenditures (outside spending)."""
        base_url = "https://api.open.fec.gov/v1/schedules/schedule_e/"

        params = {
            "api_key": api_key,
            "per_page": min(limit, 100),
            "sort": "-expenditure_amount",
        }

        # Add search filters
        if query_params.get("cycle"):
            params["cycle"] = query_params["cycle"]

        # Make request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(base_url, params=params, timeout=30)
        )
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        total = data.get("pagination", {}).get("count", len(results))

        # Log request
        log_request(
            api_name="FEC",
            endpoint=base_url,
            status_code=200,
            response_time_ms=response_time_ms,
            result_count=len(results),
            request_params=params
        )

        # Transform results
        transformed_results = []
        for expenditure in results[:limit]:
            amount = expenditure.get("expenditure_amount", 0)
            spender = expenditure.get("committee", {}).get("name", "Unknown")
            candidate = expenditure.get("candidate_name", "Unknown")
            support_oppose = expenditure.get("support_oppose_indicator", "")

            title = f"${amount:,.2f} by {spender} {'supporting' if support_oppose == 'S' else 'opposing'} {candidate}"
            url = "https://www.fec.gov/data/independent-expenditures/"

            snippet = f"Amount: ${amount:,.2f} | Purpose: {expenditure.get('expenditure_description', 'N/A')[:100]}"

            transformed = {
                "title": title,
                "url": url,
                "snippet": snippet[:500],
                "date": expenditure.get("expenditure_date"),
                "metadata": {
                    "amount": amount,
                    "spender": spender,
                    "candidate_name": candidate,
                    "support_oppose": "Support" if support_oppose == "S" else "Oppose",
                    "purpose": expenditure.get("expenditure_description"),
                    "date": expenditure.get("expenditure_date")
                }
            }
            transformed_results.append(transformed)

        return QueryResult(
            success=True,
            source="FEC",
            total=total,
            results=transformed_results,
            query_params=query_params,
            response_time_ms=response_time_ms,
            metadata={
                "api_url": base_url,
                "pagination": data.get("pagination", {})
            }
        )
