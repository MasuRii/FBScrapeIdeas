import os
import sys
import getpass
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Platform-Appropriate Data Directory ---

def get_app_data_dir() -> str:
    r"""
    Get the platform-appropriate application data directory.
    
    Returns:
        - Windows: %APPDATA%\FBScrapeIdeas\
        - macOS: ~/Library/Application Support/FBScrapeIdeas/
        - Linux: ~/.local/share/fbscrapeideas/ (XDG_DATA_HOME)
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        app_dir = os.path.join(base, 'FBScrapeIdeas')
    elif sys.platform == 'darwin':
        app_dir = os.path.expanduser('~/Library/Application Support/FBScrapeIdeas')
    else:
        # Linux/Unix - follow XDG Base Directory Specification
        base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        app_dir = os.path.join(base, 'fbscrapeideas')
    
    return app_dir


def is_frozen() -> bool:
    """Check if running as a frozen executable (PyInstaller, cx_Freeze, etc.)."""
    return getattr(sys, 'frozen', False)


def get_env_file_path() -> str:
    """
    Get the path to the .env file.
    
    - For frozen executables: Uses platform-appropriate app data directory
    - For development: Uses current directory, but checks app data dir for existing .env first
    """
    if is_frozen():
        # Use platform-appropriate app data directory for frozen builds
        app_dir = get_app_data_dir()
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, '.env')
    else:
        # Development mode - prefer current directory .env if it exists
        local_env = os.path.join(os.getcwd(), '.env')
        if os.path.exists(local_env):
            return local_env
        
        # Check if app data dir has an existing .env (for persistence across dev runs)
        app_dir = get_app_data_dir()
        app_env = os.path.join(app_dir, '.env')
        if os.path.exists(app_env):
            return app_env
        
        # Default to local .env for new development setups
        return local_env


def get_db_path(db_name: str = 'insights.db') -> str:
    """
    Get the database path, using app data directory for frozen builds.
    
    - For frozen executables: Uses platform-appropriate app data directory
    - For development: Uses current directory, but supports app data dir if DB exists there
    """
    if is_frozen():
        app_dir = get_app_data_dir()
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, db_name)
    else:
        # Development mode - prefer current directory
        local_db = os.path.join(os.getcwd(), db_name)
        if os.path.exists(local_db):
            return local_db
        
        # Check if app data dir has an existing DB
        app_dir = get_app_data_dir()
        app_db = os.path.join(app_dir, db_name)
        if os.path.exists(app_db):
            return app_db
        
        # Default to local db for new development setups
        return local_db


# --- Load .env from appropriate location ---
_env_path = get_env_file_path()
if os.path.exists(_env_path):
    load_dotenv(_env_path)
    logging.info(f"Loaded environment from: {_env_path}")
else:
    # Try loading from default locations (CWD, etc.)
    load_dotenv()


# --- Credential Saving ---

def save_credential_to_env(key: str, value: str) -> bool:
    """
    Save or update a credential in the .env file.
    
    Args:
        key: The environment variable name (e.g., "GOOGLE_API_KEY")
        value: The value to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    env_path = get_env_file_path()
    
    # Ensure directory exists
    env_dir = os.path.dirname(env_path)
    if env_dir and not os.path.exists(env_dir):
        try:
            os.makedirs(env_dir, exist_ok=True)
        except OSError as e:
            logging.error(f"Failed to create directory {env_dir}: {e}")
            return False
    
    try:
        # Read existing content
        existing_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Update or add the key
        key_found = False
        new_lines = []
        for line in existing_lines:
            stripped = line.strip()
            # Check if this line defines our key (handle KEY=value, KEY = value, etc.)
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)
        
        if not key_found:
            # Add newline before new key if file doesn't end with one
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # Also set in current environment
        os.environ[key] = value
        
        logging.info(f"Saved {key} to {env_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to save credential {key}: {e}")
        return False


def delete_env_file() -> bool:
    """
    Delete the .env file (for clearing all credentials).
    
    Returns:
        True if deleted successfully or file didn't exist, False on error
    """
    env_path = get_env_file_path()
    
    try:
        if os.path.exists(env_path):
            os.remove(env_path)
            logging.info(f"Deleted credentials file: {env_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to delete credentials file: {e}")
        return False


# --- Credential Retrieval with Prompting ---

