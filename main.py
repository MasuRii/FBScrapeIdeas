import argparse
import sqlite3
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from scraper.facebook_scraper import login_to_facebook, scrape_authenticated_group, is_facebook_session_valid
from database.crud import get_db_connection, add_scraped_post, add_comments_for_post, get_unprocessed_posts, update_post_with_ai_results, get_all_categorized_posts, get_comments_for_post
from ai.gemini_service import create_post_batches, categorize_posts_batch
from config import get_facebook_credentials
from database.db_setup import init_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    init_db()

    parser = argparse.ArgumentParser(description='University Group Insights Platform CLI')
    subparsers = parser.add_subparsers(dest='command')

    scrape_parser = subparsers.add_parser('scrape', help='Initiate the Facebook scraping process and store results in DB.')
    scrape_parser.add_argument('--group-url', required=True, help='The URL of the Facebook group to scrape.')
    scrape_parser.add_argument('--num-posts', type=int, default=20, help='The number of posts to attempt to scrape (default: 20).')
    scrape_parser.add_argument('--headless', action='store_true', help='Run the browser in headless mode (no GUI).')

    process_ai_parser = subparsers.add_parser('process-ai', help='Fetch unprocessed posts, send them to Gemini for categorization, and update DB.')

    view_parser = subparsers.add_parser('view', help='Display categorized posts from the database.')
    view_parser.add_argument('--category', help='Optional filter to display posts of a specific category.')

    args = parser.parse_args()

    if args.command == 'scrape':
        logging.info(f"Running scrape command for {args.group_url} (fetching {args.num_posts} posts).")
        
        driver = None
        conn = None
        try:
            username, password = get_facebook_credentials()
            
            logging.info("Initializing Selenium WebDriver...")
            options = webdriver.ChromeOptions()
            if args.headless:
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
                    scraped_posts = scrape_authenticated_group(driver, args.group_url, args.num_posts)
                    
                    added_count = 0
                    if scraped_posts:
                        logging.info(f"Attempting to add {len(scraped_posts)} scraped posts and their comments to the database.")
                        for post in scraped_posts:
                            internal_post_id = add_scraped_post(conn, post)
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

    elif args.command == 'process-ai':
        logging.info("Running process-ai command...")
        
        conn = get_db_connection()
        if conn:
            try:
                unprocessed_posts = get_unprocessed_posts(conn)
                logging.info(f"Retrieved {len(unprocessed_posts)} unprocessed posts from the database.")
                for i, post in enumerate(unprocessed_posts[:5]):
                    logging.debug(f"  Post {i+1}: ID={post.get('internal_post_id')}, URL={post.get('post_url')}")

                if not unprocessed_posts:
                    logging.info("No unprocessed posts found in the database.")
                    return
                
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

            except Exception as e:
                logging.error(f"An error occurred during AI processing or database update: {e}", exc_info=True)
            finally:
                conn.close()
        else:
            logging.error("Could not connect to the database.")

    elif args.command == 'view':
        category_filter = args.category if args.category else None
        print(f"Running view command (filtering by: {'all' if category_filter is None else category_filter})...")
        
        conn = get_db_connection()
        if conn:
            try:
                posts = get_all_categorized_posts(conn, category_filter)
                if not posts:
                    print("No categorized posts found in the database." + (f" for category '{category_filter}'" if category_filter else ""))
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

    else:
        parser.print_help()

if __name__ == '__main__':
    main() 