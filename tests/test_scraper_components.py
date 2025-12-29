import pytest
import runpy
import sys
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, UTC, timedelta
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By

from scraper.timestamp_parser import parse_fb_timestamp
from scraper.webdriver_setup import init_webdriver
from scraper.facebook_scraper import (
    login_to_facebook,
    check_facebook_session,
    is_facebook_session_valid,
    _get_post_identifiers_from_element,
    _extract_data_from_post_html,
)

# --- Timestamp Parser Tests ---


def test_parse_fb_timestamp_relative():
    """Test parsing relative timestamps."""
    now = datetime.now(UTC)
    result = parse_fb_timestamp("2 hrs ago")
    assert result is not None
    assert result.tzinfo == UTC
    assert now - timedelta(hours=2, minutes=5) <= result <= now - timedelta(hours=1, minutes=55)


def test_parse_fb_timestamp_absolute():
    """Test parsing absolute timestamps."""
    result = parse_fb_timestamp("January 1, 2024 at 12:00 PM")
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0


def test_parse_fb_timestamp_failure():
    """Test parsing failure."""
    result = parse_fb_timestamp("not a timestamp")
    assert result is None


# --- Auth Handler Tests ---


def test_auth_handler_main():
    """Test the main block of auth_handler."""
    with patch("config.get_facebook_credentials", return_value=("user", "pass")):
        with patch("builtins.print") as mock_print:
            if "scraper.auth_handler" in sys.modules:
                del sys.modules["scraper.auth_handler"]
            runpy.run_module("scraper.auth_handler", run_name="__main__")
            mock_print.assert_any_call("Credentials obtained (not displayed for security).")


def test_auth_handler_main_error():
    """Test the main block of auth_handler with error."""
    with patch("config.get_facebook_credentials", side_effect=ValueError("Missing creds")):
        with patch("builtins.print") as mock_print:
            if "scraper.auth_handler" in sys.modules:
                del sys.modules["scraper.auth_handler"]
            runpy.run_module("scraper.auth_handler", run_name="__main__")
            mock_print.assert_any_call("Error: Missing creds")


# --- WebDriver Setup Tests ---


@patch("scraper.webdriver_setup.webdriver.Chrome")
@patch("scraper.webdriver_setup.Service")
@patch("scraper.webdriver_setup.ChromeDriverManager")
def test_init_webdriver(mock_manager, mock_service, mock_chrome):
    """Test WebDriver initialization."""
    mock_driver_instance = MagicMock()
    mock_chrome.return_value = mock_driver_instance

    driver = init_webdriver(headless=True)

    assert driver == mock_driver_instance
    mock_chrome.assert_called_once()
    mock_driver_instance.implicitly_wait.assert_called_with(2)
    mock_driver_instance.execute_cdp_cmd.assert_called_once()


@patch("scraper.webdriver_setup.webdriver.Chrome")
@patch("scraper.webdriver_setup.Service")
@patch("scraper.webdriver_setup.ChromeDriverManager")
def test_init_webdriver_failure(mock_manager, mock_service, mock_chrome):
    """Test WebDriver initialization failure."""
    mock_chrome.side_effect = WebDriverException("Failed to start")

    with pytest.raises(WebDriverException, match="Failed to initialize Chrome WebDriver"):
        init_webdriver()


@patch("scraper.webdriver_setup.webdriver.Chrome")
@patch("scraper.webdriver_setup.Service")
@patch("scraper.webdriver_setup.ChromeDriverManager")
def test_webdriver_setup_main(mock_manager, mock_service, mock_chrome):
    """Test the main block of webdriver_setup."""
    if "scraper.webdriver_setup" in sys.modules:
        del sys.modules["scraper.webdriver_setup"]

    mock_driver = MagicMock()
    mock_chrome.return_value = mock_driver
    mock_driver.title = "Google"

    with patch("builtins.print") as mock_print:
        runpy.run_module("scraper.webdriver_setup", run_name="__main__")
        mock_print.assert_any_call("WebDriver initialized successfully.")
        mock_print.assert_any_call("Accessed page title: Google")


# --- Facebook Scraper Helper Tests ---


@patch("scraper.facebook_scraper.WebDriverWait")
@patch("scraper.facebook_scraper.EC")
def test_login_to_facebook_success(mock_ec, mock_wait):
    """Test successful login."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance

    # Mock elements
    mock_accept = MagicMock()
    mock_email = MagicMock()
    mock_pass = MagicMock()
    mock_login = MagicMock()
    mock_feed = MagicMock()

    # Configure wait.until to return these elements in order
    mock_wait_instance.until.side_effect = [
        mock_accept,  # cookie banner
        mock_email,  # email field
        mock_pass,  # password field
        mock_login,  # login button
        mock_feed,  # post-login feed
    ]

    result = login_to_facebook(mock_driver, "user", "pass")

    assert result is True
    mock_driver.get.assert_called_with("https://www.facebook.com/")


@patch("scraper.facebook_scraper.WebDriverWait")
def test_login_to_facebook_timeout(mock_wait):
    """Test login timeout."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance
    mock_wait_instance.until.side_effect = TimeoutException("Timeout")

    with patch("scraper.facebook_scraper.time.sleep", return_value=None):
        result = login_to_facebook(mock_driver, "user", "pass")

    assert result is False


