"""
Menu presentation and command dispatching for the FB Scrape Ideas CLI.
Handles both interactive menu and command-line argument modes.
"""

import argparse
import asyncio
import getpass
import os
import re
from datetime import datetime
from typing import Optional

ASCII_ART = r"""
 _____  ____        _____   __  ____    ____  ____    ___      ____  ___      ___   ____  _____
|     ||    \      / ___/  /  ]|    \  /    T|    \  /  _]    l    j|   \    /  _] /    T/ ___/
|   __j|  o  )    (   \_  /  / |  D  )Y  o  ||  o  )/  [_      |  T |    \  /  [_ Y  o  (   \_
|  l_  |     T     \__  T/  /  |    / |     ||   _/Y    _]     |  | |  D  YY    _]|     |\__  T
|   _] |  O  |     /  \ /   \_ |    \ |  _  ||  |  |   [_      |  | |     ||   [_ |  _  |/  \ |
|  T   |     |     \    \     ||  .  Y|  |  ||  |  |     T     j  l |     ||     T|  |  |\    |
l__j   l_____j      \___j\____jl__j\_jl__j__jl__j  l_____j    |____jl_____jl_____jl__j__j \___j
"""

# --- Input Validation Helpers ---


def validate_facebook_url(url: str) -> bool:
    """Validates if the URL is a valid Facebook group URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid Facebook URL, False otherwise
    """
    if not url:
        return False
    # Accept facebook.com or fb.com URLs
    pattern = r"^https?://(www\.)?(facebook\.com|fb\.com)/groups/[\w.-]+/?.*$"
    return bool(re.match(pattern, url, re.IGNORECASE))


def validate_date_format(date_str: str) -> bool:
    """Validates if the date string is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid format, False otherwise
    """
    if not date_str:
        return True  # Empty is acceptable for optional fields
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_positive_integer(value: str) -> tuple[bool, int]:
    """Validates if the string is a positive integer.

    Args:
        value: String to validate

    Returns:
        Tuple of (is_valid, parsed_value)
    """
    if not value:
        return True, 0
    if value.isdigit() and int(value) > 0:
        return True, int(value)
    return False, 0


def get_validated_input(prompt: str, validator, error_msg: str, allow_empty: bool = True) -> str:
    """Gets user input with validation and retry logic.

    Args:
        prompt: Input prompt to display
        validator: Function that returns True if input is valid
        error_msg: Error message to display on invalid input
        allow_empty: Whether empty input is allowed

    Returns:
        Validated input string
    """
    while True:
        value = input(prompt).strip()
        if not value and allow_empty:
            return value
        if not value and not allow_empty:
            print("This field is required. Please enter a value.")
            continue
        if validator(value):
            return value
        print(error_msg)


# --- AI Provider Status & Info ---


def get_ai_provider_status() -> dict:
    """Get current AI provider configuration status.

    Returns:
        Dictionary with provider status information
    """
    from ai.prompts import get_custom_prompts_path, load_custom_prompts
    from config import (
        get_ai_provider_type,
        get_gemini_model,
        get_openai_base_url,
        get_openai_model,
        has_google_api_key,
        has_openai_api_key,
    )

    provider = get_ai_provider_type()
    custom_prompts = load_custom_prompts()
    custom_prompts_path = get_custom_prompts_path()

    status = {
        "provider": provider,
        "model": "",
        "api_key_configured": False,
        "base_url": None,
        "custom_prompts_loaded": len(custom_prompts) > 0,
        "custom_prompts_path": str(custom_prompts_path),
        "custom_prompt_keys": list(custom_prompts.keys()),
    }

    if provider == "gemini":
        status["model"] = get_gemini_model()
        status["api_key_configured"] = has_google_api_key()
    elif provider == "openai":
        status["model"] = get_openai_model()
        status["base_url"] = get_openai_base_url()
        status["api_key_configured"] = has_openai_api_key()

    return status


def display_provider_info():
    """Display current AI provider information for user confirmation."""
    status = get_ai_provider_status()

    print("\n" + "-" * 50)
    print("  AI PROVIDER STATUS")
    print("-" * 50)

    provider_display = status["provider"].upper()
    if status["provider"] == "gemini":
        provider_display = "Google Gemini"
    elif status["provider"] == "openai":
        provider_display = "OpenAI-Compatible"

    print(f"  Provider: {provider_display}")
    print(f"  Model: {status['model']}")

    if status["base_url"] and status["provider"] == "openai":
        print(f"  Base URL: {status['base_url']}")

    key_status = "[OK] Configured" if status["api_key_configured"] else "[X] Not configured"
    print(f"  API Key: {key_status}")

    if status["custom_prompts_loaded"]:
        print(f"  Custom Prompts: [OK] Loaded ({', '.join(status['custom_prompt_keys'])})")
    else:
        print("  Custom Prompts: Using defaults")

    print("-" * 50)


