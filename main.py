import argparse
import asyncio
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Optional

from config import (
    get_db_path,
    get_env_file_path,
    is_first_run,
    run_setup_wizard,
    get_scraper_engine,
)
from scraper.webdriver_setup import init_webdriver
from database.crud import (
    add_comments_for_post,
    add_group,
    add_scraped_post,
    get_all_categorized_posts,
    get_comments_for_post,
    get_db_connection,
    get_distinct_values,
    get_group_by_id,
    get_unprocessed_comments,
    get_unprocessed_posts,
    list_groups,
    remove_group,
    update_comment_with_ai_results,
    update_post_with_ai_results,
)
from database.stats_queries import get_all_statistics

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("WDM").setLevel(logging.WARNING)
logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
# Suppress playwright logging unless it's an error
logging.getLogger("playwright").setLevel(logging.WARNING)


def get_or_create_group_id(
    conn: sqlite3.Connection, group_url: str, group_name: str = None
) -> int | None:
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
        logging.error(f"Error getting/creating group: {e}")
        conn.rollback()
        return None


async def handle_scrape_command(
    group_url: str = None,
    group_id: int = None,
    num_posts: int = 20,
    headless: bool = False,
    engine: str = None,
):
    """Handles the Facebook scraping process for a specific group.

    Args:
        group_url: URL of the Facebook group (either URL or ID must be provided)
        group_id: ID of an existing group (either URL or ID must be provided)
        num_posts: Number of posts to scrape (default: 20)
        headless: Run browser in headless mode (default: False)
        engine: Scraper engine to use ('selenium' or 'playwright')
    """
    if not group_url and not group_id:
        logging.error("Either --group-url or --group-id must be provided")
        return

    engine = engine or get_scraper_engine()
    logging.info(
        f"Running scrape command (fetching {num_posts} posts) using {engine} engine. Headless: {headless}"
    )

    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        if group_url and not group_id:
            group_id = get_or_create_group_id(conn, group_url)
            if not group_id:
                logging.error("Failed to resolve or create group from URL")
                return
        elif group_id and not group_url:
            # Fetch group URL from database if only ID is provided
            group_info = get_group_by_id(conn, group_id)
            if not group_info:
                logging.error(f"Group with ID {group_id} not found in database")
                return
            group_url = group_info["group_url"]
            logging.info(f"Using group URL from database: {group_url}")

        if engine == "playwright":
            from scraper.playwright_scraper import PlaywrightScraper
            from ai.filtering_pipeline import FilteringPipeline

            scraper = PlaywrightScraper(headless=headless)
            pipeline = FilteringPipeline()

            logging.info("Initializing Playwright engine...")

            added_count = 0
            scraped_count = 0

            async for post in scraper.scrape_group(group_url or f"ID:{group_id}", limit=num_posts):
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
                    internal_post_id = add_scraped_post(conn, db_post, group_id)
                    if internal_post_id:
                        added_count += 1
                        # Note: Playwright scraper currently doesn't deep-scrape comments in the main loop
                        # but we could add that later.
                    else:
                        logging.warning(
                            f"Post already exists or failed to add: {db_post.get('post_url')}"
                        )
                except Exception as e:
                    logging.error(f"Error saving post {db_post.get('post_url')}: {e}")

            logging.info(f"\nScrape Summary ({engine}):")
            logging.info(f"  Total Scraped: {scraped_count}")
            logging.info(f"  New Posts Added: {added_count}")
            logging.info(f"  AI Analyzed: {pipeline.processed_count}")
            logging.info(f"  AI Skipped: {pipeline.skipped_count}")

        else:  # Legacy Selenium engine
            from config import get_facebook_credentials
            from scraper.facebook_scraper import login_to_facebook, scrape_authenticated_group
            from ai.filtering_pipeline import FilteringPipeline

            username, password = get_facebook_credentials()
            logging.info("Initializing Selenium WebDriver...")
            driver = init_webdriver(headless=headless)
            pipeline = FilteringPipeline()

            try:
                login_success = login_to_facebook(driver, username, password)
                if login_success:
                    scraped_posts_generator = scrape_authenticated_group(
                        driver,
                        group_url or f"ID:{group_id}",
                        num_posts,
                    )
                    added_count = 0
                    scraped_count = 0
                    for post in scraped_posts_generator:
                        scraped_count += 1

                        # Real-time AI Filtering & Analysis (Legacy adaptation)
                        # FacebookScraper returns dicts that match add_scraped_post expectations
                        # but we need 'post_content_raw' for the pipeline
                        db_post = post.copy()
                        if "post_content_raw" not in db_post and "content_text" in db_post:
                            db_post["post_content_raw"] = db_post["content_text"]

                        analysis = await pipeline.analyze_post(db_post)
                        if analysis:
                            db_post.update(analysis)
                            db_post["is_processed_by_ai"] = 1
                        else:
                            db_post["is_processed_by_ai"] = 0

                        try:
                            internal_post_id = add_scraped_post(conn, db_post, group_id)
                            if internal_post_id:
                                added_count += 1
                                if post.get("comments"):
                                    add_comments_for_post(conn, internal_post_id, post["comments"])
                        except Exception as e:
                            logging.error(f"Error saving post {post.get('post_url')}: {e}")

                    logging.info(f"\nScrape Summary ({engine}):")
                    logging.info(f"  Total Scraped: {scraped_count}")
                    logging.info(f"  New Posts Added: {added_count}")
                    logging.info(f"  AI Analyzed: {pipeline.processed_count}")
                    logging.info(f"  AI Skipped: {pipeline.skipped_count}")
                else:
                    logging.error("Facebook login failed.")
            finally:
                if driver:
                    driver.quit()

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


