#!/usr/bin/env python3
"""
Test FBI Vault with playwright-stealth to bypass Cloudflare protection.
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def test_fbi_vault_stealth():
    """Test FBI Vault search with playwright-stealth."""
    print("=" * 80)
    print("FBI VAULT - PLAYWRIGHT-STEALTH BYPASS TEST")
    print("=" * 80)

    # Test URL - FBI Vault search for "terrorism"
    test_url = "https://vault.fbi.gov/search?SearchableText=terrorism"

    # Initialize stealth configuration
    stealth_config = Stealth()

    async with async_playwright() as p:
        print("\nLaunching browser with stealth mode...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Apply stealth mode
        print("Applying playwright-stealth patches...")
        await stealth_config.apply_stealth_async(page)

        print(f"\nNavigating to: {test_url}")
        try:
            response = await page.goto(test_url, wait_until="networkidle", timeout=30000)

            print(f"\nHTTP Status: {response.status}")
            print(f"Page URL: {page.url}")
            print(f"Page title: {await page.title()}")

            # Check for Cloudflare challenge markers
            content = await page.content()

            # Common Cloudflare markers
            cloudflare_markers = [
                "challenge-platform",
                "Just a moment",
                "Checking your browser",
                "cf-browser-verification",
                "ray id"
            ]

            detected_markers = [marker for marker in cloudflare_markers if marker.lower() in content.lower()]

            if detected_markers:
                print(f"\n❌ CLOUDFLARE PROTECTION ACTIVE")
                print(f"   Detected markers: {detected_markers}")
                print("\n   playwright-stealth did NOT bypass Cloudflare")
            else:
                print(f"\n✅ CLOUDFLARE BYPASSED!")

                # Try to extract search results
                # FBI Vault uses specific HTML structure
                results = await page.query_selector_all(".searchResults .tileItem")
                print(f"   Found {len(results)} search results")

                if results:
                    print("\n   First result:")
                    first = results[0]
                    title_elem = await first.query_selector(".tileHeadline a")
                    if title_elem:
                        title = await title_elem.inner_text()
                        href = await title_elem.get_attribute("href")
                        print(f"     Title: {title}")
                        print(f"     URL: {href}")

                    print("\n✅ playwright-stealth SUCCESSFULLY BYPASSED Cloudflare!")
                else:
                    print("\n⚠️  No search results found (but Cloudflare bypassed)")
                    print("   Page may have different HTML structure than expected")

            # Save screenshot for debugging
            await page.screenshot(path="/tmp/fbi_vault_stealth_test.png")
            print(f"\nScreenshot saved to: /tmp/fbi_vault_stealth_test.png")

            # Save HTML for inspection
            with open("/tmp/fbi_vault_stealth_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"HTML saved to: /tmp/fbi_vault_stealth_content.html")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print(f"   Type: {type(e).__name__}")

        finally:
            await browser.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_fbi_vault_stealth())
