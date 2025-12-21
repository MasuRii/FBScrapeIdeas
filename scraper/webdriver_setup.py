from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Modern Chrome user-agent (Chrome 131 - Dec 2024)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def init_webdriver(headless: bool = True) -> webdriver.Chrome:
    """Initializes and returns a configured Selenium WebDriver.

    Args:
        headless: Run browser in headless mode (default: True)

    Returns:
        Configured Chrome WebDriver instance

    Raises:
        WebDriverException: If driver initialization fails
        RuntimeError: If ChromeDriver cannot be installed/located
    """
    options = Options()

    # Anti-detection measures (applied in all modes)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        # Use new headless mode (Chrome 109+)
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")

        # Disable images for faster headless scraping
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)

        # Execute CDP command to mask webdriver property
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
            },
        )

        return driver

    except WebDriverException as e:
        raise WebDriverException(f"Failed to initialize Chrome WebDriver: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to install/locate ChromeDriver: {e}") from e


if __name__ == "__main__":
    driver = None
    try:
        print("Initializing headless WebDriver...")
        driver = init_webdriver(headless=True)
        print("WebDriver initialized successfully.")
        driver.get("http://google.com")
        print(f"Accessed page title: {driver.title}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver closed.")
