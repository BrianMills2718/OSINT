#!/usr/bin/env python3
"""
Test FBI Vault with undetected-chromedriver to bypass Cloudflare protection.
"""

import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_fbi_vault_undetected():
    """Test FBI Vault search with undetected-chromedriver."""
    print("=" * 80)
    print("FBI VAULT - UNDETECTED-CHROMEDRIVER BYPASS TEST")
    print("=" * 80)

    # Test URL - FBI Vault search for "terrorism"
    test_url = "https://vault.fbi.gov/search?SearchableText=terrorism"

    print("\nLaunching Chrome with undetected-chromedriver...")
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')  # Use new headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        driver = uc.Chrome(options=options)

        print(f"\nNavigating to: {test_url}")
        driver.get(test_url)

        # Wait for page to load
        time.sleep(5)

        print(f"\nPage URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Check for Cloudflare challenge markers
        page_source = driver.page_source.lower()

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
            print("\n   undetected-chromedriver did NOT bypass Cloudflare")
        else:
            print(f"\n✅ CLOUDFLARE BYPASSED!")

            # Try to extract search results
            try:
                # FBI Vault uses specific HTML structure
                results = driver.find_elements(By.CSS_SELECTOR, ".searchResults .tileItem")
                print(f"   Found {len(results)} search results")

                if results:
                    print("\n   First result:")
                    first = results[0]
                    try:
                        title_elem = first.find_element(By.CSS_SELECTOR, ".tileHeadline a")
                        print(f"     Title: {title_elem.text}")
                        print(f"     URL: {title_elem.get_attribute('href')}")
                    except Exception as e:
                        print(f"     Could not extract title: {e}")

                    print("\n✅ undetected-chromedriver SUCCESSFULLY BYPASSED Cloudflare!")
                else:
                    print("\n⚠️  No search results found (but Cloudflare bypassed)")
                    print("   Page may have different HTML structure than expected")

                    # Try alternate selectors
                    print("\n   Trying alternate selectors...")
                    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='vault.fbi.gov']")
                    print(f"   Found {len(links)} FBI Vault links")

            except Exception as e:
                print(f"\n⚠️  Error extracting results: {e}")

        # Save screenshot for debugging
        driver.save_screenshot("/tmp/fbi_vault_undetected_test.png")
        print(f"\nScreenshot saved to: /tmp/fbi_vault_undetected_test.png")

        # Save HTML for inspection
        with open("/tmp/fbi_vault_undetected_content.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"HTML saved to: /tmp/fbi_vault_undetected_content.html")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.quit()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_fbi_vault_undetected()
