import pytest
from unittest.mock import MagicMock, patch
from cli.menu_handler import (
    validate_facebook_url,
    validate_date_format,
    validate_positive_integer,
    get_validated_input,
    handle_cli_arguments,
)


def test_validate_facebook_url():
    assert validate_facebook_url("https://www.facebook.com/groups/mygroup") is True
    assert validate_facebook_url("http://fb.com/groups/anothergroup/") is True
    assert validate_facebook_url("https://facebook.com/groups/group.name") is True
    assert validate_facebook_url("https://google.com") is False
    assert validate_facebook_url("") is False


def test_validate_date_format():
    assert validate_date_format("2024-01-01") is True
    assert validate_date_format("2025-12-31") is True
    assert validate_date_format("2024-13-01") is False
    assert validate_date_format("01-01-2024") is False
    assert validate_date_format("2024/01/01") is False
    assert validate_date_format("") is True  # Optional field


def test_validate_positive_integer():
    assert validate_positive_integer("10") == (True, 10)
    assert validate_positive_integer("1") == (True, 1)
    assert validate_positive_integer("0") == (False, 0)
    assert validate_positive_integer("-5") == (False, 0)
    assert validate_positive_integer("abc") == (False, 0)
    assert validate_positive_integer("") == (True, 0)


def test_get_validated_input():
    # Test with invalid then valid input
    with patch("builtins.input", side_effect=["invalid", "https://facebook.com/groups/valid"]):
        validator = validate_facebook_url
        with patch("builtins.print") as mock_print:
            result = get_validated_input("Prompt: ", validator, "Error message", allow_empty=False)
            assert result == "https://facebook.com/groups/valid"
            mock_print.assert_any_call("Error message")


def test_get_validated_input_empty_allowed():
    with patch("builtins.input", return_value=""):
        validator = validate_facebook_url
        result = get_validated_input("Prompt: ", validator, "Error", allow_empty=True)
        assert result == ""


def test_handle_cli_arguments_scrape():
    mock_handlers = {"scrape": MagicMock()}
    args = MagicMock()
    args.command = "scrape"
    args.group_url = "https://facebook.com/groups/test"
    args.group_id = None
    args.num_posts = 10
    args.headless = True
    args.engine = "playwright"

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["scrape"].assert_called_once_with(
        group_url="https://facebook.com/groups/test",
        group_id=None,
        num_posts=10,
        headless=True,
        engine="playwright",
    )


def test_handle_cli_arguments_process_ai():
    mock_handlers = {"process_ai": AsyncMock()}
    args = MagicMock()
    args.command = "process-ai"
    args.group_id = 1

    with patch("asyncio.run") as mock_run:
        handle_cli_arguments(args, mock_handlers)
        # asyncio.run is called with a coroutine
        assert mock_run.called


def test_handle_cli_arguments_invalid_url():
    mock_handlers = {"scrape": MagicMock()}
    args = MagicMock()
    args.command = "scrape"
    args.group_url = "invalid-url"

    with patch("builtins.print") as mock_print:
        handle_cli_arguments(args, mock_handlers)
        mock_print.assert_called_with("Error: Invalid Facebook group URL provided.")
        mock_handlers["scrape"].assert_not_called()


def test_handle_cli_arguments_add_group():
    mock_handlers = {"add_group": MagicMock()}
    args = MagicMock()
    args.command = "add-group"
    args.name = "Test Group"
    args.url = "https://facebook.com/groups/test"

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["add_group"].assert_called_once_with(
        "Test Group", "https://facebook.com/groups/test"
    )


def test_handle_cli_arguments_list_groups():
    mock_handlers = {"list_groups": MagicMock()}
    args = MagicMock()
    args.command = "list-groups"

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["list_groups"].assert_called_once()


def test_handle_cli_arguments_remove_group():
    mock_handlers = {"remove_group": MagicMock()}
    args = MagicMock()
    args.command = "remove-group"
    args.id = 123

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["remove_group"].assert_called_once_with(123)


def test_handle_cli_arguments_stats():
    mock_handlers = {"stats": MagicMock()}
    args = MagicMock()
    args.command = "stats"

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["stats"].assert_called_once()


def test_handle_cli_arguments_view():
    mock_handlers = {"view": MagicMock()}
    args = MagicMock()
    args.command = "view"
    args.group_id = 1
    args.category = "Ideas"
    args.start_date = None
    args.end_date = None
    args.post_author = None
    args.comment_author = None
    args.keyword = None
    args.min_comments = None
    args.max_comments = None
    args.is_idea = False
    args.limit = 5

    handle_cli_arguments(args, mock_handlers)
    mock_handlers["view"].assert_called_once_with(
        group_id=1,
        filters={
            "category": "Ideas",
            "start_date": None,
            "end_date": None,
            "post_author": None,
            "comment_author": None,
            "keyword": None,
            "min_comments": None,
            "max_comments": None,
            "is_idea": False,
        },
        limit=5,
    )


# AsyncMock is available in unittest.mock from Python 3.8+

from unittest.mock import AsyncMock
