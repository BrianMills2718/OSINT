#!/usr/bin/env python3
"""
ClearanceJobs HTTP-based integration.

Uses direct HTTP requests instead of Playwright for 10x better performance.
Server-side rendered pages allow simple BeautifulSoup parsing.
"""

import re
import time
from typing import Dict
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


async def search_clearancejobs(
    keywords: str,
    limit: int = 10,
    headless: bool = True  # Unused, kept for compatibility
) -> Dict:
    """
    Search ClearanceJobs using HTTP requests (no browser needed).

    Args:
        keywords: Search keywords (job title/description)
        limit: Maximum number of results to return
        headless: Unused (compatibility with Playwright version)

    Returns:
        Dict with:
            - success: bool
            - total: int (total results available, 0 if no matches)
            - jobs: List[Dict] (job listings)
            - error: Optional[str]
    """

    try:
        # Build search URL with encoded keywords
        encoded_keywords = quote(keywords) if keywords else ""
        url = f'https://www.clearancejobs.com/jobs?keywords={encoded_keywords}'

        # Make HTTP request
        start_time = time.time()
        response = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            timeout=15
        )

        if response.status_code != 200:
            return {
                "success": False,
                "total": 0,
                "jobs": [],
                "error": f"HTTP {response.status_code}"
            }

        # Check for "No results found" message
        # ClearanceJobs shows suggested jobs even when query has no matches
        # We return 0 results in this case (not the suggested jobs)
        if 'No jobs found' in response.text or 'no results found' in response.text.lower():
            return {
                "success": True,
                "total": 0,
                "jobs": [],
                "error": None
            }

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract total count from "Viewing 1-20 of 1,234" text
        total = 0
        match = re.search(r'Viewing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)', response.text)
        if match:
            total = int(match.group(1).replace(',', ''))

        # Extract job cards
        job_cards = soup.select('.job-search-list-item-desktop')

        if not job_cards:
            # No job cards found in HTML
            return {
                "success": True,
                "total": 0,
                "jobs": [],
                "error": None
            }

        # Parse job data
        jobs = []
        for card in job_cards[:limit]:
            # Title and URL
            title_elem = card.select_one('.job-search-list-item-desktop__job-name')
            title = title_elem.text.strip() if title_elem else 'Unknown Title'
            job_url = title_elem.get('href', '') if title_elem else ''

            # Ensure absolute URL
            if job_url and job_url.startswith('/'):
                job_url = f'https://www.clearancejobs.com{job_url}'

            # Company
            company_elem = card.select_one('.job-search-list-item-desktop__company-name')
            company = company_elem.text.strip() if company_elem else ''

            # Location
            location_elem = card.select_one('.job-search-list-item-desktop__location')
            location = location_elem.text.strip() if location_elem else ''

            # Description (snippet)
            desc_elem = card.select_one('.job-search-list-item-desktop__description')
            description = desc_elem.text.strip() if desc_elem else ''

            # Footer contains clearance level and updated date
            footer_elem = card.select_one('.job-search-list-item-desktop__footer')
            footer_text = footer_elem.text if footer_elem else ''

            # Parse clearance level (check in priority order)
            clearance = ''
            if 'TS/SCI' in footer_text:
                clearance = 'TS/SCI'
            elif 'Top Secret' in footer_text:
                clearance = 'Top Secret'
            elif 'Secret' in footer_text and 'Top' not in footer_text:
                clearance = 'Secret'
            elif 'Public Trust' in footer_text:
                clearance = 'Public Trust'
            elif 'Confidential' in footer_text:
                clearance = 'Confidential'
            elif 'None' in footer_text:
                clearance = 'None'

            # Parse updated date
            updated = ''
            updated_match = re.search(r'Updated\s+(Today|Yesterday|\d+\s+days?\s+ago)', footer_text, re.IGNORECASE)
            if updated_match:
                updated = updated_match.group(0)

            jobs.append({
                'title': title,
                'url': job_url,
                'company': company,
                'location': location,
                'description': description,
                'snippet': description,  # Alias for compatibility
                'clearance': clearance,
                'clearance_level': clearance,  # Alias for compatibility
                'updated': updated,
                'source': 'ClearanceJobs'
            })

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "total": total,
            "jobs": jobs,
            "error": None,
            "response_time_ms": elapsed_ms
        }

    except requests.Timeout:
        return {
            "success": False,
            "total": 0,
            "jobs": [],
            "error": "Request timeout after 15 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "total": 0,
            "jobs": [],
            "error": f"Search failed: {str(e)}"
        }
