import pytest
import json
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from ai.gemini_provider import GeminiProvider
from ai.openai_provider import OpenAIProvider
from ai.provider_factory import get_ai_provider
from ai.gemini_service import create_post_batches, categorize_posts_batch

# Mock posts and comments
MOCK_POSTS = [
    {"internal_post_id": 1, "post_content_raw": "Test post 1 content with project idea"},
    {"internal_post_id": 2, "post_content_raw": "Test post 2 content about software problem"},
]

MOCK_COMMENTS = [
    {"comment_id": 101, "comment_text": "Test comment 1"},
    {"comment_id": 102, "comment_text": "Test comment 2"},
]


@pytest.fixture
def mock_gemini_response():
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        [
            {
                "postId": "POST_ID_1",
                "category": "Test Category",
                "subCategory": "Test Sub",
                "keywords": ["test", "mock"],
                "summary": "Summary 1",
                "isPotentialIdea": True,
                "reasoning": "Test reasoning",
            },
            {
                "postId": "POST_ID_2",
                "category": "Test Category 2",
                "subCategory": "Test Sub 2",
                "keywords": ["test2", "mock2"],
                "summary": "Summary 2",
                "isPotentialIdea": False,
                "reasoning": "Test reasoning 2",
            },
        ]
    )
    mock_response.candidates = [MagicMock()]
    return mock_response


@pytest.fixture
def mock_openai_response():
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "posts": [
                {
                    "postId": "POST_ID_1",
                    "category": "Test Category",
                    "subCategory": "Test Sub",
                    "keywords": ["test", "mock"],
                    "summary": "Summary 1",
                    "isPotentialIdea": True,
                    "reasoning": "Test reasoning",
                },
                {
                    "postId": "POST_ID_2",
                    "category": "Test Category 2",
                    "subCategory": "Test Sub 2",
                    "keywords": ["test2", "mock2"],
                    "summary": "Summary 2",
                    "isPotentialIdea": False,
                    "reasoning": "Test reasoning 2",
                },
            ]
        }
    )
    mock_response.choices = [mock_choice]
    return mock_response


class TestGeminiProvider:
    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch(
        self, mock_load_schema, mock_client_class, mock_gemini_response
    ):
        mock_load_schema.return_value = {"type": "object"}
        mock_client = mock_client_class.return_value
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)

        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)

        assert len(results) == 2
        assert results[0]["ai_category"] == "Test Category"
        assert results[0]["internal_post_id"] == 1
        assert "ai_summary" in results[0]

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    def test_analyze_comments_batch(self, mock_load_schema, mock_client_class):
        mock_load_schema.return_value = {"type": "object"}
        mock_client = mock_client_class.return_value

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {
                    "comment_id": "COMMENT_ID_101",
                    "category": "Spam",
                    "sentiment": "Negative",
                    "keywords": ["spam"],
                }
            ]
        )
        mock_response.candidates = [MagicMock()]
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test_key")
        results = provider.analyze_comments_batch(MOCK_COMMENTS[:1])

        assert len(results) == 1
        assert results[0]["ai_comment_category"] == "Spam"
        assert results[0]["comment_id"] == 101

    @patch("google.genai.Client")
    def test_list_available_models(self, mock_client_class):
        mock_client = mock_client_class.return_value

        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-pro"
        mock_model1.supported_actions = ["generateContent"]
        mock_model2 = MagicMock()
        mock_model2.name = "models/embedding"
        mock_model2.supported_actions = ["embedContent"]

        mock_client.models.list.return_value = [mock_model1, mock_model2]

        from ai.gemini_provider import list_gemini_models

        models = list_gemini_models("test_key")
        assert models == ["models/gemini-pro"]

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch_empty(self, mock_load_schema, mock_client_class):
        mock_load_schema.return_value = {"type": "object"}
        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch([])
        assert results == []

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch_api_blocked(self, mock_load_schema, mock_client_class):
        """Test handling when API response is blocked (no candidates)."""
        mock_load_schema.return_value = {"type": "object"}
        mock_client = mock_client_class.return_value

        # Simulate blocked response with no candidates
        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = "SAFETY"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)

        assert results == []

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch_json_decode_error(self, mock_load_schema, mock_client_class):
        """Test handling when API returns malformed JSON."""
        mock_load_schema.return_value = {"type": "object"}
        mock_client = mock_client_class.return_value

        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON {"
        mock_response.candidates = [MagicMock()]
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)

        assert results == []

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch_non_list_response(self, mock_load_schema, mock_client_class):
        """Test handling when API returns valid JSON but not a list."""
        mock_load_schema.return_value = {"type": "object"}
        mock_client = mock_client_class.return_value

        mock_response = MagicMock()
        mock_response.text = json.dumps({"error": "unexpected format"})
        mock_response.candidates = [MagicMock()]
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)

        assert results == []

    @patch("google.genai.Client")
    def test_model_name_normalization(self, mock_client_class):
        """Test that models/ prefix is stripped from model name."""
        with patch("ai.gemini_provider.GeminiProvider._load_schema", return_value={}):
            provider = GeminiProvider(api_key="test_key", model="models/gemini-pro")
            assert provider.get_model_name() == "gemini-pro"
            assert provider.provider_name == "gemini"

    @patch("google.genai.Client")
    def test_provider_name_and_model(self, mock_client_class):
        """Test provider_name property and get_model_name method."""
        with patch("ai.gemini_provider.GeminiProvider._load_schema", return_value={}):
            provider = GeminiProvider(api_key="test_key", model="gemini-2.0-flash")
            assert provider.provider_name == "gemini"
            assert provider.get_model_name() == "gemini-2.0-flash"

    @patch("google.genai.Client")
    def test_get_block_reason(self, mock_client_class):
        """Test _get_block_reason helper method."""
        with patch("ai.gemini_provider.GeminiProvider._load_schema", return_value={}):
            provider = GeminiProvider(api_key="test_key")

            # Test None response
            assert provider._get_block_reason(None) == "no response"

            # Test response with block_reason
            mock_response = MagicMock()
            mock_response.prompt_feedback = MagicMock()
            mock_response.prompt_feedback.block_reason = "SAFETY"
            assert provider._get_block_reason(mock_response) == "SAFETY"

            # Test response without prompt_feedback
            mock_response2 = MagicMock()
            mock_response2.prompt_feedback = None
            assert provider._get_block_reason(mock_response2) == "unknown"

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    def test_analyze_comments_batch_empty(self, mock_load_schema, mock_client_class):
        """Test that empty comment list returns empty results."""
        mock_load_schema.return_value = {"type": "object"}
        provider = GeminiProvider(api_key="test_key")
        results = provider.analyze_comments_batch([])
        assert results == []

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    def test_analyze_comments_batch_schema_missing(self, mock_load_schema, mock_client_class):
        """Test handling when comment schema fails to load."""
        # Return valid post schema but None for comment schema
        mock_load_schema.side_effect = [{"type": "object"}, None]
        provider = GeminiProvider(api_key="test_key")
        results = provider.analyze_comments_batch(MOCK_COMMENTS)
        assert results == []

    @patch("google.genai.Client")
    @patch("ai.gemini_provider.GeminiProvider._load_schema")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch_schema_missing(self, mock_load_schema, mock_client_class):
        """Test handling when post schema fails to load."""
        mock_load_schema.side_effect = [None, {"type": "object"}]
        provider = GeminiProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)
        assert results == []


