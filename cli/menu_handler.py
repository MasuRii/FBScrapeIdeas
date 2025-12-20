"""
Menu presentation and command dispatching for the FB Scrape Ideas CLI.
Handles both interactive menu and command-line argument modes.
"""

import argparse
import asyncio
import os
import re
import getpass
from datetime import datetime

ASCII_ART = r"""
 _____  ____        _____   __  ____    ____  ____    ___      ____  ___      ___   ____  _____
|     ||    \      / ___/  /  ]|    \  /    T|    \  /  _]    l    j|   \    /  _] /    T/ ___/
|   __j|  o  )    (   \_  /  / |  D  )Y  o  ||  o  )/  [_      |  T |    \  /  [_ Y  o  (   \_
|  l_  |     T     \__  T/  /  |    / |     ||   _/Y    _]     |  | |  D  YY    _]|     |\__  T
|   _] |  O  |     /  \ /   \_ |    \ |  _  ||  |  |   [_      |  | |     ||   [_ |  _  |/  \ |
|  T   |     |     \    \     ||  .  Y|  |  ||  |  |     T     j  l |     ||     T|  |  |\    |
l__j   l_____j      \___j\____jl__j\_jl__j__jl__j  l_____j    |____jl_____jl_____jl__j__j \___j
"""

# --- Input Validation Helpers ---

def validate_facebook_url(url: str) -> bool:
    """Validates if the URL is a valid Facebook group URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid Facebook URL, False otherwise
    """
    if not url:
        return False
    # Accept facebook.com or fb.com URLs
    pattern = r'^https?://(www\.)?(facebook\.com|fb\.com)/groups/[\w.-]+/?.*$'
    return bool(re.match(pattern, url, re.IGNORECASE))


