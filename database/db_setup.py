import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db(db_name='insights.db'):
    """
    Initializes the SQLite database and creates the Posts table if it doesn't exist.

    Args:
        db_name: The name of the SQLite database file.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Posts (
                internal_post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                facebook_post_id TEXT UNIQUE,
                post_url TEXT UNIQUE,
                post_content_raw TEXT,
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
                last_ai_processing_at TIMESTAMP
            )
        ''')

        conn.commit()
        logging.info(f"Database '{db_name}' initialized and Posts table created or verified.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db() 