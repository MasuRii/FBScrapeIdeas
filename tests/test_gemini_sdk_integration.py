#!/usr/bin/env python
"""
Integration test for verifying the Gemini SDK integration.

This test requires a live GOOGLE_API_KEY and is skipped in CI environments
or when the API key is not available.

Run manually with: pytest tests/test_gemini_sdk_integration.py -v
"""

import asyncio
import json
import os
import sys

import pytest

# Skip entire module if no API key is available
pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set - skipping live API integration tests",
)


# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # Ignore if reconfigure fails in test environment


class TestGeminiSDKIntegration:
    """Integration tests for Gemini SDK - requires live API key."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.test_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").replace("models/", "")

    def test_sdk_import(self):
        """Test that the new SDK can be imported."""
        from google import genai
        from google.genai import types

        assert genai is not None
        assert types is not None

    def test_provider_import(self):
        """Test that the GeminiProvider can be imported."""
        from ai.gemini_provider import GeminiProvider

        assert GeminiProvider is not None

    def test_client_creation(self):
        """Test that we can create a Gemini client."""
        from google import genai

        client = genai.Client(api_key=self.api_key)
        assert client is not None

    def test_list_models(self):
        """Test listing available models."""
        from google import genai

        client = genai.Client(api_key=self.api_key)
        models = client.models.list()
        model_names = [m.name for m in models]

        assert len(model_names) > 0, "Should have at least one model available"

    def test_simple_generation(self):
        """Test a simple text generation call."""
        from google import genai

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.test_model,
            contents="Say 'Hello, SDK test!' and nothing else.",
        )

        assert response is not None
        assert response.text is not None
        assert len(response.text.strip()) > 0

    def test_structured_json_output(self):
        """Test structured JSON output with schema."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        # Define a simple schema
        schema = {
            "type": "OBJECT",
            "properties": {
                "message": {"type": "STRING", "description": "A greeting message"},
                "status": {
                    "type": "STRING",
                    "enum": ["success", "error"],
                    "description": "Status of the test",
                },
            },
            "required": ["message", "status"],
        }

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema
        )

        response = client.models.generate_content(
            model=self.test_model,
            contents="Return a greeting with status 'success'. Say 'SDK integration test passed!'",
            config=config,
        )

        assert response is not None
        assert response.text is not None

        result = json.loads(response.text)
        assert "message" in result
        assert "status" in result
        assert result["status"] in ["success", "error"]

    @pytest.mark.asyncio
    async def test_async_generation(self):
        """Test async generation (used by analyze_posts_batch)."""
        from google import genai

        client = genai.Client(api_key=self.api_key)
        response = await client.aio.models.generate_content(
            model=self.test_model,
            contents="Say 'Async test passed!' and nothing else.",
        )

        assert response is not None
        assert response.text is not None
        assert len(response.text.strip()) > 0

    def test_gemini_provider_instantiation(self):
        """Test the full GeminiProvider class instantiation."""
        from ai.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key=self.api_key)

        assert provider.provider_name == "gemini"
        assert provider.get_model_name() is not None
        assert provider._post_schema is not None, "Post schema should be loaded"
        assert provider._comment_schema is not None, "Comment schema should be loaded"

    @pytest.mark.asyncio
    async def test_provider_analyze_posts(self):
        """Test the GeminiProvider's analyze_posts_batch method."""
        from ai.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key=self.api_key, model=self.test_model)

        # Create a sample post
        test_posts = [
            {
                "post_id": "test_123",
                "text": "I'm struggling to understand how to implement OAuth 2.0 in my Flask application. Can anyone explain the flow or point me to good resources?",
            }
        ]

        results = await provider.analyze_posts_batch(test_posts)

        assert results is not None
        assert len(results) > 0

        result = results[0]
        assert "ai_category" in result
        assert "ai_sentiment" in result
        assert "ai_is_potential_idea" in result


# Allow running as standalone script for manual testing
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
