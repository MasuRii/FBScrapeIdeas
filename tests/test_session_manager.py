import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from scraper.session_manager import SessionManager


class TestSessionManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session_manager = SessionManager("test_state.json")

    async def test_validate_session_logged_in(self):
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page

        # Mock profile button found
        mock_page.query_selector.side_effect = (
            lambda selector: AsyncMock() if selector == '[aria-label="Your profile"]' else None
        )

        result = await self.session_manager.validate_session(mock_context)
        self.assertTrue(result)

    async def test_validate_session_logged_out(self):
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page

        # Mock login form found, profile button not found
        mock_page.query_selector.side_effect = (
            lambda selector: AsyncMock()
            if selector == 'form[data-testid="royal_login_form"]'
            else None
        )

        result = await self.session_manager.validate_session(mock_context)
        self.assertFalse(result)

    async def test_validate_session_exception(self):
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_page.goto.side_effect = Exception("Network error")

        # Validation should return False (via tenacity retry failure or explicit catch)
        # Note: retry is configured to reraise=False in validate_session
        result = await self.session_manager.validate_session(mock_context)
        self.assertFalse(result)
