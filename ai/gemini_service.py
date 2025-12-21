"""
Gemini AI Service - Backward Compatibility Wrapper.

This module provides backward compatibility for existing code that imports
from gemini_service. It now delegates to the new provider abstraction layer.

For new code, prefer using:
    from ai.provider_factory import get_ai_provider
"""

import logging
from typing import List, Dict

# Re-export the utility function that's still used directly
from ai.gemini_provider import GeminiProvider

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def categorize_posts_batch(
    posts: List[Dict], initial_delay: float = 1.0
) -> List[Dict]:
    """
    Asynchronously sends a batch of posts to AI for categorization.

    This is a backward-compatible wrapper that uses the new provider system.

    Args:
        posts: A list of dictionaries, each containing 'internal_post_id' and 'post_content_raw'.
        initial_delay: Initial delay for retry backoff (default 1.0 seconds). Ignored in new implementation.

    Returns:
        A list of dictionaries with added AI categorization results.
    """
    from ai.provider_factory import get_ai_provider

    try:
        provider = get_ai_provider()
        return await provider.analyze_posts_batch(posts)
    except Exception as e:
        logging.error(f"Error in categorize_posts_batch: {e}")
        return []


def process_comments_with_gemini(comments: List[Dict]) -> List[Dict]:
    """
    Sends a batch of comments to AI for analysis and returns the results.

    This is a backward-compatible wrapper that uses the new provider system.

    Args:
        comments: A list of dictionaries, each containing 'comment_id' and 'comment_text'.

    Returns:
        A list of dictionaries with added AI analysis results, or an empty list if processing fails.
    """
    from ai.provider_factory import get_ai_provider

    try:
        provider = get_ai_provider()
        return provider.analyze_comments_batch(comments)
    except Exception as e:
        logging.error(f"Error in process_comments_with_gemini: {e}")
        return []


def create_post_batches(
    all_posts: List[Dict], max_tokens: int = 800000
) -> List[List[Dict]]:
    """
    Groups posts into batches based on token count (Gemini 2.0 Flash has 1M token limit).
    Uses 4:1 character-to-token ratio as a safe estimate.

    Args:
        all_posts: List of post dictionaries
        max_tokens: Maximum tokens per batch (default 800k for safety)

    Returns:
        List of batched posts
    """
    batches = []
    current_batch = []
    current_tokens = 0

    for post in all_posts:
        content = post.get("post_content_raw", "")
        post_tokens = len(content) // 4 + 100

        if current_tokens + post_tokens > max_tokens:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            else:
                logging.warning(
                    f"Single post exceeds max tokens ({post_tokens} > {max_tokens})"
                )

        current_batch.append(post)
        current_tokens += post_tokens

    if current_batch:
        batches.append(current_batch)

    if batches:
        avg_tokens = current_tokens // len(batches) if len(batches) > 0 else 0
        logging.info(
            f"Created {len(batches)} batches averaging {avg_tokens} tokens/batch"
        )

    return batches


# For backward compatibility with any code importing the module to get models
def list_available_gemini_models() -> List[str]:
    """List available Gemini models. Requires GOOGLE_API_KEY to be set."""
    from config import get_google_api_key
    from ai.gemini_provider import list_gemini_models

    try:
        api_key = get_google_api_key()
        return list_gemini_models(api_key)
    except Exception as e:
        logging.error(f"Error listing Gemini models: {e}")
        return []


if __name__ == "__main__":
    # Test the batching function
    dummy_posts = []
    for i in range(20):
        dummy_posts.append(
            {
                "internal_post_id": i + 1,
                "post_content_raw": "This is a test post content. " * 50,
            }
        )

    batches = create_post_batches(dummy_posts, max_tokens=10000)
    print(f"Created {len(batches)} batches")
