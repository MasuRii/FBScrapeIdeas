import argparse
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, UTC
import pytest

# Add project root to sys.path to allow imports from scraper/ and config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.playwright_scraper import PlaywrightScraper
from config import has_facebook_credentials, get_project_root
import scraper.js_logic as js_logic

# Setup logging to both console and file
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
stress_log_file = LOG_DIR / "stress_test.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(stress_log_file)],
)
logger = logging.getLogger(__name__)


class StressTestScraper(PlaywrightScraper):
    """
    Subclass of PlaywrightScraper that adds diagnostic capture capabilities
    for identifying the root cause of the "blackout" (empty feed) issue.
    """

    def __init__(self, headless=True):
        super().__init__(headless=headless)
        self.consecutive_empty_scrolls = 0
        self.posts_since_last_scroll = 0
        self.console_logs = []
        self.diagnostics_captured = False
        self.current_page = None
        self.session_id = uuid.uuid4().hex[:8]

    async def capture_diagnostics(self, page, label="blackout"):
        """Captures screenshot, HTML, and console logs from the page."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        screenshot_path = LOG_DIR / f"{label}_repro_{self.session_id}_{timestamp}.png"
        html_path = LOG_DIR / f"{label}_repro_{self.session_id}_{timestamp}.html"
        console_path = LOG_DIR / f"{label}_repro_{self.session_id}_{timestamp}_console.log"

        logger.error(f"Capturing diagnostics (label: {label}) to {LOG_DIR}...")

        try:
            await page.screenshot(path=str(screenshot_path))
            html = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            with open(console_path, "w", encoding="utf-8") as f:
                for entry in self.console_logs:
                    f.write(f"{entry}\n")

            # Check DOM state
            article_selector = self.selector_registry.get_selector("article")
            articles_count = await page.evaluate(
                f"document.querySelectorAll('{article_selector}').length"
            )
            feed_container_selector = self.selector_registry.get_selector("feed_container")
            feed_exists = await page.evaluate(
                f"document.querySelector('{feed_container_selector}') !== null"
            )

            logger.error(f"DIAGNOSTIC SUMMARY:")
            logger.error(f" - Screenshot: {screenshot_path}")
            logger.error(f" - HTML Source: {html_path}")
            logger.error(f" - Console Logs: {console_path}")
            logger.error(f" - Article Count: {articles_count}")
            logger.error(f" - Feed Container Exists: {feed_exists}")

        except Exception as e:
            logger.error(f"Failed to capture diagnostics: {e}")

    async def _scroll_gradually(self, page):
        """Overrides scroll to track empty yields and trigger diagnostics."""
        # Attach console listener if not already set
        if not hasattr(page, "_diagnostic_listener_set"):
            page.on(
                "console",
                lambda msg: self.console_logs.append(
                    f"[{datetime.now().isoformat()}] [{msg.type}] {msg.text}"
                ),
            )
            page._diagnostic_listener_set = True
            self.current_page = page

        # Log heartbeat before scroll
        article_selector = self.selector_registry.get_selector("article")
        articles_before = await page.evaluate(
            f"document.querySelectorAll('{article_selector}').length"
        )
        logger.info(f"Heartbeat: {articles_before} articles in DOM before scroll.")

        # Check if we yielded any posts since last scroll
        if self.posts_since_last_scroll == 0:
            self.consecutive_empty_scrolls += 1
            logger.warning(
                f"Heartbeat: 0 new posts yielded in last interval (Consecutive: {self.consecutive_empty_scrolls}/3)"
            )

            if self.consecutive_empty_scrolls >= 3:
                logger.error(
                    "!!! DETECTED POTENTIAL BLACKOUT: 3 consecutive scrolls with 0 new posts !!!"
                )
                await self.capture_diagnostics(page, label="empty_scroll")
        else:
            self.consecutive_empty_scrolls = 0

        self.posts_since_last_scroll = 0  # Reset counter for next scroll interval

        # Call original scroll logic
        await super()._scroll_gradually(page)

    async def _extract_post_data(self, element):
        """Overrides extraction to count successfully extracted posts."""
        data = await super()._extract_post_data(element)
        if data:
            self.posts_since_last_scroll += 1
        return data


async def run_stress_test(limit=100, headless=True, url=None):
    """Main orchestration for the stress test."""
    if not url:
        url = os.getenv("TEST_GROUP_URL", "https://www.facebook.com/groups/457688055182211")

    logger.info(f"Starting Stress Test on: {url}")
    logger.info(f"Target: {limit} posts. Mode: {'HEADLESS' if headless else 'HEADED'}")

    if not has_facebook_credentials():
        logger.warning(
            "No Facebook credentials found in environment. Scraper might be blocked by login wall."
        )

    scraper = StressTestScraper(headless=headless)
    total_unique_scraped = 0
    unique_ids = set()
    run_count = 0
    max_runs = 5  # Attempt up to 5 restarts to reach goal

    while total_unique_scraped < limit and run_count < max_runs:
        run_count += 1
        logger.info(
            f"--- RUN #{run_count} STARTING (Total Unique: {total_unique_scraped}/{limit}) ---"
        )

        try:
            # We use a slightly larger limit for the scraper to account for duplicates it might see internally
            # but we track unique ones ourselves here.
            async for post in scraper.scrape_group(url, limit=limit + 20):
                post_id = post["facebook_post_id"]
                if post_id not in unique_ids:
                    unique_ids.add(post_id)
                    total_unique_scraped += 1

                    if total_unique_scraped % 10 == 0:
                        logger.info(
                            f"✅ PROGRESS: {total_unique_scraped}/{limit} unique posts reached."
                        )

                    if total_unique_scraped >= limit:
                        logger.info(f"Goal reached: {total_unique_scraped} unique posts.")
                        break

            if total_unique_scraped < limit:
                logger.warning(
                    f"Run #{run_count} finished early with {total_unique_scraped} total unique posts. Restarting in 5s..."
                )
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Run #{run_count} crashed: {e}", exc_info=True)
            await asyncio.sleep(10)

    if total_unique_scraped >= limit:
        logger.info(f"SUCCESS: Stress test completed. Scraped {total_unique_scraped} unique posts.")
        return True
    else:
        logger.error(
            f"FAILED: Reached max runs ({max_runs}) without hitting target. Final count: {total_unique_scraped}"
        )
        return False


@pytest.mark.asyncio
async def test_scrolling_stress_pytest():
    """Pytest entry point for the stress test."""
    # For CI/automated testing, we might want a smaller limit or use headless
    limit = int(os.getenv("STRESS_TEST_LIMIT", "50"))
    success = await run_stress_test(limit=limit, headless=True)
    assert success


async def main():
    """Standalone entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Facebook Scraper Scrolling Stress Test")
    parser.add_argument(
        "--limit", type=int, default=100, help="Number of posts to scrape (default: 100)"
    )
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (default)")
    parser.add_argument("--url", type=str, help="Target group URL")

    args = parser.parse_args()

    headless = True
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    success = await run_stress_test(limit=args.limit, headless=headless, url=args.url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Ensure logs directory exists
    LOG_DIR.mkdir(exist_ok=True)

    # Run the main async loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stress test interrupted by user.")
