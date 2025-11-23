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
    async def create_stealth_page(browser, extra_stealth: bool = False):
        """
        Create a stealth-patched page from browser.

        Applies playwright-stealth patches to evade bot detection by:
        - Removing webdriver property
        - Spoofing navigator properties
        - Fixing Chrome runtime
        - Patching permissions API

        Args:
            browser: Playwright browser instance
            extra_stealth: Enable extra anti-detection measures for aggressive bot detection (Akamai, etc.)

        Returns:
            Page with stealth patches applied

        Raises:
            ImportError: If playwright-stealth not installed

        Example:
            >>> browser = await create_playwright_browser()
            >>> page = await create_stealth_page(browser, extra_stealth=True)
            >>> await page.goto('https://cia.gov/readingroom')
        """
        try:
            from playwright_stealth import Stealth
        except ImportError:
            raise ImportError(
                "playwright-stealth required for bot detection bypass.\n"
                "Install: pip install playwright-stealth"
            )

        import random

        # Create new page with realistic user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        ]

        page = await browser.new_page(user_agent=random.choice(user_agents))

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
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })

        # Set realistic viewport (randomize slightly)
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 2560, "height": 1440}
        ]
        await page.set_viewport_size(random.choice(viewports))

        # Extra stealth for aggressive bot detection (Akamai, Cloudflare)
        if extra_stealth:
            # Remove navigator.webdriver (backup if stealth plugin fails)
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Spoof plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Spoof languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Randomize canvas fingerprint
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    if (type === 'image/png' && this.width === 16 && this.height === 16) {
                        return originalToDataURL.apply(this, arguments);
                    }
                    const shift = Math.floor(Math.random() * 10) - 5;
                    const context = this.getContext('2d');
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + shift));
                    }
                    context.putImageData(imageData, 0, 0);
                    return originalToDataURL.apply(this, arguments);
                };

                // Spoof WebGL vendor
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
            """)

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
