import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from scraper.playwright_scraper import PlaywrightScraper


class TestPlaywrightScraper(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We don't want __init__ to actually call ensure_playwright_installed or SessionManager
        with (
            patch("scraper.playwright_scraper.ensure_playwright_installed"),
            patch("scraper.playwright_scraper.SessionManager"),
        ):
            self.scraper = PlaywrightScraper(headless=True)

    def test_derive_post_id_numeric(self):
        url = "https://www.facebook.com/groups/123/posts/456789/"
        self.assertEqual(self.scraper._derive_post_id(url), "456789")

    def test_derive_post_id_permalink(self):
        url = "https://www.facebook.com/groups/123/permalink/987654321/"
        self.assertEqual(self.scraper._derive_post_id(url), "987654321")

    def test_derive_post_id_query_param(self):
        url = "https://www.facebook.com/story.php?story_fbid=112233&id=445566"
        self.assertEqual(self.scraper._derive_post_id(url), "112233")

    async def test_extract_post_data_success(self):
        mock_element = AsyncMock()
        # Mock the evaluate method to return post data
        mock_element.evaluate.return_value = {
            "content_text": "Test content",
            "post_author_name": "Test Author",
            "raw_timestamp": "2025-01-01",
            "post_url": "https://www.facebook.com/groups/123/posts/123",
        }

        with patch("scraper.playwright_scraper.parse_fb_timestamp") as mock_parse:
            mock_parse.return_value = MagicMock()
            mock_parse.return_value.isoformat.return_value = "2025-01-01T00:00:00Z"

            result = await self.scraper._extract_post_data(mock_element)

            self.assertIsNotNone(result)
            self.assertEqual(result["facebook_post_id"], "123")
            self.assertEqual(result["text"], "Test content")
            self.assertEqual(result["author_name"], "Test Author")
            self.assertEqual(result["timestamp"], "2025-01-01T00:00:00Z")

    async def test_extract_post_data_missing_fields(self):
        mock_element = AsyncMock()
        mock_element.evaluate.return_value = {
            "content_text": None,
            "post_author_name": None,
            "raw_timestamp": None,
            "post_url": None,
        }
        result = await self.scraper._extract_post_data(mock_element)
        self.assertIsNone(result)

    async def test_prune_dom_call(self):
        mock_page = AsyncMock()
        await self.scraper._prune_dom(mock_page)
        mock_page.evaluate.assert_called_once()
        self.assertIn("querySelectorAll", mock_page.evaluate.call_args[0][0])
