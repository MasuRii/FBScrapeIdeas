import asyncio
import json
import random
import logging
import os
import uuid
import re
from datetime import datetime, UTC
from pathlib import Path
from playwright.async_api import async_playwright, Page, ElementHandle
from tenacity import retry, stop_after_attempt, wait_exponential

from .session_manager import SessionManager
from .timestamp_parser import parse_fb_timestamp
from .selectors import get_selector_registry
from .utils import derive_post_id
from . import js_logic
from config import SESSION_STATE_PATH, ensure_playwright_installed

logger = logging.getLogger(__name__)


class PlaywrightScraper:
    """
    Playwright-based scraper engine for Facebook groups.
    Implements 2025 best-in-class patterns for resilience and anti-detection.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        ensure_playwright_installed()
        self.session_manager = SessionManager(SESSION_STATE_PATH)
        self.selector_registry = get_selector_registry()

    async def scrape_group(self, group_url: str, limit: int = 10):
        """
        Main orchestration method for scraping a Facebook group.

        Yields:
            dict: Scraped post data.
        """
        async with async_playwright() as p:
            context = await self.session_manager.get_context(p, headless=self.headless)
            page = await context.new_page()

            try:
                await self._navigate_to_discussion(page, group_url)

                # Initial aggressive dismissal for start-up modals
                await self._dismiss_overlays_aggressive(page)

                posts_yielded = 0
                processed_ids = set()
                processed_content_hashes = (
                    set()
                )  # Track content to avoid duplicates with generated IDs
                scroll_attempts = 0
                max_scroll_attempts = limit * 5  # Allow for some empty scrolls

                while posts_yielded < limit and scroll_attempts < max_scroll_attempts:
                    # Aggressive overlay dismissal for both headless and non-headless
                    await self._dismiss_overlays_aggressive(page)

                    try:
                        # Ensure we have content before extracting
                        await self._wait_for_content(page)
                    except Exception as e:
                        logger.warning(f"Wait for content timed out or failed: {e}")
                        # If we already have some posts, maybe we reached the end
                        if posts_yielded > 0:
                            break

                    # Extract current visible posts
                    article_selector = self.selector_registry.get_selector("article")
                    articles = await page.query_selector_all(article_selector)

                    # If primary selectors fail, try to extract alternatives from DOM
                    if not articles and scroll_attempts > 2:
                        logger.warning(
                            "No articles found with current selectors. Attempting self-healing..."
                        )
                        await self._extract_and_learn_selectors(page, "article")
                        article_selector = self.selector_registry.get_selector("article")
                        articles = await page.query_selector_all(article_selector)

                    for article in articles:
                        if posts_yielded >= limit:
                            break

                        post_data = await self._extract_post_data(article)
                        if not post_data:
                            continue

                        # Deduplicate by post ID
                        if post_data["facebook_post_id"] in processed_ids:
                            continue

                        # Also deduplicate by content hash (for posts with generated IDs)
                        # Normalize text for more robust deduplication
                        normalized_text = re.sub(r"\W+", "", post_data.get("text", "").lower())
                        content_hash = hash(normalized_text[:200])

                        if content_hash in processed_content_hashes:
                            logger.debug(
                                f"Skipping duplicate post by content hash: {post_data['facebook_post_id']}"
                            )
                            continue

                        processed_ids.add(post_data["facebook_post_id"])
                        processed_content_hashes.add(content_hash)
                        posts_yielded += 1
                        logger.info(
                            f"Scraped post {posts_yielded}/{limit}: {post_data['facebook_post_id']}"
                        )
                        yield post_data

                        # Periodic DOM pruning to optimize memory
                        if posts_yielded % 5 == 0:
                            await self._prune_dom(page)

                    # Perform a gradual scroll to trigger loading more posts
                    await self._scroll_gradually(page)
                    scroll_attempts += 1

                logger.info(f"Finished scraping group. Total posts: {posts_yielded}")

            except Exception as e:
                logger.error(f"Error during group scraping: {e}", exc_info=True)
            finally:
                # Browser context is managed by SessionManager, but we should close the page
                await page.close()
                # Browser closing is handled by the async with context manager if we owned it,
                # but SessionManager.get_context returns a context from a browser it launched.
                browser = context.browser
                await context.close()
                if browser:
                    await browser.close()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True
    )
    async def _navigate_to_discussion(self, page: Page, url: str):
        """
        Navigates to the provided URL, respecting user-provided paths.
        Only appends /discussion if the URL is a bare group URL with no specific path.
        Includes exponential backoff retries for resilience.
        """
        target_url = url.rstrip("/")

        # Parse the URL to understand its structure
        # Only append /discussion if:
        # 1. URL doesn't already contain /discussion
        # 2. URL is a bare group URL (e.g., facebook.com/groups/123 or facebook.com/groups/groupname)
        # 3. URL doesn't have other paths like /about, /members, /media, etc.

        # Check if URL already has a specific path after the group identifier
        group_path_pattern = re.compile(
            r"facebook\.com/groups/[^/]+(/(?:discussion|about|members|media|events|files|announcements|photos|videos|search|buy_sell_discussion|pending_posts|permalink|posts|admin).*)?$",
            re.IGNORECASE,
        )

        match = group_path_pattern.search(target_url)
        has_specific_path = match and match.group(1) is not None

        if not has_specific_path and "/discussion" not in target_url:
            # Try the URL as-is first, then fall back to /discussion if no content
            logger.info(f"Navigating to user-provided URL: {target_url}")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            # Check if we have content on this page
            try:
                await page.wait_for_function(js_logic.CHECK_CONTENT_SCRIPT, timeout=10000)
                logger.info("Content found on provided URL, using as-is")
            except Exception:
                # No content found, try appending /discussion
                logger.info(f"No content found, trying with /discussion suffix")
                target_url += "/discussion"
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        else:
            # URL already has a specific path, use it as provided
            logger.info(f"Navigating to: {target_url}")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

        # Verify if we are actually on the discussion tab or if we need to click it
        try:
            discussion_tab = await page.query_selector('a[role="tab"]:has-text("Discussion")')
            if discussion_tab:
                is_selected = await discussion_tab.get_attribute("aria-selected")
                if is_selected != "true":
                    logger.info("Discussion tab not selected, clicking it...")
                    await discussion_tab.click()
                    await page.wait_for_load_state("networkidle")
        except Exception as e:
            logger.debug(f"Optional discussion tab click failed: {e}")

    async def _scroll_gradually(self, page: Page):
        """
        Human-mimicking scroll (800px increments with random delay).
        """
        scroll_step = random.randint(700, 950)
        logger.debug(f"Gradual scroll: {scroll_step}px")

        await page.evaluate(f"window.scrollBy(0, {scroll_step})")

        # Human-like delay after scrolling
        delay = random.uniform(1.0, 2.5)
        await asyncio.sleep(delay)

    async def _wait_for_content(self, page: Page):
        """
        Uses page.wait_for_function to detect actual text length (avoiding skeletons).
        """
        logger.debug("Waiting for DOM readiness (real content vs skeletons)...")
        article_selector = self.selector_registry.get_selector("article")
        # Escape quotes for use in JavaScript
        escaped_selector = article_selector.replace("'", "\\'")

        await page.wait_for_function(
            js_logic.WAIT_FOR_CONTENT_SCRIPT.format(selector=escaped_selector),
            timeout=30000,
        )

    async def _extract_post_data(self, element: ElementHandle) -> dict | None:
        """
        Extracts content, author, and timestamp using resilient selectors.
        Implements self-healing: on failure, extracts DOM structure for debugging.
        """
        try:
            # Build selector configuration from registry
            selectors_config = {
                "content": self.selector_registry.get_selectors_list("content"),
                "author": self.selector_registry.get_selectors_list("author"),
                "timestamp": self.selector_registry.get_selectors_list("timestamp"),
                "permalink": self.selector_registry.get_selectors_list("permalink"),
            }

            # Evaluate extraction script within the article element context
            # Updated 2025-12-29: Improved extraction logic for modern Facebook DOM
            data = await element.evaluate(js_logic.EXTRACT_POST_DATA_SCRIPT, selectors_config)

            # If extraction failed, trigger self-healing DOM analysis
            if data.get("extraction_failed") and not data.get("content_text"):
                logger.debug("Post extraction yielded no data. Analyzing DOM structure...")
                await self._analyze_article_dom(element)
                return None

            if not data["content_text"] and not data["post_author_name"]:
                return None

            # Generate or extract post ID
            post_id = derive_post_id(data["post_url"])
            if not post_id:
                post_id = f"gen_{uuid.uuid4().hex[:12]}"

            # Parse timestamp
            posted_at = None
            if data["raw_timestamp"]:
                parsed_dt = parse_fb_timestamp(data["raw_timestamp"])
                if parsed_dt:
                    posted_at = parsed_dt.isoformat()

            return {
                "facebook_post_id": post_id,
                "post_url": data["post_url"],
                "text": data["content_text"] or "N/A",
                "timestamp": posted_at,
                "author_name": data["post_author_name"] or "Anonymous",
                "post_author_profile_pic_url": None,
                "post_image_url": None,
                "scraped_at": datetime.now(UTC).isoformat(),
                "comments": [],
            }

        except Exception as e:
            logger.debug(f"Error extracting individual post data: {e}")
            return None

    async def _analyze_article_dom(self, element: ElementHandle) -> None:
        """
        Analyzes the DOM structure of an article to find potential selectors.
        Logs findings for future selector updates.
        """
        try:
            structure = await element.evaluate(js_logic.ANALYZE_DOM_SCRIPT)
            logger.debug(f"DOM analysis results: {json.dumps(structure, indent=2)}")
        except Exception as e:
            logger.debug(f"Failed to analyze article DOM: {e}")

    async def _extract_and_learn_selectors(self, page: Page, element_type: str) -> list[str]:
        """
        Extracts potential selectors from the current DOM for the given element type.
        Attempts to identify working selectors and adds them to the registry.

        Returns:
            List of discovered selector strings.
        """
        discovered = []

        try:
            if element_type == "article":
                # Look for common article-like patterns in the DOM
                candidates = await page.evaluate(js_logic.DISCOVER_SELECTORS_SCRIPT)

                for selector in candidates:
                    if selector and selector not in self.selector_registry.get_selectors_list(
                        element_type
                    ):
                        self.selector_registry.add_alternative(element_type, selector)
                        discovered.append(selector)
                        logger.info(f"Discovered new selector for {element_type}: {selector}")

        except Exception as e:
            logger.debug(f"Failed to extract selectors for {element_type}: {e}")

        return discovered

    async def _ensure_scrollable(self, page: Page) -> None:
        """
        Forces body and html to have overflow: visible to ensure scrolling is possible.
        Some overlays set overflow: hidden which blocks scrolling.
        """
        try:
            await page.evaluate(js_logic.FORCE_SCROLLABLE_SCRIPT)
            logger.debug("Forced overflow: visible on body and html")
        except Exception as e:
            logger.debug(f"Failed to force scrollable: {e}")

    async def _nuke_blocking_elements(self, page: Page) -> None:
        """
        Forcefully removes any elements that might be blocking the view or scrolling.
        Targets elements with role='presentation' or high z-index that cover the viewport.
        This is critical for headless mode where overlays can completely block interaction.
        """
        try:
            removed_count = await page.evaluate(js_logic.NUKE_BLOCKING_SCRIPT)
            if removed_count > 0:
                logger.info(f"Nuked {removed_count} blocking elements")
        except Exception as e:
            logger.debug(f"Failed to nuke blocking elements: {e}")

    async def _dismiss_overlays(self, page: Page) -> None:
        """
        Basic overlay dismissal using visible button clicks.
        """
        dismiss_selectors = self.selector_registry.get_selectors_list("dismiss_button")

        for selector in dismiss_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    logger.debug(f"Overlay detected, dismissing via: {selector}")
                    await button.click()
                    await asyncio.sleep(0.5)
            except Exception:
                continue

    async def _dismiss_overlays_aggressive(self, page: Page) -> None:
        """
        Aggressive overlay dismissal that works in both headless and non-headless modes.
        Uses multiple strategies:
        0. Focus simulation (force browser focus to enable interaction)
        1. Force scrollability (remove overflow:hidden)
        2. Press ESC key (high priority action)
        3. Try clicking visible dismiss buttons (including top-left close)
        4. Use JavaScript to force-click hidden buttons
        5. Nuke any remaining blocking elements
        """
        # Step 0: Focus simulation - critical for "sticky" overlays that wait for interaction
        try:
            await page.bring_to_front()
            await page.evaluate("window.focus()")
            await page.focus("body")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"Focus simulation failed: {e}")

        # Step 1: Force scrollability
        await self._ensure_scrollable(page)

        # Step 2: ESC key as high-priority action
        try:
            logger.debug("Pressing ESC to dismiss potential overlays...")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            # Also dispatch via JS for extra resilience in headless
            await page.evaluate(js_logic.DISPATCH_ESC_SCRIPT)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"ESC key press failed: {e}")

        # Step 3: Check if any dialogs/overlays exist
        has_overlays = await page.evaluate(js_logic.HAS_OVERLAYS_SCRIPT)

        if not has_overlays:
            logger.debug("No visible overlays detected after ESC")
            return

        logger.debug("Overlays still detected, attempting button clicks...")

        # Step 4: Try to click dismiss buttons (both visible and via JS)
        # Combine dismiss_button and close_button selectors
        dismiss_selectors = self.selector_registry.get_selectors_list("dismiss_button")
        close_selectors = self.selector_registry.get_selectors_list("close_button")
        all_selectors = list(dict.fromkeys(dismiss_selectors + close_selectors))

        dismissed = False

        for selector in all_selectors:
            try:
                # First try standard click on visible button
                button = await page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await button.click()
                        dismissed = True
                        logger.debug(f"Dismissed overlay via visible button: {selector}")
                        await asyncio.sleep(0.5)
                        break
                    else:
                        # Button exists but not visible - try JS click (headless mode fix)
                        await page.evaluate(js_logic.JS_CLICK_SCRIPT, selector)
                        dismissed = True
                        logger.debug(f"Dismissed overlay via JS click: {selector}")
                        await asyncio.sleep(0.5)
                        break
            except Exception as e:
                logger.debug(f"Failed to click {selector}: {e}")
                continue

        # Step 5: Nuke any remaining blocking elements
        await self._nuke_blocking_elements(page)

        # Step 6: Final force scrollability
        await self._ensure_scrollable(page)

        # Step 2: ESC key as high-priority action
        try:
            logger.debug("Pressing ESC to dismiss potential overlays...")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            # Also dispatch via JS for extra resilience in headless
            await page.evaluate(js_logic.DISPATCH_ESC_SCRIPT)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"ESC key press failed: {e}")

        # Step 3: Check if any dialogs/overlays exist
        has_overlays = await page.evaluate(js_logic.HAS_OVERLAYS_SCRIPT)

        if not has_overlays:
            logger.debug("No visible overlays detected after ESC")
            return

        logger.debug("Overlays still detected, attempting button clicks...")

        # Step 4: Try to click dismiss buttons (both visible and via JS)
        # Combine dismiss_button and close_button selectors
        dismiss_selectors = self.selector_registry.get_selectors_list("dismiss_button")
        close_selectors = self.selector_registry.get_selectors_list("close_button")
        all_selectors = list(dict.fromkeys(dismiss_selectors + close_selectors))

        dismissed = False

        for selector in all_selectors:
            try:
                # First try standard click on visible button
                button = await page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await button.click()
                        dismissed = True
                        logger.debug(f"Dismissed overlay via visible button: {selector}")
                        await asyncio.sleep(0.5)
                        break
                    else:
                        # Button exists but not visible - try JS click (headless mode fix)
                        await page.evaluate(js_logic.JS_CLICK_SCRIPT, selector)
                        dismissed = True
                        logger.debug(f"Dismissed overlay via JS click: {selector}")
                        await asyncio.sleep(0.5)
                        break
            except Exception as e:
                logger.debug(f"Failed to click {selector}: {e}")
                continue

        # Step 5: Nuke any remaining blocking elements
        await self._nuke_blocking_elements(page)

        # Step 6: Final force scrollability
        await self._ensure_scrollable(page)

        # Step 2: Check if any dialogs/overlays exist
        has_overlays = await page.evaluate(js_logic.HAS_OVERLAYS_SCRIPT)

        if not has_overlays:
            logger.debug("No visible overlays detected")
            return

        logger.debug("Overlays detected, attempting aggressive dismissal...")

        # Step 3: Try to click dismiss buttons (both visible and via JS)
        dismiss_selectors = self.selector_registry.get_selectors_list("dismiss_button")
        dismissed = False

        for selector in dismiss_selectors:
            try:
                # First try standard click on visible button
                button = await page.query_selector(selector)
                if button:
                    is_visible = await button.is_visible()
                    if is_visible:
                        await button.click()
                        dismissed = True
                        logger.debug(f"Dismissed overlay via visible button: {selector}")
                        await asyncio.sleep(0.5)
                        break
                    else:
                        # Button exists but not visible - try JS click (headless mode fix)
                        await page.evaluate(js_logic.JS_CLICK_SCRIPT, selector)
                        dismissed = True
                        logger.debug(f"Dismissed overlay via JS click: {selector}")
                        await asyncio.sleep(0.5)
                        break
            except Exception as e:
                logger.debug(f"Failed to click {selector}: {e}")
                continue

        # Step 4: ESC key fallback
        if not dismissed:
            try:
                logger.debug("Trying ESC key to dismiss overlay...")
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                # Also dispatch a keyboard event via JS (more reliable in headless)
                await page.evaluate(js_logic.DISPATCH_ESC_SCRIPT)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"ESC key fallback failed: {e}")

        # Step 5: Nuke any remaining blocking elements
        await self._nuke_blocking_elements(page)

        # Step 6: Final force scrollability to clean up any remaining overflow:hidden
        await self._ensure_scrollable(page)

    async def _prune_dom(self, page: Page):
        """
        Removes processed elements from the DOM to save memory.
        Facebook's feed can grow extremely large, slowing down the browser.
        Pattern: Every X posts, remove processed elements from the feed.
        """
        logger.debug("Pruning DOM to optimize memory...")
        try:
            article_selector = self.selector_registry.get_selector("article")
            escaped_selector = article_selector.replace("'", "\\'")

            await page.evaluate(js_logic.PRUNE_DOM_SCRIPT.format(selector=escaped_selector))
        except Exception as e:
            logger.debug(f"DOM pruning failed: {e}")
