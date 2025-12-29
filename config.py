import logging
import os
import subprocess
import sys

from dotenv import load_dotenv
from credential_manager import (
    CredentialManager,
    save_credential_to_env as _save_credential,
    delete_env_file as _delete_env,
    get_google_api_key,
    get_facebook_credentials,
    get_openai_api_key,
    run_setup_wizard,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Platform-Appropriate Data Directory ---


def get_app_data_dir() -> str:
    r"""
    Get the platform-appropriate application data directory.

    Returns:
        - Windows: %APPDATA%\FBScrapeIdeas\
        - macOS: ~/Library/Application Support/FBScrapeIdeas/
        - Linux: ~/.local/share/fbscrapeideas/ (XDG_DATA_HOME)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        app_dir = os.path.join(base, "FBScrapeIdeas")
    elif sys.platform == "darwin":
        app_dir = os.path.expanduser("~/Library/Application Support/FBScrapeIdeas")
    else:
        # Linux/Unix - follow XDG Base Directory Specification
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        app_dir = os.path.join(base, "fbscrapeideas")

    return app_dir


def is_frozen() -> bool:
    """Check if running as a frozen executable (PyInstaller, cx_Freeze, etc.)."""
    return getattr(sys, "frozen", False)


def get_project_root() -> str:
    """
    Get the project root directory.
    """
    # Use the directory containing this config.py file as the project root
    return os.path.dirname(os.path.abspath(__file__))


def get_env_file_path() -> str:
    """
    Get the path to the .env file.
    """
    if is_frozen():
        # Use platform-appropriate app data directory for frozen builds
        app_dir = get_app_data_dir()
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, ".env")
    else:
        # Development mode - always use project directory
        project_dir = get_project_root()
        return os.path.join(project_dir, ".env")


def get_db_path(db_name: str = "insights.db") -> str:
    """
    Get the database path, using app data directory for frozen builds.
    """
    if is_frozen():
        # Frozen builds use platform-appropriate app data directory
        app_dir = get_app_data_dir()
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, db_name)
    else:
        # Development mode - always use project directory
        project_dir = get_project_root()
        db_path = os.path.join(project_dir, db_name)
        return db_path


# --- Load .env from appropriate location ---
_env_path = get_env_file_path()
if os.path.exists(_env_path):
    load_dotenv(_env_path)
    # Decrypt sensitive values in os.environ for runtime use
    for key in CredentialManager.SENSITIVE_KEYS:
        val = os.getenv(key)
        if val:
            os.environ[key] = CredentialManager.decrypt(val)
    logging.info(f"Loaded environment from: {os.path.basename(_env_path)}")
else:
    load_dotenv()
    for key in CredentialManager.SENSITIVE_KEYS:
        val = os.getenv(key)
        if val:
            os.environ[key] = CredentialManager.decrypt(val)


# --- Re-export Credential Management Functions (Maintaining backward compatibility) ---


def save_credential_to_env(key: str, value: str) -> bool:
    """Wrapper for backward compatibility."""
    return _save_credential(key, value, get_env_file_path())


def delete_env_file() -> bool:
    """Wrapper for backward compatibility."""
    return _delete_env(get_env_file_path())


# --- First-Run Detection ---


def is_first_run() -> bool:
    """Check if no .env file exists."""
    return not os.path.exists(get_env_file_path())


def has_google_api_key() -> bool:
    """Check if Google API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY"))


def has_facebook_credentials() -> bool:
    """Check if Facebook credentials are configured."""
    return bool(os.getenv("FB_USER") and os.getenv("FB_PASS"))


def has_openai_api_key() -> bool:
    """Check if OpenAI API key is configured."""
    if os.getenv("OPENAI_API_KEY"):
        return True
    base_url = get_openai_base_url()
    return "localhost" in base_url or "127.0.0.1" in base_url


# --- Playwright Session Configuration ---
SESSION_STATE_PATH = os.path.join(get_project_root(), "session_state.json")


# --- Scraper Engine Configuration ---
DEFAULT_SCRAPER_ENGINE = "selenium"
_PLAYWRIGHT_CHECKED = False


def get_scraper_engine() -> str:
    """Get the configured scraper engine."""
    return os.getenv("SCRAPER_ENGINE", DEFAULT_SCRAPER_ENGINE).lower()


def ensure_playwright_installed():
    """Ensures Playwright Chromium is installed if needed."""
    global _PLAYWRIGHT_CHECKED

    if get_scraper_engine() != "playwright" or _PLAYWRIGHT_CHECKED:
        return

    try:
        import playwright  # noqa: F401
    except ImportError:
        logging.error("Playwright python package is not installed.")
        return

    try:
        logging.info("Checking/Installing Playwright Chromium...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        _PLAYWRIGHT_CHECKED = True
        logging.info("Playwright Chromium check complete.")
    except Exception as e:
        logging.error(f"Failed to ensure Playwright: {e}")


# --- AI Filtering Configuration ---
AI_FILTER_KEYWORDS = [
    "idea",
    "problem",
    "help",
    "app",
    "thesis",
    "project",
    "issue",
    "tool",
    "software",
    "startup",
    "business",
    "need",
    "recommend",
    "advice",
]


# --- AI Provider Configuration ---
DEFAULT_AI_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "models/gemini-2.0-flash"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_ai_provider_type() -> str:
    """Get the configured AI provider type."""
    return os.getenv("AI_PROVIDER", DEFAULT_AI_PROVIDER).lower()


def get_gemini_model() -> str:
    """Get the configured Gemini model."""
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    if not model.startswith("models/"):
        model = f"models/{model}"
    return model


def get_openai_base_url() -> str:
    """Get the configured OpenAI base URL."""
    return os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)


def get_openai_model() -> str:
    """Get the configured OpenAI model."""
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
