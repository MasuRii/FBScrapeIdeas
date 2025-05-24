import os
from dotenv import load_dotenv

load_dotenv()

def get_google_api_key():
    """Loads the Google API key from environment variables."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables or .env file")
    return google_api_key 