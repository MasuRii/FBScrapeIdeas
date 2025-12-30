"""
Menu presentation and command dispatching for the FB Scrape Ideas CLI.
Handles both interactive menu and command-line argument modes.
"""

import argparse
import asyncio
import os
import re
from datetime import datetime
from typing import Optional

# Import console utilities
try:
    from cli.console import (
        clear_screen,
        print_divider,
        print_error,
        print_header,
        print_info,
        print_menu,
        print_section,
        print_success,
        print_warning,
        show_provider_status,
        show_settings_status,
        ask,
    )
except ImportError:
    # Fallback for development when running from project root
    from console import (
        clear_screen,
        print_divider,
        print_error,
        print_header,
        print_info,
        print_menu,
        print_section,
        print_success,
        print_warning,
        show_provider_status,
        show_settings_status,
        ask,
    )

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
        value = ask(prompt).strip()
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
    show_provider_status(status)


def handle_ai_settings_menu():
    """AI Settings submenu for managing AI provider configuration."""
    from config import (
        get_ai_provider_type,
        get_gemini_model,
        get_openai_base_url,
        get_openai_model,
        has_google_api_key,
        has_openai_api_key,
        save_credential_to_env,
    )

    while True:
        print_header("AI Settings")

        # Show current status using rich panel
        show_provider_status(get_ai_provider_status())
        print_divider()

        # Define AI settings menu items
        ai_menu = [
            {"key": "1", "label": "Switch AI Provider", "description": ""},
            {"key": "2", "label": "Configure Gemini", "description": "model & API key"},
            {"key": "3", "label": "Configure OpenAI", "description": "base URL, model & API key"},
            {"key": "4", "label": "View/Test Current Prompts", "description": ""},
            {"key": "5", "label": "Show Custom Prompts Path", "description": ""},
            {"key": "0", "label": "Back to Settings Menu", "description": ""},
        ]

        print_menu(ai_menu, "AI Options")

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
            choice = ask("Select option").strip()
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

    print_section("Available AI Providers")

    provider_menu = []
    for i, provider in enumerate(providers, 1):
        current_marker = " ← [dim]current[/dim]" if provider == current else ""
        if provider == "gemini":
            provider_menu.append(
                {"key": str(i), "label": f"Google Gemini{current_marker}", "description": ""}
            )
        elif provider == "openai":
            provider_menu.append(
                {
                    "key": str(i),
                    "label": f"OpenAI-Compatible{current_marker}",
                    "description": "OpenAI, Ollama, LM Studio, etc.",
                }
            )
    provider_menu.append({"key": "0", "label": "Cancel", "description": ""})

    print_menu(provider_menu, "Provider Selection")

    try:
        choice = ask("Select provider (1-2, or 0 to cancel)").strip()

        if choice == "0":
            return
        elif choice == "1":
            if save_credential_to_env("AI_PROVIDER", "gemini"):
                print_success("  Switched to Gemini provider!")
            else:
                print_error("  Failed to save provider setting.")
        elif choice == "2":
            if save_credential_to_env("AI_PROVIDER", "openai"):
                print_success("  Switched to OpenAI-compatible provider!")
            else:
                print_error("  Failed to save provider setting.")
        else:
            print_error("  Invalid choice.")
    except (EOFError, KeyboardInterrupt):
        print_warning("\n  Cancelled.")


def handle_gemini_config():
    """Handle Gemini provider configuration."""
    from config import (
        get_gemini_model,
        get_google_api_key,
        has_google_api_key,
        save_credential_to_env,
    )

    print_header("Gemini Configuration")

    current_model = get_gemini_model()
    key_status = (
        "[green]✓ Configured[/green]" if has_google_api_key() else "[red]✗ Not configured[/red]"
    )

    settings_info = {
        "Current Model": current_model,
        "API Key": key_status,
    }

    show_settings_status(settings_info)
    print_divider()

    gemini_menu = [
        {"key": "1", "label": "List & Select Gemini Model", "description": ""},
        {"key": "2", "label": "Update Google API Key", "description": ""},
        {"key": "0", "label": "Back", "description": ""},
    ]

    print_menu(gemini_menu, "Gemini Options")

    try:
        choice = ask("Select option").strip()
    except (EOFError, KeyboardInterrupt):
        print_warning("\n  Cancelled.")
        return

    if choice == "1":
        handle_select_gemini_model()
    elif choice == "2":
        handle_update_google_api_key()
    elif choice == "0":
        return
    else:
        print_error("  Invalid choice.")


def handle_select_gemini_model():
    """List and select Gemini models."""
    from config import get_gemini_model, has_google_api_key, save_credential_to_env

    if not has_google_api_key():
        print("\n  [X] Google API key is not configured!")
        print("    Please configure your API key first.")
        try:
            ask("Press Enter to continue")
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
                ask("Press Enter to continue")
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
            selection = ask(f"Select model (1-{len(all_display)}, or 0 to cancel)").strip()

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
        ask("Press Enter to continue")
    except (EOFError, KeyboardInterrupt):
        pass


