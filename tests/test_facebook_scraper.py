import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from scraper.facebook_scraper import scrape_authenticated_group

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read test group links from file (with fallback for missing file)
TEST_GROUP_LINKS = []
_group_links_path = os.path.join("memory-bank", "FacebookGroupLinks.txt")
if os.path.exists(_group_links_path):
    with open(_group_links_path) as f:
        TEST_GROUP_LINKS = [line.strip() for line in f if line.strip()]

# Fallback test URLs if file doesn't exist
if not TEST_GROUP_LINKS:
    TEST_GROUP_LINKS = ["https://www.facebook.com/groups/testgroup"]


def create_mock_post(index: int) -> MagicMock:
    """Create a properly configured mock post element"""
    mock_post = MagicMock(spec=WebElement)

    # Create a proper mock link element that returns a valid Facebook URL
    mock_link = MagicMock()
    # URL must have facebook.com in netloc, and /posts/ in path for ID extraction
    post_id = 100000000000 + index
    mock_link.get_attribute.return_value = f"https://www.facebook.com/groups/test/posts/{post_id}"

    # find_elements returns list with the link (used for permalink extraction)
    mock_post.find_elements.return_value = [mock_link]

    # find_element raises exception (for timestamp fallback - not needed if link found)
    mock_post.find_element.side_effect = Exception("Not found")

    # get_attribute returns HTML content (used for outerHTML extraction)
    mock_post.get_attribute.return_value = f"<div>Test Post {index} content</div>"

    return mock_post


def create_mock_extracted_data(post_url: str, post_id: str) -> dict:
    """Create mock extracted post data that passes validation"""
    return {
        "facebook_post_id": post_id,
        "post_url": post_url,
        "content_text": f"Test content for post {post_id}",
        "posted_at": "2025-01-01T12:00:00+00:00",
        "scraped_at": "2025-01-01T12:00:00+00:00",
        "post_author_name": "Test Author",
        "post_author_profile_pic_url": None,
        "post_image_url": None,
        "comments": [],
    }


