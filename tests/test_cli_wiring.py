"""
CLI Wiring Tests for menu_handler.py

Tests that the CLI menu handler correctly wires user inputs to service calls.
Focuses on verifying:
1. Correct service methods are called with correct arguments
2. User input (via cli.console.ask) is properly passed to services
3. Service exceptions are caught and displayed via cli.console.print_error
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
import asyncio


# --- Tests for handle_scrape_command (via handle_cli_arguments) ---


class TestHandleScrapeCommand:
    """Tests for the scrape command wiring."""

    def test_scrape_calls_scraper_service_with_correct_args_via_cli(self):
        """Verify scrape command calls ScraperService.scrape_group with correct arguments."""
        from cli.menu_handler import handle_cli_arguments

        mock_scraper_service = MagicMock()
        mock_scraper_service.scrape_group = AsyncMock()

        mock_handlers = {"scrape": AsyncMock()}

        args = MagicMock()
        args.command = "scrape"
        args.group_url = "https://facebook.com/groups/testgroup"
        args.group_id = None
        args.num_posts = 25
        args.headless = True
        args.engine = "playwright"

        handle_cli_arguments(
            args,
            mock_handlers,
            scraper_service=mock_scraper_service,
            ai_service=None,
            group_service=None,
            post_service=None,
        )

        # Verify the scrape handler was called with correct args
        mock_handlers["scrape"].assert_called_once()
        call_args = mock_handlers["scrape"].call_args
        # asyncio.run wraps the coroutine, so we check the actual handler call
        assert call_args[1]["group_url"] == "https://facebook.com/groups/testgroup"
        assert call_args[1]["num_posts"] == 25
        assert call_args[1]["headless"] is True
        assert call_args[1]["engine"] == "playwright"

    def test_scrape_with_group_id_instead_of_url(self):
        """Verify scrape command works with group_id instead of group_url."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"scrape": AsyncMock()}

        args = MagicMock()
        args.command = "scrape"
        args.group_url = None
        args.group_id = 42
        args.num_posts = 10
        args.headless = False
        args.engine = "selenium"

        handle_cli_arguments(args, mock_handlers)

        mock_handlers["scrape"].assert_called_once()
        call_args = mock_handlers["scrape"].call_args
        assert call_args[1]["group_id"] == 42
        assert call_args[1]["group_url"] is None

    def test_scrape_rejects_invalid_url_with_error_message(self):
        """Verify invalid Facebook URL is rejected with error message."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"scrape": AsyncMock()}

        args = MagicMock()
        args.command = "scrape"
        args.group_url = "https://google.com/not-facebook"
        args.group_id = None
        args.num_posts = 10
        args.headless = False
        args.engine = None

        with patch("builtins.print") as mock_print:
            handle_cli_arguments(args, mock_handlers)
            mock_print.assert_called_with("Error: Invalid Facebook group URL provided.")
            mock_handlers["scrape"].assert_not_called()

    def test_scrape_handles_exception_gracefully(self):
        """Verify scrape command catches and displays exceptions."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"scrape": AsyncMock(side_effect=Exception("Network error"))}

        args = MagicMock()
        args.command = "scrape"
        args.group_url = "https://facebook.com/groups/test"
        args.group_id = None
        args.num_posts = 10
        args.headless = False
        args.engine = None

        with patch("builtins.print") as mock_print:
            handle_cli_arguments(args, mock_handlers)
            # Check that error was printed (exception is caught)
            error_calls = [
                c
                for c in mock_print.call_args_list
                if "Error" in str(c) or "error" in str(c).lower()
            ]
            assert len(error_calls) > 0


# --- Tests for handle_view_command (via handle_cli_arguments) ---


