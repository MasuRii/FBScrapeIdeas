import logging
import time
from scraper.webdriver_setup import init_webdriver
from scraper.facebook_scraper import dismiss_overlays

# Set up logging to see the output from dismiss_overlays
logging.basicConfig(level=logging.DEBUG)


def run_smoke_test(url):
    print(f"Starting smoke test for: {url}")
    driver = None
    try:
        driver = init_webdriver(headless=True)
        print("WebDriver initialized successfully.")

        print(f"Navigating to {url}...")
        driver.get(url)
        time.sleep(3)  # Wait for initial load

        print("Checking for overlays...")
        dismiss_overlays(driver)

        print("Smoke test completed successfully (no crashes).")
        print(f"Final URL: {driver.current_url}")

    except Exception as e:
        print(f"Smoke test failed with error: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver closed.")


if __name__ == "__main__":
    # Use a real Facebook URL to see if it hits a login wall or cookie banner
    test_url = "https://www.facebook.com/groups/testgroup"
    run_smoke_test(test_url)
