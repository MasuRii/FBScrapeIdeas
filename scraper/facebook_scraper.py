import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging
from datetime import datetime
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
import time
import re
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_facebook_session(driver: WebDriver) -> bool:
    """
    Checks if the current Selenium WebDriver instance is still logged into Facebook.
    A simple check is to see if a known element on the logged-in homepage exists.
    """
    logging.info("Checking Facebook session status...")
    try:
        driver.get("https://www.facebook.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='feed'] | //a[@aria-label='Home']"))
        )
        logging.info("Session appears to be active.")
        return True
    except (TimeoutException, NoSuchElementException, WebDriverException) as e:
        logging.warning(f"Session appears to be inactive or check failed: {e}")
        return False

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
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Allow essential and optional cookies')]"))
            )
            accept_button.click()
            logging.info("Accepted cookie consent.")
            time.sleep(2)
        except (NoSuchElementException, TimeoutException):
            logging.info("No cookie consent dialog found or already accepted.")
            pass

        logging.info("Attempting to find email/phone field.")
        email_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "email"))
        )
        logging.info("Email field found. Entering username.")
        email_field.send_keys(username)

        logging.info("Attempting to find password field.")
        password_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "pass"))
        )
        logging.info("Password field found. Entering password.")
        password_field.send_keys(password)

        logging.info("Attempting to find login button.")
        login_button = WebDriverWait(driver, 20).until(
             EC.element_to_be_clickable((By.NAME, "login"))
        )
        logging.info("Login button found. Clicking login.")
        login_button.click()

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH, "//div[@role='feed'] | //a[@aria-label='Home'] | //div[contains(@data-pagelet, 'Feed')]"
                ))
            )
            logging.info("Login successful: Feed element or Home link found.")
            login_successful = True
        except TimeoutException:
            logging.warning("Login appeared to fail or took too long to redirect.")
            error_message = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='login_error_message']")
            if error_message:
                logging.error(f"Facebook login error message: {error_message[0].text}")
            else:
                logging.error("Login failed: Timeout waiting for post-login page or element.")
            login_successful = False

    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Selenium element error during login: {e}")
        login_successful = False
    except WebDriverException as e:
        logging.error(f"WebDriver error during login: {e}")
        login_successful = False
    except Exception as e:
        logging.error(f"An unexpected error occurred during login: {e}")
        login_successful = False

    if login_successful:
         pass

    return login_successful

