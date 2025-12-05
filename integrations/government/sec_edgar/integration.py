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
import logging

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

# Import from sub-modules
from .constants import COMPANY_ALIASES, normalize_company_name
from .document_parser import fetch_document_content, extract_relevant_sections

# Set up logger for this module
logger = logging.getLogger(__name__)




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
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="SEC EDGAR",
            id="sec_edgar",
            category=DatabaseCategory.GOV_GENERAL,  # SEC is a government database
            requires_api_key=False,  # No API key, just User-Agent header
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.0,      # seconds (SEC APIs are fast)
            rate_limit_daily=None,          # No daily limit, just 10/sec
            description="SEC corporate filings including foreign subsidiary disclosures (Exhibit 21), financial statements, offshore entity structures, insider trading, and executive compensation. NOT for government contracts - use SAM.gov/USAspending for contracts.",

            # Query generation guidance
            query_strategies=['cik_lookup', 'ticker_lookup', 'company_name_search', 'form_type_filter'],
            characteristics={
                'supports_fallback': True,
                'search_strategies': [
                    {'method': 'cik', 'reliability': 'high', 'param': 'cik'},
                    {'method': 'ticker', 'reliability': 'high', 'param': 'ticker'},
                    {'method': 'name_exact', 'reliability': 'medium', 'param': 'company_name'},
                    {'method': 'name_fuzzy', 'reliability': 'low', 'param': 'company_name'},
                ],
                'structured_data': True,
                'rich_metadata': True,
                'date_filtering': True
            },
            typical_result_count=20,
            max_queries_recommended=5,

            # Rate Limit Recovery - SEC enforces 10 requests/second, short recovery
            rate_limit_recovery_seconds=30,  # Brief wait, then retry
            retry_on_rate_limit_within_session=True  # Worth retrying - short recovery
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
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt

        prompt = render_prompt(
            "integrations/sec_edgar_relevance.j2",
            research_question=research_question
        )

        from config_loader import config
        try:
            response = await acompletion(
                model=config.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)

        except Exception as e:
            logger.error(f"SEC EDGAR relevance check failed: {e}, defaulting to True", exc_info=True)
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
                        "enum": ["company_filings", "company_search"]
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name to search for (optional)"
                    },
                    "form_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "SEC form types to filter (e.g., 10-K, 10-Q, 8-K, 4)"
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Keywords to search for in filings (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to retrieve (1-100)"
                    }
                },
                "required": ["relevant", "reasoning", "query_type", "form_types", "limit"],
                "additionalProperties": False
            }
        }

        from config_loader import config
        response = await acompletion(
            model=config.default_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": schema}
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        # SEC EDGAR requires a company name - can't do generic keyword searches
        company_name = result.get("company_name")
        if not company_name:
            logger.debug("SEC EDGAR: No company name provided, returning not relevant")
            return None

        return {
            "query_type": result.get("query_type", "company_filings"),
            "company_name": company_name,
            "form_types": result.get("form_types", []),
            "keywords": result.get("keywords"),
            "limit": min(result.get("limit", 20), 100)  # Cap at 100
        }

    async def _search_company_cik(self, company_name: str) -> Optional[str]:
        """
        Look up CIK (Central Index Key) by company name with fuzzy matching and aliases.

        Uses multi-strategy approach:
        1. Exact match on normalized name
        2. Alias lookup for known companies
        3. Fuzzy partial matching

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

            # Normalize input company name
            normalized_input = normalize_company_name(company_name)

            # Strategy 1: Try exact match on normalized name
            for entry in data.values():
                title = entry.get("title", "")
                normalized_title = normalize_company_name(title)

                if normalized_input == normalized_title:
                    cik = str(entry.get("cik_str")).zfill(10)
                    print(f"[INFO] SEC EDGAR: Found exact match: '{company_name}' → '{title}' (CIK: {cik})")
                    return cik

            # Strategy 2: Try alias lookup for known companies
            if normalized_input in COMPANY_ALIASES:
                aliases = COMPANY_ALIASES[normalized_input]
                for alias in aliases:
                    for entry in data.values():
                        title = entry.get("title", "")
                        if alias.lower() in title.lower():
                            cik = str(entry.get("cik_str")).zfill(10)
                            print(f"[INFO] SEC EDGAR: Found via alias: '{company_name}' → '{title}' (alias: '{alias}', CIK: {cik})")
                            return cik

            # Strategy 3: Fuzzy partial matching (fallback)
            company_lower = company_name.lower()
            for entry in data.values():
                title = entry.get("title", "").lower()
                if company_lower in title or title in company_lower:
                    cik = str(entry.get("cik_str")).zfill(10)
                    print(f"[INFO] SEC EDGAR: Found via fuzzy match: '{company_name}' → '{title}' (CIK: {cik})")
                    return cik

            print(f"[INFO] SEC EDGAR: No match found for '{company_name}' (tried exact, alias, fuzzy)")
            return None

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return None instead of crashing
            logger.error(f"CIK lookup failed for '{company_name}': {e}", exc_info=True)
            print(f"[WARN] CIK lookup failed for '{company_name}': {e}")
            return None

    async def _fetch_document_content(self, doc_url: str, form_type: str) -> Optional[str]:
        """Fetch document content using imported utility."""
        return fetch_document_content(doc_url, form_type, self._get_user_agent())

    async def _extract_relevant_sections(
        self,
        content: str,
        form_type: str,
        keywords: Optional[str] = None
    ) -> Optional[str]:
        """Extract relevant sections using imported utility."""
        return extract_relevant_sections(content, form_type, keywords)

    async def _search_by_cik(self, cik: str) -> QueryResult:
        """
        Search SEC EDGAR by CIK (Central Index Key) directly.

        Args:
            cik: 10-digit CIK number

        Returns:
            QueryResult with filings found
        """
        try:
            # Ensure CIK is 10 digits with leading zeros
            cik_padded = str(cik).zfill(10)

            user_agent = self._get_user_agent()
            headers = {"User-Agent": user_agent}

            # Fetch company submissions
            response = requests.get(
                f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                headers=headers,
                timeout=15
            )

            response.raise_for_status()
            data = response.json()

            # Get recent filings
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])

            if not forms:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params={"cik": cik},
                    error=f"No filings found for CIK {cik}",
                http_code=None  # Non-HTTP error
                )

            # Build results using defensive builder (simplified for fallback)
            documents = []
            accession_numbers = filings.get("accessionNumber", [])
            filing_dates = filings.get("filingDate", [])
            company_name = SearchResultBuilder.safe_text(data.get("name"), default="Unknown")

            for i in range(min(10, len(forms))):  # Limit to 10 for fallback
                form_type = SearchResultBuilder.safe_text(forms[i])
                filing_date = filing_dates[i] if i < len(filing_dates) else ""
                accession = accession_numbers[i] if i < len(accession_numbers) else "N/A"

                # Three-tier model: preserve full content with build_with_raw()
                snippet_text = f"Accession: {accession}"
                doc = (SearchResultBuilder()
                    .title(f"{form_type} Filing - {company_name} ({filing_date})",
                           default="SEC Filing")
                    .url(f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}")
                    .snippet(snippet_text)
                    .raw_content(snippet_text)  # Full content
                    .date(filing_date)
                    .api_response(data)  # Preserve complete API response
                    .metadata({
                        "form_type": form_type,
                        "cik": cik_padded,
                        "company_name": data.get("name")
                    })
                    .build_with_raw())
                documents.append(doc)

            return QueryResult(
                success=True,
                source="SEC EDGAR",
                total=len(documents),
                results=documents,
                query_params={"cik": cik},
                response_time_ms=int(response.elapsed.total_seconds() * 1000)
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"SEC EDGAR CIK search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params={"cik": cik},
                error=f"CIK search failed: {str(e)}",
                http_code=None  # Non-HTTP error"
            )

    async def _search_by_ticker(self, ticker: str) -> QueryResult:
        """
        Search SEC EDGAR by stock ticker symbol.

        Args:
            ticker: Stock ticker (e.g., AAPL, MSFT)

        Returns:
            QueryResult with filings found
        """
        try:
            user_agent = self._get_user_agent()

            # Use company_tickers.json to find CIK from ticker
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers={"User-Agent": user_agent},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            # Find ticker match
            ticker_upper = ticker.upper()
            cik = None
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry.get("cik_str")).zfill(10)
                    break

            if not cik:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params={"ticker": ticker},
                    error=f"Ticker '{ticker}' not found",
                    http_code=None  # Not found, not HTTP
                )

            # Use CIK search
            return await self._search_by_cik(cik)

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"SEC EDGAR ticker search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params={"ticker": ticker},
                error=f"Ticker search failed: {str(e)}",
                http_code=None  # Non-HTTP error"
            )

    async def _search_by_name_exact(self, company_name: str) -> QueryResult:
        """
        Search SEC EDGAR by exact company name match.

        Args:
            company_name: Company name to search

        Returns:
            QueryResult with filings found
        """
        cik = await self._search_company_cik(company_name)
        if not cik:
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params={"company_name": company_name},
                error=f"Company '{company_name}' not found (exact match)",
                http_code=None  # Not found, not HTTP
            )

        return await self._search_by_cik(cik)

    async def _search_by_name_fuzzy(self, company_name: str) -> QueryResult:
        """
        Search SEC EDGAR by fuzzy company name match (partial matching).

        Args:
            company_name: Company name to search

        Returns:
            QueryResult with filings found
        """
        try:
            user_agent = self._get_user_agent()

            # Use company_tickers.json for fuzzy matching
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers={"User-Agent": user_agent},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            # Fuzzy search: find any company with partial name match
            company_lower = company_name.lower()
            matches = []

            for entry in data.values():
                title = entry.get("title", "").lower()
                # Check if ANY word from company_name is in title
                words = company_lower.split()
                if any(word in title for word in words if len(word) > 2):  # Skip short words
                    matches.append((entry.get("cik_str"), entry.get("title")))

            if not matches:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params={"company_name": company_name},
                    error=f"No fuzzy matches found for '{company_name}'",
                    http_code=None  # Not found, not HTTP
                )

            # Use first match
            cik = str(matches[0][0]).zfill(10)
            return await self._search_by_cik(cik)

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"SEC EDGAR fuzzy search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params={"company_name": company_name},
                error=f"Fuzzy search failed: {str(e)}",
                http_code=None  # Non-HTTP error"
            )

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 20
    ) -> QueryResult:
        """
        Execute SEC EDGAR search via public APIs with intelligent fallback.

        Uses generic fallback pattern: tries search strategies in order of
        reliability (CIK → ticker → name exact → name fuzzy) until one succeeds.

        Args:
            params: Query parameters from generate_query()
            api_key: Not used (SEC EDGAR doesn't require API key)
            limit: Maximum results to return

        Returns:
            QueryResult with filings/documents found
        """
        from core.search_fallback import execute_with_fallback

        # Use self.metadata (single source of truth)
        metadata = self.metadata

        # Check if fallback is supported (configured in DatabaseMetadata.characteristics)
        if metadata and metadata.characteristics.get('supports_fallback'):
            # Define search methods for fallback
            search_methods = {
                'cik': self._search_by_cik,
                'ticker': self._search_by_ticker,
                'name_exact': self._search_by_name_exact,
                'name_fuzzy': self._search_by_name_fuzzy,
            }

            return await execute_with_fallback(
                "SEC EDGAR",
                query_params,
                search_methods,
                metadata
            )

        # Fallback to old logic if metadata doesn't support fallback
        query_type = query_params.get("query_type", "company_filings")
        company_name = query_params.get("company_name")
        form_types = query_params.get("form_types", [])
        keywords = query_params.get("keywords")
        limit = min(query_params.get("limit", 20), limit)

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
                        query_params=query_params,
                        error=f"Company '{company_name}' not found in SEC database",
                        http_code=None  # Not found, not HTTP
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

                # Fetch content for first 3 documents (balance depth vs speed)
                docs_to_extract = min(3, limit)

                # When filtering by form type, iterate through more forms to find matches
                max_iterations = min(len(forms), limit * 10 if form_types else limit)

                for i in range(max_iterations):
                    if i >= len(forms):
                        break

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

                    # Extract content for first few documents
                    snippet = f"Report Date: {report_date} | Accession: {accession}"
                    extracted_content = None

                    if len(documents) < docs_to_extract:
                        print(f"[INFO] Fetching content from {form} filing ({filing_date})...")
                        content = await self._fetch_document_content(doc_url, form)
                        if content:
                            extracted_content = await self._extract_relevant_sections(
                                content,
                                form,
                                keywords
                            )
                            if extracted_content:
                                # Update snippet with preview of extracted content
                                preview = extracted_content[:300].replace('\n', ' ')
                                snippet = f"{preview}... [Full extraction in metadata]"

                    sec_company_name = SearchResultBuilder.safe_text(data.get("name"), default=company_name)
                    tickers = data.get("tickers", [])
                    exchanges = data.get("exchanges", [])

                    doc = (SearchResultBuilder()
                        .title(f"{form} Filing - {sec_company_name} ({filing_date})",
                               default="SEC Filing")
                        .url(doc_url)
                        .snippet(snippet)
                        .raw_content(extracted_content if extracted_content else snippet)  # Full content
                        .date(filing_date)
                        .api_response(data)  # Preserve complete API response
                        .metadata({
                            "form_type": form,
                            "filing_date": filing_date,
                            "report_date": report_date,
                            "accession_number": accession,
                            "cik": cik,
                            "company_name": data.get("name"),
                            "ticker": tickers[0] if tickers else None,
                            "exchange": exchanges[0] if exchanges else None,
                            "filing_viewer_url": filing_url,
                            "extracted_content": extracted_content
                        })
                        .build_with_raw())
                    documents.append(doc)

                    if len(documents) >= limit:
                        break

                return QueryResult(
                    success=True,
                    source="SEC EDGAR",
                    total=len(documents),
                    results=documents,
                    query_params=query_params,
                    response_time_ms=int(response.elapsed.total_seconds() * 1000)
                )

            else:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"Query type '{query_type}' not yet implemented or missing company_name",
                    http_code=None  # Validation error, not HTTP
                )

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            # HTTP errors from SEC EDGAR API
            logger.error(f"SEC EDGAR HTTP error: {e}", exc_info=True)
            if e.response.status_code == 429:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="SEC EDGAR rate limit exceeded (10 requests/second). Please wait and retry.",
                    http_code=status_code
                )
            else:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"SEC EDGAR API error: {str(e)}",
                    http_code=status_code
                )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            logger.error(f"SEC EDGAR search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="SEC EDGAR",
                total=0,
                results=[],
                query_params=query_params,
                error=f"SEC EDGAR search failed: {str(e)}",
                http_code=None  # Non-HTTP error"
            )
