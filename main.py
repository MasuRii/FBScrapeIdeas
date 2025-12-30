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
from database import get_db_connection
from services.group_service import GroupService
from services.scraper_service import ScraperService
from services.ai_service import AIService
from services.post_service import PostService
from cli.console import ask, print_info, print_error, print_success, print_warning

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("WDM").setLevel(logging.WARNING)
logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
# Suppress playwright logging unless it's an error
logging.getLogger("playwright").setLevel(logging.WARNING)


async def handle_scrape_command(
    scraper_service: ScraperService,
    group_url: str = None,
    group_id: int = None,
    num_posts: int = 20,
    headless: bool = False,
    engine: str = None,
):
    """Handles the Facebook scraping process for a specific group.

    Args:
        scraper_service: ScraperService instance
        group_url: URL of the Facebook group (either URL or ID must be provided)
        group_id: ID of an existing group (either URL or ID must be provided)
        num_posts: Number of posts to scrape (default: 20)
        headless: Run browser in headless mode (default: False)
        engine: Scraper engine to use ('selenium' or 'playwright')
    """
    if not group_url and not group_id:
        logging.error("Either --group-url or --group-id must be provided")
        return

    # If only group_id is provided, we need to fetch the URL from database
    # ScraperService handles URL resolution internally
    target_url = group_url or f"ID:{group_id}"

    result = await scraper_service.scrape_group(
        group_url=target_url,
        post_count=num_posts,
        headless=headless,
        engine=engine,
    )

    if result.success:
        logging.info(str(result))
    else:
        logging.error(str(result))


async def handle_manual_login_command(scraper_service: ScraperService = None):
    """Triggers the Playwright manual login process."""
    # Note: scraper_service is optional here only because legacy calls might not pass it,
    # but in the new architecture it should be passed.
    # However, since the handler signature in command_handlers expects just () if invoked directly
    # without service injection in some legacy paths, we handle it.
    # Actually, let's just instantiate it if missing for backward compatibility or direct calls.
    if not scraper_service:
        scraper_service = ScraperService()

    await scraper_service.manual_login()


async def handle_process_ai_command(ai_service: AIService, group_id: int = None):
    """Handles the AI processing of scraped posts for a specific group.

    Args:
        ai_service: AIService instance
        group_id: Optional ID of the group to process posts from. If None, processes all groups.
    """
    logging.info("Running process-ai command...")

    # Process unprocessed posts
    post_stats = await ai_service.process_pending_posts(group_id=group_id)
    logging.info(f"Processed {post_stats['processed']}/{post_stats['total_posts']} posts")

    # Process unprocessed comments
    comment_stats = await ai_service.process_pending_comments()
    logging.info(
        f"Processed {comment_stats['processed']}/{comment_stats['total_comments']} comments"
    )


