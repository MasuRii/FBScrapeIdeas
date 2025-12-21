"""
Gemini AI Provider implementation.

This module implements the AIProvider interface for Google's Gemini API,
supporting configurable model selection and structured JSON output.
"""

import json
import logging
import re
import time

import google.generativeai as genai
from google.api_core import exceptions as core_exceptions
from google.api_core import retry, retry_async

from ai.base_provider import AIProvider
from ai.prompts import get_comment_analysis_prompt, get_post_categorization_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Default Gemini model
DEFAULT_GEMINI_MODEL = "models/gemini-2.0-flash"


def list_gemini_models(api_key: str) -> list[str]:
    """
    List all available Gemini models that support content generation.

    Args:
        api_key: Google API key.

    Returns:
        List of model names.
    """
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        return [
            model.name
            for model in models
            if "generateContent" in model.supported_generation_methods
        ]
    except Exception as e:
        logging.error(f"Error listing Gemini models: {e}")
        return []


class GeminiProvider(AIProvider):
    """
    AI Provider implementation for Google's Gemini API.

    Supports configurable model selection and uses native JSON schema
    for structured output.
    """

    def __init__(self, api_key: str, model: str | None = None):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google API key for Gemini.
            model: Model identifier (default: models/gemini-2.0-flash).
        """
        super().__init__(model)
        self.api_key = api_key
        self._model_name = model or DEFAULT_GEMINI_MODEL

        # Ensure model name has the correct prefix
        if not self._model_name.startswith("models/"):
            self._model_name = f"models/{self._model_name}"

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self._model_name)

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

        # Build async retry policy
        async_retry = retry_async.AsyncRetry(
            predicate=retry_async.if_exception_type(
                (core_exceptions.ResourceExhausted, core_exceptions.ServiceUnavailable)
            ),
            initial=1.0,
            maximum=60.0,
            multiplier=2.0,
            deadline=300,
            jitter=True,
        )

        # Build prompt
        base_prompt = custom_prompt or get_post_categorization_prompt()
        prompt_parts = [base_prompt, "\n\nPosts:\n"]

        post_id_map = {post["internal_post_id"]: post for post in posts}
        for post in posts:
            prompt_parts.append(
                f"[POST_ID_{post['internal_post_id']}: {post['post_content_raw']}]\n"
            )

        prompt_text = "".join(prompt_parts)

        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": self._post_schema,
        }

        try:
            logging.info(f"Categorizing {len(posts)} posts with Gemini API ({self._model_name})...")

            response = await async_retry(self._model.generate_content_async)(
                prompt_text, generation_config=generation_config
            )

            if not response or not response.candidates:
                block_reason = (
                    response.prompt_feedback.block_reason
                    if hasattr(response, "prompt_feedback") and response.prompt_feedback
                    else "unknown"
                )
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

        except core_exceptions.ResourceExhausted as e:
            logging.error(f"API rate limit exceeded: {e}")
            return []
        except core_exceptions.ServiceUnavailable as e:
            logging.error(f"Gemini service unavailable: {e}")
            return []
        except core_exceptions.GoogleAPIError as e:
            logging.error(f"Google API error: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error: {type(e).__name__}: {e}")
            return []

    def _map_post_results(
        self, ai_results: list[dict], post_id_map: dict, posts: list[dict]
    ) -> list[dict]:
        """Map AI results back to original posts."""
        mapped_results = []

        for ai_result in ai_results:
            original_post = None
            post_id_from_ai = ai_result.get("postId")

            if post_id_from_ai and post_id_from_ai.startswith("POST_ID_"):
                try:
                    id_str_part = post_id_from_ai.replace("POST_ID_", "")
                    match = re.match(r"(\d+)", id_str_part)
                    if match:
                        original_id = int(match.group(1))
                        if original_id in post_id_map:
                            original_post = post_id_map[original_id]
                except (ValueError, IndexError) as e:
                    logging.warning(f"Invalid postId format: {post_id_from_ai}. Error: {e}")

            # Fallback: match by content
            if not original_post:
                ai_summary = ai_result.get("summary", "")
                for original in posts:
                    if (
                        original.get("post_content_raw")
                        and ai_summary
                        and ai_summary in original["post_content_raw"]
                    ):
                        original_post = original
                        break

            if original_post:
                combined_data = original_post.copy()
                combined_data.update(
                    {
                        "ai_category": ai_result.get("category"),
                        "ai_sub_category": ai_result.get("subCategory"),
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

        retry_policy = retry.Retry(
            predicate=retry.if_exception_type(
                (core_exceptions.ResourceExhausted, core_exceptions.ServiceUnavailable)
            ),
            initial=1.0,
            maximum=60.0,
            multiplier=2.0,
            deadline=300,
        )

        # Build prompt
        base_prompt = custom_prompt or get_comment_analysis_prompt()
        prompt_parts = [base_prompt, "\n\nComments:\n"]

        comment_id_map = {comment["comment_id"]: comment for comment in comments}
        for comment in comments:
            prompt_parts.append(
                f"[COMMENT_ID_{comment['comment_id']}: {comment['comment_text']}]\n"
            )

        prompt_text = "".join(prompt_parts)

        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": self._comment_schema,
        }

        try:
            logging.info(
                f"Analyzing {len(comments)} comments with Gemini API ({self._model_name})..."
            )

            response = retry_policy(self._model.generate_content)(
                prompt_text, generation_config=generation_config
            )

            if not response or not response.candidates:
                block_reason = (
                    response.prompt_feedback.block_reason
                    if hasattr(response, "prompt_feedback") and response.prompt_feedback
                    else "unknown"
                )
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

        except core_exceptions.ResourceExhausted as e:
            logging.error(f"API rate limit exceeded: {e}")
            return []
        except core_exceptions.ServiceUnavailable as e:
            logging.error(f"Gemini service unavailable: {e}")
            return []
        except core_exceptions.GoogleAPIError as e:
            logging.error(f"Google API error during comment analysis: {e}")
            return []
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
