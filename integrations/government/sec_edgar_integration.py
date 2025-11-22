#!/usr/bin/env python3
"""
SEC EDGAR database integration.

Provides access to U.S. Securities and Exchange Commission EDGAR database
including corporate filings, financial statements, insider trading reports,
and company information.
"""

import json
from typing import Dict, Optional, List
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


class SECEdgarIntegration(DatabaseIntegration):
    """
    Integration for SEC EDGAR - U.S. Securities and Exchange Commission filings.

    SEC EDGAR is the Electronic Data Gathering, Analysis, and Retrieval system
    used by companies and others to submit filings to the U.S. SEC.

    API Features:
    - NO API key required (public data)
    - Requires User-Agent header with email
    - Company submissions (filing history)
    - XBRL financial data (structured financials)
    - Full-text search across filings
    - Company lookup by name or CIK

    Rate Limits:
    - 10 requests per second (enforced by SEC)
    - No daily limit

    API Documentation:
    - https://www.sec.gov/edgar/sec-api-documentation
    - https://www.sec.gov/os/accessing-edgar-data
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="SEC EDGAR",
            id="sec_edgar",
            category=DatabaseCategory.GOV_GENERAL,  # SEC is a government database
            requires_api_key=False,  # No API key, just User-Agent header
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.0,      # seconds (SEC APIs are fast)
            rate_limit_daily=None,          # No daily limit, just 10/sec
            description="SEC corporate filings, financial statements, insider trading, and company information"
        )

    def _get_user_agent(self) -> str:
        """
        Get User-Agent header with email from config.

        Returns:
            User-Agent string required by SEC
        """
        db_config = config.get_database_config("sec_edgar")
        user_email = db_config.get("user_email", "")

        if not user_email:
            raise ValueError(
                "SEC EDGAR requires user email in User-Agent header. "
                "Set SEC_EDGAR_USER_EMAIL in .env file."
            )

        return f"SigInt Platform {user_email}"

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for SEC EDGAR.

        Uses LLM to determine if SEC EDGAR might have relevant information
        for the research question, considering EDGAR's strengths and limitations.

        Args:
            research_question: The user's research question

        Returns:
            True if relevant, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv

        load_dotenv()

        prompt = f"""Is SEC EDGAR relevant for researching this question?

RESEARCH QUESTION:
{research_question}

SEC EDGAR CHARACTERISTICS:
Strengths:
- Corporate filings (10-K annual reports, 10-Q quarterly reports, 8-K current reports)
- Financial statements and data (revenue, assets, liabilities via XBRL)
- Insider trading reports (Form 3, 4, 5)
- Proxy statements (executive compensation, board composition)
- Merger and acquisition filings
- IPO documents (S-1 registration statements)
- Company ownership and structure
- Historical filings back to 1994

Limitations:
- Only covers publicly-traded companies and entities required to file with SEC
- Does not include private companies (unless recently went public)
- No government contract details (use SAM.gov for that)
- No job postings (use USAJobs/ClearanceJobs for that)
- Financial data only (not operational/product details unless disclosed)

DECISION CRITERIA:
- Is relevant: If seeking corporate financial data, SEC filings, insider trading, or public company information
- NOT relevant: If ONLY seeking operational details, private companies, government contracts, or employment data

