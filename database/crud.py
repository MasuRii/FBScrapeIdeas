import json
import logging
import sqlite3
import time
from typing import Union

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

ALLOWED_FILTER_FIELDS = {"ai_category", "post_author_name", "ai_is_potential_idea"}


def _get_db_path(db_name: str = "insights.db") -> str:
    """
    Get the database path using the centralized config function.
    Falls back to local db_name if config is not available.
    """
    try:
        from config import get_db_path as config_get_db_path

        return config_get_db_path(db_name)
    except ImportError:
        # Fallback if config module not available
        return db_name


def get_db_connection(db_name="insights.db"):
    """
    Creates and returns a connection to the SQLite database.
    Uses the platform-appropriate data directory via config.
    """
    db_path = _get_db_path(db_name)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraint enforcement
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None


def add_scraped_post(db_conn: sqlite3.Connection, post_data: dict, group_id: int) -> int | None:
    """
    Inserts a new scraped post into the database for a specific group.
    Avoids duplicates based on post_url.

    Args:
        db_conn: Database connection
        post_data: Dictionary containing post data
        group_id: ID of the group this post belongs to

    Returns:
        The internal_post_id if the post was successfully added or already existed,
        None otherwise.
    """
    sql = """
        INSERT OR IGNORE INTO Posts (
            group_id, facebook_post_id, post_url, post_content_raw, posted_at, scraped_at,
            post_author_name, post_author_profile_pic_url, post_image_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        cursor = db_conn.cursor()

        # Unify keys and handle fallbacks for different scraper formats
        p_url = post_data.get("post_url") or post_data.get("url")
        p_text = (
            post_data.get("text")
            or post_data.get("post_content_raw")
            or post_data.get("content_text")
        )
        p_ts = post_data.get("timestamp") or post_data.get("posted_at")
        p_author = post_data.get("author_name") or post_data.get("post_author_name")

        cursor.execute(
            sql,
            (
                group_id,
                post_data.get("facebook_post_id"),
                p_url,
                p_text,
                p_ts,
                int(time.time()),
                p_author,
                post_data.get("post_author_profile_pic_url"),
                post_data.get("post_image_url"),
            ),
        )
        db_conn.commit()
        if cursor.rowcount > 0:
            internal_post_id = cursor.lastrowid
            logging.info(f"Added new post: {p_url} with ID {internal_post_id}")
            return internal_post_id
        else:
            logging.info(f"Post already exists (ignored): {p_url}. Retrieving existing ID.")
            cursor.execute(
                "SELECT internal_post_id FROM Posts WHERE group_id = ? AND post_url = ?",
                (group_id, p_url),
            )
            existing_id = cursor.fetchone()
            if existing_id:
                return existing_id[0]
            return None
    except sqlite3.Error as e:
        logging.error(f"Error adding post {post_data.get('post_url') or post_data.get('url')}: {e}")
        db_conn.rollback()
        return None


def update_post_with_ai_results(db_conn: sqlite3.Connection, internal_post_id: int, ai_data: dict):
    """
    Updates an existing post with AI categorization results.
    """
    sql = """
        UPDATE Posts
        SET
            ai_category = ?,
            ai_sub_category = ?,
            ai_keywords = ?,
            ai_summary = ?,
            ai_is_potential_idea = ?,
            ai_reasoning = ?,
            ai_raw_response = ?,
            is_processed_by_ai = 1,
            last_ai_processing_at = ?
        WHERE internal_post_id = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            sql,
            (
                ai_data.get("ai_category"),
                ai_data.get("ai_sub_category"),
                json.dumps(ai_data.get("ai_keywords", [])),
                ai_data.get("ai_summary"),
                int(ai_data.get("ai_is_potential_idea", 0)),
                ai_data.get("ai_reasoning"),
                json.dumps(ai_data.get("ai_raw_response", {})),
                int(time.time()),
                internal_post_id,
            ),
        )
        db_conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Updated post {internal_post_id} with AI results.")
        else:
            logging.warning(f"Attempted to update non-existent post: {internal_post_id}")
    except sqlite3.Error as e:
        logging.error(f"Error updating post {internal_post_id}: {e}")
        db_conn.rollback()