class TestFacebookScraper(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.mock_driver = MagicMock(spec=WebDriver)
        self.mock_driver.current_url = "https://www.facebook.com/groups/test"
        self.mock_driver.execute_script.return_value = None
        # By default find_elements returns empty list for overlay checks
        self.mock_driver.find_elements.return_value = []

        # Create mock post elements
        self.mock_posts = [create_mock_post(i) for i in range(20)]

    def _create_smart_wait_mock(self):
        """Create a WebDriverWait mock that succeeds for initial waits but fails for overlays"""
        mock_wait_instance = MagicMock()
        call_count = [0]

        def until_side_effect(condition):
            call_count[0] += 1
            # First few calls are for feed/post detection - return mock element
            # Increased limit to allow for overlay checks and other initial waits
            if call_count[0] <= 15:
                mock_element = MagicMock()
                mock_element.is_displayed.return_value = False
                mock_element.is_enabled.return_value = True
                return mock_element
            # Later calls are for overlays, wait conditions, see more buttons - raise timeout
            raise TimeoutException("Mocked timeout")

        mock_wait_instance.until.side_effect = until_side_effect
        return mock_wait_instance

    @patch("scraper.facebook_scraper._extract_data_from_post_html")
    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.time.sleep", return_value=None)
    def test_scraper_headless(self, mock_sleep, mock_webdriver_wait, mock_extract):
        """Test scraper in headless mode with post count limit"""
        mock_webdriver_wait.return_value = self._create_smart_wait_mock()

        # Mock the extract function to return valid data
        def extract_side_effect(html, post_url, post_id, group_url, fields=None):
            if post_url and post_id:
                return create_mock_extracted_data(post_url, post_id)
            return None

        mock_extract.side_effect = extract_side_effect

        # Track find_elements calls
        call_count = [0]

        def find_elements_side_effect(by, value=None):
            # Check if this is a call for posts
            from scraper.facebook_scraper import POST_CONTAINER_S

            if (by, value) == POST_CONTAINER_S or value == POST_CONTAINER_S[1]:
                call_count[0] += 1
                if call_count[0] <= 2:
                    return self.mock_posts[:5]
                elif call_count[0] <= 4:
                    return self.mock_posts[:10]
                elif call_count[0] <= 6:
                    return self.mock_posts[:15]
                return self.mock_posts[:20]
            # Otherwise it's likely an overlay check - return empty list
            return []

        self.mock_driver.find_elements.side_effect = find_elements_side_effect

        # Call scraper with limit of 10 posts
        results = list(
            scrape_authenticated_group(self.mock_driver, TEST_GROUP_LINKS[0], num_posts=10)
        )

        # Verify we got exactly 10 posts
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertIn("facebook_post_id", result)
            self.assertIn("post_url", result)
            self.assertIn("content_text", result)

    @patch("scraper.facebook_scraper._extract_data_from_post_html")
    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.time.sleep", return_value=None)
    def test_scraper_with_all_group_links(self, mock_sleep, mock_webdriver_wait, mock_extract):
        """Test scraper with all available test group links"""

        def extract_side_effect(html, post_url, post_id, group_url, fields=None):
            if post_url and post_id:
                return create_mock_extracted_data(post_url, post_id)
            return None

        mock_extract.side_effect = extract_side_effect

        for group_url in TEST_GROUP_LINKS:
            with self.subTest(group_url=group_url):
                mock_webdriver_wait.return_value = self._create_smart_wait_mock()

                call_count = [0]

                def find_elements_side_effect(by, value=None):
                    from scraper.facebook_scraper import POST_CONTAINER_S

                    if (by, value) == POST_CONTAINER_S or value == POST_CONTAINER_S[1]:
                        call_count[0] += 1
                        if call_count[0] <= 2:
                            return self.mock_posts[:5]
                        return self.mock_posts[:10]
                    return []

                self.mock_driver.find_elements.side_effect = find_elements_side_effect

                results = list(scrape_authenticated_group(self.mock_driver, group_url, num_posts=5))

                self.assertEqual(len(results), 5)
                self.assertTrue(all("facebook_post_id" in r for r in results))

    @patch("scraper.facebook_scraper._extract_data_from_post_html")
    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.time.sleep", return_value=None)
    def test_scraper_with_insufficient_posts(self, mock_sleep, mock_webdriver_wait, mock_extract):
        """Test when fewer posts available than requested"""
        mock_webdriver_wait.return_value = self._create_smart_wait_mock()

        def extract_side_effect(html, post_url, post_id, group_url, fields=None):
            if post_url and post_id:
                return create_mock_extracted_data(post_url, post_id)
            return None

        mock_extract.side_effect = extract_side_effect

        # Configure find_elements to only return posts for the post selector
        def find_elements_side_effect(by, value=None):
            from scraper.facebook_scraper import POST_CONTAINER_S

            if (by, value) == POST_CONTAINER_S or value == POST_CONTAINER_S[1]:
                return self.mock_posts[:3]
            return []

        self.mock_driver.find_elements.side_effect = find_elements_side_effect

        results = list(
            scrape_authenticated_group(self.mock_driver, TEST_GROUP_LINKS[0], num_posts=10)
        )

        # Should return only available posts
        self.assertEqual(len(results), 3)

    @patch("scraper.facebook_scraper.WebDriverWait")
    def test_scraper_error_handling(self, mock_webdriver_wait):
        """Test error handling during scraping"""
        # Configure mock WebDriverWait to raise a generic exception (not TimeoutException)
        # This simulates an unexpected error during scraping
        mock_wait_instance = MagicMock()
        mock_wait_instance.until.side_effect = Exception("Test error")
        mock_webdriver_wait.return_value = mock_wait_instance

        # Use the root logger since facebook_scraper logs to root via logging.error()
        with self.assertLogs(level="ERROR") as cm:
            results = list(
                scrape_authenticated_group(self.mock_driver, TEST_GROUP_LINKS[0], num_posts=10)
            )
            self.assertTrue(any("Test error" in log for log in cm.output))
            self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
