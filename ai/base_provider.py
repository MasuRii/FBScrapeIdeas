"""
Base provider abstraction layer for AI services.

This module defines the abstract interface that all AI providers must implement,
enabling seamless switching between different AI backends (Gemini, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class PostCategorizationResult:
    """Result of post categorization by AI."""

    post_id: str
    category: str
    sub_category: Optional[str]
    keywords: List[str]
    summary: str
    is_potential_idea: bool
    reasoning: str
    raw_response: Dict[str, Any]


@dataclass
class CommentAnalysisResult:
    """Result of comment analysis by AI."""

    comment_id: str
    category: str
    sentiment: str
    keywords: List[str]
    raw_response: Dict[str, Any]


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI providers (Gemini, OpenAI, etc.) must implement this interface
    to ensure consistent behavior across different backends.
    """

    def __init__(self, model: Optional[str] = None):
        """
        Initialize the AI provider.

        Args:
            model: The model identifier to use. If None, use provider default.
        """
        self.model = model

    @abstractmethod
    async def analyze_posts_batch(
        self, posts: List[Dict], custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze a batch of posts and return categorization results.

        Args:
            posts: List of dictionaries containing 'internal_post_id' and 'post_content_raw'.
            custom_prompt: Optional custom prompt to override default.

        Returns:
            List of dictionaries with original post data plus AI categorization results.
        """
        pass

    @abstractmethod
    def analyze_comments_batch(
        self, comments: List[Dict], custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze a batch of comments and return analysis results.

        Args:
            comments: List of dictionaries containing 'comment_id' and 'comment_text'.
            custom_prompt: Optional custom prompt to override default.

        Returns:
            List of dictionaries with original comment data plus AI analysis results.
        """
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """
        List all available models for this provider.

        Returns:
            List of model identifiers.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the current model name/identifier being used.

        Returns:
            Current model identifier string.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Get the provider name (e.g., 'gemini', 'openai').

        Returns:
            Provider name string.
        """
        pass