def handle_view_command(
    post_service: PostService, group_id: int = None, filters: dict = None, limit: int = None
):
    """Displays posts from the database, optionally filtered by group and other criteria.

    Args:
        post_service: PostService instance
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
            choice_str = ask("Select a field to filter by or 0 to view").strip()
            choice = int(choice_str)
        except ValueError:
            print_error("Invalid input. Please enter a number.")
            continue
        except KeyboardInterrupt:
            print_warning("\nOperation cancelled.")
            return

        if choice == 0:
            break
        elif choice == -1:
            filters = {}
            print_info("All filters cleared.")
        elif 1 <= choice <= len(filterable_fields):
            selected_key = list(filterable_fields.keys())[choice - 1]
            selected_label = filterable_fields[selected_key]

            distinct_values = post_service.get_distinct_filter_values(selected_key)
            if not distinct_values:
                print_warning(f"No distinct values found for {selected_label}.")
            else:
                print(f"\nAvailable {selected_label} values:")
                for i, value in enumerate(distinct_values, start=1):
                    print(f"{i}. {value}")
                print("0. Back to field selection")

                try:
                    value_choice_str = ask(f"Select a {selected_label} value to filter by").strip()
                    value_choice = int(value_choice_str)
                except ValueError:
                    print_error("Invalid input. No value selected.")
                    value_choice = 0
                except KeyboardInterrupt:
                    print_warning("\nOperation cancelled.")
                    return

                if 1 <= value_choice <= len(distinct_values):
                    selected_value = distinct_values[value_choice - 1]
                    print_success(f"Added filter: {selected_label} = {selected_value}")
                    filters[selected_key] = selected_value
                elif value_choice != 0:
                    print_error("Invalid choice.")
        else:
            print_error("Invalid choice. Please try again.")

    if filters:
        print("\nActive filters:")
        for key, value in filters.items():
            field_label = filterable_fields.get(key, key)
            print(f"- {field_label}: {value}")
    else:
        print("\nNo active filters")

    try:
        posts = post_service.get_filtered_posts(group_id, filters, limit)

        if not posts:
            print_info("No categorized posts found in the database.")
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

            comments = post_service.get_post_comments(post["internal_post_id"])
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


def handle_add_group_command(group_service: GroupService, group_name: str, group_url: str):
    """Handles adding a new Facebook group to track."""
    logging.info(f"Adding new group: {group_name} ({group_url})")

    group_id = group_service.add_group(url=group_url, name=group_name)
    if group_id:
        logging.info(f"Successfully added group with ID: {group_id}")
    else:
        logging.error("Failed to add group - it may already exist")


def handle_list_groups_command(group_service: GroupService):
    """Handles listing all tracked Facebook groups."""
    logging.info("Listing all groups...")

    groups = group_service.get_all_groups()
    if not groups:
        logging.info("No groups found in database.")
        return

    logging.info("\n===== Tracked Groups =====")
    for group in groups:
        print(f"ID: {group['group_id']}")
        print(f"Name: {group['group_name']}")
        print(f"URL: {group['group_url']}")
        print("-" * 20)


def handle_remove_group_command(group_service: GroupService, group_id: int):
    """Handles removing a group and its posts from tracking."""
    logging.info(f"Removing group with ID: {group_id}")

    if group_service.remove_group(group_id):
        logging.info(f"Successfully removed group (ID: {group_id})")
    else:
        logging.error(f"Failed to remove group {group_id}")


def handle_stats_command(post_service: PostService):
    """Handles the stats command to display summary statistics."""
    try:
        stats = post_service.get_statistics()
        if not stats:
            logging.info("No statistics available (database may be empty or error occurred).")
            return

        print("\n===== Database Statistics =====")
        print(f"Total Posts: {stats.get('total_posts', 0)}")
        print(f"Unprocessed Posts: {stats.get('unprocessed_posts', 0)}")
        print(f"Total Comments: {stats.get('total_comments', 0)}")
        print(f"Average Comments per Post: {stats.get('avg_comments_per_post', 0)}")

        print("\nPosts per Category:")
        for category, count in stats.get("posts_per_category", []):
            print(f"  {category}: {count}")

        print("\nTop Authors by Post Count:")
        for author, count in stats.get("top_authors", []):
            print(f"  {author}: {count} posts")

    except Exception as e:
        logging.error(f"Error generating statistics: {e}")


def check_first_run():
    """Check if this is first run and offer setup wizard."""
    if is_first_run():
        print("\n" + "=" * 60)
        print("  Welcome to FB Scrape Ideas!")
        print("=" * 60)
        print("\nIt looks like this is your first time running the app.")
        print("Let's set up your credentials.\n")

        try:
            setup = ask("Run setup now? (y/n)").lower().strip()
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
    from cli.console import safe_print

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
        safe_print("\n✅ System is healthy.")
        sys.exit(0)
    else:
        safe_print("\n❌ System health issues detected.")
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

    # Initialize services
    try:
        group_service = GroupService()
        scraper_service = ScraperService()
        ai_service = AIService()
        post_service = PostService()
        logging.info("All services initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        return

    # Database validation check (keep existing logic)
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

    # Create command handlers
    command_handlers = {
        "scrape": handle_scrape_command,
        "process_ai": handle_process_ai_command,
        "manual_login": lambda: asyncio.run(
            handle_manual_login_command(scraper_service)
        ),  # Fixed signature issue
        "view": handle_view_command,
        "export": handle_export_command,
        "add_group": handle_add_group_command,
        "list_groups": handle_list_groups_command,
        "remove_group": handle_remove_group_command,
        "stats": handle_stats_command,
        "health": handle_health_check,
    }

    run_cli(command_handlers, scraper_service, ai_service, group_service, post_service)


if __name__ == "__main__":
    main()
