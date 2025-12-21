import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_total_posts(conn: sqlite3.Connection) -> int:
    """Get total number of posts in database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Posts;")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Error getting total posts: {e}")
        return 0

def get_posts_per_category(conn: sqlite3.Connection) -> list:
    """Get post count per AI category."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ai_category, COUNT(*) 
            FROM Posts 
            GROUP BY ai_category
            ORDER BY COUNT(*) DESC;
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Error getting posts per category: {e}")
        return []

def get_unprocessed_posts_count(conn: sqlite3.Connection) -> int:
    """Get count of unprocessed posts."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Posts WHERE is_processed_by_ai = 0;")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Error getting unprocessed posts count: {e}")
        return 0

def get_total_comments(conn: sqlite3.Connection) -> int:
    """Get total number of comments."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Comments;")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Error getting total comments: {e}")
        return 0

def get_avg_comments_per_post(conn: sqlite3.Connection) -> float:
    """Calculate average comments per post."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(comment_count)
            FROM (
                SELECT COUNT(comment_id) AS comment_count
                FROM Comments
                GROUP BY internal_post_id
            );
        """)
        result = cursor.fetchone()[0]
        return round(result, 2) if result is not None else 0.0
    except sqlite3.Error as e:
        logging.error(f"Error calculating average comments per post: {e}")
        return 0.0

def get_top_authors(conn: sqlite3.Connection, limit: int = 5) -> list:
    """Get top authors by post count."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT post_author_name, COUNT(*) as post_count 
            FROM Posts 
            GROUP BY post_author_name 
            ORDER BY post_count DESC 
            LIMIT ?;
        """, (limit,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Error getting top authors: {e}")
        return []

def get_all_statistics(conn: sqlite3.Connection) -> dict:
    """Get all statistics in a single dictionary."""
    try:
        return {
            'total_posts': get_total_posts(conn),
            'posts_per_category': get_posts_per_category(conn),
            'unprocessed_posts': get_unprocessed_posts_count(conn),
            'total_comments': get_total_comments(conn),
            'avg_comments_per_post': get_avg_comments_per_post(conn),
            'top_authors': get_top_authors(conn)
        }
    except Exception as e:
        logging.error(f"Error getting all statistics: {e}")
        return {}