class TestHandleViewCommand:
    """Tests for the view command wiring."""

    def test_view_calls_post_service_get_filtered_posts(self):
        """Verify view command passes correct filters to PostService."""
        from cli.menu_handler import handle_cli_arguments

        mock_post_service = MagicMock()
        mock_handlers = {"view": MagicMock()}

        args = MagicMock()
        args.command = "view"
        args.group_id = 5
        args.category = "Ideas"
        args.start_date = "2025-01-01"
        args.end_date = "2025-12-31"
        args.post_author = "John Doe"
        args.comment_author = "Jane Smith"
        args.keyword = "startup"
        args.min_comments = 5
        args.max_comments = 100
        args.is_idea = True
        args.limit = 50

        handle_cli_arguments(
            args,
            mock_handlers,
            post_service=mock_post_service,
        )

        mock_handlers["view"].assert_called_once()
        call_args = mock_handlers["view"].call_args

        # Verify post_service is passed
        assert call_args[0][0] is mock_post_service

        # Verify filters are correctly assembled
        expected_filters = {
            "category": "Ideas",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "post_author": "John Doe",
            "comment_author": "Jane Smith",
            "keyword": "startup",
            "min_comments": 5,
            "max_comments": 100,
            "is_idea": True,
        }

        assert call_args[1]["group_id"] == 5
        assert call_args[1]["filters"] == expected_filters
        assert call_args[1]["limit"] == 50

    def test_view_with_no_filters(self):
        """Verify view command works with no filters (defaults)."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"view": MagicMock()}

        args = MagicMock()
        args.command = "view"
        args.group_id = None
        args.category = None
        args.start_date = None
        args.end_date = None
        args.post_author = None
        args.comment_author = None
        args.keyword = None
        args.min_comments = None
        args.max_comments = None
        args.is_idea = False
        args.limit = None

        handle_cli_arguments(args, mock_handlers)

        mock_handlers["view"].assert_called_once()
        call_args = mock_handlers["view"].call_args

        # All filters should be None/False
        filters = call_args[1]["filters"]
        assert filters["category"] is None
        assert filters["is_idea"] is False

    def test_view_handles_exception_gracefully(self):
        """Verify view command catches and displays exceptions."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"view": MagicMock(side_effect=Exception("Database connection failed"))}

        args = MagicMock()
        args.command = "view"
        args.group_id = None
        args.category = None
        args.start_date = None
        args.end_date = None
        args.post_author = None
        args.comment_author = None
        args.keyword = None
        args.min_comments = None
        args.max_comments = None
        args.is_idea = False
        args.limit = None

        with patch("builtins.print") as mock_print:
            handle_cli_arguments(args, mock_handlers)
            # Exception should be caught and printed
            error_calls = [
                c
                for c in mock_print.call_args_list
                if "Error" in str(c) or "error" in str(c).lower()
            ]
            assert len(error_calls) > 0


# --- Tests for handle_add_group_command (via handle_cli_arguments) ---