def handle_update_google_api_key():
    """Update Google API key."""
    from config import save_credential_to_env

    print("\n  Get your API key from: https://aistudio.google.com/apikey")

    try:
        api_key = ask("Enter new Google API Key", password=True).strip()
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

    print_header("OpenAI-Compatible Configuration")

    current_model = get_openai_model()
    current_base_url = get_openai_base_url()
    key_status = (
        "[green]✓ Configured[/green]" if has_openai_api_key() else "[red]✗ Not configured[/red]"
    )

    settings_info = {
        "Current Base URL": current_base_url,
        "Current Model": current_model,
        "API Key": key_status,
    }

    show_settings_status(settings_info)
    print_section("Common Base URLs:")
    print_info("  • OpenAI: https://api.openai.com/v1")
    print_info("  • Ollama: http://localhost:11434/v1")
    print_info("  • LM Studio: http://localhost:1234/v1")
    print_info("  • OpenRouter: https://openrouter.ai/api/v1")
    print_divider()

    openai_menu = [
        {"key": "1", "label": "Update Base URL", "description": ""},
        {"key": "2", "label": "List & Select Model", "description": "from endpoint"},
        {"key": "3", "label": "Manually Set Model Name", "description": ""},
        {"key": "4", "label": "Update OpenAI API Key", "description": ""},
        {"key": "0", "label": "Back", "description": ""},
    ]

    print_menu(openai_menu, "OpenAI Options")

    try:
        choice = ask("Select option").strip()
    except (EOFError, KeyboardInterrupt):
        print_warning("\n  Cancelled.")
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
        choice = ask("Select option").strip()

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
            new_url = ask("Enter custom base URL").strip()
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
                ask("Press Enter to continue")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        # Try to get API key (may prompt user)
        try:
            api_key = get_openai_api_key()
        except ValueError as e:
            print(f"  [X] {e}")
            try:
                ask("Press Enter to continue")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        models = list_openai_models(base_url, api_key)

        if not models:
            print("  [X] Could not retrieve models.")
            print("    Check your base URL, API key, and network connection.")
            print("    For local providers, make sure the server is running.")
            try:
                ask("Press Enter to continue")
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
            selection = ask(f"Select model (1-{len(models)}, or 0 to cancel)").strip()

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
        ask("Press Enter to continue")
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
        model_name = ask("Enter model name").strip()
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
        api_key = ask("Enter new OpenAI API Key", password=True).strip()
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
        choice = ask("Select prompt to view").strip()
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
        ask("Press Enter to continue")
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
        ask("Press Enter to continue")
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
        get_scraper_engine,
    )

    while True:
        print_header("Settings")

        # Show current status
        api_status = (
            "[green]✓ Configured[/green]" if has_google_api_key() else "[red]✗ Not configured[/red]"
        )
        fb_status = (
            "[green]✓ Configured[/green]"
            if has_facebook_credentials()
            else "[red]✗ Not configured[/red]"
        )

        # Show AI provider status
        status = get_ai_provider_status()
        provider_name = "Google Gemini" if status["provider"] == "gemini" else "OpenAI-Compatible"
        engine_name = get_scraper_engine().capitalize()

        settings_info = {
            "Google API Key": api_status,
            "Facebook Credentials": fb_status,
            "AI Provider": f"{provider_name} ({status['model']})",
            "Scraper Engine": engine_name,
        }

        show_settings_status(settings_info)
        print_divider()

        # Define settings menu items
        settings_menu = [
            {"key": "1", "label": "Update Google API Key", "description": ""},
            {"key": "2", "label": "Update Facebook Credentials", "description": ""},
            {"key": "3", "label": "Switch Scraper Engine", "description": ""},
            {"key": "4", "label": "AI Provider Settings", "description": ""},
            {"key": "5", "label": "Show Config Locations", "description": ""},
            {"key": "6", "label": "Clear All Saved Credentials", "description": "DANGER"},
            {"key": "0", "label": "Back to Main Menu", "description": ""},
        ]

        print_menu(settings_menu, "Settings Options")

        try:
            choice = ask("Select option").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if choice == "1":
            print("\nGet your API key from: https://aistudio.google.com/apikey")
            try:
                api_key = ask("Enter new Google API Key", password=True).strip()
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
                username = ask("Enter Facebook Email/Username").strip()
                password = ask("Enter Facebook Password", password=True)
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

                engine_choice = ask("Select engine (1-2)").strip()
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
            ask("Press Enter to continue")

        elif choice == "6":
            try:
                confirm = ask("Delete all saved credentials? Type 'yes' to confirm").strip()
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

    subparsers.add_parser("health", help="Verify the environment and dependencies.")

    return parser


