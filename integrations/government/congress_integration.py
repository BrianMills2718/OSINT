#!/usr/bin/env python3
"""
Congress.gov database integration.

Provides access to U.S. Congressional data including bills, members, votes,
hearings, and legislative activity from the Library of Congress API.
"""

import json
import logging
import os
from typing import Dict, Optional, List
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

# Load environment variables
load_dotenv()

# Set up logger for this module
logger = logging.getLogger(__name__)


class CongressIntegration(DatabaseIntegration):
    """
    Integration for Congress.gov - U.S. Congressional legislation and records.

    Congress.gov is the official website for U.S. federal legislative information.
    Provides access to bills, resolutions, members, votes, hearings, and more.

    API Features:
    - Requires API key from api.data.gov
    - Search bills by keyword, sponsor, committee
    - Filter by congress (e.g., 118th), chamber (House/Senate)
    - Access member information
    - Track votes, amendments, committee hearings
    - Full bill text and summaries

    Rate Limits:
    - 5,000 requests per hour
    - Default: 20 results, max 250 per request

    API Documentation:
    - https://github.com/LibraryOfCongress/api.congress.gov
    - https://api.congress.gov
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="Congress.gov",
            id="congress",
            category=DatabaseCategory.GOV_CONGRESS,
            requires_api_key=True,
            api_key_env_var="CONGRESS_API_KEY",
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.5,      # seconds
            rate_limit_daily=120000,        # 5000/hour * 24 hours
            description="U.S. Congressional bills, members, votes, and legislative records",

            # Rate Limit Recovery - Congress.gov has 5,000 requests/hour (rolling)
            # Source: https://github.com/LibraryOfCongress/api.congress.gov
            rate_limit_recovery_seconds=60,  # Wait 1 min, quota partially refills
            retry_on_rate_limit_within_session=True  # Worth retrying - hourly limit rolls
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for Congress.gov.

        Uses LLM to determine if Congressional records, bills, hearings, or
        legislative documents might have relevant information for the research question.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt
        import json

        prompt = render_prompt(
            "integrations/congress_relevance.j2",
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
            logger.warning(f"Congress relevance check failed, defaulting to True: {e}", exc_info=True)
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Congress.gov query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for the Congress.gov API.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "endpoint": "bill",
                "keywords": "artificial intelligence defense",
                "congress": 118,
                "limit": 100
            }
        """

        prompt = render_prompt(
            "integrations/congress_query.j2",
            research_question=research_question
        )

        schema = {
            "name": "congress_query",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {
                        "type": "boolean",
                        "description": "Is this question relevant for Congressional data?"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why is/isn't this relevant for Congress.gov?"
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "API endpoint to use (bill, member, amendment, law, hearing)",
                        "enum": ["bill", "member", "amendment", "law", "hearing"]
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Search keywords for the query"
                    },
                    "congress": {
                        "type": "integer",
                        "description": "Congress number (e.g., 118 for 118th Congress, 2023-2025)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to retrieve (20-250)"
                    }
                },
                "required": ["relevant", "reasoning", "endpoint", "keywords", "congress", "limit"],
                "additionalProperties": False
            }
        }

        response = await acompletion(
            model=config.default_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": schema}
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        return {
            "endpoint": result.get("endpoint", "bill"),
            "keywords": result.get("keywords", ""),
            "congress": result.get("congress", 118),  # Current congress
            "limit": min(result.get("limit", 100), 250)  # Cap at API max
        }

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        """
        Execute Congress.gov search via API with keyword filtering and summary fetching.

        Args:
            query_params: Query parameters from generate_query()
            api_key: Congress.gov API key (from api.data.gov)
            limit: Maximum results to return

        Returns:
            QueryResult with bills/records found including summaries
        """
        endpoint = query_params.get("endpoint", "bill")
        keywords = query_params.get("keywords", "")
        congress_num = query_params.get("congress", 118)
        limit = min(query_params.get("limit", 100), limit, 250)

        if not api_key:
            # Try loading from environment variable
            api_key = os.getenv("CONGRESS_API_KEY")

        if not api_key:
            return QueryResult(
                success=False,
                source="Congress.gov",
                total=0,
                results=[],
                query_params=query_params,
                error="Congress.gov API key not found. Get one at: https://api.congress.gov/sign-up/",
                http_code=None  # Configuration error, not HTTP
            )

        try:
            # Build API URL based on endpoint
            # Use search endpoint for bills when keywords provided
            if endpoint == "bill" and keywords:
                # Use bill search with query parameter
                base_url = f"https://api.congress.gov/v3/bill"
            elif endpoint == "bill":
                base_url = f"https://api.congress.gov/v3/bill/{congress_num}"
            elif endpoint == "member":
                base_url = f"https://api.congress.gov/v3/member/{congress_num}"
            elif endpoint == "amendment":
                base_url = f"https://api.congress.gov/v3/amendment/{congress_num}"
            elif endpoint == "law":
                base_url = f"https://api.congress.gov/v3/law/{congress_num}"
            elif endpoint == "hearing":
                base_url = f"https://api.congress.gov/v3/hearing/{congress_num}"
            else:
                base_url = f"https://api.congress.gov/v3/bill/{congress_num}"

            # Build request params
            params = {
                "api_key": api_key,
                "format": "json",
                "limit": limit,
                "offset": 0
            }

            # Add search query for bills (Congress API supports 'query' parameter)
            if endpoint == "bill" and keywords:
                # Search bill titles and text using query parameter
                params["query"] = keywords
                # Filter to specific congress if specified
                params["congress"] = congress_num

            # Make request (async)
            start_time = datetime.now()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    base_url,
                    params=params,
                    timeout=30
                )
            )
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            response.raise_for_status()
            data = response.json()

            # Parse response based on endpoint
            documents = []

            if endpoint == "bill":
                bills = data.get("bills", [])

                # Fetch summaries for top bills (up to 10 to avoid rate limits)
                bills_with_summaries = await self._fetch_bill_summaries(
                    bills[:min(10, len(bills))],
                    api_key
                )

                for bill in bills_with_summaries:
                    title = SearchResultBuilder.safe_text(bill.get("title"))
                    summary = SearchResultBuilder.safe_text(bill.get("summary"))
                    latest_action = SearchResultBuilder.safe_text(
                        bill.get('latestAction', {}).get('text'), default='N/A'
                    )

                    # Build comprehensive snippet with actual content
                    snippet_parts = []
                    if summary:
                        snippet_parts.append(f"Summary: {summary[:500]}")
                    snippet_parts.append(f"Latest Action: {latest_action[:200]}")
                    snippet_parts.append(f"Introduced: {bill.get('introducedDate', 'N/A')}")

                    bill_type = SearchResultBuilder.safe_text(bill.get("type"))
                    bill_number = SearchResultBuilder.safe_text(bill.get("number"))

                    # Three-tier model: preserve full content with build_with_raw()
                    snippet_text = " | ".join(snippet_parts)
                    doc = (SearchResultBuilder()
                        .title(f"{bill_type} {bill_number} - {title}" if bill_type or bill_number else title,
                               default="Untitled Bill")
                        .url(bill.get("url"))
                        .snippet(snippet_text)
                        .raw_content(summary if summary else snippet_text)  # Full content
                        .date(bill.get('introducedDate'))
                        .api_response(bill)  # Preserve complete API response
                        .metadata({
                            "bill_type": bill.get("type"),
                            "bill_number": bill.get("number"),
                            "congress": bill.get("congress"),
                            "introduced_date": bill.get("introducedDate"),
                            "sponsors": bill.get("sponsors", []),
                            "committees": bill.get("committees", []),
                            "has_summary": bool(summary),
                            "description": summary if summary else latest_action
                        })
                        .build_with_raw())
                    documents.append(doc)

            elif endpoint == "member":
                members = data.get("members", [])
                for member in members:
                    name = SearchResultBuilder.safe_text(member.get("name"))
                    if keywords and keywords.lower() not in name.lower():
                        continue

                    state = SearchResultBuilder.safe_text(member.get("state"))
                    party = SearchResultBuilder.safe_text(member.get("party"))
                    chamber = SearchResultBuilder.safe_text(member.get("chamber"))
                    district = SearchResultBuilder.safe_text(member.get("district"), default="N/A")

                    # Three-tier model: preserve full content with build_with_raw()
                    snippet_text = f"Chamber: {chamber} | District: {district}"
                    doc = (SearchResultBuilder()
                        .title(f"{name} ({state}-{party})" if name else "Unknown Member",
                               default="Unknown Member")
                        .url(member.get("url"))
                        .snippet(snippet_text)
                        .raw_content(snippet_text)  # Full content
                        .api_response(member)  # Preserve complete API response
                        .metadata({
                            "member_id": member.get("bioguideId"),
                            "party": member.get("party"),
                            "state": member.get("state"),
                            "chamber": member.get("chamber"),
                            "description": f"{name} - {chamber} member from {state}"
                        })
                        .build_with_raw())
                    documents.append(doc)

            elif endpoint == "hearing":
                hearings = data.get("hearings", [])

                # Fetch hearing details for top hearings (up to 10)
                hearings_with_details = await self._fetch_hearing_details(
                    hearings[:min(10, len(hearings))],
                    api_key
                )

                for hearing in hearings_with_details:
                    chamber = SearchResultBuilder.safe_text(hearing.get("chamber"))
                    number = SearchResultBuilder.safe_text(hearing.get("number"))
                    jacket_number = SearchResultBuilder.safe_text(hearing.get("jacketNumber"))
                    title = SearchResultBuilder.safe_text(hearing.get("title"), default=f"Hearing {number}")
                    description = SearchResultBuilder.safe_text(hearing.get("description"))
                    update_date = SearchResultBuilder.safe_text(hearing.get("updateDate"), default="N/A")

                    snippet_desc = description[:300] if description else "No description available"

                    # Three-tier model: preserve full content with build_with_raw()
                    snippet_text = f"{snippet_desc} | Chamber: {chamber} | Updated: {update_date}"
                    doc = (SearchResultBuilder()
                        .title(f"{title} - {chamber} (Congress {congress_num})", default="Untitled Hearing")
                        .url(hearing.get("url"))
                        .snippet(snippet_text)
                        .raw_content(description if description else snippet_text)  # Full content
                        .date(hearing.get("updateDate"))
                        .api_response(hearing)  # Preserve complete API response
                        .metadata({
                            "chamber": chamber,
                            "number": number,
                            "jacket_number": jacket_number,
                            "congress": hearing.get("congress"),
                            "update_date": hearing.get("updateDate"),
                            "title": title,
                            "description": description if description else f"{chamber} hearing #{number}"
                        })
                        .build_with_raw())
                    documents.append(doc)

            # Limit results to limit
            documents = documents[:limit]

            # Log the request
            log_request(
                api_name="Congress.gov",
                endpoint=base_url,
                status_code=200,
                result_count=len(documents),
                request_params={
                    "keywords": keywords,
                    "endpoint": endpoint,
                    "congress": congress_num
                }
            )

            return QueryResult(
                success=True,
                source="Congress.gov",
                total=len(documents),
                results=documents,
                query_params=query_params,
                response_time_ms=response_time_ms
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"Congress.gov HTTP error: {e}", exc_info=True)
            status_code = e.response.status_code if e.response else None
            error_msg = f"HTTP {status_code}: {e.response.reason if e.response else 'Unknown'}"
            if status_code == 401:
                error_msg = "Invalid API key. Get one at: https://api.congress.gov/sign-up/"
            elif status_code == 429:
                error_msg = "Rate limit exceeded (5000/hour). Wait before retrying."

            return QueryResult(
                success=False,
                source="Congress.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=error_msg,
                http_code=status_code
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"Congress operation failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="Congress.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Congress.gov API error: {str(e)}",
                http_code=None  # Non-HTTP error
            )

    async def _fetch_bill_summaries(
        self,
        bills: List[Dict],
        api_key: str
    ) -> List[Dict]:
        """
        Fetch summaries for a list of bills.

        Makes individual API calls to get bill summaries. Limited to first N bills
        to respect rate limits.

        Args:
            bills: List of bill dictionaries from list endpoint
            api_key: Congress.gov API key

        Returns:
            Bills with 'summary' field populated where available
        """
        if not bills:
            return bills

        loop = asyncio.get_event_loop()
        enhanced_bills = []

        for bill in bills:
            # Copy original bill data
            enhanced_bill = dict(bill)

            try:
                # Build URL for bill summaries
                congress = bill.get("congress", 118)
                bill_type = bill.get("type", "").lower()
                bill_number = bill.get("number", "")

                if bill_type and bill_number:
                    summary_url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/summaries"

                    # Fetch summary
                    response = await loop.run_in_executor(
                        None,
                        lambda url=summary_url: requests.get(
                            url,
                            params={"api_key": api_key, "format": "json"},
                            timeout=10
                        )
                    )

                    if response.status_code == 200:
                        data = response.json()
                        summaries = data.get("summaries", [])

                        # Get most recent summary (they're ordered by update date)
                        if summaries:
                            # Prefer CRS summary, fall back to first available
                            for summary in summaries:
                                text = summary.get("text", "")
                                if text:
                                    # Strip HTML tags for cleaner text
                                    import re
                                    clean_text = re.sub(r'<[^>]+>', '', text)
                                    enhanced_bill["summary"] = clean_text[:1000]  # Limit length
                                    break

            except Exception as e:
                # Log but don't fail - summary is optional enhancement
                logger.debug(f"Failed to fetch summary for bill {bill.get('number')}: {e}")

            enhanced_bills.append(enhanced_bill)

            # Small delay to avoid rate limiting (5000/hour = ~1.4/sec)
            await asyncio.sleep(0.2)

        return enhanced_bills

    async def _fetch_hearing_details(
        self,
        hearings: List[Dict],
        api_key: str
    ) -> List[Dict]:
        """
        Fetch details for a list of hearings including titles and descriptions.

        Makes individual API calls to get hearing details. Limited to first N hearings
        to respect rate limits.

        Args:
            hearings: List of hearing dictionaries from list endpoint
            api_key: Congress.gov API key

        Returns:
            Hearings with 'title' and 'description' fields populated where available
        """
        if not hearings:
            return hearings

        loop = asyncio.get_event_loop()
        enhanced_hearings = []

        for hearing in hearings:
            # Copy original hearing data
            enhanced_hearing = dict(hearing)

            try:
                # The hearing URL from list response points to detail endpoint
                detail_url = hearing.get("url", "")

                if detail_url:
                    # Fetch hearing detail
                    response = await loop.run_in_executor(
                        None,
                        lambda url=detail_url: requests.get(
                            url,
                            params={"api_key": api_key, "format": "json"},
                            timeout=10
                        )
                    )

                    if response.status_code == 200:
                        data = response.json()
                        hearing_detail = data.get("hearing", {})

                        # Extract title and description
                        title = hearing_detail.get("title", "")
                        if title:
                            enhanced_hearing["title"] = title

                        # Try to get description from various fields
                        description = ""
                        if hearing_detail.get("description"):
                            description = hearing_detail["description"]
                        elif hearing_detail.get("committees"):
                            committees = hearing_detail["committees"]
                            if committees:
                                committee_names = [c.get("name", "") for c in committees if c.get("name")]
                                if committee_names:
                                    description = f"Committee: {', '.join(committee_names)}"

                        if description:
                            enhanced_hearing["description"] = description

            except Exception as e:
                # Log but don't fail - detail is optional enhancement
                logger.debug(f"Failed to fetch details for hearing {hearing.get('number')}: {e}")

            enhanced_hearings.append(enhanced_hearing)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.2)

        return enhanced_hearings
