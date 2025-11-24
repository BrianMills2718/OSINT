#!/usr/bin/env python3
"""
Congress.gov database integration.

Provides access to U.S. Congressional data including bills, members, votes,
hearings, and legislative activity from the Library of Congress API.
"""

import json
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
from core.api_request_tracker import log_request
from config_loader import config

# Load environment variables
load_dotenv()


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
        return DatabaseMetadata(
            name="Congress.gov",
            id="congress",
            category=DatabaseCategory.GOV_CONGRESS,
            requires_api_key=True,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.5,      # seconds
            rate_limit_daily=120000,        # 5000/hour * 24 hours
            description="U.S. Congressional bills, members, votes, and legislative records"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for Congress.gov.

        Uses LLM to determine if Congressional records, bills, hearings, or
        legislative documents might have relevant information for the research question.

        Args:
            research_question: The user's research question

        Returns:
            True if Congress.gov might have relevant information, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv
        import json

        load_dotenv()

        prompt = f"""Is Congress.gov relevant for researching this question?

RESEARCH QUESTION:
{research_question}

CONGRESS.GOV CHARACTERISTICS:
Strengths:
- Bills, resolutions, and legislative text
- Congressional hearings and testimony (including GAO reports to Congress)
- Committee reports and legislative analysis
- Roll call votes and legislative history
- Member information and sponsored bills
- Congressional Record (floor speeches, debates)

Limitations:
- Only U.S. Congressional activities (not executive or judicial)
- No contractor databases or procurement records
- No job listings or employment data
- Limited to legislative process documentation

DECISION CRITERIA:
- Is relevant: If seeking bills, hearings, legislative analysis, GAO testimony, Congressional oversight, or legislative history
- NOT relevant: If ONLY seeking executive orders, court cases, contracts, or non-legislative information

Return JSON with your decision:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why Congress.gov is/isn't relevant for this question"
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
            print(f"[WARN] Congress.gov relevance check failed: {e}, defaulting to True")
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
            model="gpt-4o-mini",
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
        Execute Congress.gov search via API.

        Args:
            query_params: Query parameters from generate_query()
            api_key: Congress.gov API key (from api.data.gov)
            limit: Maximum results to return

        Returns:
            QueryResult with bills/records found
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
                error="Congress.gov API key not found. Get one at: https://api.congress.gov/sign-up/"
            )

        try:
            # Build API URL based on endpoint
            if endpoint == "bill":
                # Search all bills in specified congress
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

            # Make request (async)
            start_time = datetime.now()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    base_url,
                    params={
                        "api_key": api_key,
                        "format": "json",
                        "limit": limit,
                        "offset": 0
                    },
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
                for bill in bills:
                    # Note: Congress API doesn't support keyword search
                    # Returns all bills from specified congress
                    # Keyword filtering happens in LLM relevance filter instead
                    title = bill.get("title", "")

                    doc = {
                        "title": f"{bill.get('type', '')} {bill.get('number', '')} - {title}",
                        "url": bill.get("url", ""),
                        "snippet": f"Introduced: {bill.get('introducedDate', 'N/A')} | Latest Action: {bill.get('latestAction', {}).get('text', 'N/A')[:200]}",
                        "date": bill.get('introducedDate'),  # Date bill was introduced
                        "metadata": {
                            "bill_type": bill.get("type"),
                            "bill_number": bill.get("number"),
                            "congress": bill.get("congress"),
                            "introduced_date": bill.get("introducedDate"),
                            "sponsors": bill.get("sponsors", []),
                            "committees": bill.get("committees", [])
                        }
                    }
                    documents.append(doc)

            elif endpoint == "member":
                members = data.get("members", [])
                for member in members:
                    name = member.get("name", "")
                    if keywords and keywords.lower() not in name.lower():
                        continue

                    doc = {
                        "title": f"{name} ({member.get('state', '')}-{member.get('party', '')})",
                        "url": member.get("url", ""),
                        "snippet": f"Chamber: {member.get('chamber', '')} | District: {member.get('district', 'N/A')}",
                        "metadata": {
                            "member_id": member.get("bioguideId"),
                            "party": member.get("party"),
                            "state": member.get("state"),
                            "chamber": member.get("chamber")
                        }
                    }
                    documents.append(doc)

            elif endpoint == "hearing":
                hearings = data.get("hearings", [])
                for hearing in hearings:
                    # Hearing summary from list endpoint doesn't include title/description
                    # Build informative title from available metadata
                    chamber = hearing.get("chamber", "")
                    number = hearing.get("number", "")
                    jacket_number = hearing.get("jacketNumber", "")

                    doc = {
                        "title": f"Hearing {number} - {chamber} (Congress {congress_num})",
                        "url": hearing.get("url", ""),
                        "snippet": f"Chamber: {chamber} | Number: {number} | Jacket: {jacket_number} | Updated: {hearing.get('updateDate', 'N/A')}",
                        "date": hearing.get("updateDate"),
                        "metadata": {
                            "chamber": chamber,
                            "number": number,
                            "jacket_number": jacket_number,
                            "congress": hearing.get("congress"),
                            "update_date": hearing.get("updateDate")
                        }
                    }
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
            error_msg = f"HTTP {e.response.status_code}: {e.response.reason}"
            if e.response.status_code == 401:
                error_msg = "Invalid API key. Get one at: https://api.congress.gov/sign-up/"
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded (5000/hour). Wait before retrying."

            return QueryResult(
                success=False,
                source="Congress.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=error_msg
            )

        except Exception as e:
            return QueryResult(
                success=False,
                source="Congress.gov",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Congress.gov API error: {str(e)}"
            )
