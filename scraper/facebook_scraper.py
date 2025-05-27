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
from dateutil.parser import parse

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
    
    POST_CONTAINER_SELECTORS = 'div.x1yztbdb.x1n2onr6.xh8yej3.x1ja2u2z, div[role="article"]'
    
    AUTHOR_PIC_SVG_IMG_SELECTOR = 'div:first-child svg image'
    AUTHOR_PIC_IMG_SELECTOR = 'div:first-child img[alt*="profile picture"], div:first-child img[data-imgperflogname*="profile"]'
    SPECIFIC_AUTHOR_PIC_SELECTOR = 'div[role="button"] svg image'

    AUTHOR_NAME_SELECTORS = 'h2 strong, h2 a[role="link"] strong, h3 strong, h3 a[role="link"] strong, a[aria-label][href*="/user/"] > strong, a[aria-label][href*="/profile.php"] > strong'
    ANON_AUTHOR_NAME_SELECTOR = 'h2[id^="«r"] strong object div'
    GENERAL_AUTHOR_NAME_SELECTOR = 'a[href*="/groups/"][href*="/user/"] span, a[href*="/profile.php"] span, span > strong > a[role="link"]'

    POST_TEXT_CONTAINER_SELECTORS = 'div[data-ad-rendering-role="story_message"], div[data-ad-preview="message"], div[data-ad-comet-preview="message"]'
    GENERIC_TEXT_DIV_SELECTOR = 'div[dir="auto"]:not([class*=" "]):not(:has(button)):not(:has(a[role="button"]))'

    POST_IMAGE_SELECTORS = 'img.x168nmei, div[data-imgperflogname="MediaGridPhoto"] img, div[style*="background-image"]'

    COMMENT_CONTAINER_SELECTORS = 'div[aria-label*="Comment by"], ul > li div[role="article"]'

    COMMENTER_PIC_SVG_IMG_SELECTOR = 'svg image'
    COMMENTER_PIC_IMG_SELECTOR = 'img[alt*="profile picture"], img[data-imgperflogname*="profile"]'
    SPECIFIC_COMMENTER_PIC_SELECTOR = 'a[role="link"] svg image'

    COMMENTER_NAME_SELECTORS = 'a[href*="/user/"] span, a[href*="/profile.php"] span, span > a[role="link"] > span > span[dir="auto"]'
    GENERAL_COMMENTER_NAME_SELECTOR = 'div[role="button"] > strong > span, a[aria-hidden="false"][role="link"]'

    COMMENT_TEXT_SELECTORS = 'div[data-ad-preview="message"] > span, div[dir="auto"][style="text-align: start;"]'
    COMMENT_TEXT_CONTAINER_FALLBACK_SELECTORS = '.xmjcpbm.xtq9sad + div, .xv55zj0 + div'
    ACTUAL_COMMENT_TEXT_FALLBACK_SELECTORS = 'div[dir="auto"], span[dir="auto"]'

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


            potential_post_elements = driver.find_elements(By.CSS_SELECTOR, POST_CONTAINER_SELECTORS)

            logging.debug(f"Found {len(potential_post_elements)} potential post elements on the page.")

            for post_element in potential_post_elements:
                try:
                    post_url = None
                    post_id = None
                    post_text = None
                    posted_at = None
                    post_author_name = None
                    post_author_profile_pic_url = None
                    post_image_url = None
                    comments_data = []
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
                             logging.debug(f"Element does not appear to be a post (no standard link or timestamp found). Skipping element from scroll attempt {scroll_attempt}.")
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
                         logging.debug(f"Could not determine post URL or ID. Skipping element from scroll attempt {scroll_attempt}.")
                         continue

                    try:
                        author_pic_svg_img = post_element.find_elements(By.CSS_SELECTOR, AUTHOR_PIC_SVG_IMG_SELECTOR)
                        if author_pic_svg_img:
                            post_author_profile_pic_url = author_pic_svg_img[0].get_attribute('xlink:href')
                        else:
                            author_pic_img = post_element.find_elements(By.CSS_SELECTOR, AUTHOR_PIC_IMG_SELECTOR)
                            if author_pic_img:
                                post_author_profile_pic_url = author_pic_img[0].get_attribute('src')
                            else:
                                specific_author_pic = post_element.find_elements(By.CSS_SELECTOR, SPECIFIC_AUTHOR_PIC_SELECTOR)
                                if specific_author_pic:
                                    post_author_profile_pic_url = specific_author_pic[0].get_attribute('xlink:href')
                        logging.debug(f"Extracted author profile pic: {post_author_profile_pic_url}")
                    except Exception as e:
                        logging.warning(f"Could not extract author profile picture for post {post_id}: {e}")

                    try:
                        author_name_el = post_element.find_elements(By.CSS_SELECTOR, AUTHOR_NAME_SELECTORS)
                        if author_name_el:
                            post_author_name = author_name_el[0].text.strip()
                        else:
                            anon_author_name_el = post_element.find_elements(By.CSS_SELECTOR, ANON_AUTHOR_NAME_SELECTOR)
                            if anon_author_name_el:
                                post_author_name = anon_author_name_el[0].text.strip()
                            else:
                                general_author_name_el = post_element.find_elements(By.CSS_SELECTOR, GENERAL_AUTHOR_NAME_SELECTOR)
                                if general_author_name_el:
                                    post_author_name = general_author_name_el[0].text.strip()
                        logging.debug(f"Extracted author name: {post_author_name}")
                    except Exception as e:
                        logging.warning(f"Could not extract author name for post {post_id}: {e}")

                    try:
                        post_text = None
                        
                        post_text = None
                        
                        try:
                            see_more_button = WebDriverWait(post_element, 2).until(
                                EC.element_to_be_clickable((By.XPATH, ".//div[@role='button'][contains(., 'See more')] | .//a[contains(., 'See more')]"))
                            )
                            logging.info(f"Attempting to click 'See more' button for post {post_id}.")
                            driver.execute_script("arguments[0].scrollIntoView(true);", see_more_button)
                            time.sleep(0.5)
                            try:
                                see_more_button.click()
                            except Exception as click_e:
                                logging.warning(f"Direct click failed for 'See more' button, trying JS click: {click_e}")
                                driver.execute_script("arguments[0].click();", see_more_button)
                            time.sleep(1)
                            logging.info(f"Clicked 'See more' button for post {post_id}.")
                        except (TimeoutException, NoSuchElementException):
                            logging.debug(f"No 'See more' button found or clickable for post {post_id}.")
                            pass
                        except Exception as e:
                            logging.warning(f"Error handling 'See more' button for post {post_id}: {e}")
                            pass

                        post_text_container = post_element.find_elements(By.CSS_SELECTOR, POST_TEXT_CONTAINER_SELECTORS)
                        if post_text_container:
                            soup = BeautifulSoup(post_text_container[0].get_attribute('outerHTML'), 'html.parser')
                            text_parts = []
                            for child in soup.select(':scope > div, :scope > span'):
                                if child.get_text(strip=True) and not child.select('div[role="button"], a[role="button"]'):
                                    text_parts.append(child.get_text(strip=True))
                            
                            if text_parts:
                                post_text = '\n'.join(text_parts)
                                logging.debug(f"Extracted post text from parts using BeautifulSoup for {post_id}.")
                            else:
                                post_text = soup.get_text(strip=True)
                                logging.debug(f"Extracted post text from container innerText using BeautifulSoup for {post_id}.")

                        if not post_text:
                            try:
                                generic_text_div = post_element.find_element(By.CSS_SELECTOR, GENERIC_TEXT_DIV_SELECTOR)
                                post_text = generic_text_div.text.strip()
                                logging.debug(f"Extracted post text from generic div for {post_id}.")
                            except NoSuchElementException:
                                logging.debug(f"Generic text div not found for post {post_id}.")
                                pass

                        if not post_text:
                            try:
                                full_element_text = post_element.text.strip()
                                post_text = re.sub(r'\s+', ' ', full_element_text).strip()
                                logging.debug(f"Extracted post text from full element text for {post_id}.")
                            except Exception as e:
                                logging.warning(f"Error extracting full element text for post {post_id}: {e}")
                                post_text = "N/A"

                        if not post_text or post_text.strip() == "":
                            logging.warning(f"Post text is empty or N/A after all extraction attempts for post (ID: {post_id}, URL: {post_url}).")
                            post_text = "N/A"
                        else:
                            logging.info(f"Successfully extracted post_text for {post_id}.")

                    except Exception as e:
                        logging.error(f"An unexpected error occurred during post text extraction for post (ID: {post_id}, URL: {post_url}): {e}", exc_info=True)
                        post_text = "N/A"

                    try:
                        post_image_el = post_element.find_elements(By.CSS_SELECTOR, POST_IMAGE_SELECTORS)
                        if post_image_el:
                            if post_image_el[0].tag_name == 'img':
                                post_image_url = post_image_el[0].get_attribute('src')
                            elif post_image_el[0].tag_name == 'div' and post_image_el[0].value_of_css_property('background-image'):
                                bg_image = post_image_el[0].value_of_css_property('background-image')
                                if 'url("' in bg_image and '")' in bg_image:
                                    post_image_url = bg_image[bg_image.find('("') + 2 : bg_image.rfind('")')]
                        logging.debug(f"Extracted post image URL: {post_image_url}")
                    except Exception as e:
                        logging.warning(f"Could not extract post image for post {post_id}: {e}")

                    try:
                        comment_elements = post_element.find_elements(By.CSS_SELECTOR, COMMENT_CONTAINER_SELECTORS)
                        for comment_el in comment_elements:
                            comment = {
                                'commenterProfilePic': None,
                                'commenterName': None,
                                'commentText': None,
                                'commentFacebookId': None
                            }

                            try:
                                commenter_pic_svg_img = comment_el.find_elements(By.CSS_SELECTOR, COMMENTER_PIC_SVG_IMG_SELECTOR)
                                if commenter_pic_svg_img:
                                    comment['commenterProfilePic'] = commenter_pic_svg_img[0].get_attribute('xlink:href')
                                else:
                                    commenter_pic_img = comment_el.find_elements(By.CSS_SELECTOR, COMMENTER_PIC_IMG_SELECTOR)
                                    if commenter_pic_img:
                                        comment['commenterProfilePic'] = commenter_pic_img[0].get_attribute('src')
                                    else:
                                        specific_commenter_pic = comment_el.find_elements(By.CSS_SELECTOR, SPECIFIC_COMMENTER_PIC_SELECTOR)
                                        if specific_commenter_pic:
                                            comment['commenterProfilePic'] = specific_commenter_pic[0].get_attribute('xlink:href')
                            except Exception as e:
                                logging.debug(f"Could not extract commenter profile pic: {e}")

                            try:
                                commenter_name_el = comment_el.find_elements(By.CSS_SELECTOR, COMMENTER_NAME_SELECTORS)
                                if commenter_name_el:
                                    comment['commenterName'] = commenter_name_el[0].text.strip()
                                else:
                                    general_commenter_name_el = comment_el.find_elements(By.CSS_SELECTOR, GENERAL_COMMENTER_NAME_SELECTOR)
                                    if general_commenter_name_el:
                                        comment['commenterName'] = general_commenter_name_el[0].text.strip()
                            except Exception as e:
                                logging.debug(f"Could not extract commenter name: {e}")

                            try:
                                comment_text_el = comment_el.find_elements(By.CSS_SELECTOR, COMMENT_TEXT_SELECTORS)
                                if comment_text_el:
                                    comment['commentText'] = comment_text_el[0].text.strip()
                                else:
                                    comment_text_container = comment_el.find_elements(By.CSS_SELECTOR, COMMENT_TEXT_CONTAINER_FALLBACK_SELECTORS)
                                    if comment_text_container:
                                        actual_text_el = comment_text_container[0].find_elements(By.CSS_SELECTOR, ACTUAL_COMMENT_TEXT_FALLBACK_SELECTORS)
                                        if actual_text_el:
                                            comment['commentText'] = actual_text_el[0].text.strip()
                                        else:
                                            comment['commentText'] = comment_text_container[0].text.strip()
                            except Exception as e:
                                logging.debug(f"Could not extract comment text: {e}")

                            if comment['commenterName'] or comment['commentText']:
                                comments_data.append(comment)
                        logging.debug(f"Extracted {len(comments_data)} comments for post {post_id}.")
                    except Exception as e:
                        logging.warning(f"Error extracting comments for post {post_id}: {e}")

                    try:
                        timestamp_element = None
                        timestamp_selectors = [
                            ".//abbr",
                            ".//a[contains(@href, '/posts/')]//abbr",
                            ".//a[contains(@href, '/videos/')]//abbr",
                            ".//a[contains(@href, '/photos/')]//abbr",
                            ".//li[./span/div/a[contains(@href, '/posts/') or contains(@href, '/videos/') or contains(@href, '/photos/')]]//a[not(contains(@href, '/user/')) and string-length(text()) > 0]",
                            ".//a[contains(@href, '/groups/') and (contains(@href, '/posts/') or contains(@href, '/videos/') or contains(@href, '/photos/')) and string-length(text()) > 0 and not(contains(@href, '/user/'))]",
                            ".//div[@data-testid='post-header']//span/span/a/span/span"
                        ]

                        for selector in timestamp_selectors:
                            try:
                                timestamp_element = post_element.find_element(By.XPATH, selector)
                                if timestamp_element and (timestamp_element.text.strip() or timestamp_element.get_attribute('title')):
                                    logging.debug(f"Found timestamp element using selector: {selector}")
                                    break
                                else:
                                    timestamp_element = None
                            except NoSuchElementException:
                                logging.debug(f"Timestamp selector failed: {selector}")
                                continue

                        datetime_str = None
                        simple_time_text = None

                        if timestamp_element:
                            datetime_str = timestamp_element.get_attribute('title')
                            simple_time_text = timestamp_element.text

                        if not datetime_str and not simple_time_text:
                            try:
                                aria_label = post_element.get_attribute('aria-label')
                                if aria_label and (' ago' in aria_label or ' at ' in aria_label):
                                    logging.debug(f"Attempting to extract timestamp from aria-label: {aria_label}")
                                    time_match = re.search(r'\b(\d+\s+(?:second|minute|hour|day|week|month|year)s? ago|at .*)$', aria_label)
                                    if time_match:
                                        simple_time_text = time_match.group(0).strip()
                                        logging.debug(f"Extracted potential timestamp from aria-label: {simple_time_text}")

                            except Exception as e:
                                logging.debug(f"Error extracting timestamp from aria-label: {e}")
                                pass

                        if datetime_str:
                            try:
                                posted_at = datetime.strptime(datetime_str, "%A, %d %B %Y at %I:%M %p")
                                logging.debug(f"Parsed full datetime from title: {posted_at}")
                            except ValueError:
                                logging.warning(f"Could not parse detailed timestamp format '{datetime_str}' for post (ID: {post_id}).")
                                if simple_time_text:
                                    try:
                                        posted_at = parse(simple_time_text, fuzzy=True)
                                        logging.debug(f"Parsed simple/relative time text '{simple_time_text}' using dateutil: {posted_at}")
                                    except Exception as parse_e:
                                        logging.warning(f"Could not parse simple/relative time text '{simple_time_text}' using dateutil for post (ID: {post_id}): {parse_e}")
                                        posted_at = None
                                else:
                                    posted_at = None
                        elif simple_time_text:
                            logging.warning(f"Timestamp element found but 'title' attribute is missing for post (ID: {post_id}). Attempting to parse simple text: '{simple_time_text}'")
                            try:
                                posted_at = parse(simple_time_text, fuzzy=True)
                                logging.debug(f"Parsed simple/relative time text '{simple_time_text}' using dateutil: {posted_at}")
                            except Exception as parse_e:
                                logging.warning(f"Could not parse simple/relative time text '{simple_time_text}' using dateutil for post (ID: {post_id}): {parse_e}")
                                posted_at = None
                        else:
                            logging.debug(f"Timestamp element found but no text or title attribute for post (ID: {post_id}).")
                            posted_at = None

                    except NoSuchElementException:
                        logging.warning(f"Could not find any standard timestamp element for post (ID: {post_id}, URL: {post_url}). Timestamp will be None.")
                        logging.debug(f"HTML of post element where timestamp extraction failed for post (ID: {post_id}, URL: {post_url}): {post_element.get_attribute('outerHTML')}")
                        posted_at = None
                    except Exception as e:
                         logging.warning(f"An error occurred during timestamp extraction for post (ID: {post_id}, URL: {post_url}): {e}")
                         logging.debug(f"HTML of post element where timestamp extraction failed for post (ID: {post_id}, URL: {post_url}): {post_element.get_attribute('outerHTML')}")
                         posted_at = None

                    logging.info(f"Extracted posted_at for {post_id}: '{posted_at}'")
                    if posted_at is None:
                        logging.debug(f"HTML of post element where timestamp extraction failed: {post_element.get_attribute('outerHTML')}")

                    if (post_url or post_id) and (post_text != "N/A" or posted_at is not None or post_author_name is not None):
                         scraped_posts.append({
                             "facebook_post_id": post_id,
                             "post_url": post_url,
                             "content_text": post_text,
                             "posted_at": posted_at.isoformat() if isinstance(posted_at, datetime) else str(posted_at) if posted_at is not None else None,
                             "scraped_at": datetime.now().isoformat(),
                             "post_author_name": post_author_name,
                             "post_author_profile_pic_url": post_author_profile_pic_url,
                             "post_image_url": post_image_url,
                             "comments": comments_data
                         })
                         extracted_count += 1
                         if post_url: processed_post_urls.add(post_url)
                         if post_id: processed_post_ids.add(post_id)

                         logging.info(f"Post {extracted_count} (ID: {post_id}) - Extracted Text: '{post_text}', Timestamp: '{posted_at}'")

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