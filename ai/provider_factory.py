"""
Provider Factory for AI services.

This module provides factory functions to create the appropriate AI provider
based on configuration settings.
"""

import logging
from typing import Optional

from ai.base_provider import AIProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_ai_provider(
    provider_type: str | None = None, model: str | None = None, **kwargs
) -> AIProvider:
    """
    Factory function to get the appropriate AI provider based on configuration.

    Args:
        provider_type: Type of provider ('gemini' or 'openai').
                      If None, uses AI_PROVIDER from config.
        model: Model identifier. If None, uses provider-specific default from config.
        **kwargs: Additional provider-specific arguments.

    Returns:
        An AIProvider instance.

    Raises:
        ValueError: If required configuration is missing.
        ImportError: If required provider dependencies are not installed.
    """
    from config import get_ai_provider_type

    # Determine provider type
    provider = provider_type or get_ai_provider_type()

    if provider == "gemini":
        return _create_gemini_provider(model, **kwargs)
    elif provider == "openai":
        return _create_openai_provider(model, **kwargs)
    else:
        raise ValueError(
            f"Unknown AI provider type: {provider}. Supported providers: gemini, openai"
        )


def _create_gemini_provider(model: str | None = None, **kwargs) -> AIProvider:
    """Create a Gemini provider instance."""
    from ai.gemini_provider import GeminiProvider
    from config import get_gemini_model, get_google_api_key

    api_key = kwargs.get("api_key") or get_google_api_key()
    model_name = model or get_gemini_model()

    return GeminiProvider(api_key=api_key, model=model_name)


def _create_openai_provider(model: str | None = None, **kwargs) -> AIProvider:
    """Create an OpenAI-compatible provider instance."""
    from ai.openai_provider import OpenAIProvider
    from config import get_openai_api_key, get_openai_base_url, get_openai_model

    api_key = kwargs.get("api_key") or get_openai_api_key()
    base_url = kwargs.get("base_url") or get_openai_base_url()
    model_name = model or get_openai_model()

    return OpenAIProvider(api_key=api_key, base_url=base_url, model=model_name)


def list_available_providers() -> list:
    """List all available AI provider types."""
    return ["gemini", "openai"]


def get_provider_info(provider_type: str) -> dict:
    """
    Get information about a provider type.

    Args:
        provider_type: The provider type to get info for.

    Returns:
        Dictionary with provider information.
    """
    providers = {
        "gemini": {
            "name": "Google Gemini",
            "description": "Google's Gemini AI models with native JSON schema support",
            "required_config": ["GOOGLE_API_KEY"],
            "optional_config": ["GEMINI_MODEL"],
            "default_model": "models/gemini-2.0-flash",
        },
        "openai": {
            "name": "OpenAI-Compatible",
            "description": "OpenAI and compatible APIs (Ollama, LM Studio, OpenRouter, etc.)",
            "required_config": ["OPENAI_API_KEY"],
            "optional_config": ["OPENAI_BASE_URL", "OPENAI_MODEL"],
            "default_model": "gpt-4o-mini",
            "default_base_url": "https://api.openai.com/v1",
        },
    }

    return providers.get(provider_type, {"error": f"Unknown provider: {provider_type}"})
