"""
Prompt management system for AI providers.

This module handles loading and managing prompts for AI analysis,
supporting both default prompts and user-customized prompts loaded
from a custom_prompts.json file.
"""

import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Default prompts - used when no custom prompts are provided
# These focus on semantic task description; schema is enforced by the API when using structured outputs
DEFAULT_PROMPTS = {
    "post_categorization": (
        "You are an expert post categorizer analyzing Facebook posts from a tech/project discussion group. "
        "For each post provided with a temporary ID (like POST_ID_123), analyze and extract:\n"
        "1. Primary category: Problem Statement, Project Idea, Question/Inquiry, General Discussion, or Other\n"
        "2. Optional sub-category for more specificity\n"
        "3. Sentiment: positive, negative, neutral, or frustrated\n"
        "4. 3-5 relevant keywords capturing the main topics\n"
        "5. A concise 1-2 sentence summary of the post's core message\n"
        "6. Whether it suggests a potential project/thesis idea (true/false)\n"
        "7. Brief reasoning explaining your categorization choice\n"
        "Preserve the original post ID in your response."
    ),
    "comment_analysis": (
        "You are an expert comment analyzer. Analyze Facebook comments from a discussion group. "
        "For each comment provided with a temporary ID (like COMMENT_ID_123), extract:\n"
        "1. Category: question, suggestion_idea, agreement_positive_feedback, "
        "disagreement_negative_feedback, information_sharing, clarification_request, "
        "personal_experience, or off_topic_other\n"
        "2. Sentiment: positive, negative, or neutral\n"
        "3. 1-5 relevant keywords\n"
        "Preserve the original comment ID in your response."
    ),
}

# JSON schemas for structured output - used with OpenAI-compatible providers
POST_SCHEMA_FOR_PROMPT = """
Expected JSON schema for each post:
{
    "postId": "POST_ID_X",
    "category": "string (one of: Problem Statement, Project Idea, Question/Inquiry, General Discussion, Other)",
    "subCategory": "string or null",
    "sentiment": "string (one of: positive, negative, neutral, frustrated)",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "summary": "1-2 sentence summary",
    "isPotentialIdea": true/false,
    "reasoning": "brief justification"
}
Return a JSON array of these objects.
"""

COMMENT_SCHEMA_FOR_PROMPT = """
Expected JSON schema for each comment:
{
    "comment_id": "COMMENT_ID_X",
    "category": "string (one of: question, suggestion_idea, agreement_positive_feedback, disagreement_negative_feedback, information_sharing, clarification_request, personal_experience, off_topic_other)",
    "sentiment": "string (one of: positive, negative, neutral)",
    "keywords": ["keyword1", "keyword2"]
}
Return a JSON array of these objects.
"""


def get_custom_prompts_path() -> Path:
    """Get the path to the custom prompts file."""
    # Check in current working directory first
    cwd_path = Path.cwd() / "custom_prompts.json"
    if cwd_path.exists():
        return cwd_path

    # Check in ai directory
    ai_dir_path = Path(__file__).parent / "custom_prompts.json"
    if ai_dir_path.exists():
        return ai_dir_path

    # Check in project root (relative to ai directory)
    project_root = Path(__file__).parent.parent / "custom_prompts.json"
    if project_root.exists():
        return project_root

    return cwd_path  # Return default path even if it doesn't exist


def load_custom_prompts() -> dict[str, str]:
    """
    Load custom prompts from custom_prompts.json if it exists.

    Returns:
        Dictionary of custom prompts, or empty dict if file doesn't exist.
    """
    custom_path = get_custom_prompts_path()

    if not custom_path.exists():
        logging.debug(f"No custom prompts file found at {custom_path}")
        return {}

    try:
        with open(custom_path, encoding="utf-8") as f:
            custom_prompts = json.load(f)
            logging.info(f"Loaded custom prompts from {custom_path}")
            return custom_prompts
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing custom_prompts.json: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error loading custom prompts: {e}")
        return {}


def get_prompt(prompt_type: str, include_schema: bool = False) -> str:
    """
    Get a prompt by type, with fallback to defaults.

    Args:
        prompt_type: Type of prompt ('post_categorization' or 'comment_analysis')
        include_schema: Whether to include JSON schema in the prompt (for OpenAI providers)

    Returns:
        The prompt string.

    Raises:
        ValueError: If prompt_type is not recognized.
    """
    if prompt_type not in DEFAULT_PROMPTS:
        raise ValueError(
            f"Unknown prompt type: {prompt_type}. Available types: {list(DEFAULT_PROMPTS.keys())}"
        )

    # Try to load custom prompt first
    custom_prompts = load_custom_prompts()
    prompt = custom_prompts.get(prompt_type, DEFAULT_PROMPTS[prompt_type])

    # Add schema if requested (for OpenAI-compatible providers)
    if include_schema:
        if prompt_type == "post_categorization":
            prompt = f"{prompt}\n\n{POST_SCHEMA_FOR_PROMPT}"
        elif prompt_type == "comment_analysis":
            prompt = f"{prompt}\n\n{COMMENT_SCHEMA_FOR_PROMPT}"

    return prompt


def get_post_categorization_prompt(include_schema: bool = False) -> str:
    """Get the post categorization prompt."""
    return get_prompt("post_categorization", include_schema=include_schema)


def get_comment_analysis_prompt(include_schema: bool = False) -> str:
    """Get the comment analysis prompt."""
    return get_prompt("comment_analysis", include_schema=include_schema)


def get_all_prompts() -> dict[str, str]:
    """
    Get all prompts (custom with fallback to defaults).

    Returns:
        Dictionary of all prompts.
    """
    custom_prompts = load_custom_prompts()
    all_prompts = DEFAULT_PROMPTS.copy()
    all_prompts.update(custom_prompts)
    return all_prompts


def save_custom_prompts(prompts: dict[str, str], path: Path | None = None) -> bool:
    """
    Save custom prompts to file.

    Args:
        prompts: Dictionary of prompts to save.
        path: Optional path to save to. Defaults to custom_prompts.json in cwd.

    Returns:
        True if saved successfully, False otherwise.
    """
    if path is None:
        path = Path.cwd() / "custom_prompts.json"

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved custom prompts to {path}")
        return True
    except Exception as e:
        logging.error(f"Error saving custom prompts: {e}")
        return False
