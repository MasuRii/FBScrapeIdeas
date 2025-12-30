import unittest
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scraper.facebook_scraper import dismiss_overlays
from cli.console import safe_print


class TestOverlayDismissal(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        # Mocking By.XPATH for consistency
        self.patcher_by = patch("selenium.webdriver.common.by.By.XPATH", "xpath")
        self.patcher_by.start()

    def tearDown(self):
        self.patcher_by.stop()

    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.EC")
    def test_dismiss_overlays_success(self, mock_ec, mock_wait):
        """Test that dismiss_overlays finds an overlay and clicks the close button."""
        # 1. Setup mock overlay
        mock_overlay = MagicMock()
        mock_overlay.is_displayed.return_value = True

        # 2. Setup mock button
        mock_button = MagicMock()
        mock_button.is_displayed.return_value = True
        mock_button.is_enabled.return_value = True

        # 3. Configure driver to return the overlay
        # dismiss_overlays loops through overlay_container_selectors
        # We'll make it find one for the first selector
        self.mock_driver.find_elements.side_effect = (
            lambda by, xpath: [mock_overlay] if "dialog" in xpath else []
        )

        # 4. Configure WebDriverWait to return the button
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = mock_button

        # 5. Call the function
        dismiss_overlays(self.mock_driver)

        # 6. Verify button was clicked via execute_script
        self.mock_driver.execute_script.assert_any_call("arguments[0].click();", mock_button)
        safe_print("\n✅ Verified: Overlay button click was triggered via execute_script.")

    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.EC")
    def test_dismiss_overlays_no_overlay(self, mock_ec, mock_wait):
        """Test that dismiss_overlays handles no overlays correctly."""
        self.mock_driver.find_elements.return_value = []

        dismiss_overlays(self.mock_driver)

        # It should still call ensure_scrollable (via execute_script)
        # Match the implementation in scraper/facebook_scraper.py which uses FORCE_SCROLLABLE_SCRIPT wrapped in an IIFE
        self.mock_driver.execute_script.assert_any_call(
            "(() => {\n    document.body.style.overflow = 'visible';\n    document.body.style.overflowY = 'scroll';\n    document.documentElement.style.overflow = 'visible';\n    document.documentElement.style.overflowY = 'scroll';\n})()"
        )
        safe_print("✅ Verified: Correct actions taken when no overlays are present.")

    @patch("scraper.facebook_scraper.WebDriverWait")
    @patch("scraper.facebook_scraper.EC")
    def test_dismiss_overlays_fallback_to_esc(self, mock_ec, mock_wait):
        """Test that dismiss_overlays tries ESC key if no buttons are clickable."""
        mock_overlay = MagicMock()
        mock_overlay.is_displayed.return_value = True

        self.mock_driver.find_elements.side_effect = (
            lambda by, xpath: [mock_overlay] if "dialog" in xpath else []
        )

        # Configure WebDriverWait to fail for all buttons
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = TimeoutException("No button found")

        dismiss_overlays(self.mock_driver)

        # Verify ESC key script was called
        # Match the implementation which uses DISPATCH_ESC_SCRIPT wrapped in an IIFE
        esc_script = "(() => {\n    document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape', 'code': 'Escape', 'keyCode': 27}));\n    document.dispatchEvent(new KeyboardEvent('keyup', {'key': 'Escape', 'code': 'Escape', 'keyCode': 27}));\n})()"
        self.mock_driver.execute_script.assert_any_call(esc_script)
        safe_print("✅ Verified: Fallback to ESC key triggered when buttons are missing.")


if __name__ == "__main__":
    unittest.main()
