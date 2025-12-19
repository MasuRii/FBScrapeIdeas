import unittest
from unittest.mock import patch, MagicMock
import os
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from scraper.facebook_scraper import scrape_authenticated_group
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read test group links from file
TEST_GROUP_LINKS = []
with open(os.path.join('memory-bank', 'FacebookGroupLinks.txt'), 'r') as f:
    TEST_GROUP_LINKS = [line.strip() for line in f if line.strip()]

class TestFacebookScraper(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.mock_driver = MagicMock(spec=WebDriver)
        self.mock_driver.find_elements.return_value = []
        self.mock_driver.current_url = "https://www.facebook.com/groups/test"
        self.mock_driver.execute_script.return_value = None

        # Create mock post elements
        self.mock_posts = []
        for i in range(20):  # Enough posts to test limiting
            mock_post = MagicMock(spec=WebElement)
            mock_post.get_attribute.return_value = f"<div>Test Post {i}</div>"
            mock_post.find_elements.return_value = [MagicMock(get_attribute=lambda _: f"https://facebook.com/post{i}")]
            self.mock_posts.append(mock_post)

    def test_scraper_headless(self):
        """Test scraper in headless mode with post count limit"""
        # Configure mock driver behavior
        self.mock_driver.find_elements.side_effect = [
            self.mock_posts[:5],  # First scroll
            self.mock_posts[:10], # Second scroll
            self.mock_posts[:15], # Third scroll
            self.mock_posts[:20]  # Final scroll
        ]

        # Call scraper with limit of 10 posts
        results = list(scrape_authenticated_group(
            self.mock_driver,
            TEST_GROUP_LINKS[0],
            num_posts=10
        ))

        # Verify we got exactly 10 posts
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertIn('facebook_post_id', result)
            self.assertIn('post_url', result)
            self.assertIn('content_text', result)

    def test_scraper_with_all_group_links(self):
        """Test scraper with all available test group links"""
        for group_url in TEST_GROUP_LINKS:
            with self.subTest(group_url=group_url):
                self.mock_driver.find_elements.side_effect = [
                    self.mock_posts[:5],
                    self.mock_posts[:10]
                ]

                results = list(scrape_authenticated_group(
                    self.mock_driver,
                    group_url,
                    num_posts=5
                ))

                self.assertEqual(len(results), 5)
                self.assertTrue(all('facebook_post_id' in r for r in results))

    def test_scraper_with_insufficient_posts(self):
        """Test when fewer posts available than requested"""
        self.mock_driver.find_elements.side_effect = [
            self.mock_posts[:3],  # Only 3 posts available
            self.mock_posts[:3]
        ]

        results = list(scrape_authenticated_group(
            self.mock_driver,
            TEST_GROUP_LINKS[0],
            num_posts=10
        ))

        # Should return only available posts
        self.assertEqual(len(results), 3)

    def test_scraper_error_handling(self):
        """Test error handling during scraping"""
        self.mock_driver.find_elements.side_effect = Exception("Test error")

        with self.assertLogs(logger, level='ERROR') as cm:
            results = list(scrape_authenticated_group(
                self.mock_driver,
                TEST_GROUP_LINKS[0],
                num_posts=10
            ))
            self.assertTrue(any('Test error' in log for log in cm.output))
            self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()