def scrape_authenticated_group(driver: WebDriver, group_url: str, num_posts: int) -> List[Dict[str, Any]]:
    """
    Scrapes posts from a specified Facebook group URL using an authenticated Selenium WebDriver instance.

    Args:
        driver: An initialized and authenticated Selenium WebDriver instance.
        group_url: The URL of the Facebook group.
        num_posts: The number of posts to attempt to scrape.

    Returns:
        A list of dictionaries, each representing a post with essential information.
    """
    scraped_posts: List[Dict[str, Any]] = []
    processed_post_urls: set[str] = set()
    processed_post_ids: set[str] = set()

    logging.info(f"Navigating to group: {group_url}")
    try:
        driver.get(group_url)
        logging.info(f"Successfully navigated to {group_url}")

        WebDriverWait(driver, 30).until(
             EC.presence_of_element_located((By.XPATH, "//div[@role='feed'] | //div[@data-testid='post_scroller']"))
        )
        logging.info("Feed element found.")

        if "groups/" not in driver.current_url or "not_found" in driver.current_url or "login" in driver.current_url:
             logging.warning(f"Potential issue accessing group URL {group_url}. Current URL: {driver.current_url}. May require manual navigation or login handling.")
             if group_url not in driver.current_url:
                 driver.get(group_url)
                 WebDriverWait(driver, 30).until(
                     EC.presence_of_element_located((By.XPATH, "//div[@role='feed'] | //div[@data-testid='post_scroller']"))
                 )


        extracted_count = 0
        scroll_pause_time = 3
        max_scroll_attempts = 50

        logging.info(f"Starting to scrape up to {num_posts} posts...")

        scroll_attempt = 0
        while extracted_count < num_posts and scroll_attempt < max_scroll_attempts:
            scroll_attempt += 1
            logging.info(f"Scroll attempt {scroll_attempt}. Scraped {extracted_count} posts so far.")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(scroll_pause_time)

            overlay_selectors = [
                "//div[@data-testid='dialog']",
                "//div[contains(@role, 'dialog')]",
                "//div[@aria-label='View site information']",
                "//button[text()='Not Now']",
                "//a[@aria-label='Close']"
            ]

            for selector in overlay_selectors:
                try:
                    overlays = driver.find_elements(By.XPATH, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            logging.warning(f"Potential overlay detected with selector: {selector}. Attempting to dismiss.")
                            try:
                                dismiss_button = overlay.find_element(By.XPATH, ".//button[text()='Not Now'] | .//a[@aria-label='Close'] | .//button[contains(text(), 'Close')] | .//button[contains(text(), 'Dismiss')] | .//button[contains(text(), 'Later')] | .//div[@role='button'][contains(text(), 'Not Now')] | .//div[@role='button'][contains(text(), 'Later')]")
                                if dismiss_button.is_displayed() and dismiss_button.is_enabled():
                                     dismiss_button.click()
                                     logging.info("Overlay dismissed.")
                                     time.sleep(2)
                                     break
                                else:
                                    logging.debug("Found overlay, but dismiss button not visible or enabled.")
                            except NoSuchElementException:
                                logging.debug("No standard dismiss button found within overlay. Skipping dismissal for this overlay.")
                            except Exception as overlay_e:
                                logging.error(f"Error attempting to dismiss overlay: {overlay_e}")
                    if overlays and overlays[0].is_displayed():
                         logging.warning(f"Overlay(s) found but could not dismiss using standard buttons. Scrolling might be blocked.")

                except Exception as selector_e:
                    logging.debug(f"Error checking for overlay with selector {selector}: {selector_e}")


            potential_post_elements = driver.find_elements(By.XPATH,
                "//div[@role='feed']/div/div/div[starts-with(@class, 'x')] | "
                "//div[@role='article'] | "
                "//div[contains(@data-testid, 'post_story')] | "
                "//div[contains(@class, 'du4w35lb') and .//a[contains(@href, '/posts/')]]"
            )

            logging.debug(f"Found {len(potential_post_elements)} potential post elements on the page.")

            for post_element in potential_post_elements:
                try:
                    post_url = None
                    post_id = None
                    post_text = None
                    posted_at = None
                    is_valid_post = False

                    try:
                         link_element = post_element.find_element(By.XPATH, \
                            ".//a[contains(@href, '/posts/')] | " \
                            ".//a[contains(@href, '/videos/')] | " \
                            ".//a[contains(@href, '/photos/')] | " \
                            ".//abbr/ancestor::a"
                         )
                         raw_url = link_element.get_attribute('href')
                         if raw_url:
                             parsed_url = urlparse(raw_url)
                             clean_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                             post_url = clean_url

                             path_parts = parsed_url.path.split('/')
                             if 'posts' in path_parts:
                                 try:
                                     post_id = path_parts[path_parts.index('posts') + 1]
                                 except IndexError:
                                     pass
                             elif 'videos' in path_parts:
                                  try:
                                      post_id = path_parts[path_parts.index('videos') + 1]
                                  except IndexError:
                                      pass
                             elif 'photos' in path_parts:
                                  try:
                                      post_id = path_parts[path_parts.index('photos') + 1]
                                      query_params = parse_qs(parsed_url.query)
                                      if 'photo_id' in query_params:
                                           post_id = query_params['photo_id'][0]
                                  except (IndexError, KeyError):
                                      pass

                             if not post_id:
                                  url_id_match = re.search(r'/\d{10,}/', parsed_url.path)
                                  if url_id_match:
                                       post_id = url_id_match.group(0).strip('/')

                         if post_url:
                             is_valid_post = True

                    except NoSuchElementException:
                        try:
                             timestamp_element = post_element.find_element(By.XPATH, \
                                 ".//abbr | " \
                                 ".//a/span[@data-lexical-text='true']"
                             )
                             is_valid_post = True
                        except NoSuchElementException:
                             is_valid_post = False
                             logging.debug("Element does not appear to be a post (no standard link or timestamp found). Skipping.")
                             continue

                    if not post_id and post_url:
                        parsed_url_fallback = urlparse(post_url)
                        query_params_fallback = parse_qs(parsed_url_fallback.query)
                        if 'story_fbid' in query_params_fallback:
                             post_id = query_params_fallback['story_fbid'][0]
                        elif 'fbid' in query_params_fallback:
                             post_id = query_params_fallback['fbid'][0]
                        elif 'v' in query_params_fallback:
                             post_id = query_params_fallback['v'][0]


                    if not post_id and is_valid_post:
                        try:
                             post_id = f"generated_{hash(post_element.text[:200])}_{int(time.time())}"
                             logging.debug(f"Generated fallback post_id: {post_id}")
                        except Exception:
                            post_id = f"generated_{int(time.time())}_{extracted_count}"
                            logging.debug(f"Generated simple fallback post_id: {post_id}")


                    if post_url and post_url in processed_post_urls:
                        logging.debug(f"Skipping already processed post by URL: {post_url}")
                        continue
                    if post_id and post_id in processed_post_ids:
                        logging.debug(f"Skipping already processed post by ID: {post_id}")
                        continue
                    if not post_url and not post_id:
                         logging.debug("Could not determine post URL or ID. Skipping element.")
                         continue


                    try:
                         text_element = post_element.find_element(By.XPATH, \
                            ".//div[@data-testid='post-content'] | " \
                            ".//div[@dir='auto'] | " \
                            ".//div[contains(@class, 'kvgmc6g5')] | " \
                            ".//div[contains(@class, 'ecm0bbzt')]"
                         )
                         post_text = text_element.text.strip()
                         if len(post_text) < 20 and not any(kw in post_text.lower() for kw in ['post', 'share', 'comment']):
                             logging.debug(f"Post text seems too short ({len(post_text)} chars), may not be main content. ID: {post_id}")
                             pass

                    except NoSuchElementException:
                         logging.debug(f"Could not find standard text element for post (ID: {post_id}). Text will be N/A.")
                         post_text = "N/A"

                    try:
                         timestamp_element = post_element.find_element(By.XPATH, ".//abbr")
                         datetime_str = timestamp_element.get_attribute('title')
                         simple_time_text = timestamp_element.text

                         if datetime_str:
                             try:
                                 posted_at = datetime.strptime(datetime_str, "%A, %d %B %Y at %I:%M %p")
                                 logging.debug(f"Parsed full datetime: {posted_at}")
                             except ValueError:
                                 logging.warning(f"Could not parse detailed timestamp format '{datetime_str}' for post (ID: {post_id}). Falling back to simple text.")
                                 posted_at = simple_time_text
                                 logging.debug(f"Using simple time text as timestamp: {posted_at}")
                         elif simple_time_text:
                              logging.warning(f"Timestamp element found but 'title' attribute is missing for post (ID: {post_id}). Using simple text.")
                              posted_at = simple_time_text
                              logging.debug(f"Using simple time text as timestamp: {posted_at}")
                         else:
                              logging.debug(f"Timestamp element found but no text or title attribute for post (ID: {post_id}).")
                              posted_at = None

                    except NoSuchElementException:
                        logging.debug(f"Could not find timestamp element for post (ID: {post_id}). Timestamp will be None.")
                        posted_at = None

                    if (post_url or post_id) and (post_text != "N/A" or posted_at is not None):
                         scraped_posts.append({
                             "facebook_post_id": post_id,
                             "post_url": post_url,
                             "content_text": post_text,
                             "posted_at": posted_at.isoformat() if isinstance(posted_at, datetime) else str(posted_at) if posted_at is not None else None,
                             "scraped_at": datetime.now().isoformat()
                         })
                         extracted_count += 1
                         if post_url: processed_post_urls.add(post_url)
                         if post_id: processed_post_ids.add(post_id)

                         logging.info(f"Extracted post {extracted_count}: URL: {post_url}, ID: {post_id}")

                         if extracted_count >= num_posts:
                             logging.info(f"Reached desired number of posts ({num_posts}). Stopping scraping.")
                             break

                    else:
                         logging.debug(f"Skipping element lacking essential post data (URL: {post_url}, ID: {post_id}, Text: {post_text}, Time: {posted_at}).")


                except StaleElementReferenceException:
                     logging.warning("StaleElementReferenceException during post data extraction. Skipping element.")
                     continue
                except Exception as e:
                    logging.error(f"Error extracting data from a post element (ID: {post_id}): {e}", exc_info=True)
                    continue

            if extracted_count < num_posts:
                logging.info(f"Scraped {extracted_count} posts. Need {num_posts}. Continuing scroll...")

            else:
                break


        logging.info(f"Finished scraping loop. Total posts extracted: {extracted_count}.")
        if extracted_count < num_posts:
            logging.warning(f"Could only find {extracted_count} posts, less than the requested {num_posts}.")


    except TimeoutException:
        logging.error(f"Timed out waiting for elements while scraping group {group_url}.")
    except NoSuchElementException:
         logging.error(f"Could not find expected elements while scraping group {group_url}. Selectors may be outdated.")
    except WebDriverException as e:
        logging.error(f"A WebDriver error occurred during group scraping: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during group scraping: {e}", exc_info=True)

    return scraped_posts

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
        logging.info("Session appears valid.")
        return True
    except TimeoutException:
        logging.warning("Session check timed out or redirected to login. Session may be invalid.")
        return False
    except WebDriverException as e:
        logging.error(f"WebDriver error during session check: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during session check: {e}")
        return False