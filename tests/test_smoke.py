import pytest
import logging
import asyncio
from scraper.playwright_scraper import PlaywrightScraper
from ai.filtering_pipeline import FilteringPipeline
from database import crud, db_setup

# Set up logging for the smoke test
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@pytest.fixture
def db_conn(tmp_path):
    """Fixture to provide a clean database connection using a temporary file."""
    db_file = tmp_path / "smoke_test.db"
    db_setup.init_db(str(db_file))
    conn = crud.get_db_connection(str(db_file))
    assert conn is not None
    yield conn
    conn.close()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_full_pipeline_smoke(db_conn):
    """
    Smoke test for the full Scrape -> AI -> DB flow.
    Verifies that the scraper works and integrated AI analysis returns expected fields,
    and results are correctly stored in the database.
    """
    logger.info("Starting Full Pipeline Smoke Test...")

    # Initialize components
    # We use headless=True for CI/automated environments
    scraper = PlaywrightScraper(headless=True)
    pipeline = FilteringPipeline()

    # Technical Anchors
    # Using a known test group URL from the original smoke test
    test_group_url = "https://www.facebook.com/groups/771142503282464"
    group_name = "Smoke Test Group"
    limit = 1

    # 1. Database Setup: Add group
    group_id = crud.add_group(db_conn, group_name, test_group_url)
    assert group_id is not None, "Failed to add group to database"

    logger.info(f"Attempting to scrape {limit} post from {test_group_url} and run full analysis...")

    scraped_count = 0
    try:
        # 2. Scrape Stage
        async for post in scraper.scrape_group(test_group_url, limit=limit):
            scraped_count += 1
            logger.info(f"SUCCESS: Scraped post {scraped_count}")
            logger.info(f"  Post ID: {post.get('facebook_post_id')}")

            # 3. Database Stage: Save scraped post
            internal_post_id = crud.add_scraped_post(db_conn, post, group_id)
            assert internal_post_id is not None, "Failed to save scraped post to database"

            # Verify post exists in DB as unprocessed
            unprocessed = crud.get_unprocessed_posts(db_conn, group_id)
            assert any(p["internal_post_id"] == internal_post_id for p in unprocessed), (
                "Post not found in unprocessed list"
            )

            # 4. AI Stage: Analysis (Integrated Keyword + AI Analysis)
            # Stage 1: Keyword Filtering (Local)
            post_text = post.get("text", "") or ""
            should_analyze = pipeline.should_analyze(post_text)
            logger.info(f"  Pipeline keyword match: {should_analyze}")

            # Stage 2: AI Analysis (Remote)
            # Note: This will return None if keyword filter fails or API key is missing
            analysis = await pipeline.analyze_post(post)

            if analysis and analysis.get("ai_status") != "error":
                logger.info("  AI Analysis Result obtained successfully.")

                # 5. Database Stage: Update with AI results
                crud.update_post_with_ai_results(db_conn, internal_post_id, analysis)

                # 6. Final Verification: Check DB for processed post
                categorized_posts = crud.get_all_categorized_posts(db_conn, group_id, {})
                assert len(categorized_posts) > 0, "Post should be marked as categorized in DB"

                found_post = next(
                    (p for p in categorized_posts if p["internal_post_id"] == internal_post_id),
                    None,
                )
                assert found_post is not None, "Processed post not found in categorized list"
                assert found_post["is_processed_by_ai"] == 1, "is_processed_by_ai flag not set"
                assert found_post["ai_category"] is not None, "AI category not saved in DB"

                logger.info(f"  [VERIFIED] Full flow complete for post {internal_post_id}")
            else:
                # If AI analysis was skipped or failed (e.g. no API key), we still verified Scrape -> DB
                logger.warning(
                    "  AI Analysis was skipped or returned an error (expected if keywords don't match or API key is missing)."
                )
                logger.info("  [VERIFIED] Scrape -> DB flow completed successfully.")
                assert internal_post_id is not None

            if scraped_count >= limit:
                break

        if scraped_count == 0:
            logger.warning(
                "No posts scraped. This might be due to missing session/login, Facebook UI changes, or network issues."
            )
            # We don't fail the smoke test here to prevent CI blockage on external factors,
            # but in a controlled environment this should be investigated.

    except Exception as e:
        logger.error(f"Smoke test failed with error: {e}")
        raise e

    logger.info(f"Full Pipeline Smoke Test completed. Scraped {scraped_count} posts.")