def get_unprocessed_posts(db_conn: sqlite3.Connection, group_id: int | None) -> list[dict]:
    """
    Retrieves posts from a specific group that have not yet been processed by AI.

    Args:
        db_conn: Database connection
        group_id: ID of the group to get unprocessed posts from (if None, get from all groups)

    Returns:
        List of dictionaries containing post IDs and content
    """
    base_sql = """
        SELECT internal_post_id, post_content_raw
        FROM Posts
        WHERE is_processed_by_ai = 0 AND post_content_raw IS NOT NULL
    """
    params = []
    if group_id is not None:
        base_sql += " AND group_id = ?"
        params.append(group_id)

    try:
        cursor = db_conn.cursor()
        cursor.execute(base_sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving unprocessed posts: {e}")
        return []


def add_comments_for_post(
    db_conn: sqlite3.Connection, internal_post_id: int, comments_data: list[dict]
) -> bool:
    """
    Inserts a list of comments for a given post into the database.
    """
    if not comments_data:
        return True

    sql = """
        INSERT OR IGNORE INTO Comments (
            internal_post_id, commenter_name, commenter_profile_pic_url,
            comment_text, comment_facebook_id, comment_scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        cursor = db_conn.cursor()
        for comment in comments_data:
            cursor.execute(
                sql,
                (
                    internal_post_id,
                    comment.get("commenterName"),
                    comment.get("commenterProfilePic"),
                    comment.get("commentText"),
                    comment.get("commentFacebookId"),
                    int(time.time()),
                ),
            )
        db_conn.commit()
        logging.info(f"Added {len(comments_data)} comments for post {internal_post_id}.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error adding comments for post {internal_post_id}: {e}")
        db_conn.rollback()
        return False


def get_distinct_values(db_conn: sqlite3.Connection, field_name: str) -> list[str]:
    """
    Retrieves distinct non-null values from the specified field in the Posts table.

    Args:
        db_conn: Database connection
        field_name: The name of the field to get distinct values for

    Returns:
        List of distinct values for the given field.
    """
    # Robust identifier validation via parameterized mapping
    field_mapping = {
        "ai_category": "ai_category",
        "post_author_name": "post_author_name",
        "ai_is_potential_idea": "ai_is_potential_idea",
    }

    safe_field = field_mapping.get(field_name)
    if not safe_field:
        logging.warning(f"Field {field_name} is not allowed for distinct values retrieval.")
        return []

    try:
        cursor = db_conn.cursor()
        # Still uses f-string for column name but it's now from a trusted mapping, not raw input
        cursor.execute(f"SELECT DISTINCT {safe_field} FROM Posts WHERE {safe_field} IS NOT NULL")
        return [str(row[0]) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting distinct values for {field_name}: {e}")
        return []


def get_all_categorized_posts(
    db_conn: sqlite3.Connection,
    group_id: int | None,
    filters: dict,
    filter_field: str | None = None,
    filter_value: str | int | None = None,
) -> list[dict]:
    limit = filters.pop("limit", None) if filters else None
    """
    Retrieves all posts from a specific group that have been processed by AI, filtered by the provided criteria.

    Args:
        db_conn: Database connection object.
        group_id: ID of the group to get posts from (if None, get from all groups).
        filters: Dictionary of filters. Supported keys:
            category: filter by ai_category.
            start_date: filter by posted_at >= start_date.
            end_date: filter by posted_at <= end_date.
            post_author: filter by post_author_name (partial match).
            comment_author: filter by comment author (partial match, requires at least one matching comment).
            keyword: search in post content or comment text (partial match in either).
            min_comments: minimum number of comments on the post.
            max_comments: maximum number of comments on the post.
            is_idea: filter for posts marked as potential ideas (ai_is_potential_idea = 1).

    Returns:
        List of dictionaries representing posts that match all the filters.
    """
    base_query = """
        SELECT Posts.*,
            (SELECT COUNT(*) FROM Comments WHERE Comments.internal_post_id = Posts.internal_post_id) as comment_count
        FROM Posts
        LEFT JOIN Comments ON Posts.internal_post_id = Comments.internal_post_id
    """
    conditions = ["Posts.is_processed_by_ai = 1"]
    params = []

    if group_id is not None:
        conditions.append("Posts.group_id = ?")
        params.append(group_id)

    if filter_field and filter_value is not None:
        # Robust identifier validation via mapping
        field_mapping = {
            "ai_category": "ai_category",
            "post_author_name": "post_author_name",
            "ai_is_potential_idea": "ai_is_potential_idea",
        }

        safe_filter_field = field_mapping.get(filter_field)

        if not safe_filter_field:
            logging.warning(f"Field {filter_field} is not allowed for filtering.")
        else:
            if safe_filter_field == "ai_is_potential_idea":
                try:
                    filter_value = int(filter_value)
                except ValueError:
                    logging.error(f"Invalid value for boolean field {filter_field}: {filter_value}")
                    filter_value = None

            if filter_value is not None:
                conditions.append(f"Posts.{safe_filter_field} = ?")
                params.append(filter_value)

    if filters.get("start_date"):
        conditions.append("Posts.posted_at >= ?")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        conditions.append("Posts.posted_at <= ?")
        params.append(filters["end_date"])

    if filters.get("post_author"):
        conditions.append("Posts.post_author_name LIKE ?")
        params.append("%" + filters["post_author"] + "%")

    if filters.get("comment_author"):
        conditions.append("Comments.commenter_name LIKE ?")
        params.append("%" + filters["comment_author"] + "%")

    if filters.get("keyword"):
        keyword_pattern = "%" + filters["keyword"] + "%"
        conditions.append("(Posts.post_content_raw LIKE ? OR Comments.comment_text LIKE ?)")
        params.extend([keyword_pattern, keyword_pattern])

    if conditions:
        sql = base_query + " WHERE " + " AND ".join(conditions)
    else:
        sql = base_query

    sql += " GROUP BY Posts.internal_post_id"

    having_conditions = []
    if filters.get("min_comments") is not None:
        having_conditions.append("comment_count >= ?")
        params.append(filters["min_comments"])
    if filters.get("max_comments") is not None:
        having_conditions.append("comment_count <= ?")
        params.append(filters["max_comments"])

    if having_conditions:
        sql += " HAVING " + " AND ".join(having_conditions)

    if filters.get("is_idea"):
        if "is_idea" in filters and filters["is_idea"]:
            if "Posts.ai_is_potential_idea = 1" not in " AND ".join(conditions) and filters.get(
                "is_idea"
            ):
                conditions.append("Posts.ai_is_potential_idea = 1")
                sql = (
                    base_query
                    + " WHERE "
                    + " AND ".join(conditions)
                    + " GROUP BY Posts.internal_post_id"
                )
                if having_conditions:
                    sql += " HAVING " + " AND ".join(having_conditions)

    sql += " ORDER BY Posts.posted_at DESC"

    if limit and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)

    logging.debug(f"Executing SQL for get_all_categorized_posts: {sql} with params: {params}")

    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            post_dict = dict(row)
            if "ai_keywords" in post_dict and post_dict["ai_keywords"]:
                try:
                    post_dict["ai_keywords"] = json.loads(post_dict["ai_keywords"])
                except json.JSONDecodeError:
                    logging.warning(
                        f"Could not parse keywords JSON for post {post_dict.get('internal_post_id')}"
                    )
                    post_dict["ai_keywords"] = []
            else:
                post_dict["ai_keywords"] = []

            if "ai_raw_response" in post_dict and post_dict["ai_raw_response"]:
                try:
                    post_dict["ai_raw_response"] = json.loads(post_dict["ai_raw_response"])
                except json.JSONDecodeError:
                    logging.warning(
                        f"Could not parse raw response JSON for post {post_dict.get('internal_post_id')}"
                    )
                    pass
            post_dict["ai_is_potential_idea"] = bool(post_dict.get("ai_is_potential_idea", 0))

            results.append(post_dict)
        return results
    except sqlite3.Error as e:
        logging.error(f"Error retrieving categorized posts: {e}")
        return []


def get_comments_for_post(db_conn: sqlite3.Connection, internal_post_id: int) -> list[dict]:
    """
    Retrieves all comments for a given post.
    """
    sql = """
        SELECT *
        FROM Comments
        WHERE internal_post_id = ?
        ORDER BY comment_scraped_at ASC
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (internal_post_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving comments for post {internal_post_id}: {e}")
        return []


def get_unprocessed_comments(db_conn: sqlite3.Connection) -> list[dict]:
    """
    Retrieves comments that have not yet been processed by AI for comment analysis.
    Returns list of dictionaries containing comment_id and comment_text.
    """
    sql = """
        SELECT comment_id, comment_text
        FROM Comments
        WHERE is_processed_by_ai_comment = 0 AND comment_text IS NOT NULL
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving unprocessed comments: {e}")
        return []


def update_comment_with_ai_results(db_conn: sqlite3.Connection, comment_id: int, ai_data: dict):
    """
    Updates a comment record with AI analysis results.
    Sets is_processed_by_ai_comment = 1 and updates processing timestamp.
    """
    sql = """
        UPDATE Comments
        SET
            ai_comment_category = ?,
            ai_comment_sentiment = ?,
            ai_comment_keywords = ?,
            ai_comment_raw_response = ?,
            is_processed_by_ai_comment = 1,
            last_ai_processing_at_comment = ?
        WHERE comment_id = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            sql,
            (
                ai_data.get("ai_comment_category"),
                ai_data.get("ai_comment_sentiment"),
                json.dumps(ai_data.get("ai_comment_keywords", [])),
                json.dumps(ai_data.get("ai_comment_raw_response", {})),
                int(time.time()),
                comment_id,
            ),
        )
        db_conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Updated comment {comment_id} with AI results.")
        else:
            logging.warning(f"Attempted to update non-existent comment: {comment_id}")
    except sqlite3.Error as e:
        logging.error(f"Error updating comment {comment_id}: {e}")
        db_conn.rollback()


def add_group(db_conn: sqlite3.Connection, name: str, url: str) -> int | None:
    """
    Creates a new group record in the database.

    Args:
        db_conn: Database connection
        name: Name of the group
        url: URL of the Facebook group

    Returns:
        The group_id if successful, None otherwise.
    """
    sql = """
        INSERT INTO Groups (group_name, group_url)
        VALUES (?, ?)
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (name, url))
        db_conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error adding group {name}: {e}")
        db_conn.rollback()
        return None


def get_group_by_id(db_conn: sqlite3.Connection, group_id: int) -> dict | None:
    """
    Retrieves a group by its ID.
    """
    sql = """
        SELECT * FROM Groups WHERE group_id = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (group_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving group {group_id}: {e}")
        return None


def get_group_by_name(db_conn: sqlite3.Connection, name: str) -> dict | None:
    """
    Retrieves a group by its name (case-sensitive exact match).
    """
    sql = """
        SELECT * FROM Groups WHERE group_name = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving group by name {name}: {e}")
        return None


def get_group_by_url(db_conn: sqlite3.Connection, url: str) -> dict | None:
    """
    Retrieves a group by its URL (case-sensitive exact match).
    """
    sql = """
        SELECT * FROM Groups WHERE group_url = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (url,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving group by URL {url}: {e}")
        return None


def list_groups(db_conn: sqlite3.Connection) -> list[dict]:
    """
    Retrieves all groups from the database.
    """
    sql = """
        SELECT * FROM Groups ORDER BY group_name
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error listing groups: {e}")
        return []


def remove_group(db_conn: sqlite3.Connection, group_id: int) -> bool:
    """
    Deletes a group and all its associated posts (via cascading delete).

    Args:
        db_conn: Database connection
        group_id: ID of the group to remove

    Returns:
        True if deleted successfully, False otherwise
    """
    sql = """
        DELETE FROM Groups WHERE group_id = ?
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (group_id,))
        db_conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error removing group {group_id}: {e}")
        db_conn.rollback()
        return False


if __name__ == "__main__":
    from db_setup import init_db

    init_db()
    conn = get_db_connection()
    if conn:
        conn.execute(
            "INSERT INTO Groups (group_name, group_url) VALUES (?, ?)",
            ("Test Group", "http://example.com/group/test"),
        )
        conn.commit()
        cursor = conn.cursor()
        cursor.execute("SELECT group_id FROM Groups WHERE group_name = 'Test Group'")
        group_id = cursor.fetchone()[0]

        test_post = {
            "facebook_post_id": "test_fb_id_1",
            "post_url": "http://example.com/post/1",
            "content_text": "This is a test post content.",
            "posted_at": "2023-01-01 10:00:00",
            "post_author_name": "Test Author",
            "post_author_profile_pic_url": "http://example.com/author_pic.jpg",
            "post_image_url": "http://example.com/post_image.jpg",
        }
        post_id = add_scraped_post(conn, test_post, group_id)
        logging.info(f"Adding test post, returned ID: {post_id}")

        cursor = conn.cursor()
        cursor.execute("SELECT internal_post_id FROM Posts WHERE facebook_post_id = 'test_fb_id_1'")
        post_id = cursor.fetchone()[0]

        test_comments = [
            {
                "commenterName": "Commenter 1",
                "commenterProfilePic": "http://example.com/commenter1.jpg",
                "commentText": "This is the first comment.",
                "commentFacebookId": "comment_fb_id_1",
            },
            {
                "commenterName": "Commenter 2",
                "commenterProfilePic": "http://example.com/commenter2.jpg",
                "commentText": "This is the second comment.",
                "commentFacebookId": "comment_fb_id_2",
            },
        ]
        logging.info(f"Adding test comments: {add_comments_for_post(conn, post_id, test_comments)}")

        unprocessed = get_unprocessed_posts(conn, group_id)
        logging.info(f"Unprocessed posts: {unprocessed}")

        ai_data = {
            "ai_category": "Project Idea",
            "ai_sub_category": "Software",
            "ai_keywords": ["test", "project", "idea"],
            "ai_summary": "A summary of the test project idea.",
            "ai_is_potential_idea": True,
            "ai_reasoning": "Based on keywords.",
            "ai_raw_response": {"gemini_response": "raw json"},
        }
        logging.info(
            f"Updating post with AI results: {update_post_with_ai_results(conn, post_id, ai_data)}"
        )

        categorized = get_all_categorized_posts(conn, group_id, {})
        logging.info(f"All categorized posts: {categorized}")
        categorized_filtered = get_all_categorized_posts(
            conn, group_id, {"category": "Project Idea"}
        )
        logging.info(f"Filtered categorized posts: {categorized_filtered}")

        comments = get_comments_for_post(conn, post_id)
        logging.info(f"Comments for post {post_id}: {comments}")

        conn.close()
