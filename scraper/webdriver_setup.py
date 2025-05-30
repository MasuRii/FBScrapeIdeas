from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def init_webdriver(headless: bool = True) -> webdriver.Chrome:
    """Initializes and returns a configured Selenium WebDriver."""
    options = Options()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-css")
        
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)

    return driver

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