"""
AI Filtering Pipeline - 3-Stage Analysis.

Implements the "AI Guard" pattern to filter irrelevant posts locally
before calling expensive LLMs, and handles structured analysis.
"""

import logging
from typing import Any, Dict, List, Optional

import config
from ai.provider_factory import get_ai_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class FilteringPipeline:
    """
    Implements a 3-stage filtering and analysis pipeline:
    1. Keyword Pre-filter (Local)
    2. LLM Classification (Remote)
    3. Database Storage (Handled by caller)
    """

    def __init__(self):
        """Initialize the pipeline with configured keywords."""
        self.keywords = [k.lower() for k in getattr(config, "AI_FILTER_KEYWORDS", [])]
        self.skipped_count = 0
        self.processed_count = 0
        self._provider = None

    @property
    def provider(self):
        """Lazy-loaded AI provider."""
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    def should_analyze(self, post_text: str) -> bool:
        """
        Stage 1: Keyword Pre-filter (Local).
        Checks if the post text contains any of the high-signal keywords.

        Args:
            post_text: The raw text of the post.

        Returns:
            True if a keyword match is found, False otherwise.
        """
        if not post_text:
            return False

        text_lower = post_text.lower()
        for keyword in self.keywords:
            if keyword in text_lower:
                return True

        return False

    async def analyze_post(self, post_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Stage 2: AI Analysis with Structured Output.
        Calls Stage 1 (Keyword check), then Stage 2 (AI Analysis) if passed.

        Args:
            post_data: Dictionary containing post content and metadata.
                       Must have 'text' and 'post_id'.

        Returns:
            Structured analysis object or None if skipped or failed.
        """
        results = await self.analyze_posts_batch([post_data])
        return results[0] if results else None

    async def analyze_posts_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze a batch of posts using the 3-stage pipeline.

        Args:
            posts: List of post dictionaries.

        Returns:
            List of analyzed post dictionaries.
        """
        to_analyze = []
        results = []

        for post in posts:
            post_text = post.get("text", post.get("post_content_raw", ""))
            post_id = post.get(
                "facebook_post_id", post.get("post_id", post.get("internal_post_id", "unknown"))
            )

            if self.should_analyze(post_text):
                to_analyze.append(post)
                self.processed_count += 1
            else:
                self.skipped_count += 1
                logging.info(f"Post {post_id} skipped by keyword filter.")

        if to_analyze:
            try:
                ai_results = await self.provider.analyze_posts_batch(to_analyze)
                results.extend(ai_results)
            except Exception as e:
                logging.error(f"AI Batch Analysis failed: {e}")
                # Mark as error but don't stop pipeline
                for post in to_analyze:
                    results.append(
                        {**post, "ai_status": "error", "ai_error": str(e), "is_processed_by_ai": 0}
                    )

        return results

    def get_stats(self) -> Dict[str, int]:
        """Returns analysis statistics."""
        return {
            "processed": self.processed_count,
            "skipped": self.skipped_count,
        }
