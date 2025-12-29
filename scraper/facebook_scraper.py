import concurrent.futures
import json
import logging
import random
import re
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import dateparser
import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .js_logic import (
    DISPATCH_ESC_SCRIPT,
    FORCE_SCROLLABLE_SCRIPT,
    NUKE_BLOCKING_SCRIPT,
    PRUNE_DOM_SCRIPT,
)
from .selectors import get_selector_registry
from .timestamp_parser import parse_fb_timestamp
from .utils import derive_post_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.INFO)

# Legacy pointers for tests
_registry = get_selector_registry()
POST_CONTAINER_S = (By.CSS_SELECTOR, _registry.get_selector("article"))
POST_PERMALINK_XPATH_S = (
    By.XPATH,
    ".//a[contains(@href, '/posts/')] | .//a[contains(@href, '/videos/')] | .//a[contains(@href, '/photos/')] | .//abbr/ancestor::a",
)
FEED_OR_SCROLLER_XPATH_S = (By.XPATH, "//div[@role='feed'] | //div[@data-testid='post_scroller']")
SEE_MORE_BUTTON_XPATH_S = (
    By.XPATH,
    ".//div[@role='button'][contains(., 'See more') or contains(., 'Show more')] | .//a[contains(., 'See more') or contains(., 'Show more')]",
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (NoSuchElementException, StaleElementReferenceException, TimeoutException)
    ),
    reraise=True,
)
def check_facebook_session(driver: WebDriver) -> bool:
    """
    Checks if the current Selenium WebDriver instance is still logged into Facebook.
    A simple check is to see if a known element on the logged-in homepage exists.
    """
    logging.info("Checking Facebook session status...")
    try:
        driver.get("https://www.facebook.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[role='feed'], a[aria-label='Home']")
            )
        )
        logging.debug("Session appears to be active.")
        return True
    except (TimeoutException, NoSuchElementException, WebDriverException) as e:
        logging.warning(f"Session appears to be inactive or check failed: {e}")
        return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (NoSuchElementException, StaleElementReferenceException, TimeoutException)
    ),
    reraise=True,
)
def login_to_facebook(driver: WebDriver, username: str, password: str) -> bool:
    """
    Automates logging into Facebook using provided credentials.

    Args:
        driver: The Selenium WebDriver instance.
        username: The Facebook username (email or phone).
        password: The Facebook password.

    Returns:
        True if login is successful, False otherwise.
    """
    login_successful = False
    try:
        logging.info("Navigating to Facebook login page.")
        driver.get("https://www.facebook.com/")

        try:
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-cookiebanner='accept_button']")
                )
            )
            accept_button.click()
            logging.debug("Accepted cookie consent.")
            time.sleep(2)
        except (NoSuchElementException, TimeoutException):
            logging.debug("No cookie consent dialog found or already accepted.")
            pass

        logging.debug("Attempting to find email/phone field.")
        email_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "email"))
        )
        logging.debug("Email field found. Entering username.")
        email_field.send_keys(username)

        logging.debug("Attempting to find password field.")
        password_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "pass"))
        )
        logging.debug("Password field found. Entering password.")
        password_field.send_keys(password)

        logging.debug("Attempting to find login button.")
        login_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "login"))
        )
        logging.debug("Login button found. Clicking login.")
        login_button.click()

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div[role='feed'], a[aria-label='Home'], div[data-pagelet*='Feed']",
                    )
                )
            )
            logging.info("Login successful: Feed element or Home link found.")
            login_successful = True
        except TimeoutException:
            logging.warning("Login appeared to fail or took too long to redirect.")
            error_message = driver.find_elements(
                By.CSS_SELECTOR, "div[data-testid='login_error_message']"
            )
            if error_message:
                logging.error(f"Facebook login error message: {error_message[0].text}")
            else:
                logging.error("Login failed: Timeout waiting for post-login page or element.")
            login_successful = False

    except (NoSuchElementException, TimeoutException) as e:
        logging.error(
            f"Selenium element error during login (username={username[:3]}***): {type(e).__name__}: {e}"
        )
        login_successful = False
    except WebDriverException as e:
        logging.error(
            f"WebDriver error during login (username={username[:3]}***): {type(e).__name__}: {e}"
        )
        login_successful = False
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during login (username={username[:3]}***): {type(e).__name__}: {e}"
        )
        login_successful = False

    if login_successful:
        # OPTIMIZATION: Skip overlay dismissal on homepage - we navigate away immediately
        # Overlays are handled after navigating to target page in scrape_authenticated_group()
        # This avoids 2+ minute delays from long timeouts when overlays don't exist
        logging.debug("Login successful. Proceeding to target page (overlay handling deferred).")

    return login_successful


