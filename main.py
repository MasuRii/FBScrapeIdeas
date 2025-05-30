import argparse
import sqlite3
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from database.crud import (
    get_db_connection, add_scraped_post, add_comments_for_post,
    get_unprocessed_posts, update_post_with_ai_results,
    get_all_categorized_posts, get_comments_for_post,
    get_unprocessed_comments, update_comment_with_ai_results,
    add_group, get_group_by_id, list_groups, remove_group
)
from database.db_setup import init_db
from typing import Optional

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clear_screen():
    """Clears the terminal screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

ASCII_ART = r"""
 _____  ____        _____   __  ____    ____  ____    ___      ____  ___      ___   ____  _____
|     ||    \      / ___/  /  ]|    \  /    T|    \  /  _]    l    j|   \    /  _] /    T/ ___/
|   __j|  o  )    (   \_  /  / |  D  )Y  o  ||  o  )/  [_      |  T |    \  /  [_ Y  o  (   \_
|  l_  |     T     \__  T/  /  |    / |     ||   _/Y    _]     |  | |  D  YY    _]|     |\__  T
|   _] |  O  |     /  \ /   \_ |    \ |  _  ||  |  |   [_      |  | |     ||   [_ |  _  |/  \ |
|  T   |     |     \    \     ||  .  Y|  |  ||  |  |     T     j  l |     ||     T|  |  |\    |
l__j   l_____j      \___j\____jl__j\_jl__j__jl__j  l_____j    |____jl_____jl_____jl__j__j \___j
"""

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
    
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
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
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

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

                scraped_posts = scrape_authenticated_group(driver, group_url or f"ID:{group_id}", num_posts)
                
                added_count = 0
                if scraped_posts:
                    logging.info(f"Attempting to add {len(scraped_posts)} scraped posts and their comments to the database.")
                    for post in scraped_posts:
                        internal_post_id = add_scraped_post(conn, post, group_id)
                        if internal_post_id:
                            added_count += 1
                            if post.get('comments'):
                                add_comments_for_post(conn, internal_post_id, post['comments'])
                        else:
                            logging.warning(f"Failed to add post {post.get('post_url')}. Skipping comments for this post.")
                    logging.info(f"Successfully added {added_count} new posts (and their comments) to the database.")
                else:
                     logging.info("No posts were scraped.")
            else:
                logging.error("Could not connect to the database.")
                
        else:
            logging.error("Facebook login failed. Cannot proceed with scraping.")

    except Exception as e:
        logging.error(f"An error occurred during the scraping process: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver closed.")
        if conn:
            conn.close()
            logging.info("Database connection closed.")

def handle_process_ai_command(group_id: int = None):
    """Handles the AI processing of scraped posts for a specific group.
    
    Args:
        group_id: Optional ID of the group to process posts from. If None, processes all groups.
    """
    from ai.gemini_service import create_post_batches, categorize_posts_batch, process_comments_with_gemini
    
    logging.info("Running process-ai command...")
    
    conn = get_db_connection()
    if conn:
        try:
            unprocessed_posts = get_unprocessed_posts(conn, group_id)
            if not unprocessed_posts:
                logging.info("No unprocessed posts found in the database.")
            else:
                logging.info(f"Retrieved {len(unprocessed_posts)} unprocessed posts from the database.")
                for i, post in enumerate(unprocessed_posts[:5]):
                    logging.debug(f"  Post {i+1}: ID={post.get('internal_post_id')}, URL={post.get('post_url')}")

                logging.info(f"Found {len(unprocessed_posts)} unprocessed posts. Creating batches...")
                post_batches = create_post_batches(unprocessed_posts)
                
                processed_count = 0
                for i, batch in enumerate(post_batches):
                    logging.info(f"Processing batch {i+1}/{len(post_batches)} with {len(batch)} posts...")
                    ai_results = categorize_posts_batch(batch)
                    
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
                
                logging.info(f"Successfully processed {processed_comment_count} comments with AI.")

        except Exception as e:
            logging.error(f"An error occurred during AI processing or database update: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logging.error("Could not connect to the database.")

def handle_view_command(group_id: int = None, filters: dict = None):
    """Displays categorized posts from the database, optionally filtered by group.
    
    Args:
        group_id: Optional ID of the group to view posts from
        filters: Dictionary of additional filters to apply
    """
    filters = filters or {}
    if group_id:
        print(f"Running view command for group {group_id} with filters: {filters}")
    else:
        print(f"Running view command with filters: {filters}")
    
    conn = get_db_connection()
    if conn:
        try:
            posts = get_all_categorized_posts(conn, group_id, filters) if group_id else get_all_categorized_posts(conn, None, filters)
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
        data = exporter.fetch_data_for_export(conn, filters, args.entity)
        
        if not data:
            logging.warning("No data found for the specified filters and entity.")
            return
        
        if args.format == 'csv':
            exporter.export_to_csv(data, args.output)
            logging.info(f"Successfully exported {len(data)} records to CSV: {args.output}")
        elif args.format == 'json':
            exporter.export_to_json(data, args.output)
            logging.info(f"Successfully exported {len(data)} records to JSON: {args.output}")
        else:
            logging.error(f"Unsupported export format: {args.format}")
            
    except Exception as e:
        logging.error(f"Error during export: {e}", exc_info=True)
    finally:
        conn.close()

from database.stats_queries import get_all_statistics

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
    init_db()

    parser = argparse.ArgumentParser(description='University Group Insights Platform CLI')
    subparsers = parser.add_subparsers(dest='command')

    scrape_parser = subparsers.add_parser('scrape', help='Initiate the Facebook scraping process and store results in DB.')
    group_group = scrape_parser.add_mutually_exclusive_group(required=True)
    group_group.add_argument('--group-url', help='The URL of the Facebook group to scrape.')
    group_group.add_argument('--group-id', type=int, help='The ID of an existing group to scrape.')
    scrape_parser.add_argument('--num-posts', type=int, default=20, help='The number of posts to attempt to scrape (default: 20).')
    scrape_parser.add_argument('--headless', action='store_true', help='Run the browser in headless mode (no GUI).')

    process_ai_parser = subparsers.add_parser('process-ai', help='Fetch unprocessed posts and comments, send them to Gemini for categorization, and update DB.')
    process_ai_parser.add_argument('--group-id', type=int, help='Only process posts from this group ID.')

    view_parser = subparsers.add_parser('view', help='Display categorized posts from the database.')
    view_parser.add_argument('--group-id', type=int, help='Only show posts from this group ID.')
    view_parser.add_argument('--category', help='Optional filter to display posts of a specific category.')
    view_parser.add_argument('--start-date', help='Filter posts by start date (YYYY-MM-DD).')
    view_parser.add_argument('--end-date', help='Filter posts by end date (YYYY-MM-DD).')
    view_parser.add_argument('--post-author', help='Filter by post author name.')
    view_parser.add_argument('--comment-author', help='Filter by comment author name.')
    view_parser.add_argument('--keyword', help='Keyword search in post and comment content.')
    view_parser.add_argument('--min-comments', type=int, help='Minimum number of comments.')
    view_parser.add_argument('--max-comments', type=int, help='Maximum number of comments.')
    view_parser.add_argument('--is-idea', action='store_true', help='Filter for posts marked as potential ideas.')

    export_parser = subparsers.add_parser('export-data', help='Export data (posts or comments) to CSV or JSON file.')
    export_parser.add_argument('--format', required=True, choices=['csv', 'json'], help='Output format: csv or json.')
    export_parser.add_argument('--output', required=True, help='Output file path.')
    export_parser.add_argument('--entity', choices=['posts', 'comments', 'all'], default='posts', help='Data entity to export (default: posts).')
    export_parser.add_argument('--category', help='Optional filter to export posts of a specific category.')
    export_parser.add_argument('--start-date', help='Filter posts by start date (YYYY-MM-DD).')
    export_parser.add_argument('--end-date', help='Filter posts by end date (YYYY-MM-DD).')
    export_parser.add_argument('--post-author', help='Filter by post author name.')
    export_parser.add_argument('--comment-author', help='Filter by comment author name.')
    export_parser.add_argument('--keyword', help='Keyword search in post and comment content.')
    export_parser.add_argument('--min-comments', type=int, help='Minimum number of comments.')
    export_parser.add_argument('--max-comments', type=int, help='Maximum number of comments.')
    export_parser.add_argument('--is-idea', action='store_true', help='Filter for posts marked as potential ideas.')

    add_group_parser = subparsers.add_parser('add-group', help='Add a new Facebook group to track.')
    add_group_parser.add_argument('--name', required=True, help='Name of the Facebook group.')
    add_group_parser.add_argument('--url', required=True, help='URL of the Facebook group.')
    
    list_groups_parser = subparsers.add_parser('list-groups', help='List all tracked Facebook groups.')
    
    remove_group_parser = subparsers.add_parser('remove-group', help='Remove a Facebook group from tracking.')
    remove_group_parser.add_argument('--id', type=int, required=True, help='ID of the group to remove.')

    stats_parser = subparsers.add_parser('stats', help='Display summary statistics about the data in the database.')
    
    args = parser.parse_args()

    if args.command:
        if args.command == 'scrape':
            handle_scrape_command(args.group_url, args.group_id, args.num_posts, args.headless)
        elif args.command == 'process-ai':
            handle_process_ai_command(args.group_id)
        elif args.command == 'view':
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
            handle_view_command(args.group_id, filters)
        elif args.command == 'export-data':
            handle_export_command(args)
        elif args.command == 'add-group':
            handle_add_group_command(args.name, args.url)
        elif args.command == 'list-groups':
            handle_list_groups_command()
        elif args.command == 'remove-group':
            handle_remove_group_command(args.id)
        elif args.command == 'stats':
            handle_stats_command()
    else:
        while True:
            clear_screen()
            print(ASCII_ART)
            print("\nFB Scrape Ideas Menu:")
            print("1. Scrape Posts from Facebook Group")
            print("2. Process Scraped Posts and Comments with AI")
            print("3. View Categorized Posts")
            print("4. Manage Groups")
            print("5. Exit")
            
            choice = input("\nEnter your choice: ").strip()
            
            if choice == '1':
                group_url = input("Enter Facebook Group URL: ").strip()
                num_posts_input = input("Enter number of posts to scrape (default: 20, press Enter for default): ").strip()
                num_posts = int(num_posts_input) if num_posts_input.isdigit() else 20
                headless_input = input("Run in headless mode? (yes/no, default: no): ").strip().lower()
                headless = headless_input == 'yes'
                handle_scrape_command(group_url=group_url, num_posts=num_posts, headless=headless)
                input("\nPress Enter to continue...")
            elif choice == '2':
                handle_process_ai_command()
                input("\nPress Enter to continue...")
            elif choice == '3':
                filters = {}
                category_filter = input("Enter category to filter by (optional, press Enter for all): ").strip()
                if category_filter:
                    filters['category'] = category_filter
                
                start_date = input("Start date (YYYY-MM-DD, optional): ").strip()
                if start_date:
                    filters['start_date'] = start_date
                
                end_date = input("End date (YYYY-MM-DD, optional): ").strip()
                if end_date:
                    filters['end_date'] = end_date
                
                post_author = input("Filter by post author name (optional): ").strip()
                if post_author:
                    filters['post_author'] = post_author
                
                comment_author = input("Filter by comment author name (optional): ").strip()
                if comment_author:
                    filters['comment_author'] = comment_author
                
                keyword = input("Keyword search (optional): ").strip()
                if keyword:
                    filters['keyword'] = keyword
                
                min_comments = input("Minimum comments (optional): ").strip()
                if min_comments.isdigit():
                    filters['min_comments'] = int(min_comments)
                
                max_comments = input("Maximum comments (optional): ").strip()
                if max_comments.isdigit():
                    filters['max_comments'] = int(max_comments)
                
                is_idea = input("Show only potential ideas? (yes/no, default: no): ").strip().lower()
                if is_idea == 'yes':
                    filters['is_idea'] = True
                
                handle_view_command(filters=filters)
                input("\nPress Enter to continue...")
            elif choice == '4':
                print("\nGroup Management:")
                print("1. Add New Group")
                print("2. List All Groups")
                print("3. Remove Group")
                print("4. Back to Main Menu")
                
                sub_choice = input("\nEnter your choice: ").strip()
                
                if sub_choice == '1':
                    name = input("Enter group name: ").strip()
                    url = input("Enter group URL: ").strip()
                    handle_add_group_command(name, url)
                elif sub_choice == '2':
                    handle_list_groups_command()
                elif sub_choice == '3':
                    group_id = input("Enter group ID to remove: ").strip()
                    if group_id.isdigit():
                        handle_remove_group_command(int(group_id))
                    else:
                        print("Invalid group ID. Must be a number.")
                elif sub_choice == '4':
                    continue
                else:
                    print("Invalid choice.")
                input("\nPress Enter to continue...")
            elif choice == '5':
                print("Exiting application. Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
                input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()