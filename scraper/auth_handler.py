"""
Authentication handler for Facebook scraping.
Re-exports get_facebook_credentials from config for backward compatibility.
"""

# Import from config.py to maintain single source of truth
from config import get_facebook_credentials

# Re-export for any modules that import from auth_handler
__all__ = ["get_facebook_credentials"]

if __name__ == "__main__":
    try:
        fb_user, fb_pass = get_facebook_credentials()
        print("Credentials obtained (not displayed for security).")
    except ValueError as e:
        print(f"Error: {e}")
