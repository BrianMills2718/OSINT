#!/usr/bin/env python3
"""
Stealth browser factory for bypassing bot detection.

Provides pre-configured Playwright and Selenium browsers with anti-detection
patches. Use this for integrations that face Akamai, Cloudflare, or similar
bot protection systems.

Examples:
    >>> # Playwright (async)
    >>> browser = await StealthBrowser.create_playwright_browser()
    >>> page = await StealthBrowser.create_stealth_page(browser)
    >>> await page.goto('https://protected-site.gov')

    >>> # Selenium (sync)
    >>> driver = StealthBrowser.create_selenium_browser()
    >>> driver.get('https://protected-site.gov')
"""

from typing import Optional
import asyncio


class StealthBrowser:
    """
    Factory for creating anti-detection browsers.

    Supports both Playwright and Selenium with stealth configurations
    to bypass Akamai Bot Manager, Cloudflare, and similar protections.
    """

    @staticmethod
    async def create_playwright_browser(headless: bool = True):
        """
        Create Playwright browser with anti-detection configuration.

        Args:
            headless: Run in headless mode (default True)

        Returns:
            Browser instance ready for stealth page creation

        Raises:
            ImportError: If playwright-stealth not installed

        Example:
            >>> browser = await StealthBrowser.create_playwright_browser()
            >>> page = await StealthBrowser.create_stealth_page(browser)
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright required for browser automation.\n"
                "Install: pip install playwright && playwright install chromium"
            )

        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-dev-shm-usage',  # Fix memory issues
                '--no-sandbox',  # Required for some environments
                '--disable-web-security',  # Avoid CORS issues
                '--disable-features=IsolateOrigins,site-per-process'  # Performance
            ]
        )
        return browser

    @staticmethod
    async def create_stealth_page(browser):
        """
        Create a stealth-patched page from browser.

        Applies playwright-stealth patches to evade bot detection by:
        - Removing webdriver property
        - Spoofing navigator properties
        - Fixing Chrome runtime
        - Patching permissions API

        Args:
            browser: Playwright browser instance

        Returns:
            Page with stealth patches applied

        Raises:
            ImportError: If playwright-stealth not installed

        Example:
            >>> browser = await create_playwright_browser()
            >>> page = await create_stealth_page(browser)
            >>> await page.goto('https://cia.gov/readingroom')
        """
        try:
            from playwright_stealth import Stealth
        except ImportError:
            raise ImportError(
                "playwright-stealth required for bot detection bypass.\n"
                "Install: pip install playwright-stealth"
            )

        page = await browser.new_page()

        # Apply stealth patches using playwright-stealth 2.0+ API
        stealth_config = Stealth()
        await stealth_config.apply_stealth_async(page)

        # Additional headers to mimic real browser
        await page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })

        # Set realistic viewport
        await page.set_viewport_size({"width": 1920, "height": 1080})

        return page

    @staticmethod
    def create_selenium_browser(headless: bool = False):
        """
        Create Selenium browser with undetected-chromedriver.

        Uses undetected-chromedriver which patches Selenium to avoid detection.
        Note: Headless mode is often detected, so default is visible browser.

        Args:
            headless: Run in headless mode (default False - headless often detected)

        Returns:
            WebDriver instance configured to evade detection

        Raises:
            ImportError: If undetected-chromedriver not installed

        Example:
            >>> driver = StealthBrowser.create_selenium_browser()
            >>> driver.get('https://cia.gov/readingroom')
            >>> # ... scrape content ...
            >>> driver.quit()
        """
        try:
            import undetected_chromedriver as uc
        except ImportError:
            raise ImportError(
                "undetected-chromedriver required for Selenium bot detection bypass.\n"
                "Install: pip install undetected-chromedriver"
            )

        import os
        import platform

        options = uc.ChromeOptions()

        # Headless mode (use with caution - often detected)
        if headless:
            options.add_argument('--headless=new')

        # Anti-detection arguments
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-web-security')

        # WSL2/Linux: Detect and set Chrome binary path
        chrome_binary = None
        if platform.system() == 'Linux':
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/snap/bin/chromium'
            ]

            # Try system Chrome/Chromium first
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break

            # Fallback: Use Playwright's Chromium if available
            if not chrome_binary:
                try:
                    from playwright.sync_api import sync_playwright
                    p = sync_playwright().start()
                    playwright_chromium = p.chromium.executable_path
                    p.stop()
                    if os.path.exists(playwright_chromium):
                        chrome_binary = playwright_chromium
                except Exception:
                    pass

        # Create undetected Chrome instance
        # Use browser_executable_path parameter for undetected-chromedriver
        if chrome_binary:
            driver = uc.Chrome(options=options, browser_executable_path=chrome_binary)
        else:
            driver = uc.Chrome(options=options)

        return driver


# Convenience async context manager for Playwright
class StealthPlaywright:
    """
    Async context manager for stealth Playwright sessions.

    Usage:
        >>> async with StealthPlaywright() as page:
        ...     await page.goto('https://protected-site.gov')
        ...     content = await page.content()
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None

    async def __aenter__(self):
        self.browser = await StealthBrowser.create_playwright_browser(self.headless)
        self.page = await StealthBrowser.create_stealth_page(self.browser)
        return self.page

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