Return JSON:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why SEC EDGAR is/isn't relevant"
}}"""

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default to True on parsing failure

        except Exception as e:
            # On error, default to True (let query generation handle filtering)
            print(f"[WARN] SEC EDGAR relevance check failed: {e}, defaulting to True")
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate SEC EDGAR query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate search parameters for SEC EDGAR APIs.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "query_type": "company_filings",
                "company_name": "Apple Inc",
                "form_types": ["10-K", "10-Q"],
                "limit": 20
            }
        """

        prompt = render_prompt(
            "integrations/sec_edgar_query.j2",
            research_question=research_question
        )

        schema = {
            "name": "sec_edgar_query",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {
                        "type": "boolean",
                        "description": "Is this question relevant for SEC EDGAR?"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why is/isn't this relevant for SEC EDGAR?"
                    },
                    "query_type": {
                        "type": "string",
                        "description": "Type of search to perform",
                        "enum": ["company_filings", "company_search", "form_search"]
                    },
                    "company_name": {
                        "type": ["string", "null"],
                        "description": "Company name to search for (if applicable)"
                    },
                    "form_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "SEC form types to filter (e.g., 10-K, 10-Q, 8-K, 4)"
                    },
                    "keywords": {
                        "type": ["string", "null"],
                        "description": "Keywords to search for in filings (if applicable)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to retrieve (1-100)"
                    }
                },
                "required": ["relevant", "reasoning", "query_type", "form_types", "limit", "company_name", "keywords"],
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
            "query_type": result.get("query_type", "company_filings"),
            "company_name": result.get("company_name"),
            "form_types": result.get("form_types", []),
            "keywords": result.get("keywords"),
            "limit": min(result.get("limit", 20), 100)  # Cap at 100
        }

    async def _search_company_cik(self, company_name: str) -> Optional[str]:
        """
        Look up CIK (Central Index Key) by company name.

        Args:
            company_name: Company name to search

        Returns:
            CIK number (10 digits with leading zeros), or None if not found
        """
        try:
            user_agent = self._get_user_agent()

            # Use company_tickers.json endpoint (fast CIK lookup)
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers={"User-Agent": user_agent},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            # Search for company name (case-insensitive)
            company_lower = company_name.lower()
            for entry in data.values():
                title = entry.get("title", "").lower()
                if company_lower in title or title in company_lower:
                    cik = str(entry.get("cik_str")).zfill(10)  # Pad to 10 digits
                    return cik

            return None

        except Exception as e:
            print(f"[WARN] CIK lookup failed for '{company_name}': {e}")
            return None

    async def execute_search(
        self,
        params: Dict,
        api_key: Optional[str],
        limit: int = 20
    ) -> QueryResult:
        """
        Execute SEC EDGAR search via public APIs.

        Args:
            params: Query parameters from generate_query()
            api_key: Not used (SEC EDGAR doesn't require API key)
            limit: Maximum results to return

        Returns:
            QueryResult with filings/documents found
        """
        query_type = params.get("query_type", "company_filings")
        company_name = params.get("company_name")
        form_types = params.get("form_types", [])
        keywords = params.get("keywords")
        limit = min(params.get("limit", 20), limit)

        try:
            user_agent = self._get_user_agent()
            headers = {"User-Agent": user_agent}

            # Step 1: Get CIK if company name provided
            cik = None
            if company_name:
                cik = await self._search_company_cik(company_name)
                if not cik:
                    return QueryResult(
                        success=False,
                        source="SEC EDGAR",
                        total=0,
                        results=[],
                        query_params=params,
                        error=f"Company '{company_name}' not found in SEC database"
                    )

            # Step 2: Get company filings
            if query_type == "company_filings" and cik:
                # Use submissions API: https://data.sec.gov/submissions/CIK{cik}.json
                response = requests.get(
                    f"https://data.sec.gov/submissions/CIK{cik}.json",
                    headers=headers,
                    timeout=15
                )

                response.raise_for_status()
                data = response.json()

                # Extract filings
                filings = data.get("filings", {}).get("recent", {})

                # Get filing arrays
                accession_numbers = filings.get("accessionNumber", [])
                filing_dates = filings.get("filingDate", [])
                report_dates = filings.get("reportDate", [])
                primary_documents = filings.get("primaryDocument", [])
                forms = filings.get("form", [])

                documents = []

                for i in range(min(len(forms), limit)):
                    form = forms[i]

                    # Filter by form type if specified
                    if form_types and form not in form_types:
                        continue

                    accession = accession_numbers[i] if i < len(accession_numbers) else ""
                    filing_date = filing_dates[i] if i < len(filing_dates) else ""
                    report_date = report_dates[i] if i < len(report_dates) else ""
                    primary_doc = primary_documents[i] if i < len(primary_documents) else ""

                    # Build document URL
                    accession_clean = accession.replace("-", "")
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_doc}"

                    # Build filing viewer URL
                    filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=exclude&count=100"

                    doc = {
                        "title": f"{form} Filing - {data.get('name', company_name)} ({filing_date})",
                        "url": doc_url,
                        "snippet": f"Report Date: {report_date} | Accession: {accession}",
                        "date": filing_date,
                        "metadata": {
                            "form_type": form,
                            "filing_date": filing_date,
                            "report_date": report_date,
                            "accession_number": accession,
                            "cik": cik,
                            "company_name": data.get("name"),
                            "ticker": data.get("tickers", [None])[0] if data.get("tickers") else None,
                            "exchange": data.get("exchanges", [None])[0] if data.get("exchanges") else None,
                            "filing_viewer_url": filing_url
                        }
                    }
                    documents.append(doc)

                    if len(documents) >= limit:
                        break

                return QueryResult(
                    success=True,
                    source="SEC EDGAR",
                    total=len(documents),
                    results=documents,
                    query_params=params,
                    response_time_ms=int(response.elapsed.total_seconds() * 1000)
                )

            else:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=params,
                    error=f"Query type '{query_type}' not yet implemented or missing company_name"
                )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=params,
                    error="SEC EDGAR rate limit exceeded (10 requests/second). Please wait and retry."
                )
            else:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=params,
                    error=f"SEC EDGAR API error: {str(e)}"
                )

        except Exception as e:
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params=params,
                error=f"SEC EDGAR search failed: {str(e)}"
            )
