import argparse
import sqlite3
from scraper.facebook_scraper import scrape_facebook_group
from database.crud import get_db_connection, add_scraped_post, get_unprocessed_posts, update_post_with_ai_results, get_all_categorized_posts
from ai.gemini_service import create_post_batches, categorize_posts_batch

def main():
    parser = argparse.ArgumentParser(description='University Group Insights Platform CLI')
    subparsers = parser.add_subparsers(dest='command')

    scrape_parser = subparsers.add_parser('scrape', help='Initiate the Facebook scraping process and store results in DB.')
    scrape_parser.add_argument('--group-url', required=True, help='The URL of the public Facebook group to scrape.')
    scrape_parser.add_argument('--num-posts', type=int, default=20, help='The number of posts to attempt to scrape (default: 20).')

    process_ai_parser = subparsers.add_parser('process-ai', help='Fetch unprocessed posts, send them to Gemini for categorization, and update DB.')

    view_parser = subparsers.add_parser('view', help='Display categorized posts from the database.')
    view_parser.add_argument('--category', help='Optional filter to display posts of a specific category.')

    args = parser.parse_args()

    if args.command == 'scrape':
        print(f"Running scrape command for {args.group_url} (fetching {args.num_posts} posts)...")
        
        conn = get_db_connection()
        if conn:
            try:
                scraped_posts = scrape_facebook_group(args.group_url, args.num_posts)
                added_count = 0
                for post in scraped_posts:
                    add_scraped_post(conn, post)
                    added_count += 1
                print(f"Successfully scraped and added {added_count} posts to the database.")
            except Exception as e:
                print(f"An error occurred during scraping or database insertion: {e}")
            finally:
                conn.close()
        else:
            print("Could not connect to the database.")

    elif args.command == 'process-ai':
        print("Running process-ai command...")
        
        conn = get_db_connection()
        if conn:
            try:
                unprocessed_posts = get_unprocessed_posts(conn)
                if not unprocessed_posts:
                    print("No unprocessed posts found in the database.")
                    return
                
                print(f"Found {len(unprocessed_posts)} unprocessed posts. Creating batches...")
                post_batches = create_post_batches(unprocessed_posts)
                
                processed_count = 0
                for i, batch in enumerate(post_batches):
                    print(f"Processing batch {i+1}/{len(post_batches)} with {len(batch)} posts...")
                    ai_results = categorize_posts_batch(batch)
                    
                    if ai_results:
                        for result in ai_results:
                            internal_post_id = result.get('postId')
                            if internal_post_id is not None:
                                original_post = next((p for p in batch if p.get('internal_post_id') == internal_post_id), None)
                                if original_post:
                                     update_post_with_ai_results(conn, original_post['internal_post_id'], result)
                                     processed_count += 1
                                else:
                                     print(f"Warning: AI result for unknown postId {internal_post_id} ignored.")
                            else:
                                 print("Warning: AI result missing 'postId'. Cannot map to original post.")
                    else:
                        print(f"Warning: No AI results returned for batch {i+1}.")

                print(f"Successfully processed {processed_count} posts with AI.")

            except Exception as e:
                print(f"An error occurred during AI processing or database update: {e}")
            finally:
                conn.close()
        else:
            print("Could not connect to the database.")

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