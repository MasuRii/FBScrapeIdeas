import os
from dotenv import load_dotenv
import getpass
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_google_api_key():
    """Loads the Google API key from environment variables."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables or .env file")
    return google_api_key

def get_facebook_credentials() -> tuple[str, str]:
    """
    Securely gets Facebook username and password from environment variables or via command line prompt.
    Prioritizes environment variables (FB_USER, FB_PASS) for non-interactive use.
    If not found in env, prompts the user securely.
    """
    fb_user = os.getenv("FB_USER")
    fb_pass = os.getenv("FB_PASS")

    if fb_user and fb_pass:
        logging.info("Loading Facebook credentials from environment variables.")
        return fb_user, fb_pass
    else:
        logging.info("Facebook credentials not found in environment variables. Prompting user.")
        try:
            username = input("Enter Facebook Email/Username: ")
            password = getpass.getpass("Enter Facebook Password: ")
            if not username or not password:
                raise ValueError("Username or password cannot be empty.")
            return username, password
        except Exception as e:
            logging.error(f"Error getting Facebook credentials: {e}")
            raise ValueError("Failed to get Facebook credentials.") from e

