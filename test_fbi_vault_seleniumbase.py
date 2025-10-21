#!/usr/bin/env python3
"""
Test FBI Vault with SeleniumBase UC Mode + xvfb to bypass Cloudflare.
SeleniumBase UC Mode is specifically designed for Cloudflare bypass on Linux.
"""

from seleniumbase import SB


def test_fbi_vault_seleniumbase():
    """Test FBI Vault search with SeleniumBase UC Mode."""
    print("=" * 80)
    print("FBI VAULT - SELENIUMBASE UC MODE BYPASS TEST")
    print("=" * 80)

    # Test URL - FBI Vault search for "terrorism"
    test_url = "https://vault.fbi.gov/search?SearchableText=terrorism"

    print("\nLaunching browser with SeleniumBase UC Mode...")
    print("(Using xvfb virtual display for WSL2 compatibility)")
    print("(UC Mode = Undetected ChromeDriver with Cloudflare bypass patches)")

    try:
        # Use SeleniumBase with UC Mode (Undetected ChromeDriver)
        # xvfb=True creates virtual display for headless-like operation on Linux
        # Point to Chromium from Playwright/Puppeteer
        chrome_binary = "/home/brian/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome"

        with SB(uc=True, xvfb=True, test=True, binary_location=chrome_binary) as sb:
            print(f"\nNavigating to: {test_url}")

            # Use uc_open_with_reconnect for Cloudflare-protected sites
            # The reconnect method helps bypass detection
            sb.driver.uc_open_with_reconnect(test_url, reconnect_time=4)

            # Wait a moment for page to fully load
            sb.sleep(2)

            print(f"\nPage URL: {sb.get_current_url()}")
            print(f"Page title: {sb.get_title()}")

            # Check for Cloudflare challenge markers
            page_source = sb.get_page_source().lower()

            cloudflare_markers = [
                "challenge-platform",
                "just a moment",
                "checking your browser",
                "cf-browser-verification",
            ]

            detected_markers = [marker for marker in cloudflare_markers if marker in page_source]

            if detected_markers:
                print(f"\n❌ CLOUDFLARE PROTECTION ACTIVE")
                print(f"   Detected markers: {detected_markers}")
                print("\n   SeleniumBase UC Mode did NOT bypass Cloudflare")
            else:
                print(f"\n✅ CLOUDFLARE BYPASSED!")

                # Try to extract search results
                try:
                    # Check if we can find search results
                    if sb.is_element_present(".searchResults .tileItem"):
                        results = sb.find_elements(".searchResults .tileItem")
                        print(f"   Found {len(results)} search results")

                        if results:
                            print("\n   First result:")
                            # Get first result details
                            first_title = sb.get_text(".searchResults .tileItem .tileHeadline a")
                            first_url = sb.get_attribute(".searchResults .tileItem .tileHeadline a", "href")

                            print(f"     Title: {first_title}")
                            print(f"     URL: {first_url}")

                            print("\n✅ SeleniumBase UC Mode SUCCESSFULLY BYPASSED Cloudflare!")
                    else:
                        print("\n⚠️  No search results found with .searchResults selector")
                        print("   Checking if Cloudflare bypassed with alternate indicators...")

                        # Try alternate selectors - look for FBI Vault content
                        fbi_links = sb.find_elements('a[href*="vault.fbi.gov"]')
                        print(f"   Found {len(fbi_links)} FBI Vault links")

                        if len(fbi_links) > 5:  # If we found multiple FBI links, likely real page
                            print("\n✅ SeleniumBase UC Mode likely BYPASSED Cloudflare (found FBI content)")
                            print("   Page may have different HTML structure than expected")
                        else:
                            print("\n⚠️  Unclear if bypass succeeded")

                except Exception as e:
                    print(f"\n⚠️  Error extracting results: {e}")
                    print(f"   Type: {type(e).__name__}")

            # Save screenshot for debugging
            try:
                sb.save_screenshot("/tmp/fbi_vault_seleniumbase_test.png")
                print(f"\nScreenshot saved to: /tmp/fbi_vault_seleniumbase_test.png")
            except Exception as e:
                print(f"\nCould not save screenshot: {e}")

            # Save HTML for inspection
            try:
                with open("/tmp/fbi_vault_seleniumbase_content.html", "w", encoding="utf-8") as f:
                    f.write(sb.get_page_source())
                print(f"HTML saved to: /tmp/fbi_vault_seleniumbase_content.html")
            except Exception as e:
                print(f"Could not save HTML: {e}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_fbi_vault_seleniumbase()
