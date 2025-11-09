#!/usr/bin/env python3
"""
Fixed Playwright-based scraper for ClearanceJobs.

The previous version filled the search input but didn't properly submit the search.
This version clicks the Search button after filling the input.
"""

import asyncio
from typing import Dict, Optional


async def search_clearancejobs(
    keywords: str,
    limit: int = 10,
    headless: bool = True
) -> Dict:
    """
    Search ClearanceJobs using Playwright to interact with the website.

    Args:
        keywords: Search keywords (job title/description)
        limit: Maximum number of results to return
        headless: Run browser in headless mode (default: True)

    Returns:
        Dict with:
            - success: bool
            - total: int (total results available)
            - jobs: List[Dict] (job listings)
            - error: Optional[str]
    """

    try:
        # Import playwright only when needed (lazy import)
        try:
            from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
        except ImportError:
            return {
                "success": False,
                "total": 0,
                "jobs": [],
                "error": "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            }

        async with async_playwright() as p:
            # Launch browser with anti-bot measures
            browser = await p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            # Step 1: Navigate to ClearanceJobs with increased timeout and wait for DOM
            await page.goto('https://www.clearancejobs.com/jobs',
                          timeout=60000,
                          wait_until='domcontentloaded')

            # Step 2: Fill search input
            await page.fill(
                'input[placeholder*="Search by keywords"]',
                keywords
            )

            # Step 3: Trigger Vue.js events to enable search button
            await page.evaluate("""
                () => {
                    const input = document.querySelector('input[placeholder*="Search by keywords"]');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                }
            """)

            # Give Vue.js a moment to process the events and enable button
            await asyncio.sleep(0.5)

            # Step 4: Click the Search button instead of pressing Enter
            # The button text is "Search" and it's a button element
            try:
                await page.click('button:has-text("Search")', timeout=5000)
            except PlaywrightTimeout:
                # If button didn't enable, try submitting the form directly
                await page.evaluate('document.querySelector("form").submit()')

            # Step 5: Wait for navigation/results to load
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except PlaywrightTimeout:
                pass  # Continue even if network doesn't idle

            # Check if URL changed (search was submitted)
            final_url = page.url
            if 'keywords' not in final_url and final_url == 'https://www.clearancejobs.com/jobs':
                # Search wasn't submitted - return error
                await browser.close()
                return {
                    "success": False,
                    "total": 0,
                    "jobs": [],
                    "error": f"Search not submitted - URL didn't change. Keywords: '{keywords}'"
                }

            # Step 6: Wait for results to load
            try:
                await page.wait_for_selector('.job-search-list-item-desktop', timeout=10000)
            except PlaywrightTimeout:
                # No results found
                await browser.close()
                return {
                    "success": True,
                    "total": 0,
                    "jobs": [],
                    "error": None
                }

            # Step 7: Extract job data
            result = await page.evaluate("""
                () => {
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
                }
            """)

            # Close browser
            await browser.close()

            return {
                "success": True,
                "total": result.get("total", 0),
                "jobs": result.get("jobs", [])[:limit],
                "error": None
            }

    except Exception as e:
        return {
            "success": False,
            "total": 0,
            "jobs": [],
            "error": str(e)
        }


# Example usage
async def main():
    """Test the fixed Playwright scraper."""
    print("Testing FIXED ClearanceJobs Playwright scraper...")

    # Test with specific keyword that should return fewer results
    result = await search_clearancejobs("Kubernetes", limit=5, headless=True)

    if result["success"]:
        print(f"✓ Found {result['total']} total results")
        print(f"✓ Returning {len(result['jobs'])} jobs\n")

        for i, job in enumerate(result['jobs'][:3], 1):
            print(f"{i}. {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   Clearance: {job['clearance']}")
            print(f"   Updated: {job['updated']}\n")
    else:
        print(f"✗ Search failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