def ensure_scrollable(driver: WebDriver) -> None:
    """Forces body and html tags to be scrollable."""
    try:
        driver.execute_script(f"({FORCE_SCROLLABLE_SCRIPT})()")
    except Exception as e:
        logging.debug(f"Failed to force scrollable: {e}")


def nuke_blocking_elements(driver: WebDriver) -> None:
    """Removes elements that might be blocking the view or scrolling."""
    try:
        driver.execute_script(f"({NUKE_BLOCKING_SCRIPT})()")
    except Exception as e:
        logging.debug(f"Failed to nuke blocking elements: {e}")


def dismiss_cookie_consent(driver: WebDriver) -> None:
    """Handles cookie consent dialogs."""
    logging.debug("Checking for cookie consent dialogs...")
    registry = get_selector_registry()
    for selector in registry.get_selectors_list("dismiss_button"):
        try:
            cookie_button = WebDriverWait(driver, 0.5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            if cookie_button.is_displayed():
                driver.execute_script("arguments[0].click();", cookie_button)
                logging.info(f"Dismissed cookie consent via '{selector}'")
                time.sleep(0.3)
                return
        except (TimeoutException, NoSuchElementException):
            continue
        except Exception as e:
            logging.debug(f"Error clicking cookie button '{selector}': {e}")


def dismiss_overlays(driver: WebDriver) -> None:
    """Detects and attempts to dismiss common Facebook overlays."""
    logging.debug("Checking for overlays to dismiss...")
    ensure_scrollable(driver)
    registry = get_selector_registry()

    try:
        if not driver.find_elements(By.CSS_SELECTOR, registry.get_selector("overlay")):
            return
    except:
        pass

    overlay_selectors = registry.get_selectors_list("overlay")
    dismiss_selectors = registry.get_selectors_list("dismiss_button")

    for selector in overlay_selectors:
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, selector)
            for overlay in overlays:
                if overlay.is_displayed():
                    dismissed = False
                    for btn_selector in dismiss_selectors:
                        try:
                            btn = WebDriverWait(overlay, 0.5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, btn_selector))
                            )
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                logging.info(f"Dismissed overlay via '{btn_selector}'")
                                time.sleep(0.5)
                                dismissed = True
                                break
                        except:
                            continue
                    if not dismissed:
                        driver.execute_script(f"({DISPATCH_ESC_SCRIPT})()")
        except Exception as e:
            logging.debug(f"Error dismissing overlays for {selector}: {e}")
    nuke_blocking_elements(driver)


def _prune_dom(driver: WebDriver) -> None:
    """Removes processed elements from the DOM to save memory."""
    try:
        selector = get_selector_registry().get_selector("article")
        driver.execute_script(f"({PRUNE_DOM_SCRIPT.replace('{selector}', selector)})()")
    except Exception as e:
        logging.debug(f"DOM pruning failed: {e}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (NoSuchElementException, StaleElementReferenceException, TimeoutException)
    ),
    reraise=True,
)
def _get_post_identifiers_from_element(
    post_element: Any, group_url_for_logging: str
) -> tuple[str | None, str | None, bool]:
    """Extracts post_url and post_id from a Selenium WebElement."""
    post_url = None
    post_id = None
    is_valid_post_candidate = False

    try:
        registry = get_selector_registry()
        # Permalink extraction
        permalink_selectors = registry.get_selectors_list("permalink")
        for selector in permalink_selectors:
            try:
                # Handle XPATH if needed, but registry is CSS-focused
                # For now we use the legacy pointers for complex XPATHs if CSS fails
                link_elements = post_element.find_elements(By.CSS_SELECTOR, selector)
                if not link_elements and "/" in selector:  # Likely XPATH
                    link_elements = post_element.find_elements(By.XPATH, selector)

                if link_elements:
                    raw_url = link_elements[0].get_attribute("href")
                    if raw_url:
                        post_url = raw_url
                        is_valid_post_candidate = True
                        post_id = derive_post_id(raw_url)
                        break
            except:
                continue

        if not is_valid_post_candidate:
            # Fallback to timestamp existence
            ts_selectors = registry.get_selectors_list("timestamp")
            for ts_sel in ts_selectors:
                try:
                    post_element.find_element(By.CSS_SELECTOR, ts_sel)
                    is_valid_post_candidate = True
                    break
                except:
                    continue

        if is_valid_post_candidate and not post_id:
            post_id = f"generated_{uuid.uuid4().hex[:12]}"

    except Exception as e:
        logging.debug(f"Error in _get_post_identifiers_from_element: {e}")
        is_valid_post_candidate = False

    return post_url, post_id, is_valid_post_candidate


