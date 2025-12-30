"""
Tests for CLI Settings Menu functionality.

Covers:
- handle_settings_menu: Main settings menu
- handle_gemini_config: Gemini API configuration
- handle_openai_config: OpenAI-compatible configuration
- handle_switch_provider: Provider switching
- handle_ai_settings_menu: AI settings submenu
"""

import pytest
from unittest.mock import MagicMock, patch, call


# --- Test: handle_switch_provider ---


class TestHandleSwitchProvider:
    """Tests for handle_switch_provider function."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_success")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_to_gemini(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_success,
        mock_save,
        mock_ask,
    ):
        """Selecting option 1 should switch to gemini provider."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.return_value = "1"
        mock_save.return_value = True

        handle_switch_provider()

        mock_save.assert_called_once_with("AI_PROVIDER", "gemini")
        mock_success.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_success")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_to_openai(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_success,
        mock_save,
        mock_ask,
    ):
        """Selecting option 2 should switch to openai provider."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.return_value = "2"
        mock_save.return_value = True

        handle_switch_provider()

        mock_save.assert_called_once_with("AI_PROVIDER", "openai")
        mock_success.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_cancel(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_save,
        mock_ask,
    ):
        """Selecting option 0 should cancel without saving."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.return_value = "0"

        handle_switch_provider()

        mock_save.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_error")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_invalid_choice(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_error,
        mock_save,
        mock_ask,
    ):
        """Invalid choice should show error and not save."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.return_value = "99"

        handle_switch_provider()

        mock_save.assert_not_called()
        mock_error.assert_called()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_error")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_save_fails(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_error,
        mock_save,
        mock_ask,
    ):
        """Should show error when save_credential_to_env returns False."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.return_value = "1"
        mock_save.return_value = False

        handle_switch_provider()

        mock_save.assert_called_once()
        mock_error.assert_called()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_warning")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_section")
    @patch("config.get_ai_provider_type", return_value="gemini")
    @patch("ai.provider_factory.list_available_providers", return_value=["gemini", "openai"])
    def test_switch_keyboard_interrupt(
        self,
        mock_providers,
        mock_get_provider,
        mock_section,
        mock_menu,
        mock_warning,
        mock_ask,
    ):
        """KeyboardInterrupt should be handled gracefully."""
        from cli.menu_handler import handle_switch_provider

        mock_ask.side_effect = KeyboardInterrupt()

        handle_switch_provider()

        mock_warning.assert_called()


# --- Test: handle_gemini_config ---


class TestHandleGeminiConfig:
    """Tests for handle_gemini_config function."""

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_select_gemini_model")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_google_api_key", return_value=True)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    def test_gemini_config_select_model(
        self,
        mock_model,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_select_model,
        mock_ask,
    ):
        """Selecting option 1 should call handle_select_gemini_model."""
        from cli.menu_handler import handle_gemini_config

        mock_ask.return_value = "1"

        handle_gemini_config()

        mock_select_model.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_update_google_api_key")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_google_api_key", return_value=False)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    def test_gemini_config_update_api_key(
        self,
        mock_model,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_update_key,
        mock_ask,
    ):
        """Selecting option 2 should call handle_update_google_api_key."""
        from cli.menu_handler import handle_gemini_config

        mock_ask.return_value = "2"

        handle_gemini_config()

        mock_update_key.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_select_gemini_model")
    @patch("cli.menu_handler.handle_update_google_api_key")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_google_api_key", return_value=True)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    def test_gemini_config_back(
        self,
        mock_model,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_update_key,
        mock_select_model,
        mock_ask,
    ):
        """Selecting option 0 should return without calling any handlers."""
        from cli.menu_handler import handle_gemini_config

        mock_ask.return_value = "0"

        handle_gemini_config()

        mock_select_model.assert_not_called()
        mock_update_key.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_error")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_google_api_key", return_value=True)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    def test_gemini_config_invalid_choice(
        self,
        mock_model,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_error,
        mock_ask,
    ):
        """Invalid choice should show error."""
        from cli.menu_handler import handle_gemini_config

        mock_ask.return_value = "99"

        handle_gemini_config()

        mock_error.assert_called()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_warning")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_google_api_key", return_value=True)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    def test_gemini_config_keyboard_interrupt(
        self,
        mock_model,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_warning,
        mock_ask,
    ):
        """KeyboardInterrupt should be handled gracefully."""
        from cli.menu_handler import handle_gemini_config

        mock_ask.side_effect = KeyboardInterrupt()

        handle_gemini_config()

        mock_warning.assert_called()


