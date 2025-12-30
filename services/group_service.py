"""
Group Service Module

This module provides a service layer for managing Facebook groups.
It wraps raw database operations and provides a clean interface for group management.
"""

import logging
from typing import Any, Dict, List, Optional

from database.crud import get_db_connection, add_group, get_group_by_id, list_groups

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class GroupService:
    """
    Service class for managing Facebook groups.

    This class encapsulates business logic for group operations and provides
    a clean abstraction over the database layer.
    """

    def __init__(self, db_name: str = "insights.db"):
        """
        Initialize the GroupService.

        Args:
            db_name: Name of the database file (default: "insights.db")
        """
        self.db_name = db_name

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """
        Retrieve all groups from the database.

        Returns:
            List of dictionaries, each representing a group with keys:
            - group_id: Unique identifier for the group
            - group_name: Name of the group
            - group_url: URL of the Facebook group
            - created_at: Timestamp when the group was added
            Returns empty list if no groups found or on error.
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return []

            groups = list_groups(conn)
            conn.close()
            logging.info(f"Retrieved {len(groups)} groups")
            return groups

        except Exception as e:
            logging.error(f"Error retrieving all groups: {e}")
            return []

    def add_group(self, url: str, name: str) -> Optional[int]:
        """
        Add a new Facebook group to the database.

        Args:
            url: URL of the Facebook group
            name: Name of the group

        Returns:
            The ID of the newly created group, or None if the operation failed.
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return None

            group_id = add_group(conn, name, url)
            conn.close()

            if group_id:
                logging.info(f"Successfully added group '{name}' with ID {group_id}")
            else:
                logging.error(f"Failed to add group '{name}'")

            return group_id

        except Exception as e:
            logging.error(f"Error adding group '{name}': {e}")
            return None

    def get_group_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific group by its ID.

        Args:
            group_id: Unique identifier of the group

        Returns:
            Dictionary containing group details with keys:
            - group_id: Unique identifier for the group
            - group_name: Name of the group
            - group_url: URL of the Facebook group
            - created_at: Timestamp when the group was added
            Returns None if group not found or on error.
        """
        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return None

            group = get_group_by_id(conn, group_id)
            conn.close()

            if group:
                logging.info(f"Retrieved group with ID {group_id}")
            else:
                logging.warning(f"Group with ID {group_id} not found")

            return group

        except Exception as e:
            logging.error(f"Error retrieving group {group_id}: {e}")
            return None

    def remove_group(self, group_id: int) -> bool:
        """
        Remove a group and all its associated posts/comments.

        Args:
            group_id: ID of the group to remove

        Returns:
            True if the group was successfully removed, False otherwise.
        """
        from database.crud import remove_group

        try:
            conn = get_db_connection(self.db_name)
            if not conn:
                logging.error("Failed to connect to database")
                return False

            result = remove_group(conn, group_id)
            conn.close()

            if result:
                logging.info(f"Successfully removed group with ID {group_id}")
            else:
                logging.error(f"Failed to remove group with ID {group_id}")

            return result

        except Exception as e:
            logging.error(f"Error removing group {group_id}: {e}")
            return False