@patch("scraper.facebook_scraper.WebDriverWait")
@patch("scraper.facebook_scraper.EC")
def test_check_facebook_session_active(mock_ec, mock_wait):
    """Test check_facebook_session when active."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance

    result = check_facebook_session(mock_driver)

    assert result is True
    mock_driver.get.assert_called_with("https://www.facebook.com/")


@patch("scraper.facebook_scraper.WebDriverWait")
def test_check_facebook_session_inactive(mock_wait):
    """Test check_facebook_session when inactive."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance
    mock_wait_instance.until.side_effect = TimeoutException("Timeout")

    with patch("scraper.facebook_scraper.time.sleep", return_value=None):
        result = check_facebook_session(mock_driver)

    assert result is False


@patch("scraper.facebook_scraper.WebDriverWait")
@patch("scraper.facebook_scraper.EC")
def test_is_facebook_session_valid_success(mock_ec, mock_wait):
    """Test is_facebook_session_valid when valid."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance

    result = is_facebook_session_valid(mock_driver)

    assert result is True
    mock_driver.get.assert_called_with("https://www.facebook.com/settings")


@patch("scraper.facebook_scraper.WebDriverWait")
def test_is_facebook_session_valid_timeout(mock_wait):
    """Test is_facebook_session_valid when timeout."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance
    mock_wait_instance.until.side_effect = TimeoutException("Timeout")

    with patch("scraper.facebook_scraper.time.sleep", return_value=None):
        result = is_facebook_session_valid(mock_driver)

    assert result is False


def test_get_post_identifiers_success():
    """Test extraction of post identifiers from element."""
    mock_element = MagicMock()
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "https://www.facebook.com/groups/test/posts/123456789/"
    mock_element.find_elements.return_value = [mock_link]

    url, post_id, is_valid = _get_post_identifiers_from_element(mock_element, "test_group")

    assert is_valid is True
    assert url == "https://www.facebook.com/groups/test/posts/123456789/"
    assert post_id == "123456789"


def test_get_post_identifiers_invalid_candidate():
    """Test when element is not a valid post candidate."""
    mock_element = MagicMock()
    mock_element.find_elements.return_value = []  # No link
    mock_element.find_element.side_effect = NoSuchElementException("No fallback")

    url, post_id, is_valid = _get_post_identifiers_from_element(mock_element, "test_group")

    assert is_valid is False


def test_extract_data_from_post_html_complex():
    """Test BeautifulSoup extraction from a more complex post HTML."""
    html = """
    <div role="article">
        <h2><strong>Author Name</strong></h2>
        <div data-ad-rendering-role="story_message">
            <span>Part 1</span>
            <span>Part 2</span>
        </div>
        <abbr title="Monday, January 1, 2024 at 12:00 PM">1 Jan</abbr>
        <img class="x168nmei" src="http://example.com/image.jpg">
        
        <!-- Comments -->
        <div aria-label="Comment by User One">
            <a href="/user/user1/"><span>User One</span></a>
            <div data-ad-preview="message"><span>Comment text one</span></div>
            <a href="https://facebook.com/comment?comment_id=999">Permalink</a>
        </div>
        <div aria-label="Comment by User Two" data-commentid="888">
            <a href="/profile.php?id=2"><span>User Two</span></a>
            <div dir="auto" style="text-align: start;">Comment text two</div>
        </div>
    </div>
    """

    data = _extract_data_from_post_html(html, "http://post.url", "post123", "group_url")

    assert data is not None
    assert data["facebook_post_id"] == "post123"
    assert data["author_name"] == "Author Name"
    assert "Part 1" in data["text"]
    assert "Part 2" in data["text"]
    assert data["post_image_url"] == "http://example.com/image.jpg"
    assert "2024-01-01" in data["timestamp"]

    assert len(data["comments"]) == 2
    assert data["comments"][0]["commenterName"] == "User One"
    assert data["comments"][0]["commentText"] == "Comment text one"
    assert data["comments"][0]["commentFacebookId"] == "999"

    assert data["comments"][1]["commenterName"] == "User Two"
    assert data["comments"][1]["commentText"] == "Comment text two"
    assert data["comments"][1]["commentFacebookId"] == "888"


def test_extract_data_from_post_html_author_pic():
    """Test author profile picture extraction."""
    html = """
    <div role="article">
        <div role="button">
            <svg><image xlink:href="http://example.com/author.jpg"></image></svg>
        </div>
        <h2><strong>Author Name</strong></h2>
        <div data-ad-rendering-role="story_message">Text</div>
        <abbr title="Jan 1, 2024">1 Jan</abbr>
    </div>
    """
    data = _extract_data_from_post_html(html, "http://post.url", "post123", "group_url")
    assert data is not None
    assert data["post_author_profile_pic_url"] == "http://example.com/author.jpg"


def test_extract_data_from_post_html_minimal():
    """Test extraction from minimal HTML that should still pass."""
    html = """
    <div role="article">
        <h2><strong>Author Name</strong></h2>
        <abbr title="Jan 1, 2024">1 Jan</abbr>
    </div>
    """
    data = _extract_data_from_post_html(html, "http://post.url", "post123", "group_url")
    assert data is not None
    assert data["author_name"] == "Author Name"


def test_extract_data_from_post_html_empty():
    """Test extraction from empty or irrelevant HTML."""
    html = "<div>Nothing here</div>"
    data = _extract_data_from_post_html(html, "http://post.url", "post123", "group_url")
    assert data is None