def validate_date_format(date_str: str) -> bool:
    """Validates if the date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not date_str:
        return True  # Empty is acceptable for optional fields
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_positive_integer(value: str) -> tuple[bool, int]:
    """Validates if the string is a positive integer.
    
    Args:
        value: String to validate
        
    Returns:
        Tuple of (is_valid, parsed_value)
    """
    if not value:
        return True, 0
    if value.isdigit() and int(value) > 0:
        return True, int(value)
    return False, 0


def get_validated_input(prompt: str, validator, error_msg: str, allow_empty: bool = True) -> str:
    """Gets user input with validation and retry logic.
    
    Args:
        prompt: Input prompt to display
        validator: Function that returns True if input is valid
        error_msg: Error message to display on invalid input
        allow_empty: Whether empty input is allowed
        
    Returns:
        Validated input string
    """
    while True:
        value = input(prompt).strip()
        if not value and allow_empty:
            return value
        if not value and not allow_empty:
            print("This field is required. Please enter a value.")
            continue
        if validator(value):
            return value
        print(error_msg)


# --- Core Functions ---

def handle_settings_menu():
    """Settings submenu for managing credentials and configuration."""
    from config import (
        save_credential_to_env, delete_env_file, 
        get_env_file_path, get_db_path,
        has_google_api_key, has_facebook_credentials
    )
    
    while True:
        print("\n" + "=" * 50)
        print("  SETTINGS")
        print("=" * 50)
        
        # Show current status
        api_status = "Configured" if has_google_api_key() else "Not configured"
        fb_status = "Configured" if has_facebook_credentials() else "Not configured"
        print(f"\n  Google API Key: {api_status}")
        print(f"  Facebook Credentials: {fb_status}")
        
        print("\n  1. Update Google API Key")
        print("  2. Update Facebook Credentials")
        print("  3. Show Config Locations")
        print("  4. Clear All Saved Credentials")
        print("  0. Back to Main Menu")
        print("=" * 50)
        
        try:
            choice = input("\nSelect option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break
        
        if choice == '1':
            print("\nGet your API key from: https://aistudio.google.com/apikey")
            try:
                api_key = getpass.getpass("Enter new Google API Key: ").strip()
                if api_key:
                    if save_credential_to_env("GOOGLE_API_KEY", api_key):
                        print("  API key updated!")
                    else:
                        print("  Failed to save API key.")
                else:
                    print("  No API key entered, skipping.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                
        elif choice == '2':
            try:
                username = input("Enter Facebook Email/Username: ").strip()
                password = getpass.getpass("Enter Facebook Password: ")
                if username and password:
                    saved_user = save_credential_to_env("FB_USER", username)
                    saved_pass = save_credential_to_env("FB_PASS", password)
                    if saved_user and saved_pass:
                        print("  Credentials updated!")
                    else:
                        print("  Failed to save credentials.")
                else:
                    print("  Username and password are required.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                
        elif choice == '3':
            print(f"\n  Config file: {get_env_file_path()}")
            print(f"  Database: {get_db_path()}")
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            try:
                confirm = input("  Delete all saved credentials? Type 'yes' to confirm: ").strip()
                if confirm.lower() == 'yes':
                    if delete_env_file():
                        print("  Credentials deleted!")
                    else:
                        print("  Failed to delete credentials.")
                else:
                    print("  Cancelled.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                
        elif choice == '0':
            break
        else:
            print("  Invalid choice. Please enter 0-4.")


def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def create_arg_parser():
    """Creates and configures the argument parser with all supported commands."""
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

    view_parser = subparsers.add_parser('view', help='Display posts from the database.')
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
    view_parser.add_argument('--limit', type=int, help='Limit the number of posts to display')

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

    setup_parser = subparsers.add_parser('setup', help='Run the setup wizard to configure credentials.')

    return parser

def run_interactive_menu(command_handlers):
    """Run the interactive CLI menu interface.
    
    Args:
        command_handlers: Dict mapping command names to their handler functions
    """
    while True:
        clear_screen()
        print(ASCII_ART)
        print("\nFB Scrape Ideas - Command Menu:")
        print("\n1. Data Collection:")
        print("   - Scrape Posts, Author Details & Comments")
        print("   - Configurable post count and headless mode")
        print("\n2. AI Processing:")
        print("   - Process Posts & Comments with Gemini AI")
        print("   - Categorizes content and analyzes sentiment")
        print("\n3. Data Access & Filtering:")
        print("   - Browse Posts with Author Details & Comments")
        print("   - Filter by category, date, author, keywords")
        print("   - View potential project ideas")
        print("\n4. Data Management & Analytics:")
        print("   - Export Data to CSV/JSON")
        print("   - Manage Facebook Groups (Add/List/Remove)")
        print("   - View Statistics & Trends")
        print("\n5. Settings:")
        print("   - Manage API Keys & Credentials")
        print("   - View Config Locations")
        print("\n6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            try:
                # Validate Facebook URL
                group_url = get_validated_input(
                    "Enter Facebook Group URL: ",
                    validate_facebook_url,
                    "Invalid URL. Please enter a valid Facebook group URL (e.g., https://facebook.com/groups/groupname)",
                    allow_empty=False
                )
                
                # Validate number of posts
                num_posts_input = input("Enter number of posts to scrape (default: 20, press Enter for default): ").strip()
                if num_posts_input:
                    is_valid, num_posts = validate_positive_integer(num_posts_input)
                    if not is_valid:
                        print("Invalid number. Using default value of 20.")
                        num_posts = 20
                else:
                    num_posts = 20
                
                headless_input = input("Run in headless mode? (yes/no, default: no): ").strip().lower()
                headless = headless_input == 'yes'
                
                command_handlers['scrape'](group_url=group_url, num_posts=num_posts, headless=headless)
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during scraping: {e}")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            try:
                asyncio.run(command_handlers['process_ai']())
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during AI processing: {e}")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            try:
                filters = {}
                category_filter = input("Enter category to filter by (optional, press Enter for all): ").strip()
                if category_filter:
                    filters['category'] = category_filter
                
                # Validate date inputs
                start_date = get_validated_input(
                    "Start date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15)"
                )
                if start_date:
                    filters['start_date'] = start_date
                
                end_date = get_validated_input(
                    "End date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15)"
                )
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
                if min_comments:
                    is_valid, value = validate_positive_integer(min_comments)
                    if is_valid and value > 0:
                        filters['min_comments'] = value
                    elif min_comments:
                        print("Invalid number for minimum comments, ignoring filter.")
                
                max_comments = input("Maximum comments (optional): ").strip()
                if max_comments:
                    is_valid, value = validate_positive_integer(max_comments)
                    if is_valid and value > 0:
                        filters['max_comments'] = value
                    elif max_comments:
                        print("Invalid number for maximum comments, ignoring filter.")
                
                is_idea = input("Show only potential ideas? (yes/no, default: no): ").strip().lower()
                if is_idea == 'yes':
                    filters['is_idea'] = True
                
                command_handlers['view'](filters=filters)
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError viewing posts: {e}")
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            print("\nData Management Options:")
            print("1. Add New Facebook Group")
            print("2. List All Tracked Groups")
            print("3. Remove Group from Tracking")
            print("4. Export Data to CSV/JSON")
            print("5. View Statistics")
            print("6. Back to Main Menu")
            
            sub_choice = input("\nEnter your choice (1-6): ").strip()
            
            try:
                if sub_choice == '1':
                    name = input("Enter group name: ").strip()
                    if not name:
                        print("Group name cannot be empty.")
                    else:
                        url = get_validated_input(
                            "Enter group URL: ",
                            validate_facebook_url,
                            "Invalid URL. Please enter a valid Facebook group URL.",
                            allow_empty=False
                        )
                        command_handlers['add_group'](name, url)
                        
                elif sub_choice == '2':
                    command_handlers['list_groups']()
                    
                elif sub_choice == '3':
                    group_id_input = input("Enter group ID to remove: ").strip()
                    is_valid, group_id = validate_positive_integer(group_id_input)
                    if is_valid and group_id > 0:
                        command_handlers['remove_group'](group_id)
                    else:
                        print("Invalid group ID. Must be a positive number.")
                        
                elif sub_choice == '4':
                    format_choice = input("Choose format (csv/json): ").strip().lower()
                    if format_choice not in ['csv', 'json']:
                        print("Invalid format. Must be 'csv' or 'json'")
                    else:
                        print("\nOutput File Path Guidelines:")
                        print("- For Windows: Use any of these formats:")
                        print("  1. Full path with filename: C:\\MyFolder\\data.csv")
                        print("  2. Directory path only: C:\\MyFolder")
                        print("  3. Drive only: E:\\ (will use default filename)")
                        print("\nOutput Files:")
                        print("- Creates separate files for each data type:")
                        print("  * [path]_groups.[ext]  - Group information")
                        print("  * [path]_posts.[ext]   - Post data")
                        print("  * [path]_comments.[ext] - Comment data")
                        print("  * [path]_all.[ext]     - Combined data")
                        
                        output_file = input("\nEnter output file path: ").strip()
                        if not output_file:
                            print("Output path cannot be empty.")
                        else:
                            args = type('Args', (), {
                                'format': format_choice,
                                'output': output_file,
                                'entity': 'all',
                                'category': None,
                                'start_date': None,
                                'end_date': None,
                                'post_author': None,
                                'comment_author': None,
                                'keyword': None,
                                'min_comments': None,
                                'max_comments': None,
                                'is_idea': False
                            })()
                            command_handlers['export'](args)
                            
                elif sub_choice == '5':
                    command_handlers['stats']()
                    
                elif sub_choice == '6':
                    continue
                else:
                    print("Invalid choice. Please enter a number between 1-6.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError: {e}")
            input("\nPress Enter to continue...")
            
        elif choice == '5':
            handle_settings_menu()
            
        elif choice == '6':
            print("Exiting application. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1-6.")
            input("\nPress Enter to continue...")

def handle_cli_arguments(args, command_handlers):
    """Handle command-line arguments and execute the appropriate command handler.

    Args:
        args: Parsed command-line arguments from argparse
        command_handlers: Dict mapping command names to their handler functions
    """
    try:
        if args.command:
            if args.command == 'scrape':
                # Validate URL if provided via CLI
                if args.group_url and not validate_facebook_url(args.group_url):
                    print("Error: Invalid Facebook group URL provided.")
                    return
                command_handlers['scrape'](args.group_url, args.group_id, args.num_posts, args.headless)
            elif args.command == 'process-ai':
                asyncio.run(command_handlers['process_ai'](args.group_id))
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
                command_handlers['view'](args.group_id, filters, args.limit)
            elif args.command == 'export-data':
                command_handlers['export'](args)
            elif args.command == 'add-group':
                # Validate URL for add-group command
                if not validate_facebook_url(args.url):
                    print("Error: Invalid Facebook group URL provided.")
                    return
                command_handlers['add_group'](args.name, args.url)
            elif args.command == 'list-groups':
                command_handlers['list_groups']()
            elif args.command == 'remove-group':
                command_handlers['remove_group'](args.id)
            elif args.command == 'stats':
                command_handlers['stats']()
            elif args.command == 'setup':
                from config import run_setup_wizard
                run_setup_wizard()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")

def run_cli(command_handlers):
    """Main entry point for the CLI interface.
    
    Supports both interactive menu and command-line argument modes.
    
    Args:
        command_handlers: Dict mapping command names to their handler functions
            Required keys:
            - 'scrape': Function to handle scraping
            - 'process_ai': Function to handle AI processing
            - 'view': Function to handle viewing posts
            - 'export': Function to handle data export
            - 'add_group': Function to handle adding groups
            - 'list_groups': Function to handle listing groups
            - 'remove_group': Function to handle removing groups
            - 'stats': Function to handle statistics display
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    if args.command:
        handle_cli_arguments(args, command_handlers)
    else:
        run_interactive_menu(command_handlers)
