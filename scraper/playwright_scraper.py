import asyncio
import random
import logging
import uuid
import re
from datetime import datetime, UTC
from playwright.async_api import async_playwright, Page, ElementHandle
from tenacity import retry, stop_after_attempt, wait_exponential
from .session_manager import SessionManager
from .timestamp_parser import parse_fb_timestamp
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

                posts_yielded = 0
                processed_ids = set()
                scroll_attempts = 0
                max_scroll_attempts = limit * 5  # Allow for some empty scrolls

                while posts_yielded < limit and scroll_attempts < max_scroll_attempts:
                    try:
                        # Ensure we have content before extracting
                        await self._wait_for_content(page)
                    except Exception as e:
                        logger.warning(f"Wait for content timed out or failed: {e}")
                        # If we already have some posts, maybe we reached the end
                        if posts_yielded > 0:
                            break

                    # Dismiss any overlays that might have appeared
                    await self._dismiss_overlays(page)

                    # Extract current visible posts
                    # 2025 Selectors: div[role="article"] and data-pagelet="FeedUnit"
                    articles = await page.query_selector_all(
                        'div[role="article"], [data-pagelet^="FeedUnit"]'
                    )

                    for article in articles:
                        if posts_yielded >= limit:
                            break

                        post_data = await self._extract_post_data(article)
                        if post_data and post_data["facebook_post_id"] not in processed_ids:
                            processed_ids.add(post_data["facebook_post_id"])
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
        Uses the Discussion Tab Anchor pattern to ensure we're at the post feed.
        Includes exponential backoff retries for resilience.
        """
        target_url = url.rstrip("/")
        if "/discussion" not in target_url:
            target_url += "/discussion"

        logger.info(f"Navigating to: {target_url} (with retry support)")
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
        await page.wait_for_function(
            """() => {
                const articles = document.querySelectorAll('div[role="article"], [data-pagelet^="FeedUnit"]');
                if (articles.length === 0) return false;
                
                return Array.from(articles).some(article => {
                    const text = article.innerText || "";
                    return text.length > 100;
                });
            }""",
            timeout=30000,
        )

    async def _extract_post_data(self, element: ElementHandle) -> dict | None:
        """
        Extracts content, author, and timestamp using resilient 2025 selectors.
        """
        try:
            # Evaluate extraction script within the article element context
            data = await element.evaluate("""(article) => {
                const selectors = {
                    content: [
                        'div[data-ad-comet-preview="message"]',
                        'div[data-ad-rendering-role="story_message"]',
                        'div[dir="auto"]'
                    ],
                    author: [
                        'h2 strong a',
                        'h3 strong a',
                        'a[role="link"] strong',
                        'h2 span[dir="auto"] a',
                        'h3 span[dir="auto"] a'
                    ],
                    timestamp: [
                        'abbr[title]',
                        'a[href*="/posts/"] span[data-lexical-text="true"]',
                        'a[aria-label] span[dir="auto"]'
                    ],
                    permalink: [
                        'a[href*="/posts/"]',
                        'a[href*="/videos/"]',
                        'a[href*="/photos/"]',
                        'a[href*="/groups/"][href*="/permalink/"]'
                    ]
                };

                const findFirstMatch = (selectorsList) => {
                    for (const selector of selectorsList) {
                        const el = article.querySelector(selector);
                        if (el) return el;
                    }
                    return null;
                };

                const contentEl = findFirstMatch(selectors.content);
                const authorEl = findFirstMatch(selectors.author);
                const timestampEl = findFirstMatch(selectors.timestamp);
                const permalinkEl = findFirstMatch(selectors.permalink);

                return {
                    content_text: contentEl ? contentEl.innerText : null,
                    post_author_name: authorEl ? authorEl.innerText : null,
                    raw_timestamp: timestampEl ? (timestampEl.getAttribute('title') || timestampEl.innerText) : null,
                    post_url: permalinkEl ? permalinkEl.href : null
                };
            }""")

            if not data["content_text"] and not data["post_author_name"]:
                return None

            # Generate or extract post ID
            post_id = self._derive_post_id(data["post_url"])
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

    def _derive_post_id(self, url: str | None) -> str | None:
        """
        Helper to extract numeric or alphanumeric ID from various FB URL formats.
        """
        if not url:
            return None

        try:
            # Check for numeric ID in path
            match = re.search(r"/(?:posts|permalink|videos|photos|story)/(\d+)", url)
            if match:
                return match.group(1)

            # Check for alphanumeric ID in path
            path_parts = url.split("/")
            for part in ["posts", "permalink", "videos", "photos", "story"]:
                if part in path_parts:
                    idx = path_parts.index(part)
                    if idx + 1 < len(path_parts):
                        candidate = path_parts[idx + 1].split("?")[0]
                        if candidate:
                            return candidate

            # Check query parameters
            query_match = re.search(r"(?:story_fbid|fbid|id)=(\d+)", url)
            if query_match:
                return query_match.group(1)

        except Exception:
            pass

        return None

    async def _dismiss_overlays(self, page: Page):
        """
        Dismisses intrusive Facebook overlays using resilient selectors.
        """
        dismiss_selectors = [
            'div[role="dialog"] div[role="button"][aria-label="Close"]',
            'div[role="dialog"] div[role="button"][aria-label="Not now"]',
            'button[data-cookiebanner="accept_button"]',
            'div[aria-label="Close"]',
            'div[aria-label="Not now"]',
        ]

        for selector in dismiss_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    logger.debug(f"Overlay detected, dismissing via: {selector}")
                    await button.click()
                    await asyncio.sleep(0.5)
            except Exception:
                continue

    async def _prune_dom(self, page: Page):
        """
        Removes processed elements from the DOM to save memory.
        Facebook's feed can grow extremely large, slowing down the browser.
        Pattern: Every X posts, remove processed elements from the feed.
        """
        logger.debug("Pruning DOM to optimize memory...")
        try:
            # Select articles that are likely already processed
            # We keep the last few to ensure we don't break the infinite scroll trigger
            await page.evaluate("""() => {
                const articles = document.querySelectorAll('div[role="article"], [data-pagelet^="FeedUnit"]');
                if (articles.length > 10) {
                    // Remove all but the last 5 articles
                    for (let i = 0; i < articles.length - 5; i++) {
                        articles[i].remove();
                    }
                    console.log(`Pruned ${articles.length - 5} elements from DOM.`);
                }
            }""")
        except Exception as e:
            logger.debug(f"DOM pruning failed: {e}")