def get_google_api_key() -> str:
    """
    Gets the Google API key from environment variables or prompts the user.
    
    Returns:
        The Google API key
        
    Raises:
        ValueError: If no API key is provided
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if api_key:
        logging.info("Loading Google API key from environment variables.")
        return api_key
    
    logging.info("Google API key not found. Prompting user.")
    print("\n" + "=" * 50)
    print("  Google API Key not found!")
    print("=" * 50)
    print("\nThe Gemini API key is required for AI features.")
    print("Get your API key from: https://aistudio.google.com/apikey\n")
    
    try:
        api_key = getpass.getpass("Enter Google API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        raise ValueError("Google API key is required for AI features.")
    
    if not api_key:
        raise ValueError("Google API key is required for AI features.")
    
    # Offer to save
    try:
        save = input("Save API key for future sessions? (y/n): ").lower().strip()
        if save == 'y':
            if save_credential_to_env("GOOGLE_API_KEY", api_key):
                print("  API key saved!")
            else:
                print("  Warning: Failed to save API key. It will need to be re-entered next time.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Skipping save.")
    
    return api_key


def get_facebook_credentials() -> tuple[str, str]:
    """
    Securely gets Facebook username and password from environment variables or via command line prompt.
    Prioritizes environment variables (FB_USER, FB_PASS) for non-interactive use.
    If not found in env, prompts the user securely and offers to save.
    
    Returns:
        Tuple of (username, password)
        
    Raises:
        ValueError: If credentials are empty or not provided
    """
    fb_user = os.getenv("FB_USER")
    fb_pass = os.getenv("FB_PASS")

    if fb_user and fb_pass:
        logging.info("Loading Facebook credentials from environment variables.")
        return fb_user, fb_pass
    
    logging.info("Facebook credentials not found in environment variables. Prompting user.")
    print("\n" + "=" * 50)
    print("  Facebook Credentials Required")
    print("=" * 50)
    print("\nFacebook credentials are required for scraping.\n")
    
    try:
        username = input("Enter Facebook Email/Username: ").strip()
        password = getpass.getpass("Enter Facebook Password: ")
    except (EOFError, KeyboardInterrupt):
        print("\n")
        raise ValueError("Facebook email and password are required.")
    
    if not username or not password:
        raise ValueError("Facebook email and password are required.")
    
    # Offer to save
    try:
        save = input("Save credentials for future sessions? (y/n): ").lower().strip()
        if save == 'y':
            saved_user = save_credential_to_env("FB_USER", username)
            saved_pass = save_credential_to_env("FB_PASS", password)
            if saved_user and saved_pass:
                print("  Credentials saved!")
            else:
                print("  Warning: Failed to save credentials. They will need to be re-entered next time.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Skipping save.")
    
    return username, password


# --- First-Run Detection ---

def is_first_run() -> bool:
    """
    Check if this is the first run of the application.
    
    Returns:
        True if no .env file exists (first run), False otherwise
    """
    env_path = get_env_file_path()
    return not os.path.exists(env_path)


def has_google_api_key() -> bool:
    """Check if Google API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY"))


def has_facebook_credentials() -> bool:
    """Check if Facebook credentials are configured."""
    return bool(os.getenv("FB_USER") and os.getenv("FB_PASS"))


# --- Setup Wizard ---

def run_setup_wizard() -> None:
    """Interactive setup wizard for first-time users."""
    print("\n" + "-" * 50)
    print("  SETUP WIZARD")
    print("-" * 50)
    
    # Google API Key
    print("\n1)  Google Gemini API Key")
    print("    Get your key: https://aistudio.google.com/apikey")
    
    try:
        api_key = getpass.getpass("    Enter API Key (or press Enter to skip): ").strip()
        if api_key:
            if save_credential_to_env("GOOGLE_API_KEY", api_key):
                print("    Saved!")
            else:
                print("    Warning: Failed to save API key.")
    except (EOFError, KeyboardInterrupt):
        print("\n    Skipped.")
    
    # Facebook Credentials
    print("\n2)  Facebook Credentials")
    print("    Required for scraping Facebook groups")
    
    try:
        fb_setup = input("    Set up now? (y/n): ").lower().strip()
        if fb_setup == 'y':
            username = input("    Email/Username: ").strip()
            password = getpass.getpass("    Password: ")
            if username and password:
                saved_user = save_credential_to_env("FB_USER", username)
                saved_pass = save_credential_to_env("FB_PASS", password)
                if saved_user and saved_pass:
                    print("    Saved!")
                else:
                    print("    Warning: Failed to save credentials.")
    except (EOFError, KeyboardInterrupt):
        print("\n    Skipped.")
    
    print("\n" + "-" * 50)
    print("  Setup complete!")
    print("-" * 50)
    print(f"\nCredentials saved to: {get_env_file_path()}")
    print("You can edit this file directly to update credentials.\n")
