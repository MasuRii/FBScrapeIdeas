"""
AI Service Module

This module provides a service layer for AI processing of posts and comments.
It encapsulates the business logic for orchestrating AI operations and provides
a clean abstraction over the AI providers and database operations.
"""

import logging
from typing import Any, Dict, List, Optional

from ai.gemini_service import create_post_batches
from ai.provider_factory import get_ai_provider
from database.crud import (
    get_db_connection,
    get_unprocessed_posts,
    get_unprocessed_comments,
    update_post_with_ai_results,
    update_comment_with_ai_results,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class AIService:
    """
    Service class for managing AI processing of posts and comments.

    This class encapsulates business logic for AI operations including:
    - Provider initialization and management
    - Fetching unprocessed posts/comments from database
    - Batching and processing content with AI
    - Updating database with AI results
    """

    def __init__(self, db_name: str = "insights.db"):
        """
        Initialize the AIService.

        Args:
            db_name: Name of the database file (default: "insights.db")
        """
        self.db_name = db_name
        self._provider = None

    def _get_provider(self, provider_type: Optional[str] = None) -> Any:
        """
        Get or create the AI provider instance.

        Args:
            provider_type: Optional provider type ('gemini' or 'openai').
                          If None, uses default from config.

        Returns:
            An AIProvider instance.

        Raises:
            ValueError: If provider initialization fails.
        """
        if self._provider is None:
            try:
                self._provider = get_ai_provider(provider_type=provider_type)
                logging.info(
                    f"Initialized AI provider: {self._provider.provider_name} "
                    f"({self._provider.get_model_name()})"
                )
            except Exception as e:
                logging.error(f"Failed to initialize AI provider: {e}")
                raise ValueError(f"Provider initialization failed: {e}")

        return self._provider

    async def process_pending_posts(
        self,
        limit: Optional[int] = None,
        provider_type: Optional[str] = None,
        group_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process pending (unprocessed) posts with AI.

        Fetches unprocessed posts from the database, batches them, sends to AI
        for analysis, and updates the database with results.

        Args:
            limit: Maximum number of posts to process. If None, processes all unprocessed posts.
            provider_type: Type of provider ('gemini' or 'openai'). If None, uses default from config.
            group_id: Optional group ID to filter posts. If None, processes posts from all groups.

        Returns:
            Dictionary with processing statistics:
            - total_posts: Total unprocessed posts found
            - processed: Number of posts successfully processed
            - batches: Number of batches processed
            - errors: Number of errors encountered

        Raises:
            ValueError: If provider initialization fails.
            Exception: If database connection fails.
        """
        stats = {
            "total_posts": 0,
            "processed": 0,
            "batches": 0,
            "errors": 0,
        }

        conn = None
        try:
            # Initialize AI provider
            ai_provider = self._get_provider(provider_type)

            # Connect to database
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                raise Exception("Database connection failed")

            # Fetch unprocessed posts
            unprocessed_posts = get_unprocessed_posts(conn, group_id)

            if not unprocessed_posts:
                logging.info("No unprocessed posts found in the database.")
                return stats

            stats["total_posts"] = len(unprocessed_posts)

            # Apply limit if specified
            if limit and limit < len(unprocessed_posts):
                unprocessed_posts = unprocessed_posts[:limit]
                logging.info(f"Processing {limit} posts (limited from {stats['total_posts']})")
            else:
                logging.info(f"Found {len(unprocessed_posts)} unprocessed posts to process")

            # Log sample of posts
            for i, post in enumerate(unprocessed_posts[:5]):
                logging.debug(
                    f"  Post {i + 1}: ID={post.get('internal_post_id')}, "
                    f"content_length={len(post.get('post_content_raw', ''))}"
                )

            # Create batches
            logging.info("Creating batches for AI processing...")
            post_batches = create_post_batches(unprocessed_posts)
            logging.info(f"Created {len(post_batches)} batches")

            # Process each batch
            for i, batch in enumerate(post_batches):
                logging.info(
                    f"Processing batch {i + 1}/{len(post_batches)} with {len(batch)} posts..."
                )

                try:
                    # Analyze batch with AI
                    ai_results = await ai_provider.analyze_posts_batch(batch)

                    if ai_results:
                        logging.info(f"Received {len(ai_results)} AI results for batch {i + 1}")

                        # Update database with results
                        for result in ai_results:
                            internal_post_id = result.get("internal_post_id")
                            if internal_post_id is not None:
                                try:
                                    update_post_with_ai_results(conn, internal_post_id, result)
                                    stats["processed"] += 1
                                    logging.debug(f"Successfully updated post {internal_post_id}")
                                except Exception as db_e:
                                    logging.error(f"Error updating post {internal_post_id}: {db_e}")
                                    stats["errors"] += 1
                            else:
                                logging.error(f"AI result missing 'internal_post_id': {result}")
                                stats["errors"] += 1
                    else:
                        logging.warning(f"No AI results returned for batch {i + 1}")
                        stats["errors"] += len(batch)

                    stats["batches"] += 1

                except Exception as batch_e:
                    logging.error(f"Error processing batch {i + 1}: {batch_e}")
                    stats["errors"] += len(batch)

            # Log summary
            logging.info(
                f"AI processing complete. "
                f"Processed: {stats['processed']}/{stats['total_posts']}, "
                f"Batches: {stats['batches']}, "
                f"Errors: {stats['errors']}"
            )

            return stats

        except Exception as e:
            logging.error(f"Error in process_pending_posts: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    async def process_pending_comments(
        self, limit: Optional[int] = None, provider_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process pending (unprocessed) comments with AI.

        Fetches unprocessed comments from the database, batches them, sends to AI
        for analysis, and updates the database with results.

        Args:
            limit: Maximum number of comments to process. If None, processes all unprocessed comments.
            provider_type: Type of provider ('gemini' or 'openai'). If None, uses default from config.

        Returns:
            Dictionary with processing statistics:
            - total_comments: Total unprocessed comments found
            - processed: Number of comments successfully processed
            - batches: Number of batches processed
            - errors: Number of errors encountered

        Raises:
            ValueError: If provider initialization fails.
            Exception: If database connection fails.
        """
        stats = {
            "total_comments": 0,
            "processed": 0,
            "batches": 0,
            "errors": 0,
        }

        conn = None
        try:
            # Initialize AI provider
            ai_provider = self._get_provider(provider_type)

            # Connect to database
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                raise Exception("Database connection failed")

            # Fetch unprocessed comments
            unprocessed_comments = get_unprocessed_comments(conn)

            if not unprocessed_comments:
                logging.info("No unprocessed comments found in the database.")
                return stats

            stats["total_comments"] = len(unprocessed_comments)

            # Apply limit if specified
            if limit and limit < len(unprocessed_comments):
                unprocessed_comments = unprocessed_comments[:limit]
                logging.info(
                    f"Processing {limit} comments (limited from {stats['total_comments']})"
                )
            else:
                logging.info(f"Found {len(unprocessed_comments)} unprocessed comments to process")

            # Create batches (fixed size for comments)
            batch_size = 5
            comment_batches = [
                unprocessed_comments[i : i + batch_size]
                for i in range(0, len(unprocessed_comments), batch_size)
            ]

            logging.info(f"Created {len(comment_batches)} batches")

            # Process each batch
            for i, batch in enumerate(comment_batches):
                logging.info(
                    f"Processing comment batch {i + 1}/{len(comment_batches)} "
                    f"with {len(batch)} comments..."
                )

                try:
                    # Analyze batch with AI
                    ai_results = ai_provider.analyze_comments_batch(batch)

                    if ai_results:
                        logging.info(
                            f"Received {len(ai_results)} AI results for comment batch {i + 1}"
                        )

                        # Update database with results
                        for result in ai_results:
                            comment_id = result.get("comment_id")
                            if comment_id is not None:
                                try:
                                    update_comment_with_ai_results(conn, comment_id, result)
                                    stats["processed"] += 1
                                    logging.debug(f"Successfully updated comment {comment_id}")
                                except Exception as db_e:
                                    logging.error(f"Error updating comment {comment_id}: {db_e}")
                                    stats["errors"] += 1
                            else:
                                logging.error(f"AI result missing 'comment_id': {result}")
                                stats["errors"] += 1
                    else:
                        logging.warning(f"No AI results returned for comment batch {i + 1}")
                        stats["errors"] += len(batch)

                    stats["batches"] += 1

                except Exception as batch_e:
                    logging.error(f"Error processing comment batch {i + 1}: {batch_e}")
                    stats["errors"] += len(batch)

            # Log summary
            logging.info(
                f"Comment AI processing complete. "
                f"Processed: {stats['processed']}/{stats['total_comments']}, "
                f"Batches: {stats['batches']}, "
                f"Errors: {stats['errors']}"
            )

            return stats

        except Exception as e:
            logging.error(f"Error in process_pending_comments: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
