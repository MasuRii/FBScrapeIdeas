import argparse
import sqlite3
import logging
import asyncio
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from database.crud import (
    get_db_connection, add_scraped_post, add_comments_for_post,
    get_unprocessed_posts, update_post_with_ai_results,
    get_all_categorized_posts, get_comments_for_post,
    get_unprocessed_comments, update_comment_with_ai_results,
    add_group, get_group_by_id, list_groups, remove_group,
    get_distinct_values
)
from database.db_setup import init_db
from database.stats_queries import get_all_statistics
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('WDM').setLevel(logging.WARNING)
logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

# Current Chrome user-agent string (Chrome 131)
CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def get_or_create_group_id(conn: sqlite3.Connection, group_url: str, group_name: str = None) -> Optional[int]:
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
            (group_name, group_url)
        )
        conn.commit()
        return cursor.lastrowid
        
    except sqlite3.Error as e:
        logging.error(f"Error getting/creating group: {e}")
        conn.rollback()
        return None


def handle_scrape_command(group_url: str = None, group_id: int = None, num_posts: int = 20, headless: bool = False):
    """Handles the Facebook scraping process for a specific group.
    
    Args:
        group_url: URL of the Facebook group (either URL or ID must be provided)
        group_id: ID of an existing group (either URL or ID must be provided)
        num_posts: Number of posts to scrape (default: 20)
        headless: Run browser in headless mode (default: False)
    """
    if not group_url and not group_id:
        logging.error("Either --group-url or --group-id must be provided")
        return

    logging.info(f"Running scrape command (fetching {num_posts} posts). Headless: {headless}")
    
    # Import scraper-specific modules here to avoid circular imports
    from scraper.facebook_scraper import login_to_facebook, scrape_authenticated_group
    from config import get_facebook_credentials

    driver = None
    conn = None
    try:
        username, password = get_facebook_credentials()
        
        logging.info("Initializing Selenium WebDriver...")
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
        
        options.add_argument(f"user-agent={CHROME_USER_AGENT}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("WebDriver initialized.")

        login_success = login_to_facebook(driver, username, password)
        
        if login_success:
            logging.info("Facebook login successful.")
            
            conn = get_db_connection()
            if conn:
                if group_url and not group_id:
                    group_id = get_or_create_group_id(conn, group_url)
                    if not group_id:
                        logging.error("Failed to resolve or create group from URL")
                        return

                scraped_posts_generator = scrape_authenticated_group(
                    driver,
                    group_url or f"ID:{group_id}",
                    num_posts,
                )
                added_count = 0
                scraped_count = 0
                for post in scraped_posts_generator:
                    scraped_count += 1
                    try:
                        internal_post_id = add_scraped_post(conn, post, group_id)
                        if internal_post_id:
                            added_count += 1
                            if post.get('comments'):
                                add_comments_for_post(conn, internal_post_id, post['comments'])
                        else:
                            logging.warning(f"Failed to add post {post.get('post_url')}. Skipping comments for this post.")
                    except Exception as e:
                        logging.error(f"Error saving post {post.get('post_url')}: {e}")
                if scraped_count > 0:
                    logging.info(f"Scraped {scraped_count} posts. Successfully added {added_count} new posts (and their comments) to the database.")
                else:
                    logging.info("No posts were scraped.")
            else:
                logging.error("Could not connect to the database.")
                
        else:
            logging.error("Facebook login failed. Cannot proceed with scraping.")

    except ValueError as e:
        logging.error(f"Configuration error: {e}")
    except Exception as e:
        logging.error(f"An error occurred during the scraping process: {e}", exc_info=True)
    finally:
        if driver:
            try:
                driver.quit()
                logging.info("WebDriver closed.")
            except Exception as e:
                logging.warning(f"Error closing WebDriver: {e}")
        if conn:
            try:
                conn.close()
                logging.info("Database connection closed.")
            except Exception as e:
                logging.warning(f"Error closing database connection: {e}")


async def handle_process_ai_command(group_id: int = None):
    """Handles the AI processing of scraped posts for a specific group.
    
    Args:
        group_id: Optional ID of the group to process posts from. If None, processes all groups.
    """
    from ai.gemini_service import create_post_batches, categorize_posts_batch, process_comments_with_gemini
    
    logging.info("Running process-ai command...")
    
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
            for i, post in enumerate(unprocessed_posts[:min(5, len(unprocessed_posts))]):
                logging.debug(f"  Post {i+1}: ID={post.get('internal_post_id')}, URL={post.get('post_url')}")

            logging.info(f"Found {len(unprocessed_posts)} unprocessed posts. Creating batches...")
            post_batches = create_post_batches(unprocessed_posts)
            
            processed_count = 0
            for i, batch in enumerate(post_batches):
                logging.info(f"Processing batch {i+1}/{len(post_batches)} with {len(batch)} posts...")
                try:
                    ai_results = await categorize_posts_batch(batch)
                    
                    if ai_results:
                        logging.info(f"Received {len(ai_results)} mapped AI results for batch {i+1}.")
                        for result in ai_results:
                            internal_post_id = result.get('internal_post_id')
                            if internal_post_id is not None:
                                try:
                                    logging.debug(f"Attempting to update post {internal_post_id} with AI results.")
                                    update_post_with_ai_results(conn, internal_post_id, result)
                                    logging.debug(f"Successfully updated post {internal_post_id} with AI results.")
                                    processed_count += 1
                                except Exception as db_e:
                                    logging.error(f"Error updating post {internal_post_id} with AI results: {db_e}")
                            else:
                                logging.error(f"AI result missing 'internal_post_id'. Cannot update database for result: {result}")
                    else:
                        logging.warning(f"No AI results returned or mapped for batch {i+1}.")
                except Exception as batch_e:
                    logging.error(f"Error processing batch {i+1}: {batch_e}")

            logging.info(f"Successfully processed {processed_count} posts with AI.")
        
        unprocessed_comments = get_unprocessed_comments(conn)
        if not unprocessed_comments:
            logging.info("No unprocessed comments found in the database.")
        else:
            logging.info(f"Found {len(unprocessed_comments)} unprocessed comments. Processing in batches...")
            batch_size = 5
            comment_batches = [unprocessed_comments[i:i+batch_size] for i in range(0, len(unprocessed_comments), batch_size)]
            processed_comment_count = 0
            for i, batch in enumerate(comment_batches):
                logging.info(f"Processing comment batch {i+1}/{len(comment_batches)} with {len(batch)} comments...")
                try:
                    ai_comment_results = process_comments_with_gemini(batch)
                    if ai_comment_results:
                        logging.info(f"Received {len(ai_comment_results)} mapped AI results for comment batch {i+1}.")
                        for result in ai_comment_results:
                            comment_id = result.get('comment_id')
                            if comment_id is not None:
                                try:
                                    update_comment_with_ai_results(conn, comment_id, result)
                                    processed_comment_count += 1
                                except Exception as db_e:
                                    logging.error(f"Error updating comment {comment_id} with AI results: {db_e}")
                            else:
                                logging.error(f"AI result missing 'comment_id'. Cannot update database for result: {result}")
                    else:
                        logging.warning(f"No AI results returned or mapped for comment batch {i+1}.")
                except Exception as batch_e:
                    logging.error(f"Error processing comment batch {i+1}: {batch_e}")
            
            logging.info(f"Successfully processed {processed_comment_count} comments with AI.")

    except Exception as e:
        logging.error(f"An error occurred during AI processing or database update: {e}", exc_info=True)
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
            'ai_category': 'Category',
            'post_author_name': 'Author Name',
            'ai_is_potential_idea': 'Potential Idea'
        }
        print("\nAvailable filter fields:")
        for i, (field_key, field_label) in enumerate(filterable_fields.items(), start=1):
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
            selected_key = list(filterable_fields.keys())[choice-1]
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
                            value_choice = int(input(f"Select a {selected_label} value to filter by: "))
                        except ValueError:
                            print("Invalid input. No value selected.")
                            value_choice = 0
                        except KeyboardInterrupt:
                            print("\nOperation cancelled.")
                            return
                        
                        if 1 <= value_choice <= len(distinct_values):
                            selected_value = distinct_values[value_choice-1]
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
                filters['limit'] = limit
                
            filter_field = filters.pop('field', None)
            filter_value = filters.pop('value', None) if 'value' in filters else None

            posts = get_all_categorized_posts(conn, group_id, filters, filter_field, filter_value) if group_id else get_all_categorized_posts(conn, None, filters, filter_field, filter_value)
            if not posts:
                print("No categorized posts found in the database.")
                return
            
            print(f"Found {len(posts)} categorized posts:")
            for post in posts:
                print("-" * 20)
                print(f"Post URL: {post.get('post_url', 'N/A')}")
                print(f"Author: {post.get('post_author_name', 'N/A')}")
                if post.get('post_author_profile_pic_url'):
                    print(f"Author Profile Pic: {post['post_author_profile_pic_url']}")
                if post.get('post_image_url'):
                    print(f"Post Image: {post['post_image_url']}")
                print(f"Posted At: {post.get('posted_at', 'N/A')}")
                print(f"Content: {post.get('post_content_raw', 'N/A')}")
                print(f"Category: {post.get('ai_category', 'N/A')}")
                if post.get('ai_sub_category'):
                    print(f"Sub-category: {post['ai_sub_category']}")
                print(f"Summary: {post.get('ai_summary', 'N/A')}")
                print(f"Potential Idea: {'Yes' if post.get('ai_is_potential_idea') else 'No'}")
                if post.get('ai_keywords'):
                     if isinstance(post['ai_keywords'], list):
                          print(f"Keywords: {', '.join(post['ai_keywords'])}")
                     else:
                          print(f"Keywords: {post['ai_keywords']}")
                if post.get('ai_reasoning'):
                     print(f"Reasoning: {post['ai_reasoning']}")

                comments = get_comments_for_post(conn, post['internal_post_id'])
                if comments:
                    print("  Comments:")
                    for comment in comments:
                        print(f"    - Commenter: {comment.get('commenter_name', 'N/A')}")
                        if comment.get('commenter_profile_pic_url'):
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
        'category': args.category,
        'start_date': args.start_date,
        'end_date': args.end_date,
        'post_author': args.post_author,
        'comment_author': args.comment_author,
        'keyword': args.keyword,
        'min_comments': args.min_comments,
        'max_comments': args.max_comments,
        'is_idea': args.is_idea
    }
    
    filters = {k: v for k, v in filters.items() if v is not None and v != ''}
    
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
        
        if args.format == 'csv':
            exporter.export_to_csv(result, args.output)
            for data_type, path in paths.items():
                if result[data_type]:
                    logging.info(f"Successfully exported {len(result[data_type])} {data_type} to CSV: {path}")
        elif args.format == 'json':
            exporter.export_to_json(result, args.output)
            for data_type, path in paths.items():
                if result[data_type]:
                    logging.info(f"Successfully exported {len(result[data_type])} {data_type} to JSON: {path}")
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
        for category, count in stats['posts_per_category']:
            print(f"  {category}: {count}")
            
        print("\nTop Authors by Post Count:")
        for author, count in stats['top_authors']:
            print(f"  {author}: {count} posts")
            
    except Exception as e:
        logging.error(f"Error generating statistics: {e}")
    finally:
        conn.close()


def main():
    """Main entry point for the FB Scrape Ideas CLI application."""
    from cli.menu_handler import run_cli
    
    try:
        init_db()
        
        conn = get_db_connection()
        if conn is None:
            logging.error("Failed to connect to database after initialization")
            return
            
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required_tables = {'Groups', 'Posts', 'Comments'}
        
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
        'scrape': handle_scrape_command,
        'process_ai': handle_process_ai_command,
        'view': handle_view_command,
        'export': handle_export_command,
        'add_group': handle_add_group_command,
        'list_groups': handle_list_groups_command,
        'remove_group': handle_remove_group_command,
        'stats': handle_stats_command
    }
    
    run_cli(command_handlers)


if __name__ == '__main__':
    main()
