import base64
import getpass
import hashlib
import logging
import os
import platform
import sys
from cryptography.fernet import Fernet
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CredentialManager:
    """Handles encryption and decryption of sensitive credentials using a machine-specific key."""

    _key = None
    SENSITIVE_KEYS = ["FB_USER", "FB_PASS", "GOOGLE_API_KEY", "OPENAI_API_KEY"]

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        """
        Derives a machine-specific encryption key.
        Uses platform.node() and a salt to create a deterministic but machine-locked key.
        """
        if cls._key:
            return cls._key

        # Derive a key from machine-specific info
        machine_id = platform.node() or "fbscrape-fallback-id"
        salt = b"fb-scrape-ideas-2025-security-salt"

        hasher = hashlib.sha256()
        hasher.update(machine_id.encode())
        hasher.update(salt)
        cls._key = base64.urlsafe_b64encode(hasher.digest())
        return cls._key

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """Encrypts a string and returns the base64 encoded ciphertext."""
        if not plain_text:
            return ""
        try:
            f = Fernet(cls._get_encryption_key())
            return f.encrypt(plain_text.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return plain_text

    @classmethod
    def decrypt(cls, cipher_text: str) -> str:
        """Decrypts a base64 encoded ciphertext string."""
        if not cipher_text or not isinstance(cipher_text, str):
            return cipher_text

        # Check if it looks like a Fernet token (starts with 'gAAAA')
        if not cipher_text.startswith("gAAAA"):
            return cipher_text

        try:
            f = Fernet(cls._get_encryption_key())
            return f.decrypt(cipher_text.encode()).decode()
        except Exception as e:
            logger.warning(f"Decryption failed, returning as-is: {e}")
            return cipher_text


def set_secure_permissions(path: str) -> None:
    """Sets file permissions to owner read/write only (0o600) on Unix-like systems."""
    if platform.system() != "Windows":
        try:
            os.chmod(path, 0o600)
        except Exception as e:
            logger.warning(f"Failed to set secure permissions on {path}: {e}")


def save_credential_to_env(key: str, value: str, env_path: str) -> bool:
    """Save or update a credential in the .env file, encrypting if sensitive."""
    # Ensure directory exists
    env_dir = os.path.dirname(env_path)
    if env_dir and not os.path.exists(env_dir):
        try:
            os.makedirs(env_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {env_dir}: {e}")
            return False

    try:
        # Read existing content
        existing_lines = []
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                existing_lines = f.readlines()

        # Encrypt sensitive values before saving to .env
        value_to_save = value
        if key in CredentialManager.SENSITIVE_KEYS:
            value_to_save = CredentialManager.encrypt(value)

        # Update or add the key
        key_found = False
        new_lines = []
        for line in existing_lines:
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                new_lines.append(f"{key}={value_to_save}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={value_to_save}\n")

        # Write back
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # Set secure permissions
        set_secure_permissions(env_path)

        # Also set in current environment (as plain text)
        os.environ[key] = value
        logger.info(f"Saved {key} to {os.path.basename(env_path)}")
        return True
    except Exception as e:
        logger.error(f"Failed to save credential {key}: {e}")
        return False


def delete_env_file(env_path: str) -> bool:
    """Delete the .env file."""
    try:
        if os.path.exists(env_path):
            os.remove(env_path)
            logger.info(f"Deleted credentials file: {env_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete credentials file: {e}")
        return False


def get_google_api_key() -> str:
    from config import get_env_file_path  # Local import to avoid circular dependencies

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key

    if os.getenv("CI") == "true" or not sys.stdin.isatty():
        raise ValueError("GOOGLE_API_KEY environment variable is required in non-interactive mode.")

    print("\n" + "=" * 50 + "\n  Google API Key not found!\n" + "=" * 50)
    print("\nGet your API key from: https://aistudio.google.com/apikey\n")

    try:
        api_key = getpass.getpass("Enter Google API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise ValueError("Google API key is required.") from None

    if not api_key:
        raise ValueError("Google API key is required.")

    if input("Save API key for future sessions? (y/n): ").lower().strip() == "y":
        save_credential_to_env("GOOGLE_API_KEY", api_key, get_env_file_path())

    return api_key


def get_facebook_credentials() -> tuple[str, str]:
    from config import get_env_file_path

    fb_user = os.getenv("FB_USER")
    fb_pass = os.getenv("FB_PASS")

    if fb_user and fb_pass:
        return fb_user, fb_pass

    if os.getenv("CI") == "true" or not sys.stdin.isatty():
        raise ValueError("FB_USER and FB_PASS required in non-interactive mode.")

    print("\n" + "=" * 50 + "\n  Facebook Credentials Required\n" + "=" * 50)
    try:
        username = input("Enter Facebook Email/Username: ").strip()
        password = getpass.getpass("Enter Facebook Password: ")
    except (EOFError, KeyboardInterrupt):
        raise ValueError("Facebook credentials are required.") from None

    if not username or not password:
        raise ValueError("Facebook credentials are required.")

    if input("Save credentials for future sessions? (y/n): ").lower().strip() == "y":
        save_credential_to_env("FB_USER", username, get_env_file_path())
        save_credential_to_env("FB_PASS", password, get_env_file_path())

    return username, password


def get_openai_api_key() -> str:
    from config import get_env_file_path, get_openai_base_url

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    base_url = get_openai_base_url()
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return "not-needed"

    if os.getenv("CI") == "true" or not sys.stdin.isatty():
        raise ValueError("OPENAI_API_KEY required in non-interactive mode.")

    print("\n" + "=" * 50 + "\n  OpenAI API Key not found!\n" + "=" * 50)
    try:
        api_key = getpass.getpass("Enter OpenAI API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise ValueError("OpenAI API key is required.") from None

    if not api_key:
        raise ValueError("OpenAI API key is required.")

    if input("Save API key for future sessions? (y/n): ").lower().strip() == "y":
        save_credential_to_env("OPENAI_API_KEY", api_key, get_env_file_path())

    return api_key


def run_setup_wizard() -> None:
    from config import get_env_file_path

    print("\n" + "-" * 50 + "\n  SETUP WIZARD\n" + "-" * 50)

    # Google API Key
    print("\n1)  Google Gemini API Key")
    try:
        api_key = getpass.getpass("    Enter API Key (or press Enter to skip): ").strip()
        if api_key:
            save_credential_to_env("GOOGLE_API_KEY", api_key, get_env_file_path())
    except (EOFError, KeyboardInterrupt):
        print("\n    Skipped.")

    # Facebook Credentials
    print("\n2)  Facebook Credentials")
    try:
        if input("    Set up now? (y/n): ").lower().strip() == "y":
            username = input("    Email/Username: ").strip()
            password = getpass.getpass("    Password: ")
            if username and password:
                save_credential_to_env("FB_USER", username, get_env_file_path())
                save_credential_to_env("FB_PASS", password, get_env_file_path())
    except (EOFError, KeyboardInterrupt):
        print("\n    Skipped.")

    print("\n" + "-" * 50 + "\n  Setup complete!\n" + "-" * 50)
