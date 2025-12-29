"""
Gemini AI Provider implementation.

This module implements the AIProvider interface for Google's Gemini API,
supporting configurable model selection and structured JSON output.

Updated for google-genai SDK (v1.0+) - the new official SDK replacing
the deprecated google-generativeai package.
"""

import json
import logging
import time
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from ai.base_provider import AIProvider
from ai.prompts import get_comment_analysis_prompt, get_post_categorization_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Default Gemini model
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

# Retry configuration constants
RETRY_MAX_ATTEMPTS = 5
RETRY_MULTIPLIER = 1
RETRY_MIN_WAIT = 1
RETRY_MAX_WAIT = 60
RETRY_JITTER_MAX = 2


def list_gemini_models(api_key: str) -> list[str]:
    """
    List all available Gemini models that support content generation.

    Args:
        api_key: Google API key.

    Returns:
        List of model names.
    """
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        return [
            model.name
            for model in models
            if hasattr(model, "supported_actions") and "generateContent" in model.supported_actions
        ]
    except Exception as e:
        logging.error(f"Error listing Gemini models: {e}")
        return []


class GeminiProvider(AIProvider):
    """
    AI Provider implementation for Google's Gemini API.

    Supports configurable model selection and uses native JSON schema
    for structured output.

    Updated for google-genai SDK v1.0+ with unified Client interface.
    """

    def __init__(self, api_key: str, model: str | None = None):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google API key for Gemini.
            model: Model identifier (default: gemini-2.0-flash).
        """
        super().__init__(model)
        self.api_key = api_key
        self._model_name = model or DEFAULT_GEMINI_MODEL

        # New SDK doesn't require "models/" prefix - normalize the model name
        if self._model_name.startswith("models/"):
            self._model_name = self._model_name.replace("models/", "", 1)

        # Initialize the new unified client
        self._client = genai.Client(api_key=api_key)

        # Load JSON schemas
        self._post_schema = self._load_schema("ai/gemini_schema.json")
        self._comment_schema = self._load_schema("ai/gemini_comment_schema.json")

    def _load_schema(self, schema_path: str) -> dict | None:
        """Load a JSON schema from file."""
        try:
            with open(schema_path) as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Schema file not found: {schema_path}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding schema {schema_path}: {e}")
            return None

    @property
    def provider_name(self) -> str:
        return "gemini"

    def get_model_name(self) -> str:
        return self._model_name

    def list_available_models(self) -> list[str]:
        """List all available Gemini models."""
        return list_gemini_models(self.api_key)

    def _create_generation_config(self, schema: dict) -> types.GenerateContentConfig:
        """
        Create a GenerateContentConfig with JSON schema for structured output.

        Args:
            schema: The JSON schema dictionary.

        Returns:
            GenerateContentConfig instance.
        """
        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )

    async def analyze_posts_batch(
        self, posts: list[dict], custom_prompt: str | None = None
    ) -> list[dict]:
        """
        Analyze a batch of posts using Gemini API.

        Args:
            posts: List of post dictionaries.
            custom_prompt: Optional custom prompt to use.

        Returns:
            List of posts with AI categorization results.
        """
        if not posts:
            return []

        if not self._post_schema:
            logging.error("Post schema not loaded. Cannot process posts.")
            return []

        # Build prompt
        base_prompt = custom_prompt or get_post_categorization_prompt()
        prompt_parts = [base_prompt, "\n\nPosts:\n"]

        post_id_map = {}
        for post in posts:
            # Use post_id or internal_post_id as the identifier for AI mapping
            p_id = post.get("post_id") or post.get("internal_post_id")
            if p_id:
                post_id_map[str(p_id)] = post

        for post in posts:
            p_id = post.get("post_id") or post.get("internal_post_id")
            p_text = post.get("text") or post.get("post_content_raw") or "N/A"
            prompt_parts.append(f"[POST_ID_{p_id}: {p_text}]\n")

        prompt_text = "".join(prompt_parts)

        # Create generation config with schema
        config = self._create_generation_config(self._post_schema)

        try:
            logging.info(f"Categorizing {len(posts)} posts with Gemini API ({self._model_name})...")

            # Use tenacity retry with async call via client.aio
            response = await self._async_generate_with_retry(prompt_text, config)

            if not response or not response.candidates:
                block_reason = self._get_block_reason(response)
                logging.error(f"Gemini API call failed. Block reason: {block_reason}")
                return []

            logging.info("Gemini API call successful.")

            try:
                categorized_results_list = json.loads(response.text)
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError parsing Gemini response: {e}")
                return []

            if not isinstance(categorized_results_list, list):
                logging.error(f"Gemini response was not a list: {response.text}")
                return []

            return self._map_post_results(categorized_results_list, post_id_map, posts)

        except Exception as e:
            logging.error(f"Unexpected error: {type(e).__name__}: {e}")
            return []

    async def _async_generate_with_retry(
        self, prompt: str, config: types.GenerateContentConfig
    ) -> Any:
        """
        Async content generation with tenacity retry logic.

        Args:
            prompt: The prompt text.
            config: Generation configuration.

        Returns:
            The API response.
        """

        # Define retry decorator for async - retry on server errors and client errors
        @retry(
            retry=retry_if_exception_type((ServerError, ClientError)),
            stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=RETRY_MULTIPLIER, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT
            )
            + wait_random(0, RETRY_JITTER_MAX),
            reraise=True,
        )
        async def _call():
            return await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            )

        return await _call()

    def _sync_generate_with_retry(self, prompt: str, config: types.GenerateContentConfig) -> Any:
        """
        Sync content generation with tenacity retry logic.

        Args:
            prompt: The prompt text.
            config: Generation configuration.

        Returns:
            The API response.
        """

        # Define retry decorator for sync - retry on server errors and client errors
        @retry(
            retry=retry_if_exception_type((ServerError, ClientError)),
            stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=RETRY_MULTIPLIER, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT
            )
            + wait_random(0, RETRY_JITTER_MAX),
            reraise=True,
        )
        def _call():
            return self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            )

        return _call()

    def _get_block_reason(self, response: Any) -> str:
        """Extract block reason from response if available."""
        if response is None:
            return "no response"
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            if hasattr(response.prompt_feedback, "block_reason"):
                return str(response.prompt_feedback.block_reason)
        return "unknown"

    def _map_post_results(
        self, ai_results: list[dict], post_id_map: dict, posts: list[dict]
    ) -> list[dict]:
        """Map AI results back to original posts."""
        mapped_results = []

        for ai_result in ai_results:
            original_post = None
            post_id_from_ai = ai_result.get("postId")

            if post_id_from_ai and post_id_from_ai.startswith("POST_ID_"):
                id_str_part = post_id_from_ai.replace("POST_ID_", "")
                if id_str_part in post_id_map:
                    original_post = post_id_map[id_str_part]

            # Fallback: match by content
            if not original_post:
                ai_summary = ai_result.get("summary", "")
                for original in posts:
                    original_content = original.get("text") or original.get("post_content_raw", "")
                    if original_content and ai_summary and ai_summary in original_content:
                        original_post = original
                        break

            if original_post:
                combined_data = original_post.copy()
                combined_data.update(
                    {
                        "ai_category": ai_result.get("category"),
                        "ai_sub_category": ai_result.get("subCategory"),
                        "ai_sentiment": ai_result.get("sentiment"),
                        "ai_keywords": json.dumps(ai_result.get("keywords", [])),
                        "ai_summary": ai_result.get("summary"),
                        "ai_is_potential_idea": int(ai_result.get("isPotentialIdea", False)),
                        "ai_reasoning": ai_result.get("reasoning"),
                        "ai_raw_response": json.dumps(ai_result),
                        "is_processed_by_ai": 1,
                        "last_ai_processing_at": int(time.time()),
                    }
                )
                mapped_results.append(combined_data)
            else:
                logging.warning(f"Could not map AI result to original post: {ai_result}")

        logging.info(f"Successfully mapped {len(mapped_results)} posts.")
        return mapped_results

    def analyze_comments_batch(
        self, comments: list[dict], custom_prompt: str | None = None
    ) -> list[dict]:
        """
        Analyze a batch of comments using Gemini API (synchronous).

        Args:
            comments: List of comment dictionaries.
            custom_prompt: Optional custom prompt to use.

        Returns:
            List of comments with AI analysis results.
        """
        if not comments:
            return []

        if not self._comment_schema:
            logging.error("Comment schema not loaded. Cannot process comments.")
            return []

        # Build prompt
        base_prompt = custom_prompt or get_comment_analysis_prompt()
        prompt_parts = [base_prompt, "\n\nComments:\n"]

        comment_id_map = {comment["comment_id"]: comment for comment in comments}
        for comment in comments:
            prompt_parts.append(
                f"[COMMENT_ID_{comment['comment_id']}: {comment['comment_text']}]\n"
            )

        prompt_text = "".join(prompt_parts)

        # Create generation config with schema
        config = self._create_generation_config(self._comment_schema)

        try:
            logging.info(
                f"Analyzing {len(comments)} comments with Gemini API ({self._model_name})..."
            )

            # Use sync generation with retry
            response = self._sync_generate_with_retry(prompt_text, config)

            if not response or not response.candidates:
                block_reason = self._get_block_reason(response)
                logging.error(f"Gemini API call for comments failed. Block reason: {block_reason}")
                return []

            logging.info("Gemini API call for comments successful.")

            try:
                analysis_results_list = json.loads(response.text)
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError parsing comment response: {e}")
                return []

            if not isinstance(analysis_results_list, list):
                logging.error("Gemini response for comments was not a list")
                return []

            return self._map_comment_results(analysis_results_list, comment_id_map)

        except Exception as e:
            logging.error(f"Unexpected error during comment analysis: {type(e).__name__}: {e}")
            return []

    def _map_comment_results(self, ai_results: list[dict], comment_id_map: dict) -> list[dict]:
        """Map AI results back to original comments."""
        mapped_results = []

        for ai_result in ai_results:
            original_comment = None
            comment_id_from_ai = ai_result.get("comment_id")

            if comment_id_from_ai and comment_id_from_ai.startswith("COMMENT_ID_"):
                try:
                    original_id = int(comment_id_from_ai.replace("COMMENT_ID_", ""))
                    if original_id in comment_id_map:
                        original_comment = comment_id_map[original_id]
                except (ValueError, IndexError) as e:
                    logging.warning(f"Invalid commentId format: {comment_id_from_ai}. Error: {e}")

            if original_comment:
                combined_data = original_comment.copy()
                combined_data.update(
                    {
                        "ai_comment_category": ai_result.get("category"),
                        "ai_comment_sentiment": ai_result.get("sentiment"),
                        "ai_comment_keywords": json.dumps(ai_result.get("keywords", [])),
                        "ai_comment_raw_response": json.dumps(ai_result),
                    }
                )
                mapped_results.append(combined_data)
            else:
                logging.warning(f"Could not map AI result to comment: {ai_result}")

        logging.info(f"Successfully analyzed and mapped {len(mapped_results)} comments.")
        return mapped_results
