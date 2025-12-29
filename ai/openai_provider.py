"""
OpenAI-Compatible AI Provider implementation.

This module implements the AIProvider interface for OpenAI-compatible APIs,
supporting custom base URLs for providers like Ollama, LM Studio, OpenRouter, etc.
"""

import json
import logging
import re
import time

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from ai.base_provider import AIProvider
from ai.prompts import get_comment_analysis_prompt, get_post_categorization_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Default OpenAI settings
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def list_openai_models(base_url: str, api_key: str) -> list[str]:
    """
    List available models from an OpenAI-compatible endpoint.

    Args:
        base_url: The base URL of the API.
        api_key: API key for authentication.

    Returns:
        List of model IDs.
    """
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        models = client.models.list()
        return [model.id for model in models.data]
    except Exception as e:
        logging.error(f"Error listing models from {base_url}: {e}")
        return []


class OpenAIProvider(AIProvider):
    """
    AI Provider implementation for OpenAI-compatible APIs.

    Supports custom base URLs for different providers:
    - OpenAI: https://api.openai.com/v1
    - Ollama: http://localhost:11434/v1
    - LM Studio: http://localhost:1234/v1
    - OpenRouter: https://openrouter.ai/api/v1
    - etc.
    """

    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        """
        Initialize the OpenAI-compatible provider.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for the API (default: OpenAI).
            model: Model identifier (default: gpt-4o-mini).
        """
        super().__init__(model)
        self.api_key = api_key
        self.base_url = base_url or DEFAULT_OPENAI_BASE_URL
        self._model_name = model or DEFAULT_OPENAI_MODEL

        self.client = OpenAI(base_url=self.base_url, api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_model_name(self) -> str:
        return self._model_name

    def list_available_models(self) -> list[str]:
        """List all available models from the endpoint."""
        return list_openai_models(self.base_url, self.api_key)

    def _extract_json_from_response(self, content: str) -> list[dict] | None:
        """
        Extract JSON array from response content.

        Handles cases where the model might return markdown code blocks
        or extra text around the JSON.
        """
        if not content:
            return None

        # Try direct JSON parse first
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return None
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if code_block_match:
            try:
                result = json.loads(code_block_match.group(1).strip())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Try to find JSON array in the content
        array_match = re.search(r"\[[\s\S]*\]", content)
        if array_match:
            try:
                result = json.loads(array_match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        logging.error(f"Could not extract JSON from response: {content[:500]}...")
        return None

    async def analyze_posts_batch(
        self, posts: list[dict], custom_prompt: str | None = None
    ) -> list[dict]:
        """
        Analyze a batch of posts using OpenAI-compatible API.

        Note: This method is synchronous despite being async, as the openai
        library handles async internally.

        Args:
            posts: List of post dictionaries.
            custom_prompt: Optional custom prompt to use.

        Returns:
            List of posts with AI categorization results.
        """
        if not posts:
            return []

        # Build system prompt with schema
        system_prompt = custom_prompt or get_post_categorization_prompt(include_schema=True)

        # Build user prompt with posts
        user_prompt_parts = ["Posts:\n"]
        post_id_map = {}
        for post in posts:
            p_id = post.get("post_id") or post.get("internal_post_id")
            if p_id:
                post_id_map[str(p_id)] = post

        for post in posts:
            p_id = post.get("post_id") or post.get("internal_post_id")
            p_text = post.get("text") or post.get("post_content_raw") or "N/A"
            user_prompt_parts.append(f"[POST_ID_{p_id}: {p_text}]\n")

        user_prompt = "".join(user_prompt_parts)

        try:
            logging.info(
                f"Categorizing {len(posts)} posts with OpenAI-compatible API ({self._model_name})..."
            )

            response = self.client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            if not response.choices:
                logging.error("OpenAI API returned no choices")
                return []

            content = response.choices[0].message.content
            logging.debug(f"Raw response: {content[:500] if content else 'None'}...")

            # Handle response that might be wrapped in an object
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    # Check for common wrapper keys
                    for key in ["posts", "results", "data", "items"]:
                        if key in parsed and isinstance(parsed[key], list):
                            categorized_results_list = parsed[key]
                            break
                    else:
                        # If no wrapper, try to find any list value
                        for value in parsed.values():
                            if isinstance(value, list):
                                categorized_results_list = value
                                break
                        else:
                            logging.error(
                                f"Response is object but contains no list: {content[:500]}"
                            )
                            return []
                elif isinstance(parsed, list):
                    categorized_results_list = parsed
                else:
                    logging.error(f"Unexpected response format: {type(parsed)}")
                    return []
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError: {e}. Content: {content[:500]}")
                # Try extraction as fallback
                categorized_results_list = self._extract_json_from_response(content)
                if not categorized_results_list:
                    return []

            return self._map_post_results(categorized_results_list, post_id_map, posts)

        except RateLimitError as e:
            logging.error(f"Rate limit exceeded: {e}")
            return []
        except APIConnectionError as e:
            logging.error(f"API connection error: {e}")
            return []
        except APIError as e:
            logging.error(f"API error: {e}")
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

            if post_id_from_ai and str(post_id_from_ai).startswith("POST_ID_"):
                id_str_part = str(post_id_from_ai).replace("POST_ID_", "")
                if id_str_part in post_id_map:
                    original_post = post_id_map[id_str_part]

            # Fallback: match by summary content
            if not original_post:
                ai_summary = ai_result.get("summary", "")
                for original in posts:
                    original_content = original.get("text") or original.get("post_content_raw", "")
                    if original_content and ai_summary:
                        if ai_summary in original_content:
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
        Analyze a batch of comments using OpenAI-compatible API.

        Args:
            comments: List of comment dictionaries.
            custom_prompt: Optional custom prompt to use.

        Returns:
            List of comments with AI analysis results.
        """
        if not comments:
            return []

        # Build system prompt with schema
        system_prompt = custom_prompt or get_comment_analysis_prompt(include_schema=True)

        # Build user prompt with comments
        user_prompt_parts = ["Comments:\n"]
        comment_id_map = {comment["comment_id"]: comment for comment in comments}

        for comment in comments:
            user_prompt_parts.append(
                f"[COMMENT_ID_{comment['comment_id']}: {comment['comment_text']}]\n"
            )

        user_prompt = "".join(user_prompt_parts)

        try:
            logging.info(
                f"Analyzing {len(comments)} comments with OpenAI-compatible API ({self._model_name})..."
            )

            response = self.client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            if not response.choices:
                logging.error("OpenAI API returned no choices for comments")
                return []

            content = response.choices[0].message.content

            # Handle response that might be wrapped in an object
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    # Check for common wrapper keys
                    for key in ["comments", "results", "data", "items"]:
                        if key in parsed and isinstance(parsed[key], list):
                            analysis_results_list = parsed[key]
                            break
                    else:
                        for value in parsed.values():
                            if isinstance(value, list):
                                analysis_results_list = value
                                break
                        else:
                            logging.error("Response is object but contains no list")
                            return []
                elif isinstance(parsed, list):
                    analysis_results_list = parsed
                else:
                    logging.error(f"Unexpected response format for comments: {type(parsed)}")
                    return []
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError parsing comment response: {e}")
                analysis_results_list = self._extract_json_from_response(content)
                if not analysis_results_list:
                    return []

            return self._map_comment_results(analysis_results_list, comment_id_map)

        except RateLimitError as e:
            logging.error(f"Rate limit exceeded: {e}")
            return []
        except APIConnectionError as e:
            logging.error(f"API connection error: {e}")
            return []
        except APIError as e:
            logging.error(f"API error during comment analysis: {e}")
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

            if comment_id_from_ai and str(comment_id_from_ai).startswith("COMMENT_ID_"):
                try:
                    original_id = int(str(comment_id_from_ai).replace("COMMENT_ID_", ""))
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
