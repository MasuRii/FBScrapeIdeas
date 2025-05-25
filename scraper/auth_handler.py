import os
import getpass

def get_facebook_credentials() -> tuple[str, str]:
    """Securely gets Facebook credentials from environment variables or CLI input."""
    username = os.getenv("FB_USER")
    password = os.getenv("FB_PASS")

    if not username or not password:
        print("Please provide Facebook credentials.")
        username = input("Enter Facebook username/email: ")
        password = getpass.getpass("Enter Facebook password: ")

    if not username or not password:
        raise ValueError("Facebook username and password must be provided.")

    return username, password

if __name__ == "__main__":
    # Example usage for testing
    try:
        fb_user, fb_pass = get_facebook_credentials()
        print("Credentials obtained (not displayed for security).")
        # In a real scenario, these would be passed to the scraper
        # print(f"Username: {fb_user}") # Do NOT print sensitive info
        # print(f"Password: {fb_pass}") # Do NOT print sensitive info
    except ValueError as e:
        print(f"Error: {e}") 