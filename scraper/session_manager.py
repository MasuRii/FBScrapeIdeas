import asyncio
import json
import os
import logging
from playwright.async_api import async_playwright, BrowserContext, Playwright
from tenacity import retry, stop_after_attempt, wait_exponential
from config import SESSION_STATE_PATH
from credential_manager import CredentialManager, set_secure_permissions

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Handles Playwright's storage_state lifecycle (Save/Load/Manual Login).
    """

    def __init__(self, state_path: str = SESSION_STATE_PATH):
        self.state_path = state_path

    async def get_context(self, playwright: Playwright, headless: bool = True) -> BrowserContext:
        """
        Loads storage_state if it exists; otherwise triggers manual login.

        Args:
            playwright: The async_playwright instance.
            headless: Whether to run the browser in headless mode.

        Returns:
            A Playwright BrowserContext with the session loaded.
        """
        browser = await playwright.chromium.launch(headless=headless)

        if os.path.exists(self.state_path):
            logger.info(f"Attempting to load session from {os.path.basename(self.state_path)}")
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Decrypt the content. Handles backward compatibility for plain-text JSON.
                decrypted_content = CredentialManager.decrypt(content)
                state_dict = json.loads(decrypted_content)

                context = await browser.new_context(storage_state=state_dict)

                if await self.validate_session(context):
                    logger.info("Session is valid.")
                    return context
                else:
                    logger.warning("Session is invalid or expired. Triggering manual login.")
                    await context.close()
                    await browser.close()
            except Exception as e:
                logger.error(f"Failed to load/decrypt session state: {e}")
                await browser.close()
        else:
            logger.info("No session state found. Triggering manual login.")
            await browser.close()

        # Trigger manual login if no valid session exists
        return await self.manual_login(playwright)

    async def manual_login(self, playwright: Playwright) -> BrowserContext:
        """
        Launches a visible browser, waits for user to log in, and saves state.

        Args:
            playwright: The async_playwright instance.

        Returns:
            A Playwright BrowserContext after successful login.
        """
        logger.info("Launching headful browser for manual login...")
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("\n" + "=" * 60)
        print("  MANUAL LOGIN REQUIRED")
        print("=" * 60)
        print("  1. A browser window has opened.")
        print("  2. Please log in to Facebook manually.")
        print("  3. Once you reach the News Feed, the session will be saved.")
        print("  4. Do NOT close the browser window manually.")
        print("=" * 60 + "\n")

        await page.goto("https://www.facebook.com/")

        try:
            # Wait for navigation to the feed - detect by URL not containing 'login'
            # and containing 'facebook.com'
            logger.info("Waiting for user to complete login...")
            await page.wait_for_url(
                lambda url: "facebook.com" in url and "login" not in url,
                timeout=300000,  # 5 minutes timeout for manual login
            )

            # Wait for a known-logged-in element to be absolutely sure
            # Global nav usually appears on the feed
            await page.wait_for_selector('[aria-label="Your profile"]', timeout=30000)

            logger.info("Login detected. Saving session state...")

            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)

            # Save storage state (cookies + local storage)
            state_dict = await context.storage_state()
            encrypted_state = CredentialManager.encrypt(json.dumps(state_dict))

            with open(self.state_path, "w", encoding="utf-8") as f:
                f.write(encrypted_state)

            # Set secure permissions
            set_secure_permissions(self.state_path)

            logger.info(
                f"Session saved successfully (encrypted) to {os.path.basename(self.state_path)}"
            )

            print("\n  [SUCCESS] Session saved! Continuing...\n")
            return context

        except Exception as e:
            logger.error(f"Manual login failed or timed out: {e}")
            await browser.close()
            raise

    async def validate_session(self, context: BrowserContext) -> bool:
        """
        Opens a page and checks for a 'logged in' indicator.
        Includes exponential backoff retries. Returns False if all attempts fail.

        Args:
            context: The Playwright BrowserContext to validate.

        Returns:
            True if the session is valid (logged in), False otherwise.
        """
        try:
            return await self._validate_session_internal(context)
        except Exception as e:
            logger.debug(f"Session validation failed after retries: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _validate_session_internal(self, context: BrowserContext) -> bool:
        """Internal method for session validation with retry logic."""
        page = await context.new_page()
        try:
            # Navigate to Facebook home
            await page.goto(
                "https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000
            )

            # Check for a "logged in" indicator
            # 1. Profile button
            profile_btn = await page.query_selector('[aria-label="Your profile"]')
            if profile_btn:
                return True

            # 2. Check for absence of login form
            login_form = await page.query_selector('form[data-testid="royal_login_form"]')
            if login_form:
                return False

            # 3. Check for specific text that only appears when logged in
            if await page.query_selector('text="What\'s on your mind?"'):
                return True

            return False
        except Exception as e:
            # Raise exception to trigger tenacity retry
            raise e
        finally:
            await page.close()
