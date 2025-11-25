#!/usr/bin/env python3
"""
SEC EDGAR document parsing utilities.

Functions for fetching and extracting relevant content from SEC filings.
"""

import re
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_document_content(
    doc_url: str,
    form_type: str,
    user_agent: str
) -> Optional[str]:
    """
    Fetch and extract relevant content from SEC document.

    Args:
        doc_url: URL to SEC document (HTML format)
        form_type: Type of form (10-K, 10-Q, etc.)
        user_agent: User-Agent header for SEC compliance

    Returns:
        Extracted text content or None if fetch fails
    """
    try:
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
        logger.error(f"Failed to fetch document content from {doc_url}: {e}", exc_info=True)
        print(f"[WARN] Failed to fetch document content from {doc_url}: {e}")
        return None


def extract_relevant_sections(
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
        logger.error(f"Section extraction failed: {e}", exc_info=True)
        print(f"[WARN] Section extraction failed: {e}")
        return None