async def handle_manual_login_command():
    """Triggers the Playwright manual login process."""
    from scraper.session_manager import SessionManager
    from config import SESSION_STATE_PATH
    import playwright.async_api

    manager = SessionManager(SESSION_STATE_PATH)
    async with playwright.async_api.async_playwright() as p:
        await manager.manual_login(p)


async def handle_process_ai_command(group_id: int = None):
    """Handles the AI processing of scraped posts for a specific group.

    Args:
        group_id: Optional ID of the group to process posts from. If None, processes all groups.
    """
    from ai.gemini_service import create_post_batches
    from ai.provider_factory import get_ai_provider

    logging.info("Running process-ai command...")

    # Get AI provider
    try:
        ai_provider = get_ai_provider()
        logging.info(
            f"Using AI provider: {ai_provider.provider_name} ({ai_provider.get_model_name()})"
        )
    except Exception as e:
        logging.error(f"Failed to initialize AI provider: {e}")
        return

    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        unprocessed_posts = get_unprocessed_posts(conn, group_id)
        if not unprocessed_posts:
            logging.info("No unprocessed posts found in the database.")
        else:
            logging.info(f"Retrieved {len(unprocessed_posts)} unprocessed posts from the database.")
            for i, post in enumerate(unprocessed_posts[: min(5, len(unprocessed_posts))]):
                logging.debug(
                    f"  Post {i + 1}: ID={post.get('internal_post_id')}, URL={post.get('post_url')}"
                )

            logging.info(f"Found {len(unprocessed_posts)} unprocessed posts. Creating batches...")
            post_batches = create_post_batches(unprocessed_posts)

            processed_count = 0
            for i, batch in enumerate(post_batches):
                logging.info(
                    f"Processing batch {i + 1}/{len(post_batches)} with {len(batch)} posts..."
                )
                try:
                    ai_results = await ai_provider.analyze_posts_batch(batch)

                    if ai_results:
                        logging.info(
                            f"Received {len(ai_results)} mapped AI results for batch {i + 1}."
                        )
                        for result in ai_results:
                            internal_post_id = result.get("internal_post_id")
                            if internal_post_id is not None:
                                try:
                                    logging.debug(
                                        f"Attempting to update post {internal_post_id} with AI results."
                                    )
                                    update_post_with_ai_results(conn, internal_post_id, result)
                                    logging.debug(
                                        f"Successfully updated post {internal_post_id} with AI results."
                                    )
                                    processed_count += 1
                                except Exception as db_e:
                                    logging.error(
                                        f"Error updating post {internal_post_id} with AI results: {db_e}"
                                    )
                            else:
                                logging.error(
                                    f"AI result missing 'internal_post_id'. Cannot update database for result: {result}"
                                )
                    else:
                        logging.warning(f"No AI results returned or mapped for batch {i + 1}.")
                except Exception as batch_e:
                    logging.error(f"Error processing batch {i + 1}: {batch_e}")

            logging.info(f"Successfully processed {processed_count} posts with AI.")

        unprocessed_comments = get_unprocessed_comments(conn)
        if not unprocessed_comments:
            logging.info("No unprocessed comments found in the database.")
        else:
            logging.info(
                f"Found {len(unprocessed_comments)} unprocessed comments. Processing in batches..."
            )
            batch_size = 5
            comment_batches = [
                unprocessed_comments[i : i + batch_size]
                for i in range(0, len(unprocessed_comments), batch_size)
            ]
            processed_comment_count = 0
            for i, batch in enumerate(comment_batches):
                logging.info(
                    f"Processing comment batch {i + 1}/{len(comment_batches)} with {len(batch)} comments..."
                )
                try:
                    ai_comment_results = ai_provider.analyze_comments_batch(batch)
                    if ai_comment_results:
                        logging.info(
                            f"Received {len(ai_comment_results)} mapped AI results for comment batch {i + 1}."
                        )
                        for result in ai_comment_results:
                            comment_id = result.get("comment_id")
                            if comment_id is not None:
                                try:
                                    update_comment_with_ai_results(conn, comment_id, result)
                                    processed_comment_count += 1
                                except Exception as db_e:
                                    logging.error(
                                        f"Error updating comment {comment_id} with AI results: {db_e}"
                                    )
                            else:
                                logging.error(
                                    f"AI result missing 'comment_id'. Cannot update database for result: {result}"
                                )
                    else:
                        logging.warning(
                            f"No AI results returned or mapped for comment batch {i + 1}."
                        )
                except Exception as batch_e:
                    logging.error(f"Error processing comment batch {i + 1}: {batch_e}")

            logging.info(f"Successfully processed {processed_comment_count} comments with AI.")

    except Exception as e:
        logging.error(
            f"An error occurred during AI processing or database update: {e}",
            exc_info=True,
        )
    finally:
        try:
            conn.close()
        except Exception as e:
            logging.warning(f"Error closing database connection: {e}")


