import csv
import json
import sqlite3
from typing import List, Dict
from database import crud

def fetch_data_for_export(conn: sqlite3.Connection, filters: Dict, entity: str = "posts") -> List[Dict]:
    """
    Fetches data from database based on filters and entity type.
    
    Args:
        conn: Database connection
        filters: Filter parameters for posts
        entity: Type of data to export (posts, comments, or all)
    
    Returns:
        List of dictionaries containing data for export
    """
    results = []
    if entity in ["posts", "all"]:
        posts = crud.get_all_categorized_posts(conn, filters)
        results.extend(posts)
    
    if entity in ["comments", "all"]:
        posts = crud.get_all_categorized_posts(conn, filters)
        for post in posts:
            comments = crud.get_comments_for_post(conn, post["internal_post_id"])
            results.extend(comments)
    
    return results

def export_to_csv(data: List[Dict], output_path: str):
    """
    Exports data to CSV file.
    
    Args:
        data: List of dictionaries to export
        output_path: Path to output CSV file
    """
    if not data:
        return
        
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def export_to_json(data: List[Dict], output_path: str):
    """
    Exports data to JSON file.
    
    Args:
        data: List of dictionaries to export
        output_path: Path to output JSON file
    """
    with open(output_path, "w", encoding="utf-8") as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)