class TestOpenAIProvider:
    @patch("openai.resources.chat.Completions.create")
    @patch("openai.OpenAI")
    @pytest.mark.asyncio
    async def test_analyze_posts_batch(self, mock_openai_class, mock_create, mock_openai_response):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create = mock_create
        mock_create.return_value = mock_openai_response

        provider = OpenAIProvider(api_key="test_key")
        results = await provider.analyze_posts_batch(MOCK_POSTS)

        assert len(results) == 2
        assert results[0]["ai_category"] == "Test Category"
        assert results[1]["ai_category"] == "Test Category 2"

    @patch("openai.resources.chat.Completions.create")
    @patch("openai.OpenAI")
    def test_analyze_comments_batch(self, mock_openai_class, mock_create):
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create = mock_create

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(
            {
                "comments": [
                    {
                        "comment_id": "COMMENT_ID_101",
                        "category": "Question",
                        "sentiment": "Neutral",
                        "keywords": ["how"],
                    }
                ]
            }
        )
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response

        provider = OpenAIProvider(api_key="test_key")
        results = provider.analyze_comments_batch(MOCK_COMMENTS[:1])

        assert len(results) == 1
        assert results[0]["ai_comment_category"] == "Question"

    def test_extract_json_from_response(self):
        provider = OpenAIProvider(api_key="test_key")

        # Test markdown code block
        content = 'Here is the JSON:\n```json\n[{"id": 1}]\n```'
        assert provider._extract_json_from_response(content) == [{"id": 1}]

        # Test raw list
        content = '[{"id": 2}]'
        assert provider._extract_json_from_response(content) == [{"id": 2}]

        # Test text around JSON
        content = 'Some text [{"id": 3}] some more text'
        assert provider._extract_json_from_response(content) == [{"id": 3}]

    @patch("openai.resources.models.Models.list")
    @patch("openai.OpenAI")
    def test_list_available_models(self, mock_openai_class, mock_list):
        mock_client = mock_openai_class.return_value
        mock_client.models.list = mock_list

        mock_model1 = MagicMock()
        mock_model1.id = "gpt-4"
        mock_model2 = MagicMock()
        mock_model2.id = "gpt-3.5"

        mock_response = MagicMock()
        mock_response.data = [mock_model1, mock_model2]
        mock_list.return_value = mock_response

        provider = OpenAIProvider(api_key="test_key")
        models = provider.list_available_models()
        assert models == ["gpt-4", "gpt-3.5"]


def test_provider_factory():
    with (
        patch("config.get_google_api_key", return_value="test_key"),
        patch("config.get_gemini_model", return_value="gemini-test"),
        patch("config.get_ai_provider_type", return_value="gemini"),
        patch("google.genai.Client"),
        patch("ai.gemini_provider.GeminiProvider._load_schema", return_value={}),
    ):
        provider = get_ai_provider("gemini")
        assert provider.provider_name == "gemini"
        assert provider.get_model_name() == "gemini-test"


def test_create_post_batches():
    posts = [{"post_content_raw": "a" * 400}] * 10  # ~100 tokens per post
    batches = create_post_batches(posts, max_tokens=300)
    assert len(batches) >= 3


@pytest.mark.asyncio
async def test_categorize_posts_batch_wrapper():
    # Patch where it's used, not where it's defined
    with patch("ai.filtering_pipeline.get_ai_provider") as mock_factory:
        mock_provider = MagicMock()
        mock_provider.analyze_posts_batch = AsyncMock(return_value=[{"status": "ok"}])
        mock_factory.return_value = mock_provider

        # Ensure posts pass the filter
        posts = [{"internal_post_id": 1, "text": "project idea"}]

        results = await categorize_posts_batch(posts)
        assert len(results) == 1
        assert results[0]["status"] == "ok"
        mock_provider.analyze_posts_batch.assert_called_once()
