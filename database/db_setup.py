import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db(db_name='insights.db'):
    """
    Initializes the SQLite database and creates required tables if they don't exist.
    Now supports multiple Facebook groups with Groups table.

    Args:
        db_name: The name of the SQLite database file.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Enable foreign key constraint enforcement
        cursor.execute('PRAGMA foreign_keys = ON')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT UNIQUE NOT NULL,
                group_url TEXT UNIQUE NOT NULL,
                last_scraped_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Posts (
                internal_post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                facebook_post_id TEXT UNIQUE,
                post_url TEXT UNIQUE,
                post_content_raw TEXT,
                post_author_name TEXT,
                post_author_profile_pic_url TEXT,
                post_image_url TEXT,
                posted_at TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_category TEXT,
                ai_sub_category TEXT,
                ai_keywords TEXT, -- Storing as JSON string
                ai_summary TEXT,
                ai_is_potential_idea INTEGER DEFAULT 0, -- 0 for False, 1 for True
                ai_reasoning TEXT,
                ai_raw_response TEXT, -- Storing as JSON string
                is_processed_by_ai INTEGER DEFAULT 0, -- 0 for False, 1 for True
                last_ai_processing_at TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES Groups(group_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_post_id INTEGER,
                commenter_name TEXT,
                commenter_profile_pic_url TEXT,
                comment_text TEXT,
                comment_facebook_id TEXT UNIQUE,
                comment_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_comment_category TEXT,
                ai_comment_sentiment TEXT,
                ai_comment_keywords TEXT,
                ai_comment_raw_response TEXT,
                is_processed_by_ai_comment INTEGER DEFAULT 0,
                last_ai_processing_at_comment TIMESTAMP,
                FOREIGN KEY (internal_post_id) REFERENCES Posts(internal_post_id)
            )
        ''')

        conn.commit()
        logging.info(f"Database '{db_name}' initialized with Groups and Posts tables created or verified.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db() 