def run_interactive_menu(
    command_handlers,
    scraper_service=None,
    ai_service=None,
    group_service=None,
    post_service=None,
):
    """Run interactive CLI menu interface.

    Args:
        command_handlers: Dict mapping command names to their handler functions
        scraper_service: ScraperService instance for scrape operations
        ai_service: AIService instance for AI processing
        group_service: GroupService instance for group management
        post_service: PostService instance for post retrieval
    """
    while True:
        clear_screen()
        print_header("FB Scrape Ideas", "University Group Insights Platform")

        # Define menu items
        menu_items = [
            {
                "key": "1",
                "label": "Data Collection",
                "description": "Scrape posts, author details & comments",
            },
            {
                "key": "2",
                "label": "Session Management",
                "description": "Manual login to Facebook (Playwright)",
            },
            {
                "key": "3",
                "label": "AI Processing",
                "description": "Process posts & comments with AI categorization",
            },
            {
                "key": "4",
                "label": "Data Access & Filtering",
                "description": "Browse posts with filters (category, date, author)",
            },
            {
                "key": "5",
                "label": "Data Management & Analytics",
                "description": "Export data, manage groups, view statistics",
            },
            {
                "key": "6",
                "label": "Settings",
                "description": "Manage API keys, credentials & configuration",
            },
            {"key": "7", "label": "Exit", "description": "Quit application"},
        ]

        print_menu(menu_items, "Main Menu")

        choice = ask("Enter your choice (1-7)").strip()

        if choice == "1":
            try:
                from config import get_scraper_engine

                print_section("Data Collection - Scrape Facebook Posts")

                # Validate Facebook URL
                group_url = get_validated_input(
                    "Enter Facebook Group URL: ",
                    validate_facebook_url,
                    "Invalid URL. Please enter a valid Facebook group URL (e.g., https://facebook.com/groups/groupname)",
                    allow_empty=False,
                )

                # Validate number of posts
                num_posts_input = ask(
                    "Enter number of posts to scrape (default: 20, press Enter for default)"
                ).strip()
                if num_posts_input:
                    is_valid, num_posts = validate_positive_integer(num_posts_input)
                    if not is_valid:
                        print_warning("Invalid number. Using default value of 20.")
                        num_posts = 20
                else:
                    num_posts = 20

                # Use defaults from config - no more headless/engine prompts
                headless = True  # Default to headless for cleaner UX
                engine = get_scraper_engine()  # Use configured engine

                print_divider()
                print_info(f"Engine: {engine} | Headless: {headless} | Posts: {num_posts}")
                print_divider()

                asyncio.run(
                    command_handlers["scrape"](
                        scraper_service,
                        group_url=group_url,
                        num_posts=num_posts,
                        headless=headless,
                        engine=engine,
                    )
                )
            except KeyboardInterrupt:
                print_warning("\nOperation cancelled by user.")
            except Exception as e:
                print_error(f"\nError during scraping: {e}")
            ask("Press Enter to continue")

        elif choice == "2":
            try:
                print("\nTrigging Manual Login...")
                asyncio.run(command_handlers["manual_login"]())
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during manual login: {e}")
            ask("Press Enter to continue")

        elif choice == "3":
            try:
                # Display current AI provider info before processing
                display_provider_info()

                # Check if provider is configured
                status = get_ai_provider_status()
                if not status["api_key_configured"]:
                    print("\n  [!] Warning: API key not configured for current provider!")
                    print("  Configure it in Settings > AI Provider Settings")
                    proceed = ask("Continue anyway? (y/n)").strip().lower()
                    if proceed != "y":
                        ask("Press Enter to continue")
                        continue

                asyncio.run(command_handlers["process_ai"](ai_service))
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError during AI processing: {e}")
            ask("Press Enter to continue")

        elif choice == "4":
            try:
                filters = {}
                category_filter = ask(
                    "Enter category to filter by (optional, press Enter for all)"
                ).strip()
                if category_filter:
                    filters["category"] = category_filter

                # Validate date inputs
                start_date = get_validated_input(
                    "Start date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2025-01-15)",
                )
                if start_date:
                    filters["start_date"] = start_date

                end_date = get_validated_input(
                    "End date (YYYY-MM-DD, optional): ",
                    validate_date_format,
                    "Invalid date format. Please use YYYY-MM-DD (e.g., 2025-01-15)",
                )
                if end_date:
                    filters["end_date"] = end_date

                post_author = ask("Filter by post author name (optional)").strip()
                if post_author:
                    filters["post_author"] = post_author

                comment_author = ask("Filter by comment author name (optional)").strip()
                if comment_author:
                    filters["comment_author"] = comment_author

                keyword = ask("Keyword search (optional)").strip()
                if keyword:
                    filters["keyword"] = keyword

                min_comments = ask("Minimum comments (optional)").strip()
                if min_comments:
                    is_valid, value = validate_positive_integer(min_comments)
                    if is_valid and value > 0:
                        filters["min_comments"] = value
                    elif min_comments:
                        print("Invalid number for minimum comments, ignoring filter.")

                max_comments = ask("Maximum comments (optional)").strip()
                if max_comments:
                    is_valid, value = validate_positive_integer(max_comments)
                    if is_valid and value > 0:
                        filters["max_comments"] = value
                    elif max_comments:
                        print("Invalid number for maximum comments, ignoring filter.")

                is_idea = ask("Show only potential ideas? (yes/no, default: no)").strip().lower()
                if is_idea == "yes":
                    filters["is_idea"] = True

                command_handlers["view"](post_service, filters=filters)
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError viewing posts: {e}")
            ask("Press Enter to continue")

        elif choice == "5":
            print("\nData Management Options:")
            print("1. Add New Facebook Group")
            print("2. List All Tracked Groups")
            print("3. Remove Group from Tracking")
            print("4. Export Data to CSV/JSON")
            print("5. View Statistics")
            print("6. Back to Main Menu")

            sub_choice = ask("Enter your choice (1-6)").strip()

            try:
                if sub_choice == "1":
                    name = ask("Enter group name").strip()
                    if not name:
                        print("Group name cannot be empty.")
                    else:
                        url = get_validated_input(
                            "Enter group URL: ",
                            validate_facebook_url,
                            "Invalid URL. Please enter a valid Facebook group URL.",
                            allow_empty=False,
                        )
                        command_handlers["add_group"](group_service, name, url)

                elif sub_choice == "2":
                    command_handlers["list_groups"](group_service)

                elif sub_choice == "3":
                    group_id_input = ask("Enter group ID to remove").strip()
                    is_valid, group_id = validate_positive_integer(group_id_input)
                    if is_valid and group_id > 0:
                        command_handlers["remove_group"](group_service, group_id)
                    else:
                        print("Invalid group ID. Must be a positive number.")

                elif sub_choice == "4":
                    format_choice = ask("Choose format (csv/json)").strip().lower()
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

                        output_file = ask("Enter output file path").strip()
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
                    command_handlers["stats"](post_service)

                elif sub_choice == "6":
                    continue
                else:
                    print("Invalid choice. Please enter a number between 1-6.")

            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
            except Exception as e:
                print(f"\nError: {e}")
            ask("Press Enter to continue")

        elif choice == "6":
            handle_settings_menu()

        elif choice == "7":
            print_success("Exiting application. Goodbye!")
            break
        else:
            print_error("Invalid choice. Please enter a number between 1-7.")
            ask("Press Enter to continue")


