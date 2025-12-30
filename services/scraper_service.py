"""
Scraper Service - Orchestrates Facebook group scraping operations.

This service encapsulates the logic for scraping Facebook groups using
either the Playwright or Selenium engines, handling engine selection,
initialization, and error recovery.
"""

import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional

from config import get_facebook_credentials, get_scraper_engine
from database.crud import add_comments_for_post, add_scraped_post, get_db_connection
from scraper.webdriver_setup import init_webdriver

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""

    success: bool
    scraped_count: int
    added_count: int
    ai_processed_count: int
    ai_skipped_count: int
    error_message: Optional[str] = None

    def __str__(self) -> str:
        """Return a string summary of the scrape result."""
        if self.success:
            return (
                f"Scrape completed successfully. "
                f"Total Scraped: {self.scraped_count}, "
                f"New Posts Added: {self.added_count}, "
                f"AI Analyzed: {self.ai_processed_count}, "
                f"AI Skipped: {self.ai_skipped_count}"
            )
        else:
            return f"Scrape failed: {self.error_message}"


class ScraperService:
    """
    Service for orchestrating Facebook group scraping operations.

    This service manages the selection and execution of scraping engines
    (Playwright or Selenium), handles AI filtering integration, and provides
    a clean interface for scraping operations.
    """

    def __init__(self):
        """Initialize ScraperService."""
        self.logger = logger

    def _get_or_create_group_id(
        self, conn: sqlite3.Connection, group_url: str, group_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Gets the group_id for a given URL, creating a new group entry if it doesn't exist.

        Args:
            conn: Database connection
            group_url: URL of the Facebook group
            group_name: Optional name for the group (used when creating new group)

        Returns:
            group_id if found/created, None on error
        """
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT group_id FROM Groups WHERE group_url = ?", (group_url,))
            existing = cursor.fetchone()
            if existing:
                return existing[0]

            if not group_name:
                group_name = f"Group from {group_url}"

            cursor.execute(
                "INSERT INTO Groups (group_name, group_url) VALUES (?, ?)",
                (group_name, group_url),
            )
            conn.commit()
            return cursor.lastrowid

        except sqlite3.Error as e:
            self.logger.error(f"Error getting/creating group: {e}")
            conn.rollback()
            return None

    async def scrape_group(
        self,
        group_url: str,
        post_count: int,
        headless: bool = False,
        engine: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape posts from a Facebook group using the specified engine.

        Args:
            group_url: URL of the Facebook group
            post_count: Number of posts to scrape
            headless: Run browser in headless mode (default: False)
            engine: Scraper engine to use ('selenium' or 'playwright').
                    If None, uses the default from config.

        Returns:
            ScrapeResult: Object containing scrape statistics and status.

        Raises:
            ValueError: If engine is not 'selenium' or 'playwright'
            Exception: For unexpected errors during scraping
        """
        # Determine engine if not specified
        engine = engine or get_scraper_engine()
        engine = engine.lower()

        if engine not in ("selenium", "playwright"):
            raise ValueError(f"Invalid engine '{engine}'. Must be 'selenium' or 'playwright'.")

        self.logger.info(
            f"Starting scrape of {group_url} "
            f"(fetching {post_count} posts) using {engine} engine. "
            f"Headless: {headless}"
        )

        # Get database connection
        conn = get_db_connection()
        if not conn:
            return ScrapeResult(
                success=False,
                scraped_count=0,
                added_count=0,
                ai_processed_count=0,
                ai_skipped_count=0,
                error_message="Could not connect to the database.",
            )

        try:
            # Get or create group_id from group_url
            group_id = self._get_or_create_group_id(conn, group_url)
            if not group_id:
                return ScrapeResult(
                    success=False,
                    scraped_count=0,
                    added_count=0,
                    ai_processed_count=0,
                    ai_skipped_count=0,
                    error_message="Failed to resolve or create group from URL",
                )

            # Execute scraping with the appropriate engine
            if engine == "playwright":
                result = await self._scrape_with_playwright(
                    conn=conn,
                    group_url=group_url,
                    limit=post_count,
                    headless=headless,
                    group_id=group_id,
                )
            else:  # selenium
                result = await self._scrape_with_selenium(
                    conn=conn,
                    group_url=group_url,
                    num_posts=post_count,
                    headless=headless,
                    group_id=group_id,
                )

            return result

        except Exception as e:
            self.logger.error(f"An error occurred during scraping: {e}", exc_info=True)
            return ScrapeResult(
                success=False,
                scraped_count=0,
                added_count=0,
                ai_processed_count=0,
                ai_skipped_count=0,
                error_message=str(e),
            )
        finally:
            conn.close()

    async def _scrape_with_playwright(
        self, conn, group_url: str, limit: int, headless: bool, group_id: int
    ) -> ScrapeResult:
        """
        Scrape using the Playwright engine.

        Args:
            conn: Database connection
            group_url: URL of the Facebook group
            limit: Number of posts to scrape
            headless: Run browser in headless mode

        Returns:
            ScrapeResult with scrape statistics
        """
        from scraper.playwright_scraper import PlaywrightScraper
        from ai.filtering_pipeline import FilteringPipeline

        scraper = PlaywrightScraper(headless=headless)
        pipeline = FilteringPipeline()

        self.logger.info("Initializing Playwright engine...")

        added_count = 0
        scraped_count = 0

        try:
            async for post in scraper.scrape_group(group_url, limit=limit):
                scraped_count += 1

                # Transform Playwright format to DB format
                db_post = post.copy()

                # Real-time AI Filtering & Analysis
                analysis = await pipeline.analyze_post(db_post)
                if analysis:
                    db_post.update(analysis)
                    db_post["is_processed_by_ai"] = 1
                else:
                    db_post["is_processed_by_ai"] = 0

                try:
                    internal_post_id = add_scraped_post(conn, db_post, group_id=group_id)
                    if internal_post_id:
                        added_count += 1
                        # Note: Playwright scraper currently doesn't deep-scrape
                        # comments in the main loop, but we could add that later.
                    else:
                        self.logger.warning(
                            f"Post already exists or failed to add: {db_post.get('post_url')}"
                        )
                except Exception as e:
                    self.logger.error(f"Error saving post {db_post.get('post_url')}: {e}")

            self.logger.info(
                f"\nScrape Summary (Playwright):\n"
                f"  Total Scraped: {scraped_count}\n"
                f"  New Posts Added: {added_count}\n"
                f"  AI Analyzed: {pipeline.processed_count}\n"
                f"  AI Skipped: {pipeline.skipped_count}"
            )

            return ScrapeResult(
                success=True,
                scraped_count=scraped_count,
                added_count=added_count,
                ai_processed_count=pipeline.processed_count,
                ai_skipped_count=pipeline.skipped_count,
            )

        except Exception as e:
            self.logger.error(f"Error during Playwright scraping: {e}", exc_info=True)
            return ScrapeResult(
                success=False,
                scraped_count=scraped_count,
                added_count=added_count,
                ai_processed_count=pipeline.processed_count,
                ai_skipped_count=pipeline.skipped_count,
                error_message=str(e),
            )

    async def manual_login(self):
        """
        Triggers the Playwright manual login process.
        """
        try:
            from config import SESSION_STATE_PATH
            from scraper.session_manager import SessionManager
            import playwright.async_api

            self.logger.info("Starting manual login process...")
            manager = SessionManager(SESSION_STATE_PATH)
            async with playwright.async_api.async_playwright() as p:
                await manager.manual_login(p)

        except Exception as e:
            self.logger.error(f"Error during manual login: {e}")
            raise

    async def _scrape_with_selenium(
        self, conn, group_url: str, num_posts: int, headless: bool, group_id: int
    ) -> ScrapeResult:
        """
        Scrape using the Selenium engine.

        Args:
            conn: Database connection
            group_url: URL of the Facebook group
            num_posts: Number of posts to scrape
            headless: Run browser in headless mode

        Returns:
            ScrapeResult with scrape statistics
        """
        from scraper.facebook_scraper import login_to_facebook, scrape_authenticated_group
        from ai.filtering_pipeline import FilteringPipeline

        username, password = get_facebook_credentials()
        self.logger.info("Initializing Selenium WebDriver...")
        driver = init_webdriver(headless=headless)
        pipeline = FilteringPipeline()

        added_count = 0
        scraped_count = 0

        try:
            login_success = login_to_facebook(driver, username, password)
            if login_success:
                scraped_posts_generator = scrape_authenticated_group(
                    driver,
                    group_url,
                    num_posts,
                )
                for post in scraped_posts_generator:
                    scraped_count += 1

                    # Real-time AI Filtering & Analysis (Legacy adaptation)
                    # FacebookScraper returns dicts that match add_scraped_post
                    # expectations, but we need 'post_content_raw' for the pipeline
                    db_post = post.copy()
                    if "post_content_raw" not in db_post and "text" in db_post:
                        db_post["post_content_raw"] = db_post["text"]

                    analysis = await pipeline.analyze_post(db_post)
                    if analysis:
                        db_post.update(analysis)
                        db_post["is_processed_by_ai"] = 1
                    else:
                        db_post["is_processed_by_ai"] = 0

                    try:
                        internal_post_id = add_scraped_post(conn, db_post, group_id=group_id)
                        if internal_post_id:
                            added_count += 1
                            if post.get("comments"):
                                add_comments_for_post(conn, internal_post_id, post["comments"])
                    except Exception as e:
                        self.logger.error(f"Error saving post {post.get('post_url')}: {e}")

                self.logger.info(
                    f"\nScrape Summary (Selenium):\n"
                    f"  Total Scraped: {scraped_count}\n"
                    f"  New Posts Added: {added_count}\n"
                    f"  AI Analyzed: {pipeline.processed_count}\n"
                    f"  AI Skipped: {pipeline.skipped_count}"
                )

                return ScrapeResult(
                    success=True,
                    scraped_count=scraped_count,
                    added_count=added_count,
                    ai_processed_count=pipeline.processed_count,
                    ai_skipped_count=pipeline.skipped_count,
                )
            else:
                self.logger.error("Facebook login failed.")
                return ScrapeResult(
                    success=False,
                    scraped_count=0,
                    added_count=0,
                    ai_processed_count=0,
                    ai_skipped_count=0,
                    error_message="Facebook login failed.",
                )
        except Exception as e:
            self.logger.error(f"Error during Selenium scraping: {e}", exc_info=True)
            return ScrapeResult(
                success=False,
                scraped_count=scraped_count,
                added_count=added_count,
                ai_processed_count=pipeline.processed_count,
                ai_skipped_count=pipeline.skipped_count,
                error_message=str(e),
            )
        finally:
            if driver:
                driver.quit()