def handle_ai_settings_menu():
    """AI Settings submenu for managing AI provider configuration."""
    from config import (
        get_ai_provider_type,
        get_gemini_model,
        get_google_api_key,
        get_openai_base_url,
        get_openai_model,
        has_google_api_key,
        has_openai_api_key,
        save_credential_to_env,
    )

    while True:
        print("\n" + "=" * 50)
        print("  AI SETTINGS")
        print("=" * 50)

        # Show current status
        status = get_ai_provider_status()
        provider_name = "Google Gemini" if status["provider"] == "gemini" else "OpenAI-Compatible"

        print(f"\n  Current Provider: {provider_name}")
        print(f"  Current Model: {status['model']}")
        if status["base_url"] and status["provider"] == "openai":
            print(f"  Base URL: {status['base_url']}")

        key_status = "Configured" if status["api_key_configured"] else "Not configured"
        print(f"  API Key Status: {key_status}")

        prompts_status = (
            "Custom prompts loaded" if status["custom_prompts_loaded"] else "Using defaults"
        )
        print(f"  Prompts: {prompts_status}")

        print("\n  1. Switch AI Provider")
        print("  2. Configure Gemini (model, API key)")
        print("  3. Configure OpenAI (base URL, model, API key)")
        print("  4. View/Test Current Prompts")
        print("  5. Show Custom Prompts Path")
        print("  0. Back to Settings Menu")
        print("=" * 50)

        try:
            choice = input("\nSelect option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if choice == "1":
            handle_switch_provider()
        elif choice == "2":
            handle_gemini_config()
        elif choice == "3":
            handle_openai_config()
        elif choice == "4":
            handle_view_prompts()
        elif choice == "5":
            handle_show_prompts_path()
        elif choice == "0":
            break
        else:
            print("  Invalid choice. Please enter 0-5.")


def handle_switch_provider():
    """Handle switching between AI providers."""
    from ai.provider_factory import list_available_providers
    from config import get_ai_provider_type, save_credential_to_env

    current = get_ai_provider_type()
    providers = list_available_providers()

    print("\n  Available AI Providers:")
    for i, provider in enumerate(providers, 1):
        current_marker = " (current)" if provider == current else ""
        if provider == "gemini":
            print(f"    {i}. Google Gemini{current_marker}")
        elif provider == "openai":
            print(f"    {i}. OpenAI-Compatible (OpenAI, Ollama, LM Studio, etc.){current_marker}")

    try:
        choice = input("\n  Select provider (1-2, or 0 to cancel): ").strip()

        if choice == "0":
            return
        elif choice == "1":
            if save_credential_to_env("AI_PROVIDER", "gemini"):
                print("  [OK] Switched to Gemini provider!")
            else:
                print("  [X] Failed to save provider setting.")
        elif choice == "2":
            if save_credential_to_env("AI_PROVIDER", "openai"):
                print("  [OK] Switched to OpenAI-compatible provider!")
            else:
                print("  [X] Failed to save provider setting.")
        else:
            print("  Invalid choice.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")


def handle_gemini_config():
    """Handle Gemini provider configuration."""
    from config import (
        get_gemini_model,
        get_google_api_key,
        has_google_api_key,
        save_credential_to_env,
    )

    print("\n" + "-" * 50)
    print("  GEMINI CONFIGURATION")
    print("-" * 50)

    current_model = get_gemini_model()
    key_status = "[OK] Configured" if has_google_api_key() else "[X] Not configured"

    print(f"\n  Current Model: {current_model}")
    print(f"  API Key: {key_status}")

    print("\n  1. List & Select Gemini Model")
    print("  2. Update Google API Key")
    print("  0. Back")

    try:
        choice = input("\n  Select option: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if choice == "1":
        handle_select_gemini_model()
    elif choice == "2":
        handle_update_google_api_key()
    elif choice == "0":
        return
    else:
        print("  Invalid choice.")


def handle_select_gemini_model():
    """List and select Gemini models."""
    from config import get_gemini_model, has_google_api_key, save_credential_to_env

    if not has_google_api_key():
        print("\n  [X] Google API key is not configured!")
        print("    Please configure your API key first.")
        try:
            input("\n  Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return

    print("\n  Fetching available Gemini models...")

    try:
        from ai.gemini_provider import list_gemini_models
        from config import get_google_api_key

        api_key = get_google_api_key()
        models = list_gemini_models(api_key)

        if not models:
            print("  [X] Could not retrieve models. Check your API key and network connection.")
            try:
                input("\n  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        # Filter to show only generative models (ones that are useful for our purposes)
        # and sort them for better display
        current_model = get_gemini_model()

        print(f"\n  Found {len(models)} available models:")
        print("-" * 50)

        # Group by type for cleaner display
        flash_models = [m for m in models if "flash" in m.lower()]
        pro_models = [m for m in models if "pro" in m.lower() and "flash" not in m.lower()]
        other_models = [m for m in models if m not in flash_models and m not in pro_models]

        all_display = []

        if flash_models:
            print("  Flash Models (fast, cost-effective):")
            for model in sorted(flash_models):
                all_display.append(model)
                idx = len(all_display)
                current_marker = " ← current" if model == current_model else ""
                print(f"    {idx}. {model}{current_marker}")

        if pro_models:
            print("\n  Pro Models (more capable):")
            for model in sorted(pro_models):
                all_display.append(model)
                idx = len(all_display)
                current_marker = " ← current" if model == current_model else ""
                print(f"    {idx}. {model}{current_marker}")

        if other_models:
            print("\n  Other Models:")
            for model in sorted(other_models):
                all_display.append(model)
                idx = len(all_display)
                current_marker = " ← current" if model == current_model else ""
                print(f"    {idx}. {model}{current_marker}")

        print("-" * 50)

        try:
            selection = input(f"\n  Select model (1-{len(all_display)}, or 0 to cancel): ").strip()

            if selection == "0":
                return

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(all_display):
                    selected_model = all_display[idx]
                    if save_credential_to_env("GEMINI_MODEL", selected_model):
                        print(f"  [OK] Model set to: {selected_model}")
                    else:
                        print("  [X] Failed to save model setting.")
                else:
                    print("  Invalid selection.")
            except ValueError:
                print("  Invalid input. Please enter a number.")
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")

    except ImportError as e:
        print(f"  [X] Error importing Gemini provider: {e}")
    except Exception as e:
        print(f"  [X] Error: {e}")

    try:
        input("\n  Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def handle_update_google_api_key():
    """Update Google API key."""
    from config import save_credential_to_env

    print("\n  Get your API key from: https://aistudio.google.com/apikey")

    try:
        api_key = getpass.getpass("  Enter new Google API Key: ").strip()
        if api_key:
            if save_credential_to_env("GOOGLE_API_KEY", api_key):
                print("  [OK] API key updated!")
            else:
                print("  [X] Failed to save API key.")
        else:
            print("  No API key entered, skipping.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")


def handle_openai_config():
    """Handle OpenAI-compatible provider configuration."""
    from config import (
        get_openai_base_url,
        get_openai_model,
        has_openai_api_key,
        save_credential_to_env,
    )

    print("\n" + "-" * 50)
    print("  OPENAI-COMPATIBLE CONFIGURATION")
    print("-" * 50)

    current_model = get_openai_model()
    current_base_url = get_openai_base_url()
    key_status = "[OK] Configured" if has_openai_api_key() else "[X] Not configured"

    print(f"\n  Current Base URL: {current_base_url}")
    print(f"  Current Model: {current_model}")
    print(f"  API Key: {key_status}")

    print("\n  Common Base URLs:")
    print("    • OpenAI: https://api.openai.com/v1")
    print("    • Ollama: http://localhost:11434/v1")
    print("    • LM Studio: http://localhost:1234/v1")
    print("    • OpenRouter: https://openrouter.ai/api/v1")

    print("\n  1. Update Base URL")
    print("  2. List & Select Model (from endpoint)")
    print("  3. Manually Set Model Name")
    print("  4. Update OpenAI API Key")
    print("  0. Back")

    try:
        choice = input("\n  Select option: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if choice == "1":
        handle_update_openai_base_url()
    elif choice == "2":
        handle_select_openai_model()
    elif choice == "3":
        handle_set_openai_model_manually()
    elif choice == "4":
        handle_update_openai_api_key()
    elif choice == "0":
        return
    else:
        print("  Invalid choice.")


def handle_update_openai_base_url():
    """Update OpenAI base URL."""
    from config import get_openai_base_url, save_credential_to_env

    current = get_openai_base_url()
    print(f"\n  Current Base URL: {current}")

    print("\n  Quick options:")
    print("    1. OpenAI (https://api.openai.com/v1)")
    print("    2. Ollama (http://localhost:11434/v1)")
    print("    3. LM Studio (http://localhost:1234/v1)")
    print("    4. OpenRouter (https://openrouter.ai/api/v1)")
    print("    5. Enter custom URL")
    print("    0. Cancel")

    try:
        choice = input("\n  Select option: ").strip()

        url_map = {
            "1": "https://api.openai.com/v1",
            "2": "http://localhost:11434/v1",
            "3": "http://localhost:1234/v1",
            "4": "https://openrouter.ai/api/v1",
        }

        if choice == "0":
            return
        elif choice in url_map:
            new_url = url_map[choice]
        elif choice == "5":
            new_url = input("  Enter custom base URL: ").strip()
            if not new_url:
                print("  No URL entered, cancelling.")
                return
        else:
            print("  Invalid choice.")
            return

        if save_credential_to_env("OPENAI_BASE_URL", new_url):
            print(f"  [OK] Base URL set to: {new_url}")
        else:
            print("  [X] Failed to save base URL.")

    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")


def handle_select_openai_model():
    """List and select models from OpenAI-compatible endpoint."""
    from config import (
        get_openai_api_key,
        get_openai_base_url,
        get_openai_model,
        save_credential_to_env,
    )

    base_url = get_openai_base_url()
    print(f"\n  Fetching models from: {base_url}")

    try:
        # Check if openai package is available
        try:
            from ai.openai_provider import list_openai_models
        except ImportError:
            print("  [X] OpenAI package not installed.")
            print("    Install with: pip install openai")
            try:
                input("\n  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        # Try to get API key (may prompt user)
        try:
            api_key = get_openai_api_key()
        except ValueError as e:
            print(f"  [X] {e}")
            try:
                input("\n  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        models = list_openai_models(base_url, api_key)

        if not models:
            print("  [X] Could not retrieve models.")
            print("    Check your base URL, API key, and network connection.")
            print("    For local providers, make sure the server is running.")
            try:
                input("\n  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        current_model = get_openai_model()

        print(f"\n  Found {len(models)} available models:")
        print("-" * 50)

        for i, model in enumerate(sorted(models), 1):
            current_marker = " ← current" if model == current_model else ""
            print(f"    {i}. {model}{current_marker}")

        print("-" * 50)

        try:
            selection = input(f"\n  Select model (1-{len(models)}, or 0 to cancel): ").strip()

            if selection == "0":
                return

            try:
                idx = int(selection) - 1
                sorted_models = sorted(models)
                if 0 <= idx < len(sorted_models):
                    selected_model = sorted_models[idx]
                    if save_credential_to_env("OPENAI_MODEL", selected_model):
                        print(f"  [OK] Model set to: {selected_model}")
                    else:
                        print("  [X] Failed to save model setting.")
                else:
                    print("  Invalid selection.")
            except ValueError:
                print("  Invalid input. Please enter a number.")
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")

    except Exception as e:
        print(f"  [X] Error: {e}")

    try:
        input("\n  Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def handle_set_openai_model_manually():
    """Manually set OpenAI model name."""
    from config import get_openai_model, save_credential_to_env

    current = get_openai_model()
    print(f"\n  Current Model: {current}")
    print("\n  Common model names:")
    print("    • OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo")
    print("    • Ollama: llama3, mistral, codellama, etc.")
    print("    • OpenRouter: anthropic/claude-3-sonnet, etc.")

    try:
        model_name = input("\n  Enter model name: ").strip()
        if model_name:
            if save_credential_to_env("OPENAI_MODEL", model_name):
                print(f"  [OK] Model set to: {model_name}")
            else:
                print("  [X] Failed to save model setting.")
        else:
            print("  No model name entered, skipping.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")


def handle_update_openai_api_key():
    """Update OpenAI API key."""
    from config import get_openai_base_url, save_credential_to_env

    base_url = get_openai_base_url()

    # Check if local provider (may not need key)
    if "localhost" in base_url or "127.0.0.1" in base_url:
        print("\n  Note: Local providers (Ollama, LM Studio) often don't require an API key.")
        print("  You can enter 'not-needed' or leave blank.")
    else:
        print("\n  Get your API key from: https://platform.openai.com/api-keys")

    try:
        api_key = getpass.getpass("  Enter new OpenAI API Key: ").strip()
        if api_key:
            if save_credential_to_env("OPENAI_API_KEY", api_key):
                print("  [OK] API key updated!")
            else:
                print("  [X] Failed to save API key.")
        else:
            print("  No API key entered, skipping.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")


def handle_view_prompts():
    """View current prompts (default and custom)."""
    from ai.prompts import (
        DEFAULT_PROMPTS,
        get_comment_analysis_prompt,
        get_post_categorization_prompt,
        load_custom_prompts,
    )

    print("\n" + "-" * 50)
    print("  CURRENT PROMPTS")
    print("-" * 50)

    custom_prompts = load_custom_prompts()

    print("\n  1. Post Categorization Prompt")
    print("  2. Comment Analysis Prompt")
    print("  0. Back")

    try:
        choice = input("\n  Select prompt to view: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if choice == "1":
        prompt_key = "post_categorization"
        prompt_name = "Post Categorization"
    elif choice == "2":
        prompt_key = "comment_analysis"
        prompt_name = "Comment Analysis"
    elif choice == "0":
        return
    else:
        print("  Invalid choice.")
        return

    is_custom = prompt_key in custom_prompts
    source = "CUSTOM" if is_custom else "DEFAULT"

    if prompt_key == "post_categorization":
        prompt = get_post_categorization_prompt()
    else:
        prompt = get_comment_analysis_prompt()

    print(f"\n  {prompt_name} Prompt ({source}):")
    print("=" * 50)

    # Wrap long lines for display
    import textwrap

    wrapped = textwrap.fill(prompt, width=70)
    for line in wrapped.split("\n"):
        print(f"  {line}")

    print("=" * 50)

    try:
        input("\n  Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def handle_show_prompts_path():
    """Show the path where custom prompts should be placed."""
    import os

    from ai.prompts import get_custom_prompts_path, load_custom_prompts

    custom_path = get_custom_prompts_path()
    custom_prompts = load_custom_prompts()

    print("\n" + "-" * 50)
    print("  CUSTOM PROMPTS CONFIGURATION")
    print("-" * 50)

    print(f"\n  Custom prompts file: {custom_path}")
    print(f"  File exists: {'Yes' if os.path.exists(custom_path) else 'No'}")

    if custom_prompts:
        print(f"\n  Loaded custom prompts: {', '.join(custom_prompts.keys())}")
    else:
        print("\n  No custom prompts loaded (using defaults)")

    print("\n  To customize prompts, create a JSON file with this structure:")
    print("  {")
    print('    "post_categorization": "Your custom prompt for posts...",')
    print('    "comment_analysis": "Your custom prompt for comments..."')
    print("  }")

    print("\n  See custom_prompts.example.json for a full example.")

    try:
        input("\n  Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


# --- Core Functions ---


def handle_settings_menu():
    """Settings submenu for managing credentials and configuration."""
    from config import (
        delete_env_file,
        get_db_path,
        get_env_file_path,
        has_facebook_credentials,
        has_google_api_key,
        save_credential_to_env,
    )

    while True:
        print("\n" + "=" * 50)
        print("  SETTINGS")
        print("=" * 50)

        # Show current status
        api_status = "Configured" if has_google_api_key() else "Not configured"
        fb_status = "Configured" if has_facebook_credentials() else "Not configured"
        print(f"\n  Google API Key: {api_status}")
        print(f"  Facebook Credentials: {fb_status}")

        # Show AI provider status
        status = get_ai_provider_status()
        provider_name = "Google Gemini" if status["provider"] == "gemini" else "OpenAI-Compatible"
        print(f"  AI Provider: {provider_name} ({status['model']})")

        from config import get_scraper_engine

        print(f"  Scraper Engine: {get_scraper_engine().capitalize()}")

        print("\n  1. Update Google API Key")
        print("  2. Update Facebook Credentials")
        print("  3. Switch Scraper Engine")
        print("  4. AI Provider Settings")
        print("  5. Show Config Locations")
        print("  6. Clear All Saved Credentials")
        print("  0. Back to Main Menu")
        print("=" * 50)

        try:
            choice = input("\nSelect option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if choice == "1":
            print("\nGet your API key from: https://aistudio.google.com/apikey")
            try:
                api_key = getpass.getpass("Enter new Google API Key: ").strip()
                if api_key:
                    if save_credential_to_env("GOOGLE_API_KEY", api_key):
                        print("  API key updated!")
                    else:
                        print("  Failed to save API key.")
                else:
                    print("  No API key entered, skipping.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")

        elif choice == "2":
            try:
                username = input("Enter Facebook Email/Username: ").strip()
                password = getpass.getpass("Enter Facebook Password: ")
                if username and password:
                    saved_user = save_credential_to_env("FB_USER", username)
                    saved_pass = save_credential_to_env("FB_PASS", password)
                    if saved_user and saved_pass:
                        print("  Credentials updated!")
                    else:
                        print("  Failed to save credentials.")
                else:
                    print("  Username and password are required.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")

        elif choice == "3":
            try:
                from config import save_credential_to_env, get_scraper_engine

                current = get_scraper_engine()
                print(f"\n  Current Scraper Engine: {current.capitalize()}")
                print("  1. Selenium (Stable, requires Chrome)")
                print("  2. Playwright (2025 Standard, resilient, headless support)")

                engine_choice = input("\n  Select engine (1-2): ").strip()
                if engine_choice == "1":
                    save_credential_to_env("SCRAPER_ENGINE", "selenium")
                    print("  [OK] Switched to Selenium.")
                elif engine_choice == "2":
                    save_credential_to_env("SCRAPER_ENGINE", "playwright")
                    print("  [OK] Switched to Playwright.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")

        elif choice == "4":
            handle_ai_settings_menu()

        elif choice == "5":
            print(f"\n  Config file: {get_env_file_path()}")
            print(f"  Database: {get_db_path()}")
            input("\nPress Enter to continue...")

        elif choice == "6":
            try:
                confirm = input("  Delete all saved credentials? Type 'yes' to confirm: ").strip()
                if confirm.lower() == "yes":
                    if delete_env_file():
                        print("  Credentials deleted!")
                    else:
                        print("  Failed to delete credentials.")
                else:
                    print("  Cancelled.")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")

        elif choice == "0":
            break
        else:
            print("  Invalid choice. Please enter 0-5.")


def clear_screen():
    """Clears the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def create_arg_parser():
    """Creates and configures the argument parser with all supported commands."""
    parser = argparse.ArgumentParser(description="University Group Insights Platform CLI")
    subparsers = parser.add_subparsers(dest="command")

    scrape_parser = subparsers.add_parser(
        "scrape", help="Initiate the Facebook scraping process and store results in DB."
    )
    group_group = scrape_parser.add_mutually_exclusive_group(required=True)
    group_group.add_argument("--group-url", help="The URL of the Facebook group to scrape.")
    group_group.add_argument("--group-id", type=int, help="The ID of an existing group to scrape.")
    scrape_parser.add_argument(
        "--num-posts",
        type=int,
        default=20,
        help="The number of posts to attempt to scrape (default: 20).",
    )
    scrape_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode (no GUI).",
    )
    scrape_parser.add_argument(
        "--engine",
        choices=["selenium", "playwright"],
        help="Scraper engine to use (default: from config).",
    )

    subparsers.add_parser(
        "manual-login",
        help="Open a browser for manual Facebook login (Playwright only).",
    )

    process_ai_parser = subparsers.add_parser(
        "process-ai",
        help="Fetch unprocessed posts and comments, send them to Gemini for categorization, and update DB.",
    )
    process_ai_parser.add_argument(
        "--group-id", type=int, help="Only process posts from this group ID."
    )

    view_parser = subparsers.add_parser("view", help="Display posts from the database.")
    view_parser.add_argument("--group-id", type=int, help="Only show posts from this group ID.")
    view_parser.add_argument(
        "--category", help="Optional filter to display posts of a specific category."
    )
    view_parser.add_argument("--start-date", help="Filter posts by start date (YYYY-MM-DD).")
    view_parser.add_argument("--end-date", help="Filter posts by end date (YYYY-MM-DD).")
    view_parser.add_argument("--post-author", help="Filter by post author name.")
    view_parser.add_argument("--comment-author", help="Filter by comment author name.")
    view_parser.add_argument("--keyword", help="Keyword search in post and comment content.")
    view_parser.add_argument("--min-comments", type=int, help="Minimum number of comments.")
    view_parser.add_argument("--max-comments", type=int, help="Maximum number of comments.")
    view_parser.add_argument(
        "--is-idea",
        action="store_true",
        help="Filter for posts marked as potential ideas.",
    )
    view_parser.add_argument("--limit", type=int, help="Limit the number of posts to display")

    export_parser = subparsers.add_parser(
        "export-data", help="Export data (posts or comments) to CSV or JSON file."
    )
    export_parser.add_argument(
        "--format",
        required=True,
        choices=["csv", "json"],
        help="Output format: csv or json.",
    )
    export_parser.add_argument("--output", required=True, help="Output file path.")
    export_parser.add_argument(
        "--entity",
        choices=["posts", "comments", "all"],
        default="posts",
        help="Data entity to export (default: posts).",
    )
    export_parser.add_argument(
        "--category", help="Optional filter to export posts of a specific category."
    )
    export_parser.add_argument("--start-date", help="Filter posts by start date (YYYY-MM-DD).")
    export_parser.add_argument("--end-date", help="Filter posts by end date (YYYY-MM-DD).")
    export_parser.add_argument("--post-author", help="Filter by post author name.")
    export_parser.add_argument("--comment-author", help="Filter by comment author name.")
    export_parser.add_argument("--keyword", help="Keyword search in post and comment content.")
    export_parser.add_argument("--min-comments", type=int, help="Minimum number of comments.")
    export_parser.add_argument("--max-comments", type=int, help="Maximum number of comments.")
    export_parser.add_argument(
        "--is-idea",
        action="store_true",
        help="Filter for posts marked as potential ideas.",
    )

    add_group_parser = subparsers.add_parser("add-group", help="Add a new Facebook group to track.")
    add_group_parser.add_argument("--name", required=True, help="Name of the Facebook group.")
    add_group_parser.add_argument("--url", required=True, help="URL of the Facebook group.")

    subparsers.add_parser("list-groups", help="List all tracked Facebook groups.")

    remove_group_parser = subparsers.add_parser(
        "remove-group", help="Remove a Facebook group from tracking."
    )
    remove_group_parser.add_argument(
        "--id", type=int, required=True, help="ID of the group to remove."
    )

    subparsers.add_parser(
        "stats", help="Display summary statistics about the data in the database."
    )

    subparsers.add_parser("setup", help="Run the setup wizard to configure credentials.")

    return parser


def run_interactive_menu(command_handlers):
    """Run the interactive CLI menu interface.

    Args:
        command_handlers: Dict mapping command names to their handler functions
    """
    while True:
        clear_screen()
        print(ASCII_ART)
        print("\nFB Scrape Ideas - Command Menu:")
        print("\n1. Data Collection:")
        print("   - Scrape Posts, Author Details & Comments")
        print("   - Configurable post count and headless mode")
        print("   - Supports Selenium and Playwright engines")
        print("\n2. Session Management (Playwright):")
        print("   - Manual Login to Facebook")
        print("   - Validate and save session state")
        print("\n3. AI Processing:")
        print("   - Process Posts & Comments with AI")
        print("   - Categorizes content and analyzes sentiment")
        print("   - Supports Gemini and OpenAI-compatible providers")
        print("\n4. Data Access & Filtering:")
        print("   - Browse Posts with Author Details & Comments")
        print("   - Filter by category, date, author, keywords")
        print("   - View potential project ideas")
        print("\n5. Data Management & Analytics:")
        print("   - Export Data to CSV/JSON")
        print("   - Manage Facebook Groups (Add/List/Remove)")
        print("   - View Statistics & Trends")
        print("\n6. Settings:")
        print("   - Manage API Keys & Credentials")
        print("   - Configure Scraper Engine (Selenium/Playwright)")
        print("   - Configure AI Provider (Gemini/OpenAI)")
        print("\n7. Exit")

        choice = input("\nEnter your choice (1-7): ").strip()

        if choice == "1":
            try:
                from config import get_scraper_engine

                # Validate Facebook URL
                group_url = get_validated_input(
                    "Enter Facebook Group URL: ",
                    validate_facebook_url,
                    "Invalid URL. Please enter a valid Facebook group URL (e.g., https://facebook.com/groups/groupname)",
                    allow_empty=False,
                )

                # Validate number of posts
                num_posts_input = input(
                    "Enter number of posts to scrape (default: 20, press Enter for default): "
                ).strip()
                if num_posts_input:
                    is_valid, num_posts = validate_positive_integer(num_posts_input)
                    if not is_valid:
                        print("Invalid number. Using default value of 20.")
                        num_posts = 20
                else:
                    num_posts = 20

                headless_input = (
                    input("Run in headless mode? (yes/no, default: no): ").strip().lower()
                )
                headless = headless_input == "yes"

                current_engine = get_scraper_engine()
                engine_input = (
                    input(f"Engine (selenium/playwright, default: {current_engine}): ")
                    .strip()
                    .lower()
                )
                engine = (
                    engine_input if engine_input in ["selenium", "playwright"] else current_engine
                )

                asyncio.run(
                    command_handlers["scrape"](
                        group_url=group_url, num_posts=num_posts, headless=headless, engine=engine
                    )
                )
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during scraping: {e}")
            input("\nPress Enter to continue...")

        elif choice == "2":
            try:
                print("\nTrigging Manual Login...")
                asyncio.run(command_handlers["manual_login"]())
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during manual login: {e}")
            input("\nPress Enter to continue...")

        elif choice == "3":
            try:
                # Display current AI provider info before processing
                display_provider_info()

                # Check if provider is configured
                status = get_ai_provider_status()
                if not status["api_key_configured"]:
                    print("\n  [!] Warning: API key not configured for current provider!")
                    print("  Configure it in Settings > AI Provider Settings")
                    proceed = input("\n  Continue anyway? (y/n): ").strip().lower()
                    if proceed != "y":
                        input("\nPress Enter to continue...")
                        continue

                asyncio.run(command_handlers["process_ai"]())
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during AI processing: {e}")
            input("\nPress Enter to continue...")

        elif choice == "4":
            try:
                filters = {}
                category_filter = input(
                    "Enter category to filter by (optional, press Enter for all): "
                ).strip()
                if category_filter:
                    filters["category"] = category_filter

                # Validate date inputs
                start_date = get_validated_input(
                    "Start date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15)",
                )
                if start_date:
                    filters["start_date"] = start_date

                end_date = get_validated_input(
                    "End date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15)",
                )
                if end_date:
                    filters["end_date"] = end_date

                post_author = input("Filter by post author name (optional): ").strip()
                if post_author:
                    filters["post_author"] = post_author

                comment_author = input("Filter by comment author name (optional): ").strip()
                if comment_author:
                    filters["comment_author"] = comment_author

                keyword = input("Keyword search (optional): ").strip()
                if keyword:
                    filters["keyword"] = keyword

                min_comments = input("Minimum comments (optional): ").strip()
                if min_comments:
                    is_valid, value = validate_positive_integer(min_comments)
                    if is_valid and value > 0:
                        filters["min_comments"] = value
                    elif min_comments:
                        print("Invalid number for minimum comments, ignoring filter.")

                max_comments = input("Maximum comments (optional): ").strip()
                if max_comments:
                    is_valid, value = validate_positive_integer(max_comments)
                    if is_valid and value > 0:
                        filters["max_comments"] = value
                    elif max_comments:
                        print("Invalid number for maximum comments, ignoring filter.")

                is_idea = (
                    input("Show only potential ideas? (yes/no, default: no): ").strip().lower()
                )
                if is_idea == "yes":
                    filters["is_idea"] = True

                command_handlers["view"](filters=filters)
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError viewing posts: {e}")
            input("\nPress Enter to continue...")

        elif choice == "5":
            print("\nData Management Options:")
            print("1. Add New Facebook Group")
            print("2. List All Tracked Groups")
            print("3. Remove Group from Tracking")
            print("4. Export Data to CSV/JSON")
            print("5. View Statistics")
            print("6. Back to Main Menu")

            sub_choice = input("\nEnter your choice (1-6): ").strip()

            try:
                if sub_choice == "1":
                    name = input("Enter group name: ").strip()
                    if not name:
                        print("Group name cannot be empty.")
                    else:
                        url = get_validated_input(
                            "Enter group URL: ",
                            validate_facebook_url,
                            "Invalid URL. Please enter a valid Facebook group URL.",
                            allow_empty=False,
                        )
                        command_handlers["add_group"](name, url)

                elif sub_choice == "2":
                    command_handlers["list_groups"]()

                elif sub_choice == "3":
                    group_id_input = input("Enter group ID to remove: ").strip()
                    is_valid, group_id = validate_positive_integer(group_id_input)
                    if is_valid and group_id > 0:
                        command_handlers["remove_group"](group_id)
                    else:
                        print("Invalid group ID. Must be a positive number.")

                elif sub_choice == "4":
                    format_choice = input("Choose format (csv/json): ").strip().lower()
                    if format_choice not in ["csv", "json"]:
                        print("Invalid format. Must be 'csv' or 'json'")
                    else:
                        print("\nOutput File Path Guidelines:")
                        print("- For Windows: Use any of these formats:")
                        print("  1. Full path with filename: C:\\MyFolder\\data.csv")
                        print("  2. Directory path only: C:\\MyFolder")
                        print("  3. Drive only: E:\\ (will use default filename)")
                        print("\nOutput Files:")
                        print("- Creates separate files for each data type:")
                        print("  * [path]_groups.[ext]  - Group information")
                        print("  * [path]_posts.[ext]   - Post data")
                        print("  * [path]_comments.[ext] - Comment data")
                        print("  * [path]_all.[ext]     - Combined data")

                        output_file = input("\nEnter output file path: ").strip()
                        if not output_file:
                            print("Output path cannot be empty.")
                        else:
                            args = type(
                                "Args",
                                (),
                                {
                                    "format": format_choice,
                                    "output": output_file,
                                    "entity": "all",
                                    "category": None,
                                    "start_date": None,
                                    "end_date": None,
                                    "post_author": None,
                                    "comment_author": None,
                                    "keyword": None,
                                    "min_comments": None,
                                    "max_comments": None,
                                    "is_idea": False,
                                },
                            )()
                            command_handlers["export"](args)

                elif sub_choice == "5":
                    command_handlers["stats"]()

                elif sub_choice == "6":
                    continue
                else:
                    print("Invalid choice. Please enter a number between 1-6.")

            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError: {e}")
            input("\nPress Enter to continue...")

        elif choice == "6":
            handle_settings_menu()

        elif choice == "7":
            print("Exiting application. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1-7.")
            input("\nPress Enter to continue...")


def handle_cli_arguments(args, command_handlers):
    """Handle command-line arguments and execute the appropriate command handler.

    Args:
        args: Parsed command-line arguments from argparse
        command_handlers: Dict mapping command names to their handler functions
    """
    try:
        if args.command:
            if args.command == "scrape":
                # Validate URL if provided via CLI
                if args.group_url and not validate_facebook_url(args.group_url):
                    print("Error: Invalid Facebook group URL provided.")
                    return
                asyncio.run(
                    command_handlers["scrape"](
                        group_url=args.group_url,
                        group_id=args.group_id,
                        num_posts=args.num_posts,
                        headless=args.headless,
                        engine=args.engine,
                    )
                )
            elif args.command == "manual-login":
                asyncio.run(command_handlers["manual_login"]())
            elif args.command == "process-ai":
                asyncio.run(command_handlers["process_ai"](args.group_id))
            elif args.command == "view":
                filters = {
                    "category": args.category,
                    "start_date": args.start_date,
                    "end_date": args.end_date,
                    "post_author": args.post_author,
                    "comment_author": args.comment_author,
                    "keyword": args.keyword,
                    "min_comments": args.min_comments,
                    "max_comments": args.max_comments,
                    "is_idea": args.is_idea,
                }
                command_handlers["view"](group_id=args.group_id, filters=filters, limit=args.limit)
            elif args.command == "export-data":
                command_handlers["export"](args)
            elif args.command == "add-group":
                # Validate URL for add-group command
                if not validate_facebook_url(args.url):
                    print("Error: Invalid Facebook group URL provided.")
                    return
                command_handlers["add_group"](args.name, args.url)
            elif args.command == "list-groups":
                command_handlers["list_groups"]()
            elif args.command == "remove-group":
                command_handlers["remove_group"](args.id)
            elif args.command == "stats":
                command_handlers["stats"]()
            elif args.command == "setup":
                from config import run_setup_wizard

                run_setup_wizard()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")


def run_cli(command_handlers):
    """Main entry point for the CLI interface.

    Supports both interactive menu and command-line argument modes.

    Args:
        command_handlers: Dict mapping command names to their handler functions
            Required keys:
            - 'scrape': Function to handle scraping
            - 'process_ai': Function to handle AI processing
            - 'view': Function to handle viewing posts
            - 'export': Function to handle data export
            - 'add_group': Function to handle adding groups
            - 'list_groups': Function to handle listing groups
            - 'remove_group': Function to handle removing groups
            - 'stats': Function to handle statistics display
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    if args.command:
        handle_cli_arguments(args, command_handlers)
    else:
        run_interactive_menu(command_handlers)