def handle_cli_arguments(
    args,
    command_handlers,
    scraper_service=None,
    ai_service=None,
    group_service=None,
    post_service=None,
):
    """Handle command-line arguments and execute appropriate command handler.

    Args:
        args: Parsed command-line arguments from argparse
        command_handlers: Dict mapping command names to their handler functions
        scraper_service: ScraperService instance for scrape operations
        ai_service: AIService instance for AI processing
        group_service: GroupService instance for group management
        post_service: PostService instance for post retrieval
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
                        scraper_service,
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
                asyncio.run(command_handlers["process_ai"](ai_service, args.group_id))
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
                command_handlers["view"](
                    post_service, group_id=args.group_id, filters=filters, limit=args.limit
                )
            elif args.command == "export-data":
                command_handlers["export"](args)
            elif args.command == "add-group":
                # Validate URL for add-group command
                if not validate_facebook_url(args.url):
                    print("Error: Invalid Facebook group URL provided.")
                    return
                command_handlers["add_group"](group_service, args.name, args.url)
            elif args.command == "list-groups":
                command_handlers["list_groups"](group_service)
            elif args.command == "remove-group":
                command_handlers["remove_group"](group_service, args.id)
            elif args.command == "stats":
                command_handlers["stats"](post_service)
            elif args.command == "setup":
                from config import run_setup_wizard

                run_setup_wizard()
            elif args.command == "health":
                asyncio.run(command_handlers["health"]())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")


def run_cli(
    command_handlers,
    scraper_service=None,
    ai_service=None,
    group_service=None,
    post_service=None,
):
    """Main entry point for CLI interface.

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
        scraper_service: ScraperService instance for scrape operations
        ai_service: AIService instance for AI processing
        group_service: GroupService instance for group management
        post_service: PostService instance for post retrieval
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    if args.command:
        handle_cli_arguments(
            args,
            command_handlers,
            scraper_service,
            ai_service,
            group_service,
            post_service,
        )
    else:
        run_interactive_menu(
            command_handlers, scraper_service, ai_service, group_service, post_service
        )
