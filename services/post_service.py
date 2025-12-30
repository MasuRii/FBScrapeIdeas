"""
Post Service Module

This module provides a service layer for retrieving and analyzing post data.
It encapsulates database queries related to viewing posts, comments, and statistics.
"""

import logging
from typing import Any, Dict, List, Optional

from database.crud import (
    get_all_categorized_posts,
    get_comments_for_post,
    get_db_connection,
    get_distinct_values,
)
from database.stats_queries import get_all_statistics

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class PostService:
    """
    Service class for retrieving and analyzing posts.

    This class provides methods to:
    - Retrieve filtered and categorized posts
    - Get comments for specific posts
    - Fetch distinct values for filtering
    - Generate database statistics
    """

    def __init__(self, db_name: str = "insights.db"):
        """
        Initialize the PostService.

        Args:
            db_name: Name of the database file (default: "insights.db")
        """
        self.db_name = db_name

    def get_filtered_posts(
        self,
        group_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve posts based on group ID and filters.

        Args:
            group_id: Optional ID of the group to filter by
            filters: Dictionary of filter criteria (category, dates, authors, etc.)
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries matching the criteria
        """
        if filters is None:
            filters = {}

        # Handle limit being passed in filters or as arg
        if limit is not None:
            filters["limit"] = limit

        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return []

            # Extract special filter fields if present
            filter_field = filters.pop("field", None)
            filter_value = filters.pop("value", None) if "value" in filters else None

            posts = get_all_categorized_posts(conn, group_id, filters, filter_field, filter_value)

            conn.close()
            return posts

        except Exception as e:
            logging.error(f"Error retrieving filtered posts: {e}")
            return []

    def get_post_comments(self, internal_post_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve comments for a specific post.

        Args:
            internal_post_id: The internal ID of the post

        Returns:
            List of comment dictionaries
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return []

            comments = get_comments_for_post(conn, internal_post_id)
            conn.close()
            return comments

        except Exception as e:
            logging.error(f"Error retrieving comments for post {internal_post_id}: {e}")
            return []

    def get_distinct_filter_values(self, field_name: str) -> List[str]:
        """
        Get distinct values for a specific field to populate filter options.

        Args:
            field_name: The database field name to query (e.g., 'ai_category')

        Returns:
            List of distinct string values
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return []

            values = get_distinct_values(conn, field_name)
            conn.close()
            return values

        except Exception as e:
            logging.error(f"Error retrieving distinct values for {field_name}: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the database.

        Returns:
            Dictionary containing various statistics (counts, averages, top authors)
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return {}

            stats = get_all_statistics(conn)
            conn.close()
            return stats

        except Exception as e:
            logging.error(f"Error generating statistics: {e}")
            return {}