def _extract_data_from_post_html(
    post_html_content: str,
    post_url_from_main: str | None,
    post_id_from_main: str | None,
    group_url_context: str,
    fields_to_scrape: list[str] | None = None,
) -> dict[str, Any] | None:
    """Extracts post details using BeautifulSoup and SelectorRegistry."""
    soup = BeautifulSoup(post_html_content, "html.parser")
    registry = get_selector_registry()

    post_data = {
        "facebook_post_id": post_id_from_main,
        "post_url": post_url_from_main,
        "text": "N/A",
        "timestamp": None,
        "scraped_at": datetime.now(UTC).isoformat(),
        "author_name": None,
        "post_author_profile_pic_url": None,
        "post_image_url": None,
        "comments": [],
    }

    scrape_all = not fields_to_scrape

    # Helper to try multiple selectors
    def select_first(soup_obj, element_type):
        for selector in registry.get_selectors_list(element_type):
            try:
                el = soup_obj.select_one(selector)
                if el:
                    return el
            except:
                continue
        return None

    # Author Pic
    if scrape_all or "post_author_profile_pic_url" in fields_to_scrape:
        author_pic_el = select_first(soup, "author_pic")
        if author_pic_el:
            post_data["post_author_profile_pic_url"] = author_pic_el.get(
                "xlink:href"
            ) or author_pic_el.get("src")

    # Author Name
    if scrape_all or "post_author_name" in fields_to_scrape:
        author_el = select_first(soup, "author")
        if author_el:
            post_data["author_name"] = author_el.get_text(strip=True)

    # Content Text
    if scrape_all or "content_text" in fields_to_scrape:
        text_container = select_first(soup, "content")
        if text_container:
            post_data["text"] = text_container.get_text(separator="\n", strip=True)

    # Image
    if scrape_all or "post_image_url" in fields_to_scrape:
        img_el = select_first(soup, "post_image")
        if img_el:
            if img_el.name == "img":
                post_data["post_image_url"] = img_el.get("src")
            elif "style" in img_el.attrs:
                match = re.search(r'url\("?([^")]*)"?\)', img_el["style"])
                if match:
                    post_data["post_image_url"] = match.group(1)

    # Timestamp
    if scrape_all or "posted_at" in fields_to_scrape:
        raw_timestamp = None
        ts_el = select_first(soup, "timestamp")
        if ts_el:
            raw_timestamp = ts_el.get("title") or ts_el.get_text(strip=True)

        if raw_timestamp:
            parsed_dt = parse_fb_timestamp(raw_timestamp)
            if parsed_dt:
                post_data["timestamp"] = parsed_dt.isoformat()

    # Comments
    if scrape_all or "comments" in fields_to_scrape:
        comment_selectors = registry.get_selectors_list("comment_container")
        comment_elements = []
        for sel in comment_selectors:
            comment_elements.extend(soup.select(sel))

        for comment_el in comment_elements:
            comment_data = {
                "commenterName": None,
                "commentText": "N/A",
                "commentFacebookId": None,
                "comment_timestamp": None,
            }

            c_author = select_first(comment_el, "author")
            if c_author:
                comment_data["commenterName"] = c_author.get_text(strip=True)

            c_text = select_first(comment_el, "comment_text")
            if c_text:
                comment_data["commentText"] = c_text.get_text(strip=True)

            # Check for comment ID (both in links and on the container itself)
            c_id = select_first(comment_el, "comment_id")
            if c_id:
                if c_id.get("href"):
                    qs = parse_qs(urlparse(c_id["href"]).query)
                    if "comment_id" in qs:
                        comment_data["commentFacebookId"] = qs["comment_id"][0]
                elif c_id.has_attr("data-commentid"):
                    comment_data["commentFacebookId"] = c_id["data-commentid"]

            # Fallback: check the container itself for data-commentid
            if not comment_data["commentFacebookId"] and comment_el.has_attr("data-commentid"):
                comment_data["commentFacebookId"] = comment_el["data-commentid"]

            if comment_data["commenterName"] or comment_data["commentText"] != "N/A":
                post_data["comments"].append(comment_data)

    if (post_data["post_url"] or post_data["facebook_post_id"]) and (
        post_data["text"] != "N/A" or post_data["timestamp"] or post_data["author_name"]
    ):
        return post_data
    return None