# --- Test: handle_update_google_api_key ---


class TestHandleUpdateGoogleApiKey:
    """Tests for handle_update_google_api_key function."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("builtins.print")
    def test_update_google_api_key_success(self, mock_print, mock_save, mock_ask):
        """Successfully updating API key."""
        from cli.menu_handler import handle_update_google_api_key

        mock_ask.return_value = "test-api-key-12345"
        mock_save.return_value = True

        handle_update_google_api_key()

        mock_save.assert_called_once_with("GOOGLE_API_KEY", "test-api-key-12345")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("builtins.print")
    def test_update_google_api_key_failure(self, mock_print, mock_save, mock_ask):
        """Save failure should print error."""
        from cli.menu_handler import handle_update_google_api_key

        mock_ask.return_value = "test-api-key"
        mock_save.return_value = False

        handle_update_google_api_key()

        mock_save.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("builtins.print")
    def test_update_google_api_key_empty(self, mock_print, mock_save, mock_ask):
        """Empty input should skip saving."""
        from cli.menu_handler import handle_update_google_api_key

        mock_ask.return_value = ""

        handle_update_google_api_key()

        mock_save.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("builtins.print")
    def test_update_google_api_key_cancelled(self, mock_print, mock_ask):
        """KeyboardInterrupt should cancel gracefully."""
        from cli.menu_handler import handle_update_google_api_key

        mock_ask.side_effect = KeyboardInterrupt()

        handle_update_google_api_key()

        # Should not raise exception


# --- Test: handle_openai_config ---


class TestHandleOpenaiConfig:
    """Tests for handle_openai_config function."""

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_update_openai_base_url")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_openai_api_key", return_value=True)
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    def test_openai_config_update_base_url(
        self,
        mock_model,
        mock_base_url,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_section,
        mock_info,
        mock_divider,
        mock_menu,
        mock_update_url,
        mock_ask,
    ):
        """Selecting option 1 should call handle_update_openai_base_url."""
        from cli.menu_handler import handle_openai_config

        mock_ask.return_value = "1"

        handle_openai_config()

        mock_update_url.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_select_openai_model")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_openai_api_key", return_value=True)
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    def test_openai_config_select_model(
        self,
        mock_model,
        mock_base_url,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_section,
        mock_info,
        mock_divider,
        mock_menu,
        mock_select_model,
        mock_ask,
    ):
        """Selecting option 2 should call handle_select_openai_model."""
        from cli.menu_handler import handle_openai_config

        mock_ask.return_value = "2"

        handle_openai_config()

        mock_select_model.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_set_openai_model_manually")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_openai_api_key", return_value=False)
    @patch("config.get_openai_base_url", return_value="http://localhost:11434/v1")
    @patch("config.get_openai_model", return_value="llama3")
    def test_openai_config_set_model_manually(
        self,
        mock_model,
        mock_base_url,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_section,
        mock_info,
        mock_divider,
        mock_menu,
        mock_set_manual,
        mock_ask,
    ):
        """Selecting option 3 should call handle_set_openai_model_manually."""
        from cli.menu_handler import handle_openai_config

        mock_ask.return_value = "3"

        handle_openai_config()

        mock_set_manual.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_update_openai_api_key")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_openai_api_key", return_value=False)
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("config.get_openai_model", return_value="gpt-4o")
    def test_openai_config_update_api_key(
        self,
        mock_model,
        mock_base_url,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_section,
        mock_info,
        mock_divider,
        mock_menu,
        mock_update_key,
        mock_ask,
    ):
        """Selecting option 4 should call handle_update_openai_api_key."""
        from cli.menu_handler import handle_openai_config

        mock_ask.return_value = "4"

        handle_openai_config()

        mock_update_key.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.print_info")
    @patch("cli.menu_handler.print_section")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("config.has_openai_api_key", return_value=True)
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    def test_openai_config_back(
        self,
        mock_model,
        mock_base_url,
        mock_has_key,
        mock_header,
        mock_settings,
        mock_section,
        mock_info,
        mock_divider,
        mock_menu,
        mock_ask,
    ):
        """Selecting option 0 should return without calling handlers."""
        from cli.menu_handler import handle_openai_config

        mock_ask.return_value = "0"

        handle_openai_config()

        # No exception raised, function returns


# --- Test: handle_update_openai_base_url ---


class TestHandleUpdateOpenaiBaseUrl:
    """Tests for handle_update_openai_base_url function."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_openai(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 1 should set OpenAI base URL."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.return_value = "1"
        mock_save.return_value = True

        handle_update_openai_base_url()

        mock_save.assert_called_once_with("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_ollama(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 2 should set Ollama base URL."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.return_value = "2"
        mock_save.return_value = True

        handle_update_openai_base_url()

        mock_save.assert_called_once_with("OPENAI_BASE_URL", "http://localhost:11434/v1")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_lmstudio(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 3 should set LM Studio base URL."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.return_value = "3"
        mock_save.return_value = True

        handle_update_openai_base_url()

        mock_save.assert_called_once_with("OPENAI_BASE_URL", "http://localhost:1234/v1")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_openrouter(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 4 should set OpenRouter base URL."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.return_value = "4"
        mock_save.return_value = True

        handle_update_openai_base_url()

        mock_save.assert_called_once_with("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_custom(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 5 should prompt for custom URL."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.side_effect = ["5", "https://my-custom-api.com/v1"]
        mock_save.return_value = True

        handle_update_openai_base_url()

        mock_save.assert_called_once_with("OPENAI_BASE_URL", "https://my-custom-api.com/v1")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_custom_empty(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Empty custom URL should cancel."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.side_effect = ["5", ""]

        handle_update_openai_base_url()

        mock_save.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_base_url_cancel(self, mock_print, mock_get_url, mock_save, mock_ask):
        """Selecting option 0 should cancel without saving."""
        from cli.menu_handler import handle_update_openai_base_url

        mock_ask.return_value = "0"

        handle_update_openai_base_url()

        mock_save.assert_not_called()


# --- Test: handle_set_openai_model_manually ---


class TestHandleSetOpenaiModelManually:
    """Tests for handle_set_openai_model_manually function."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    @patch("builtins.print")
    def test_set_model_success(self, mock_print, mock_get_model, mock_save, mock_ask):
        """Setting a model name should save it."""
        from cli.menu_handler import handle_set_openai_model_manually

        mock_ask.return_value = "llama3"
        mock_save.return_value = True

        handle_set_openai_model_manually()

        mock_save.assert_called_once_with("OPENAI_MODEL", "llama3")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    @patch("builtins.print")
    def test_set_model_empty(self, mock_print, mock_get_model, mock_save, mock_ask):
        """Empty model name should skip saving."""
        from cli.menu_handler import handle_set_openai_model_manually

        mock_ask.return_value = ""

        handle_set_openai_model_manually()

        mock_save.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_model", return_value="gpt-4o-mini")
    @patch("builtins.print")
    def test_set_model_failure(self, mock_print, mock_get_model, mock_save, mock_ask):
        """Save failure should print error."""
        from cli.menu_handler import handle_set_openai_model_manually

        mock_ask.return_value = "mistral"
        mock_save.return_value = False

        handle_set_openai_model_manually()

        mock_save.assert_called_once()


# --- Test: handle_update_openai_api_key ---


class TestHandleUpdateOpenaiApiKey:
    """Tests for handle_update_openai_api_key function."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_openai_key_success(self, mock_print, mock_base_url, mock_save, mock_ask):
        """Successfully updating OpenAI API key."""
        from cli.menu_handler import handle_update_openai_api_key

        mock_ask.return_value = "sk-test-key"
        mock_save.return_value = True

        handle_update_openai_api_key()

        mock_save.assert_called_once_with("OPENAI_API_KEY", "sk-test-key")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="http://localhost:11434/v1")
    @patch("builtins.print")
    def test_update_openai_key_local_provider(self, mock_print, mock_base_url, mock_save, mock_ask):
        """Local providers should show note about API key being optional."""
        from cli.menu_handler import handle_update_openai_api_key

        mock_ask.return_value = "not-needed"
        mock_save.return_value = True

        handle_update_openai_api_key()

        mock_save.assert_called_once_with("OPENAI_API_KEY", "not-needed")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("config.get_openai_base_url", return_value="https://api.openai.com/v1")
    @patch("builtins.print")
    def test_update_openai_key_empty(self, mock_print, mock_base_url, mock_save, mock_ask):
        """Empty input should skip saving."""
        from cli.menu_handler import handle_update_openai_api_key

        mock_ask.return_value = ""

        handle_update_openai_api_key()

        mock_save.assert_not_called()


# --- Test: handle_settings_menu ---


class TestHandleSettingsMenu:
    """Tests for handle_settings_menu function (main settings menu)."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_update_google_api_key(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_save,
        mock_ask,
    ):
        """Option 1 should update Google API key."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["1", "new-api-key", "0"]  # Update key, then exit
        mock_save.return_value = True

        handle_settings_menu()

        mock_save.assert_any_call("GOOGLE_API_KEY", "new-api-key")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=False)
    @patch("config.has_google_api_key", return_value=False)
    def test_settings_menu_update_fb_credentials(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_save,
        mock_ask,
    ):
        """Option 2 should update Facebook credentials."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["2", "user@email.com", "password123", "0"]
        mock_save.return_value = True

        handle_settings_menu()

        mock_save.assert_any_call("FB_USER", "user@email.com")
        mock_save.assert_any_call("FB_PASS", "password123")

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_switch_engine_to_playwright(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_save,
        mock_ask,
    ):
        """Option 3 should switch scraper engine."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["3", "2", "0"]  # Switch engine, select playwright, exit
        mock_save.return_value = True

        handle_settings_menu()

        mock_save.assert_any_call("SCRAPER_ENGINE", "playwright")

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_ai_settings_menu")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_ai_settings(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_ai_settings,
        mock_ask,
    ):
        """Option 4 should open AI settings submenu."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["4", "0"]  # AI settings, exit

        handle_settings_menu()

        mock_ai_settings.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("config.get_db_path", return_value="/path/to/insights.db")
    @patch("config.get_env_file_path", return_value="/path/to/.env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    @patch("builtins.print")
    def test_settings_menu_show_config_locations(
        self,
        mock_print,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_env_path,
        mock_db_path,
        mock_ask,
    ):
        """Option 5 should show config locations."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["5", "", "0"]  # Show config, continue, exit

        handle_settings_menu()

        # Verify config paths are accessed
        mock_env_path.assert_called()
        mock_db_path.assert_called()

    @patch("cli.menu_handler.ask")
    @patch("config.delete_env_file")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_clear_credentials_confirmed(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_delete,
        mock_ask,
    ):
        """Option 6 with 'yes' confirmation should delete credentials."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["6", "yes", "0"]  # Clear creds, confirm, exit
        mock_delete.return_value = True

        handle_settings_menu()

        mock_delete.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("config.delete_env_file")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_clear_credentials_cancelled(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_delete,
        mock_ask,
    ):
        """Option 6 without 'yes' confirmation should not delete."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["6", "no", "0"]  # Clear creds, cancel, exit

        handle_settings_menu()

        mock_delete.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_exit(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_ask,
    ):
        """Option 0 should exit the menu."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.return_value = "0"

        handle_settings_menu()

        # Should complete without error


# --- Test: handle_ai_settings_menu ---


class TestHandleAISettingsMenu:
    """Tests for handle_ai_settings_menu function."""

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_switch_provider")
    @patch("builtins.print")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_provider_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    def test_ai_menu_switch_provider(
        self,
        mock_status,
        mock_header,
        mock_show_status,
        mock_divider,
        mock_menu,
        mock_print,
        mock_switch,
        mock_ask,
    ):
        """Option 1 should call handle_switch_provider."""
        from cli.menu_handler import handle_ai_settings_menu

        mock_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
            "api_key_configured": True,
            "base_url": None,
            "custom_prompts_loaded": False,
        }
        mock_ask.side_effect = ["1", "0"]  # Switch provider, then exit

        handle_ai_settings_menu()

        mock_switch.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_gemini_config")
    @patch("builtins.print")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_provider_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    def test_ai_menu_configure_gemini(
        self,
        mock_status,
        mock_header,
        mock_show_status,
        mock_divider,
        mock_menu,
        mock_print,
        mock_gemini,
        mock_ask,
    ):
        """Option 2 should call handle_gemini_config."""
        from cli.menu_handler import handle_ai_settings_menu

        mock_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
            "api_key_configured": True,
            "base_url": None,
            "custom_prompts_loaded": False,
        }
        mock_ask.side_effect = ["2", "0"]  # Gemini config, then exit

        handle_ai_settings_menu()

        mock_gemini.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_openai_config")
    @patch("builtins.print")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_provider_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    def test_ai_menu_configure_openai(
        self,
        mock_status,
        mock_header,
        mock_show_status,
        mock_divider,
        mock_menu,
        mock_print,
        mock_openai,
        mock_ask,
    ):
        """Option 3 should call handle_openai_config."""
        from cli.menu_handler import handle_ai_settings_menu

        mock_status.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key_configured": True,
            "base_url": "https://api.openai.com/v1",
            "custom_prompts_loaded": False,
        }
        mock_ask.side_effect = ["3", "0"]  # OpenAI config, then exit

        handle_ai_settings_menu()

        mock_openai.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_view_prompts")
    @patch("builtins.print")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_provider_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    def test_ai_menu_view_prompts(
        self,
        mock_status,
        mock_header,
        mock_show_status,
        mock_divider,
        mock_menu,
        mock_print,
        mock_view,
        mock_ask,
    ):
        """Option 4 should call handle_view_prompts."""
        from cli.menu_handler import handle_ai_settings_menu

        mock_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
            "api_key_configured": True,
            "base_url": None,
            "custom_prompts_loaded": True,
        }
        mock_ask.side_effect = ["4", "0"]  # View prompts, then exit

        handle_ai_settings_menu()

        mock_view.assert_called_once()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.handle_show_prompts_path")
    @patch("builtins.print")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_provider_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    def test_ai_menu_show_prompts_path(
        self,
        mock_status,
        mock_header,
        mock_show_status,
        mock_divider,
        mock_menu,
        mock_print,
        mock_path,
        mock_ask,
    ):
        """Option 5 should call handle_show_prompts_path."""
        from cli.menu_handler import handle_ai_settings_menu

        mock_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
            "api_key_configured": False,
            "base_url": None,
            "custom_prompts_loaded": False,
        }
        mock_ask.side_effect = ["5", "0"]  # Show path, then exit

        handle_ai_settings_menu()

        mock_path.assert_called_once()


# --- Test: get_ai_provider_status ---


class TestGetAIProviderStatus:
    """Tests for get_ai_provider_status function."""

    @patch("ai.prompts.get_custom_prompts_path")
    @patch("ai.prompts.load_custom_prompts")
    @patch("config.has_google_api_key", return_value=True)
    @patch("config.get_gemini_model", return_value="models/gemini-2.0-flash")
    @patch("config.get_ai_provider_type", return_value="gemini")
    def test_gemini_provider_status(
        self, mock_type, mock_model, mock_has_key, mock_custom, mock_path
    ):
        """Gemini provider should return correct status."""
        from cli.menu_handler import get_ai_provider_status

        mock_custom.return_value = {}
        mock_path.return_value = "/path/to/prompts.json"

        status = get_ai_provider_status()

        assert status["provider"] == "gemini"
        assert status["model"] == "models/gemini-2.0-flash"
        assert status["api_key_configured"] is True
        assert status["base_url"] is None

    @patch("ai.prompts.get_custom_prompts_path")
    @patch("ai.prompts.load_custom_prompts")
    @patch("config.has_openai_api_key", return_value=False)
    @patch("config.get_openai_base_url", return_value="http://localhost:11434/v1")
    @patch("config.get_openai_model", return_value="llama3")
    @patch("config.get_ai_provider_type", return_value="openai")
    def test_openai_provider_status(
        self, mock_type, mock_model, mock_base_url, mock_has_key, mock_custom, mock_path
    ):
        """OpenAI provider should return correct status including base_url."""
        from cli.menu_handler import get_ai_provider_status

        mock_custom.return_value = {"post_categorization": "custom prompt"}
        mock_path.return_value = "/path/to/prompts.json"

        status = get_ai_provider_status()

        assert status["provider"] == "openai"
        assert status["model"] == "llama3"
        assert status["api_key_configured"] is False
        assert status["base_url"] == "http://localhost:11434/v1"
        assert status["custom_prompts_loaded"] is True
        assert "post_categorization" in status["custom_prompt_keys"]


# --- Edge Cases & Error Conditions ---


class TestSettingsEdgeCases:
    """Edge case tests for settings functions."""

    @patch("cli.menu_handler.ask")
    @patch("config.save_credential_to_env")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=False)
    @patch("config.has_google_api_key", return_value=False)
    def test_settings_menu_fb_empty_credentials(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_save,
        mock_ask,
    ):
        """Empty FB credentials should not be saved."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        # Empty username and password
        mock_ask.side_effect = ["2", "", "", "0"]

        handle_settings_menu()

        mock_save.assert_not_called()

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="playwright")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_invalid_option(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_ask,
    ):
        """Invalid menu option should be handled gracefully."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = ["99", "0"]  # Invalid option, then exit

        handle_settings_menu()

        # Should complete without error

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_keyboard_interrupt(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_ask,
    ):
        """KeyboardInterrupt should exit menu gracefully."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = KeyboardInterrupt()

        handle_settings_menu()

        # Should complete without raising

    @patch("cli.menu_handler.ask")
    @patch("cli.menu_handler.print_menu")
    @patch("cli.menu_handler.print_divider")
    @patch("cli.menu_handler.show_settings_status")
    @patch("cli.menu_handler.print_header")
    @patch("cli.menu_handler.get_ai_provider_status")
    @patch("config.get_scraper_engine", return_value="selenium")
    @patch("config.has_facebook_credentials", return_value=True)
    @patch("config.has_google_api_key", return_value=True)
    def test_settings_menu_eof_error(
        self,
        mock_has_google,
        mock_has_fb,
        mock_engine,
        mock_provider_status,
        mock_header,
        mock_settings,
        mock_divider,
        mock_menu,
        mock_ask,
    ):
        """EOFError should exit menu gracefully."""
        from cli.menu_handler import handle_settings_menu

        mock_provider_status.return_value = {
            "provider": "gemini",
            "model": "models/gemini-2.0-flash",
        }
        mock_ask.side_effect = EOFError()

        handle_settings_menu()

        # Should complete without raising
