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
import re
from bs4 import BeautifulSoup
import logging
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

# Set up logger for this module
logger = logging.getLogger(__name__)


# Common company name aliases and variations for defense contractors
# Maps: normalized search name → list of possible SEC database variations
COMPANY_ALIASES = {
    # Defense contractors
    "northrop grumman": ["NORTHROP GRUMMAN", "NORTHROP GRUMMAN CORP"],
    "raytheon": ["RAYTHEON", "RAYTHEON TECHNOLOGIES", "RTX CORP", "RAYTHEON CO"],
    "lockheed martin": ["LOCKHEED MARTIN", "LOCKHEED MARTIN CORP"],
    "boeing": ["BOEING CO", "BOEING"],
    "general dynamics": ["GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"],
    "l3harris": ["L3HARRIS", "L3HARRIS TECHNOLOGIES", "HARRIS CORP"],
    "bae systems": ["BAE SYSTEMS", "BAE SYSTEMS PLC"],
    "huntington ingalls": ["HUNTINGTON INGALLS", "HUNTINGTON INGALLS INDUSTRIES"],
    "leidos": ["LEIDOS", "LEIDOS HOLDINGS"],
    "booz allen": ["BOOZ ALLEN", "BOOZ ALLEN HAMILTON"],
    "caci": ["CACI", "CACI INTERNATIONAL"],
    "saic": ["SAIC", "SCIENCE APPLICATIONS INTERNATIONAL"],
    "textron": ["TEXTRON", "TEXTRON INC"],
    "kratos": ["KRATOS", "KRATOS DEFENSE"],
    "anduril": ["ANDURIL", "ANDURIL INDUSTRIES"],
    "palantir": ["PALANTIR", "PALANTIR TECHNOLOGIES"],
    # Tech companies (common in research queries)
    "microsoft": ["MICROSOFT", "MICROSOFT CORP"],
    "amazon": ["AMAZON", "AMAZON COM INC"],
    "google": ["ALPHABET", "GOOGLE", "ALPHABET INC"],
    "meta": ["META", "META PLATFORMS", "FACEBOOK"],
    "apple": ["APPLE", "APPLE INC"],
}


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for matching.

    Strips common suffixes and standardizes format.

    Args:
        name: Raw company name

    Returns:
        Normalized name (lowercase, no suffixes)
    """
    if not name:
        return ""

    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove common suffixes
    suffixes_to_remove = [
        " corporation",
        " corp",
        " incorporated",
        " inc",
        " company",
        " co",
        " llc",
        " ltd",
        " limited",
        " plc",
        " group",
        " holdings",
        " industries",
        " technologies",
        " systems",
        " solutions",
        ",",
        ".",
    ]

    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    return normalized


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
            description="SEC corporate filings including foreign subsidiary disclosures (Exhibit 21), financial statements, offshore entity structures, insider trading, and executive compensation. NOT for government contracts - use SAM.gov/USAspending for contracts."
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
            # Catch-all at integration boundary - acceptable to return default instead of crashing
            logger.error(f"SEC EDGAR relevance check failed: {e}, defaulting to True", exc_info=True)
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
        """
        Fetch and extract relevant content from SEC document.

        Args:
            doc_url: URL to SEC document (HTML format)
            form_type: Type of form (10-K, 10-Q, etc.)

        Returns:
            Extracted text content or None if fetch fails
        """
        try:
            user_agent = self._get_user_agent()
            response = requests.get(
                doc_url,
                headers={"User-Agent": user_agent},
                timeout=30  # Longer timeout for document downloads
            )

            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract text content
            # SEC documents are typically in <document> tags or standard HTML
            text_content = soup.get_text(separator='\n', strip=True)

            # Limit size (first 50KB of text to avoid overwhelming)
            if len(text_content) > 50000:
                text_content = text_content[:50000] + "\n\n[Content truncated - document exceeds 50KB]"

            return text_content

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return None instead of crashing
            logger.error(f"Failed to fetch document content from {doc_url}: {e}", exc_info=True)
            print(f"[WARN] Failed to fetch document content from {doc_url}: {e}")
            return None

    async def _extract_relevant_sections(
        self,
        content: str,
        form_type: str,
        keywords: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract relevant sections from SEC filing content using pattern matching.

        Args:
            content: Full document text
            form_type: Type of form (10-K, 10-Q, etc.)
            keywords: Optional keywords to search for (e.g., "offshore", "subsidiaries", "tax")

        Returns:
            Extracted relevant sections or None
        """
        if not content:
            return None

        try:
            extracted_sections = []

            # Common patterns for important sections
            section_patterns = {
                "subsidiaries": r"(?i)(exhibit\s+21|list\s+of\s+subsidiaries|subsidiaries\s+of|foreign\s+subsidiaries).*?(?=\n\s*\n|\nexhibit|\nitem\s+\d+|$)",
                "offshore": r"(?i)(offshore|tax\s+haven|foreign\s+jurisdiction|international\s+tax|transfer\s+pricing).*?(?:\n.*?){0,20}",
                "tax": r"(?i)(note\s+\d+.*?income\s+tax|provision\s+for\s+income\s+tax|tax\s+rate\s+reconciliation|deferred\s+tax).*?(?:\n.*?){0,30}",
                "segments": r"(?i)(note\s+\d+.*?segment|segment\s+information|geographic\s+information|foreign\s+operations).*?(?:\n.*?){0,30}",
            }

            # If keywords provided, focus on those patterns
            if keywords:
                keywords_lower = keywords.lower()
                for pattern_name, pattern in section_patterns.items():
                    if pattern_name in keywords_lower or any(kw in pattern_name for kw in keywords_lower.split()):
                        matches = re.finditer(pattern, content, re.DOTALL)
                        for match in matches:
                            section_text = match.group(0)
                            if len(section_text) > 200:  # Only include substantial sections
                                extracted_sections.append(f"--- {pattern_name.upper()} SECTION ---\n{section_text[:2000]}")

            # If no keyword matches or no keywords, try all patterns
            if not extracted_sections:
                for pattern_name, pattern in section_patterns.items():
                    matches = re.finditer(pattern, content, re.DOTALL)
                    for match in matches:
                        section_text = match.group(0)
                        if len(section_text) > 200:
                            extracted_sections.append(f"--- {pattern_name.upper()} SECTION ---\n{section_text[:2000]}")
                            if len(extracted_sections) >= 3:  # Limit to 3 sections
                                break
                    if len(extracted_sections) >= 3:
                        break

            if extracted_sections:
                return "\n\n".join(extracted_sections)

            # If no structured sections found, return first 3000 chars
            return content[:3000] + "\n\n[Note: No specific sections identified - showing document preview]"

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return None instead of crashing
            logger.error(f"Section extraction failed: {e}", exc_info=True)
            print(f"[WARN] Section extraction failed: {e}")
            return None

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
                    error=f"No filings found for CIK {cik}"
                )

            # Build results (simplified for fallback - full extraction done later)
            documents = []
            accession_numbers = filings.get("accessionNumber", [])
            filing_dates = filings.get("filingDate", [])

            for i in range(min(10, len(forms))):  # Limit to 10 for fallback
                doc = {
                    "title": f"{forms[i]} Filing - {data.get('name', 'Unknown')} ({filing_dates[i] if i < len(filing_dates) else ''})",
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}",
                    "snippet": f"Accession: {accession_numbers[i] if i < len(accession_numbers) else 'N/A'}",
                    "date": filing_dates[i] if i < len(filing_dates) else "",
                    "metadata": {
                        "form_type": forms[i],
                        "cik": cik_padded,
                        "company_name": data.get("name")
                    }
                }
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
                error=f"CIK search failed: {str(e)}"
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
                    error=f"Ticker '{ticker}' not found"
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
                error=f"Ticker search failed: {str(e)}"
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
                error=f"Company '{company_name}' not found (exact match)"
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
                    error=f"No fuzzy matches found for '{company_name}'"
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
                error=f"Fuzzy search failed: {str(e)}"
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
        from integrations.source_metadata import get_source_metadata

        metadata = get_source_metadata("SEC EDGAR")

        # Check if fallback is supported
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

                    doc = {
                        "title": f"{form} Filing - {data.get('name', company_name)} ({filing_date})",
                        "url": doc_url,
                        "snippet": snippet,
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
                            "filing_viewer_url": filing_url,
                            "extracted_content": extracted_content  # NEW: Include extracted sections
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
                    error=f"Query type '{query_type}' not yet implemented or missing company_name"
                )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="SEC EDGAR rate limit exceeded (10 requests/second). Please wait and retry."
                )
            else:
                return QueryResult(
                    success=False,
                    source="SEC EDGAR",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"SEC EDGAR API error: {str(e)}"
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
                error=f"SEC EDGAR search failed: {str(e)}"
            )