def scrape_authenticated_group(
    driver: WebDriver, group_url: str, num_posts: int, fields_to_scrape: list[str] | None = None
) -> Iterator[dict[str, Any]]:
    """Scrapes posts from a Facebook group using parallel parsing."""
    processed_urls: set[str] = set()
    processed_ids: set[str] = set()
    registry = get_selector_registry()

    logging.info(f"Navigating to group: {group_url}")
    try:
        driver.get(group_url)
        dismiss_overlays(driver)

        # Wait for posts
        article_selector = registry.get_selector("article")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, article_selector))
        )

        extracted_count = 0
        scroll_attempt = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        stuck_scrolls = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            active_futures = []

            while extracted_count < num_posts and scroll_attempt < 50:
                scroll_attempt += 1
                ensure_scrollable(driver)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(0.8, 1.5))

                # Smart overlay dismissal
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    stuck_scrolls += 1
                    if stuck_scrolls >= 2:
                        dismiss_overlays(driver)
                        stuck_scrolls = 0
                else:
                    stuck_scrolls = 0
                last_height = new_height

                elements = driver.find_elements(By.CSS_SELECTOR, article_selector)
                for el in elements:
                    if extracted_count + len(active_futures) >= num_posts:
                        break

                    url, pid, is_valid = _get_post_identifiers_from_element(el, group_url)
                    if not is_valid or (url in processed_urls) or (pid in processed_ids):
                        continue

                    try:
                        see_more = el.find_element(By.XPATH, SEE_MORE_BUTTON_XPATH_S[1])
                        driver.execute_script("arguments[0].click();", see_more)
                        time.sleep(0.1)
                    except:
                        pass

                    html = el.get_attribute("outerHTML")
                    if not html:
                        continue

                    if url:
                        processed_urls.add(url)
                    if pid:
                        processed_ids.add(pid)
                    active_futures.append(
                        executor.submit(
                            _extract_data_from_post_html,
                            html,
                            url,
                            pid,
                            group_url,
                            fields_to_scrape,
                        )
                    )

                # Collect completed results
                for f in [f for f in active_futures if f.done()]:
                    active_futures.remove(f)
                    res = f.result()
                    if res:
                        yield res
                        extracted_count += 1
                        if extracted_count % 5 == 0:
                            _prune_dom(driver)

                if extracted_count >= num_posts:
                    break

            # Final collection
            for f in concurrent.futures.as_completed(active_futures, timeout=30):
                if extracted_count >= num_posts:
                    break
                try:
                    res = f.result()
                    if res:
                        yield res
                        extracted_count += 1
                except:
                    pass

    except Exception as e:
        logging.error(f"Error scraping {group_url}: {e}", exc_info=True)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (NoSuchElementException, StaleElementReferenceException, TimeoutException)
    ),
    reraise=True,
)
def is_facebook_session_valid(driver: WebDriver) -> bool:
    """
    Performs a basic check to see if the current Facebook session in the driver is still active.
    """
    try:
        logging.info("Checking Facebook session validity...")
        driver.get("https://www.facebook.com/settings")
        WebDriverWait(driver, 10).until(
            EC.url_contains("settings")
            or EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Facebook']"))
        )
        logging.debug("Session appears valid.")
        return True
    except TimeoutException as e:
        logging.warning(
            f"Session check timed out or redirected to login. Session may be invalid: {e}"
        )
        return False
    except WebDriverException as e:
        logging.error(f"WebDriver error during session check: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during session check: {type(e).__name__}: {e}")
        return False