def handle_view_command(group_id: int = None, filters: dict = None, limit: int = None):
    """Displays posts from the database, optionally filtered by group and other criteria.

    Args:
        group_id: Optional ID of the group to view posts from
        filters: Dictionary of additional filters to apply
        limit: Maximum number of posts to display
    """
    if filters is None:
        filters = {}

    while True:
        filterable_fields = {
            "ai_category": "Category",
            "post_author_name": "Author Name",
            "ai_is_potential_idea": "Potential Idea",
        }
        print("\nAvailable filter fields:")
        for i, (_field_key, field_label) in enumerate(filterable_fields.items(), start=1):
            print(f"{i}. {field_label}")
        print("0. Apply filters and view posts")
        print("-1. Clear all filters")

        try:
            choice = int(input("Select a field to filter by or 0 to view: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return

        if choice == 0:
            break
        elif choice == -1:
            filters = {}
            print("All filters cleared.")
        elif 1 <= choice <= len(filterable_fields):
            selected_key = list(filterable_fields.keys())[choice - 1]
            selected_label = filterable_fields[selected_key]

            conn = get_db_connection()
            if conn:
                try:
                    distinct_values = get_distinct_values(conn, selected_key)
                    if not distinct_values:
                        print(f"No distinct values found for {selected_label}.")
                    else:
                        print(f"\nAvailable {selected_label} values:")
                        for i, value in enumerate(distinct_values, start=1):
                            print(f"{i}. {value}")
                        print("0. Back to field selection")

                        try:
                            value_choice = int(
                                input(f"Select a {selected_label} value to filter by: ")
                            )
                        except ValueError:
                            print("Invalid input. No value selected.")
                            value_choice = 0
                        except KeyboardInterrupt:
                            print("\nOperation cancelled.")
                            return

                        if 1 <= value_choice <= len(distinct_values):
                            selected_value = distinct_values[value_choice - 1]
                            print(f"Added filter: {selected_label} = {selected_value}")
                            filters[selected_key] = selected_value
                        elif value_choice != 0:
                            print("Invalid choice.")
                except Exception as e:
                    print(f"Error retrieving distinct values: {e}")
                finally:
                    conn.close()
            else:
                print("Could not connect to the database.")
        else:
            print("Invalid choice. Please try again.")

    if filters:
        print("\nActive filters:")
        for key, value in filters.items():
            field_label = filterable_fields.get(key, key)
            print(f"- {field_label}: {value}")
    else:
        print("\nNo active filters")

    conn = get_db_connection()
    if conn:
        try:
            if limit:
                filters["limit"] = limit

            filter_field = filters.pop("field", None)
            filter_value = filters.pop("value", None) if "value" in filters else None

            posts = (
                get_all_categorized_posts(conn, group_id, filters, filter_field, filter_value)
                if group_id
                else get_all_categorized_posts(conn, None, filters, filter_field, filter_value)
            )
            if not posts:
                print("No categorized posts found in the database.")
                return

            print(f"Found {len(posts)} categorized posts:")
            for post in posts:
                print("-" * 20)
                print(f"Post URL: {post.get('post_url', 'N/A')}")
                print(f"Author: {post.get('post_author_name', 'N/A')}")
                if post.get("post_author_profile_pic_url"):
                    print(f"Author Profile Pic: {post['post_author_profile_pic_url']}")
                if post.get("post_image_url"):
                    print(f"Post Image: {post['post_image_url']}")
                print(f"Posted At: {post.get('posted_at', 'N/A')}")
                print(f"Content: {post.get('post_content_raw', 'N/A')}")
                print(f"Category: {post.get('ai_category', 'N/A')}")
                if post.get("ai_sub_category"):
                    print(f"Sub-category: {post['ai_sub_category']}")
                print(f"Summary: {post.get('ai_summary', 'N/A')}")
                print(f"Potential Idea: {'Yes' if post.get('ai_is_potential_idea') else 'No'}")
                if post.get("ai_keywords"):
                    if isinstance(post["ai_keywords"], list):
                        print(f"Keywords: {', '.join(post['ai_keywords'])}")
                    else:
                        print(f"Keywords: {post['ai_keywords']}")
                if post.get("ai_reasoning"):
                    print(f"Reasoning: {post['ai_reasoning']}")

                comments = get_comments_for_post(conn, post["internal_post_id"])
                if comments:
                    print("  Comments:")
                    for comment in comments:
                        print(f"    - Commenter: {comment.get('commenter_name', 'N/A')}")
                        if comment.get("commenter_profile_pic_url"):
                            print(f"      Pic: {comment['commenter_profile_pic_url']}")
                        print(f"      Text: {comment.get('comment_text', 'N/A')}")
                else:
                    print("  No comments.")

        except Exception as e:
            print(f"An error occurred during viewing posts: {e}")
        finally:
            conn.close()
    else:
        print("Could not connect to the database.")


def handle_export_command(args):
    """Handles the export-data command."""
    from export import exporter

    filters = {
        "category": args.category,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "post_author": args.post_author,
        "comment_author": args.comment_author,
        "keyword": args.keyword,
        "min_comments": args.min_comments,
        "max_comments": args.max_comments,
        "is_idea": args.is_idea,
    }

    filters = {k: v for k, v in filters.items() if v is not None and v != ""}

    conn = get_db_connection()
    if not conn:
        logging.error("Failed to connect to database. Export aborted.")
        return

    try:
        result = exporter.fetch_data_for_export(conn, filters, args.entity)

        has_data = any(len(data) > 0 for data in result.values())
        if not has_data:
            logging.warning("No data found for the specified filters and entity.")
            return

        paths = exporter.get_output_paths(args.output, args.format)

        if args.format == "csv":
            exporter.export_to_csv(result, args.output)
            for data_type, path in paths.items():
                if result[data_type]:
                    logging.info(
                        f"Successfully exported {len(result[data_type])} {data_type} to CSV: {path}"
                    )
        elif args.format == "json":
            exporter.export_to_json(result, args.output)
            for data_type, path in paths.items():
                if result[data_type]:
                    logging.info(
                        f"Successfully exported {len(result[data_type])} {data_type} to JSON: {path}"
                    )
        else:
            logging.error(f"Unsupported export format: {args.format}")

    except Exception as e:
        logging.error(f"Error during export: {e}", exc_info=True)
    finally:
        conn.close()


def handle_add_group_command(group_name: str, group_url: str):
    """Handles adding a new Facebook group to track."""
    logging.info(f"Adding new group: {group_name} ({group_url})")

    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        group_id = add_group(conn, group_name, group_url)
        if group_id:
            logging.info(f"Successfully added group with ID: {group_id}")
        else:
            logging.error("Failed to add group - it may already exist")
    except Exception as e:
        logging.error(f"Error adding group: {e}")
    finally:
        conn.close()


def handle_list_groups_command():
    """Handles listing all tracked Facebook groups."""
    logging.info("Listing all groups...")

    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        groups = list_groups(conn)
        if not groups:
            logging.info("No groups found in database.")
            return

        logging.info("\n===== Tracked Groups =====")
        for group in groups:
            print(f"ID: {group['group_id']}")
            print(f"Name: {group['group_name']}")
            print(f"URL: {group['group_url']}")
            print("-" * 20)
    except Exception as e:
        logging.error(f"Error listing groups: {e}")
    finally:
        conn.close()


def handle_remove_group_command(group_id: int):
    """Handles removing a group and its posts from tracking."""
    logging.info(f"Removing group with ID: {group_id}")

    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        group = get_group_by_id(conn, group_id)
        if not group:
            logging.error(f"No group found with ID: {group_id}")
            return

        if remove_group(conn, group_id):
            logging.info(f"Successfully removed group {group['group_name']} (ID: {group_id})")
        else:
            logging.error(f"Failed to remove group {group_id}")
    except Exception as e:
        logging.error(f"Error removing group: {e}")
    finally:
        conn.close()


def handle_stats_command():
    """Handles the stats command to display summary statistics."""
    conn = get_db_connection()
    if not conn:
        logging.error("Could not connect to the database.")
        return

    try:
        stats = get_all_statistics(conn)

        print("\n===== Database Statistics =====")
        print(f"Total Posts: {stats['total_posts']}")
        print(f"Unprocessed Posts: {stats['unprocessed_posts']}")
        print(f"Total Comments: {stats['total_comments']}")
        print(f"Average Comments per Post: {stats['avg_comments_per_post']}")

        print("\nPosts per Category:")
        for category, count in stats["posts_per_category"]:
            print(f"  {category}: {count}")

        print("\nTop Authors by Post Count:")
        for author, count in stats["top_authors"]:
            print(f"  {author}: {count} posts")

    except Exception as e:
        logging.error(f"Error generating statistics: {e}")
    finally:
        conn.close()


def check_first_run():
    """Check if this is first run and offer setup wizard."""
    if is_first_run():
        print("\n" + "=" * 60)
        print("  Welcome to FB Scrape Ideas!")
        print("=" * 60)
        print("\nIt looks like this is your first time running the app.")
        print("Let's set up your credentials.\n")

        try:
            setup = input("Run setup now? (y/n): ").lower().strip()
            if setup == "y":
                run_setup_wizard()
            else:
                print("\nYou can run setup later with: python main.py setup")
                print("Or credentials will be requested when needed.\n")
        except (EOFError, KeyboardInterrupt):
            print("\n\nSkipping setup. Credentials will be requested when needed.\n")


def handle_setup_command():
    """Handle the setup command to run the setup wizard."""
    print("\n" + "=" * 60)
    print("  FB Scrape Ideas - Setup")
    print("=" * 60)
    run_setup_wizard()


async def handle_health_check():
    """Performs a diagnostic check of the system's core components."""
    logging.info("Running system health check...")
    results = {"database": "UNKNOWN", "ai_provider": "UNKNOWN", "scraper_engine": "UNKNOWN"}

    # 1. Database Check
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            results["database"] = "OK"
            conn.close()
        else:
            results["database"] = "FAIL (No connection)"
    except Exception as e:
        results["database"] = f"FAIL ({str(e)})"

    # 2. AI Provider Check
    try:
        from ai.provider_factory import get_ai_provider

        provider = get_ai_provider()
        results["ai_provider"] = f"OK ({provider.provider_name})"
    except Exception as e:
        results["ai_provider"] = f"FAIL ({str(e)})"

    # 3. Scraper Engine Check
    try:
        engine = get_scraper_engine()
        if engine == "playwright":
            import playwright.async_api

            async with playwright.async_api.async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
            results["scraper_engine"] = "OK (Playwright/Chromium)"
        else:
            from scraper.webdriver_setup import init_webdriver

            driver = init_webdriver(headless=True)
            driver.quit()
            results["scraper_engine"] = "OK (Selenium/Chrome)"
    except Exception as e:
        results["scraper_engine"] = f"FAIL ({str(e)})"

    print("\n" + "=" * 30)
    print("      HEALTH CHECK REPORT")
    print("=" * 30)
    for component, status in results.items():
        print(f"{component.replace('_', ' ').title():<15}: {status}")
    print("=" * 30)

    if all("OK" in str(s) for s in results.values()):
        print("\n✅ System is healthy.")
        sys.exit(0)
    else:
        print("\n❌ System health issues detected.")
        sys.exit(1)


def main():
    """Main entry point for the FB Scrape Ideas CLI application."""
    from cli.menu_handler import run_cli

    # Check for setup command first (before full CLI parsing)
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        handle_setup_command()
        return

    # Only show first-run wizard for interactive mode (no command-line args)
    # This prevents blocking when running CLI commands
    if len(sys.argv) == 1:
        check_first_run()

    try:
        conn = get_db_connection()
        if conn is None:
            logging.error("Failed to connect to database after initialization")
            return

        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required_tables = {"Groups", "Posts", "Comments"}

        missing_tables = required_tables - tables
        if missing_tables:
            logging.error(f"Missing required tables: {missing_tables}")
            conn.close()
            return

        conn.close()
        logging.info("Database initialized successfully with all required tables.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return

    command_handlers = {
        "scrape": handle_scrape_command,
        "process_ai": handle_process_ai_command,
        "manual_login": handle_manual_login_command,
        "view": handle_view_command,
        "export": handle_export_command,
        "add_group": handle_add_group_command,
        "list_groups": handle_list_groups_command,
        "remove_group": handle_remove_group_command,
        "stats": handle_stats_command,
        "health": handle_health_check,
    }

    run_cli(command_handlers)


if __name__ == "__main__":
    main()
