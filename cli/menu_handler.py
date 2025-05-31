"""
Menu presentation and command dispatching for the FB Scrape Ideas CLI.
Handles both interactive menu and command-line argument modes.
"""

import argparse
import asyncio
import os

ASCII_ART = r"""
 _____  ____        _____   __  ____    ____  ____    ___      ____  ___      ___   ____  _____
|     ||    \      / ___/  /  ]|    \  /    T|    \  /  _]    l    j|   \    /  _] /    T/ ___/
|   __j|  o  )    (   \_  /  / |  D  )Y  o  ||  o  )/  [_      |  T |    \  /  [_ Y  o  (   \_
|  l_  |     T     \__  T/  /  |    / |     ||   _/Y    _]     |  | |  D  YY    _]|     |\__  T
|   _] |  O  |     /  \ /   \_ |    \ |  _  ||  |  |   [_      |  | |     ||   [_ |  _  |/  \ |
|  T   |     |     \    \     ||  .  Y|  |  ||  |  |     T     j  l |     ||     T|  |  |\    |
l__j   l_____j      \___j\____jl__j\_jl__j__jl__j  l_____j    |____jl_____jl_____jl__j__j \___j
"""

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
        print("\n5. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '1':
            group_url = input("Enter Facebook Group URL: ").strip()
            num_posts_input = input("Enter number of posts to scrape (default: 20, press Enter for default): ").strip()
            num_posts = int(num_posts_input) if num_posts_input.isdigit() else 20
            headless_input = input("Run in headless mode? (yes/no, default: no): ").strip().lower()
            headless = headless_input == 'yes'
            command_handlers['scrape'](group_url=group_url, num_posts=num_posts, headless=headless)
            input("\nPress Enter to continue...")
        elif choice == '2':
            asyncio.run(command_handlers['process_ai']())
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
            
            command_handlers['view'](filters=filters)
            input("\nPress Enter to continue...")
        elif choice == '4':
            print("\nData Management Options:")
            print("1. Add New Facebook Group")
            print("2. List All Tracked Groups")
            print("3. Remove Group from Tracking")
            print("4. Export Data to CSV/JSON")
            print("5. View Statistics")
            print("6. Back to Main Menu")
            
            sub_choice = input("\nEnter your choice: ").strip()
            
            if sub_choice == '1':
                name = input("Enter group name: ").strip()
                url = input("Enter group URL: ").strip()
                command_handlers['add_group'](name, url)
            elif sub_choice == '2':
                command_handlers['list_groups']()
            elif sub_choice == '3':
                group_id = input("Enter group ID to remove: ").strip()
                if group_id.isdigit():
                    command_handlers['remove_group'](int(group_id))
                else:
                    print("Invalid group ID. Must be a number.")
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
                    if output_file:
                        try:
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
                            input("\nPress Enter to continue...")
                        except Exception as e:
                            print(f"Export failed: {str(e)}")
                            input("\nPress Enter to continue...")
            elif sub_choice == '5':
                command_handlers['stats']()
            elif sub_choice == '6':
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

def handle_cli_arguments(args, command_handlers):
    """Handle command-line arguments and execute the appropriate command handler.

    Args:
        args: Parsed command-line arguments from argparse
        command_handlers: Dict mapping command names to their handler functions
    """
    if args.command:
        if args.command == 'scrape':
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
            command_handlers['add_group'](args.name, args.url)
        elif args.command == 'list-groups':
            command_handlers['list_groups']()
        elif args.command == 'remove-group':
            command_handlers['remove_group'](args.id)
        elif args.command == 'stats':
            command_handlers['stats']()

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