class TestHandleAddGroupCommand:
    """Tests for the add-group command wiring."""

    def test_add_group_calls_group_service_with_correct_args(self):
        """Verify add-group command calls GroupService.add_group with name and URL."""
        from cli.menu_handler import handle_cli_arguments

        mock_group_service = MagicMock()
        mock_handlers = {"add_group": MagicMock()}

        args = MagicMock()
        args.command = "add-group"
        args.name = "My Test Group"
        args.url = "https://facebook.com/groups/mytestgroup"

        handle_cli_arguments(
            args,
            mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["add_group"].assert_called_once_with(
            mock_group_service, "My Test Group", "https://facebook.com/groups/mytestgroup"
        )

    def test_add_group_rejects_invalid_url(self):
        """Verify add-group rejects invalid Facebook URL."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"add_group": MagicMock()}

        args = MagicMock()
        args.command = "add-group"
        args.name = "Invalid Group"
        args.url = "https://twitter.com/somegroup"

        with patch("builtins.print") as mock_print:
            handle_cli_arguments(args, mock_handlers)
            mock_print.assert_called_with("Error: Invalid Facebook group URL provided.")
            mock_handlers["add_group"].assert_not_called()

    def test_add_group_accepts_fb_com_short_url(self):
        """Verify add-group accepts fb.com short URLs."""
        from cli.menu_handler import handle_cli_arguments

        mock_group_service = MagicMock()
        mock_handlers = {"add_group": MagicMock()}

        args = MagicMock()
        args.command = "add-group"
        args.name = "Short URL Group"
        args.url = "https://fb.com/groups/shortgroup"

        handle_cli_arguments(
            args,
            mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["add_group"].assert_called_once()


# --- Tests for list_groups and remove_group commands ---


class TestListGroupsCommand:
    """Tests for the list-groups command wiring."""

    def test_list_groups_calls_group_service(self):
        """Verify list-groups calls the correct handler with group_service."""
        from cli.menu_handler import handle_cli_arguments

        mock_group_service = MagicMock()
        mock_handlers = {"list_groups": MagicMock()}

        args = MagicMock()
        args.command = "list-groups"

        handle_cli_arguments(
            args,
            mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["list_groups"].assert_called_once_with(mock_group_service)


class TestRemoveGroupCommand:
    """Tests for the remove-group command wiring."""

    def test_remove_group_calls_group_service_with_id(self):
        """Verify remove-group passes group_id to handler."""
        from cli.menu_handler import handle_cli_arguments

        mock_group_service = MagicMock()
        mock_handlers = {"remove_group": MagicMock()}

        args = MagicMock()
        args.command = "remove-group"
        args.id = 99

        handle_cli_arguments(
            args,
            mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["remove_group"].assert_called_once_with(mock_group_service, 99)


# --- Tests for stats command ---


class TestStatsCommand:
    """Tests for the stats command wiring."""

    def test_stats_calls_post_service(self):
        """Verify stats command calls handler with post_service."""
        from cli.menu_handler import handle_cli_arguments

        mock_post_service = MagicMock()
        mock_handlers = {"stats": MagicMock()}

        args = MagicMock()
        args.command = "stats"

        handle_cli_arguments(
            args,
            mock_handlers,
            post_service=mock_post_service,
        )

        mock_handlers["stats"].assert_called_once_with(mock_post_service)


# --- Tests for process-ai command ---


class TestProcessAICommand:
    """Tests for the process-ai command wiring."""

    def test_process_ai_calls_ai_service_with_group_id(self):
        """Verify process-ai command passes ai_service and group_id."""
        from cli.menu_handler import handle_cli_arguments

        mock_ai_service = MagicMock()
        mock_handlers = {"process_ai": AsyncMock()}

        args = MagicMock()
        args.command = "process-ai"
        args.group_id = 7

        handle_cli_arguments(
            args,
            mock_handlers,
            ai_service=mock_ai_service,
        )

        mock_handlers["process_ai"].assert_called_once()
        call_args = mock_handlers["process_ai"].call_args
        assert call_args[0][0] is mock_ai_service
        assert call_args[0][1] == 7

    def test_process_ai_without_group_id(self):
        """Verify process-ai works without group_id (processes all)."""
        from cli.menu_handler import handle_cli_arguments

        mock_ai_service = MagicMock()
        mock_handlers = {"process_ai": AsyncMock()}

        args = MagicMock()
        args.command = "process-ai"
        args.group_id = None

        handle_cli_arguments(
            args,
            mock_handlers,
            ai_service=mock_ai_service,
        )

        mock_handlers["process_ai"].assert_called_once()
        call_args = mock_handlers["process_ai"].call_args
        assert call_args[0][1] is None


# --- Tests for Interactive Menu Input Mocking ---


class TestInteractiveMenuInputWiring:
    """Tests for interactive menu user input handling via cli.console.ask."""

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_success")
    def test_interactive_menu_exit_option(
        self, mock_success, mock_menu, mock_header, mock_clear, mock_ask
    ):
        """Verify exit option (7) exits the interactive menu cleanly."""
        from cli.menu_handler import run_interactive_menu

        # User selects exit immediately
        mock_ask.return_value = "7"

        run_interactive_menu(
            command_handlers={},
            scraper_service=None,
            ai_service=None,
            group_service=None,
            post_service=None,
        )

        # Menu should display and then exit
        mock_success.assert_called_with("Exiting application. Goodbye!")

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_error")
    def test_interactive_menu_invalid_choice_shows_error(
        self, mock_error, mock_menu, mock_header, mock_clear, mock_ask
    ):
        """Verify invalid menu choice shows error message."""
        from cli.menu_handler import run_interactive_menu

        # User enters invalid, presses enter to continue, then exits
        mock_ask.side_effect = ["invalid", "", "7"]

        run_interactive_menu(
            command_handlers={},
            scraper_service=None,
            ai_service=None,
            group_service=None,
            post_service=None,
        )

        mock_error.assert_called_with("Invalid choice. Please enter a number between 1-7.")

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.get_validated_input")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("asyncio.run")
    @patch("config.get_scraper_engine", return_value="playwright")
    def test_interactive_menu_scrape_option_collects_input(
        self,
        mock_get_engine,
        mock_asyncio_run,
        mock_info,
        mock_divider,
        mock_get_validated,
        mock_section,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify scrape option (1) collects URL and num_posts from user."""
        from cli.menu_handler import run_interactive_menu

        # User selects scrape, provides inputs, then exits
        mock_ask.side_effect = [
            "1",  # Select scrape option
            "30",  # Number of posts
            "",  # Press enter to continue
            "7",  # Exit
        ]
        mock_get_validated.return_value = "https://facebook.com/groups/testgroup"

        mock_handlers = {"scrape": AsyncMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            scraper_service=MagicMock(),
        )

        # asyncio.run should have been called with scrape handler
        assert mock_asyncio_run.called

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.get_validated_input")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_warning")
    def test_interactive_menu_view_option_collects_filters(
        self,
        mock_warning,
        mock_divider,
        mock_get_validated,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify view option (4) collects filter inputs from user."""
        from cli.menu_handler import run_interactive_menu

        # User selects view, provides filter inputs, then exits
        mock_ask.side_effect = [
            "4",  # Select view option
            "Ideas",  # Category filter
            "John",  # Post author
            "",  # Comment author (skip)
            "startup",  # Keyword
            "5",  # Min comments
            "",  # Max comments (skip)
            "no",  # Is idea filter
            "",  # Press enter to continue
            "7",  # Exit
        ]
        mock_get_validated.side_effect = [
            "2025-01-01",  # Start date
            "2025-12-31",  # End date
        ]

        mock_handlers = {"view": MagicMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            post_service=MagicMock(),
        )

        # View handler should have been called with filters
        mock_handlers["view"].assert_called_once()


# --- Tests for Exception Handling with print_error ---


class TestExceptionDisplayViaConsole:
    """Tests that service exceptions are caught and displayed via cli.console functions."""

    @patch("cli.menu_handler.print_error")
    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.get_validated_input")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("asyncio.run")
    @patch("config.get_scraper_engine", return_value="playwright")
    def test_scrape_exception_displayed_via_print_error(
        self,
        mock_get_engine,
        mock_asyncio_run,
        mock_info,
        mock_divider,
        mock_get_validated,
        mock_section,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
        mock_print_error,
    ):
        """Verify scrape exception is caught and displayed via print_error."""
        from cli.menu_handler import run_interactive_menu

        # Simulate exception during scraping
        mock_asyncio_run.side_effect = Exception("Connection timeout")

        mock_ask.side_effect = [
            "1",  # Select scrape
            "20",  # Num posts
            "",  # Press enter
            "7",  # Exit
        ]
        mock_get_validated.return_value = "https://facebook.com/groups/test"

        run_interactive_menu(
            command_handlers={"scrape": AsyncMock()},
            scraper_service=MagicMock(),
        )

        # print_error should have been called with the exception message
        error_calls = [str(c) for c in mock_print_error.call_args_list]
        assert any("Connection timeout" in str(c) or "Error" in str(c) for c in error_calls)

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.get_validated_input")
    @patch("cli.menu_handler.print_divider")
    def test_view_exception_caught_in_interactive_mode(
        self,
        mock_divider,
        mock_get_validated,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify view exception is caught in interactive mode."""
        from cli.menu_handler import run_interactive_menu

        # User selects view which throws exception
        mock_ask.side_effect = [
            "4",  # Select view
            "",  # Category
            "",  # Post author
            "",  # Comment author
            "",  # Keyword
            "",  # Min comments
            "",  # Max comments
            "no",  # Is idea
            "",  # Press enter
            "7",  # Exit
        ]
        mock_get_validated.return_value = ""

        # Handler throws exception
        mock_handlers = {"view": MagicMock(side_effect=Exception("Database locked"))}

        with patch("builtins.print") as mock_print:
            run_interactive_menu(
                command_handlers=mock_handlers,
                post_service=MagicMock(),
            )

            # Exception should be caught, not propagated
            error_printed = any(
                "Database locked" in str(c) or "Error" in str(c) for c in mock_print.call_args_list
            )
            assert error_printed


# --- Tests for Data Management Submenu ---


class TestDataManagementSubmenu:
    """Tests for the Data Management submenu (option 5) wiring."""

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.get_validated_input")
    def test_add_group_via_submenu(
        self,
        mock_get_validated,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify add group via submenu calls handler correctly."""
        from cli.menu_handler import run_interactive_menu

        mock_ask.side_effect = [
            "5",  # Data Management
            "1",  # Add new group
            "Test Group",  # Group name
            "",  # Press enter
            "7",  # Exit
        ]
        mock_get_validated.return_value = "https://facebook.com/groups/test"

        mock_group_service = MagicMock()
        mock_handlers = {"add_group": MagicMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["add_group"].assert_called_once_with(
            mock_group_service, "Test Group", "https://facebook.com/groups/test"
        )

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    def test_list_groups_via_submenu(
        self,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify list groups via submenu calls handler correctly."""
        from cli.menu_handler import run_interactive_menu

        mock_ask.side_effect = [
            "5",  # Data Management
            "2",  # List groups
            "",  # Press enter
            "7",  # Exit
        ]

        mock_group_service = MagicMock()
        mock_handlers = {"list_groups": MagicMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["list_groups"].assert_called_once_with(mock_group_service)

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    def test_remove_group_via_submenu(
        self,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify remove group via submenu calls handler with correct ID."""
        from cli.menu_handler import run_interactive_menu

        mock_ask.side_effect = [
            "5",  # Data Management
            "3",  # Remove group
            "42",  # Group ID
            "",  # Press enter
            "7",  # Exit
        ]

        mock_group_service = MagicMock()
        mock_handlers = {"remove_group": MagicMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            group_service=mock_group_service,
        )

        mock_handlers["remove_group"].assert_called_once_with(mock_group_service, 42)

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.clear_screen")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.print_menu")
    def test_stats_via_submenu(
        self,
        mock_menu,
        mock_header,
        mock_clear,
        mock_ask,
    ):
        """Verify stats via submenu calls handler correctly."""
        from cli.menu_handler import run_interactive_menu

        mock_ask.side_effect = [
            "5",  # Data Management
            "5",  # View Statistics
            "",  # Press enter
            "7",  # Exit
        ]

        mock_post_service = MagicMock()
        mock_handlers = {"stats": MagicMock()}

        run_interactive_menu(
            command_handlers=mock_handlers,
            post_service=mock_post_service,
        )

        mock_handlers["stats"].assert_called_once_with(mock_post_service)


# --- Tests for Keyboard Interrupt Handling ---


class TestKeyboardInterruptHandling:
    """Tests that KeyboardInterrupt is caught gracefully."""

    def test_cli_arguments_handles_keyboard_interrupt(self):
        """Verify KeyboardInterrupt is caught in CLI arguments mode."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"scrape": AsyncMock(side_effect=KeyboardInterrupt())}

        args = MagicMock()
        args.command = "scrape"
        args.group_url = "https://facebook.com/groups/test"
        args.group_id = None
        args.num_posts = 10
        args.headless = False
        args.engine = None

        with patch("builtins.print") as mock_print:
            # Should not raise, should be caught
            handle_cli_arguments(args, mock_handlers)
            # Should print cancellation message
            cancel_printed = any("cancelled" in str(c).lower() for c in mock_print.call_args_list)
            assert cancel_printed


# --- Tests for export-data command ---


class TestExportDataCommand:
    """Tests for the export-data command wiring."""

    def test_export_calls_handler_with_args(self):
        """Verify export-data passes args object to handler."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"export": MagicMock()}

        args = MagicMock()
        args.command = "export-data"
        args.format = "json"
        args.output = "/path/to/output.json"
        args.entity = "posts"
        args.category = "Ideas"
        args.start_date = None
        args.end_date = None
        args.post_author = None
        args.comment_author = None
        args.keyword = None
        args.min_comments = None
        args.max_comments = None
        args.is_idea = False

        handle_cli_arguments(args, mock_handlers)

        mock_handlers["export"].assert_called_once_with(args)


# --- Tests for manual-login command ---


class TestManualLoginCommand:
    """Tests for the manual-login command wiring."""

    def test_manual_login_calls_handler(self):
        """Verify manual-login calls the correct handler."""
        from cli.menu_handler import handle_cli_arguments

        mock_handlers = {"manual_login": AsyncMock()}

        args = MagicMock()
        args.command = "manual-login"

        handle_cli_arguments(args, mock_handlers)

        mock_handlers["manual_login"].assert_called_once()
