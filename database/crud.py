import sqlite3
import json
import time
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection(db_name='insights.db'):
    """
    Creates and returns a connection to the SQLite database.
    """
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def add_scraped_post(db_conn: sqlite3.Connection, post_data: Dict):
    """
    Inserts a new scraped post into the database.
    Avoids duplicates based on post_url.
    """
    sql = '''
        INSERT OR IGNORE INTO Posts (
            facebook_post_id, post_url, post_content_raw, posted_at, scraped_at
        ) VALUES (?, ?, ?, ?, ?)
    '''
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (
            post_data.get('facebook_post_id'),
            post_data.get('post_url'),
            post_data.get('post_content_raw'),
            post_data.get('posted_at'),
            int(time.time())
        ))
        db_conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Added new post: {post_data.get('post_url')}")
        else:
            logging.info(f"Post already exists (ignored): {post_data.get('post_url')}")
    except sqlite3.Error as e:
        logging.error(f"Error adding post {post_data.get('post_url')}: {e}")
        db_conn.rollback()

def update_post_with_ai_results(db_conn: sqlite3.Connection, internal_post_id: int, ai_data: Dict):
    """
    Updates an existing post with AI categorization results.
    """
    sql = '''
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
    '''
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, (
            ai_data.get('ai_category'),
            ai_data.get('ai_sub_category'),
            ai_data.get('ai_keywords'),
            ai_data.get('ai_summary'),
            ai_data.get('ai_is_potential_idea'),
            ai_data.get('ai_reasoning'),
            ai_data.get('ai_raw_response'),
            int(time.time()),
            internal_post_id
        ))
        db_conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Updated post {internal_post_id} with AI results.")
        else:
             logging.warning(f"Attempted to update non-existent post: {internal_post_id}")
    except sqlite3.Error as e:
        logging.error(f"Error updating post {internal_post_id}: {e}")
        db_conn.rollback()

def get_unprocessed_posts(db_conn: sqlite3.Connection) -> List[Dict]:
    """
    Retrieves posts that have not yet been processed by AI.
    """
    sql = '''
        SELECT internal_post_id, post_content_raw
        FROM Posts
        WHERE is_processed_by_ai = 0
    '''
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error retrieving unprocessed posts: {e}")
        return []

def get_all_categorized_posts(db_conn: sqlite3.Connection, category_filter: Optional[str] = None) -> List[Dict]:
    """
    Retrieves all posts that have been processed by AI, optionally filtered by category.
    """
    sql = '''
        SELECT *
        FROM Posts
        WHERE is_processed_by_ai = 1
    '''
    params = []
    if category_filter:
        sql += " AND ai_category = ?"
        params.append(category_filter)

    sql += " ORDER BY posted_at DESC"

    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            post_dict = dict(row)
            if 'ai_keywords' in post_dict and post_dict['ai_keywords']:
                try:
                    post_dict['ai_keywords'] = json.loads(post_dict['ai_keywords'])
                except json.JSONDecodeError:
                    logging.warning(f"Could not parse keywords JSON for post {post_dict.get('internal_post_id')}")
                    post_dict['ai_keywords'] = []
            else:
                 post_dict['ai_keywords'] = []

            if 'ai_raw_response' in post_dict and post_dict['ai_raw_response']:
                 try:
                     post_dict['ai_raw_response'] = json.loads(post_dict['ai_raw_response'])
                 except json.JSONDecodeError:
                     logging.warning(f"Could not parse raw response JSON for post {post_dict.get('internal_post_id')}")
                     pass
            post_dict['ai_is_potential_idea'] = bool(post_dict.get('ai_is_potential_idea', 0))

            results.append(post_dict)
        return results
    except sqlite3.Error as e:
        logging.error(f"Error retrieving categorized posts: {e}")
        return []

if __name__ == '__main__':






    pass 