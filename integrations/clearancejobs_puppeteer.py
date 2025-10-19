#!/usr/bin/env python3
"""
Puppeteer-based scraper for ClearanceJobs.

The official ClearanceJobs Python library uses an undocumented API that
doesn't properly filter search results. This module uses Puppeteer MCP
to interact with the actual website search form.
"""

import json
from typing import List, Dict, Optional
import asyncio


class PuppeteerNotAvailableError(Exception):
    """Raised when Puppeteer MCP tools are not available."""
    pass


async def search_clearancejobs(
    keywords: str,
    limit: int = 10,
    puppeteer_navigate=None,
    puppeteer_fill=None,
    puppeteer_evaluate=None,
    puppeteer_click=None
) -> Dict:
    """
    Search ClearanceJobs using Puppeteer to interact with the website.

    Args:
        keywords: Search keywords (job title/description)
        limit: Maximum number of results to return
        puppeteer_navigate: MCP puppeteer_navigate function
        puppeteer_fill: MCP puppeteer_fill function
        puppeteer_evaluate: MCP puppeteer_evaluate function
        puppeteer_click: MCP puppeteer_click function

    Returns:
        Dict with:
            - success: bool
            - total: int (total results available)
            - jobs: List[Dict] (job listings)
            - error: Optional[str]

    Raises:
        PuppeteerNotAvailableError: If Puppeteer MCP tools not provided
    """

    if not all([puppeteer_navigate, puppeteer_fill, puppeteer_evaluate, puppeteer_click]):
        raise PuppeteerNotAvailableError(
            "Puppeteer MCP tools are required. "
            "Please ensure the Puppeteer MCP server is configured."
        )

    try:
        # Step 1: Navigate to ClearanceJobs
        await puppeteer_navigate(url="https://www.clearancejobs.com/jobs")

        # Step 2: Fill search input
        await puppeteer_fill(
            selector='input[placeholder*="Search by keywords"]',
            value=keywords
        )

        # Step 3: Trigger Vue.js events to enable search button
        await puppeteer_evaluate(script="""
            (() => {
                const input = document.querySelector('input[placeholder*="Search by keywords"]');
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                return { success: true };
            })()
        """)

        # Step 4: Click search button
        await puppeteer_click(selector="button.search-cta")

        # Step 5: Wait a moment for results to load
        await asyncio.sleep(2)

        # Step 6: Extract job data
        result = await puppeteer_evaluate(script="""
            (() => {
                // Dismiss cookie popup if present
                const rejectBtn = Array.from(document.querySelectorAll('button'))
                    .find(btn => btn.textContent.includes('Reject All'));
                if (rejectBtn) rejectBtn.click();

                // Get total count from the page header "Viewing 1-20 of 1,555"
                const viewingText = document.body.textContent.match(/Viewing\\s+\\d+\\s*-\\s*\\d+\\s+of\\s+([\\d,]+)/);
                const total = viewingText ? parseInt(viewingText[1].replace(/,/g, '')) : 0;

                // Get all job cards
                const jobCards = document.querySelectorAll('.job-search-list-item-desktop');

                // Extract data from each job
                const jobs = Array.from(jobCards).map(card => {
                    const titleLink = card.querySelector('.job-search-list-item-desktop__job-name');
                    const companyLink = card.querySelector('.job-search-list-item-desktop__company-name');
                    const location = card.querySelector('.job-search-list-item-desktop__location');
                    const description = card.querySelector('.job-search-list-item-desktop__description');

                    // Parse footer text for clearance and updated date
                    const footerText = card.querySelector('.job-search-list-item-desktop__footer')?.textContent || '';

                    // Extract clearance - check in priority order
                    let clearance = '';
                    if (footerText.includes('TS/SCI')) clearance = 'TS/SCI';
                    else if (footerText.includes('Top Secret')) clearance = 'Top Secret';
                    else if (footerText.includes('Secret') && !footerText.includes('Top')) clearance = 'Secret';
                    else if (footerText.includes('Public Trust')) clearance = 'Public Trust';
                    else if (footerText.includes('Confidential')) clearance = 'Confidential';
                    else if (footerText.includes('None')) clearance = 'None';

                    // Extract updated date
                    const updatedMatch = footerText.match(/Updated\\s+(Today|Yesterday|\\d+\\s+days?\\s+ago)/i);
                    const updated = updatedMatch ? updatedMatch[0] : '';

                    return {
                        title: titleLink?.textContent?.trim() || '',
                        url: titleLink?.href || '',
                        company: companyLink?.textContent?.trim() || '',
                        location: location?.textContent?.trim() || '',
                        clearance: clearance,
                        updated: updated,
                        description: description?.textContent?.trim() || ''
                    };
                });

                return {
                    total: total || jobs.length,
                    jobs: jobs
                };
            })()
        """)

        # Parse the result
        data = json.loads(result) if isinstance(result, str) else result

        return {
            "success": True,
            "total": data.get("total", 0),
            "jobs": data.get("jobs", [])[:limit],
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "total": 0,
            "jobs": [],
            "error": str(e)
        }
