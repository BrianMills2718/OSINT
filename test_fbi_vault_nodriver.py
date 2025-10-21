#!/usr/bin/env python3
"""
Test FBI Vault with nodriver to bypass Cloudflare protection.
"""

import asyncio
import nodriver as uc


async def test_fbi_vault_nodriver():
    """Test FBI Vault search with nodriver."""
    print("=" * 80)
    print("FBI VAULT - NODRIVER BYPASS TEST")
    print("=" * 80)

    # Test URL - FBI Vault search for "terrorism"
    test_url = "https://vault.fbi.gov/search?SearchableText=terrorism"

    print("\nLaunching browser with nodriver...")
    print("(nodriver uses direct CDP communication, no webdriver leaks)")

    browser = None
    try:
        # Launch browser with nodriver (NON-headless mode for Cloudflare bypass)
        # Use Chromium from Playwright/Puppeteer
        # NOTE: Headless mode is detectable by Cloudflare, so we use headed mode
        chrome_path = "/home/brian/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome"
        browser = await uc.start(
            headless=False,  # MUST be False for Cloudflare bypass
            browser_executable_path=chrome_path
        )

        print(f"\nNavigating to: {test_url}")
        page = await browser.get(test_url)

        # Wait for page to load
        await asyncio.sleep(5)

        print(f"\nPage URL: {page.url}")

        # Get page title (nodriver API)
        try:
            title = await page.evaluate("document.title")
            print(f"Page title: {title}")
        except:
            print("Could not get title")

        # Get page content (nodriver uses evaluate to get HTML)
        content = await page.evaluate("document.documentElement.outerHTML")
        content_lower = content.lower()

        # Check for Cloudflare challenge markers
        cloudflare_markers = [
            "challenge-platform",
            "just a moment",
            "checking your browser",
            "cf-browser-verification",
        ]

        detected_markers = [marker for marker in cloudflare_markers if marker in content_lower]

        if detected_markers:
            print(f"\n❌ CLOUDFLARE PROTECTION ACTIVE")
            print(f"   Detected markers: {detected_markers}")
            print("\n   nodriver did NOT bypass Cloudflare")
        else:
            print(f"\n✅ CLOUDFLARE BYPASSED!")

            # Try to extract search results using JavaScript
            try:
                # FBI Vault uses specific HTML structure
                # Count search results using JavaScript
                results_count = await page.evaluate(
                    "document.querySelectorAll('.searchResults .tileItem').length"
                )
                print(f"   Found {results_count} search results")

                if results_count > 0:
                    print("\n   First result:")

                    # Get first result title and URL
                    first_title = await page.evaluate(
                        "document.querySelector('.searchResults .tileItem .tileHeadline a')?.textContent"
                    )
                    first_url = await page.evaluate(
                        "document.querySelector('.searchResults .tileItem .tileHeadline a')?.href"
                    )

                    if first_title:
                        print(f"     Title: {first_title.strip()}")
                    if first_url:
                        print(f"     URL: {first_url}")

                    print("\n✅ nodriver SUCCESSFULLY BYPASSED Cloudflare!")
                else:
                    print("\n⚠️  No search results found with .searchResults selector")
                    print("   Checking if Cloudflare bypassed with alternate indicators...")

                    # Try alternate selectors - count FBI Vault links
                    links_count = await page.evaluate(
                        "document.querySelectorAll('a[href*=\"vault.fbi.gov\"]').length"
                    )
                    print(f"   Found {links_count} FBI Vault links")

                    if links_count > 5:  # If we found multiple FBI links, likely real page
                        print("\n✅ nodriver likely BYPASSED Cloudflare (found FBI content)")
                        print("   Page may have different HTML structure than expected")
                    else:
                        print("\n⚠️  Unclear if bypass succeeded")

            except Exception as e:
                print(f"\n⚠️  Error extracting results: {e}")
                print(f"   Type: {type(e).__name__}")

        # Save screenshot for debugging
        try:
            screenshot_data = await page.screenshot(scale="page")
            with open("/tmp/fbi_vault_nodriver_test.png", "wb") as f:
                f.write(screenshot_data)
            print(f"\nScreenshot saved to: /tmp/fbi_vault_nodriver_test.png")
        except Exception as e:
            print(f"\nCould not save screenshot: {e}")

        # Save HTML for inspection
        try:
            with open("/tmp/fbi_vault_nodriver_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"HTML saved to: /tmp/fbi_vault_nodriver_content.html")
        except Exception as e:
            print(f"Could not save HTML: {e}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        if browser:
            try:
                await browser.stop()
            except:
                pass

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run async function
    asyncio.run(test_fbi_vault_nodriver())
