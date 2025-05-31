import csv
import json
import sqlite3
import logging
import os
from pathlib import Path
from typing import List, Dict, Tuple
from database import crud

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_output_paths(base_path: str, file_format: str = 'csv') -> Dict[str, str]:
    """
    Generate appropriate output paths for all data types.
    
    Args:
        base_path: Original output path provided by user
        file_format: Export format (csv/json)
    
    Returns:
        Dictionary mapping data types to their absolute file paths
    """
    abs_path = os.path.abspath(base_path)
    
    if not os.path.isdir(abs_path) and os.path.splitext(os.path.basename(abs_path))[0]:
        base_dir = os.path.dirname(abs_path)
        filename = os.path.splitext(os.path.basename(abs_path))[0]
    else:
        base_dir = abs_path
        filename = 'fbdata'
    
    ext = f".{file_format}"
    paths = {
        'posts': os.path.join(base_dir, f"{filename}_posts{ext}"),
        'comments': os.path.join(base_dir, f"{filename}_comments{ext}"),
        'groups': os.path.join(base_dir, f"{filename}_groups{ext}"),
        'combined': os.path.join(base_dir, f"{filename}_all{ext}")
    }
    
    logging.info(f"Generated export paths:")
    for data_type, file_path in paths.items():
        logging.info(f"  {data_type}: {file_path}")
    
    return paths

def ensure_dir_exists(file_path: str) -> None:
    """Creates directory path if it doesn't exist.
    Args:
        file_path: Path to file where data will be exported
    """
    output_dir = os.path.dirname(os.path.abspath(file_path))
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create directory {output_dir}: {e}")
        raise

def fetch_data_for_export(conn: sqlite3.Connection, filters: Dict, entity: str = "posts") -> Dict[str, List[Dict]]:
    """
    Fetches data from database based on filters and entity type.

    Args:
        conn: Database connection
        filters: Filter parameters for posts
        entity: Type of data to export (posts, comments, groups, or all)

    Returns:
        Dictionary containing lists of posts, comments, groups, and combined data
    """
    result = {
        'posts': [],
        'comments': [],
        'groups': [],
        'combined': []
    }
    
    try:
        if entity in ["groups", "all"]:
            result['groups'] = crud.list_groups(conn)
            result['combined'].extend(result['groups'])
        
        if entity in ["posts", "all"]:
            result['posts'] = crud.get_all_categorized_posts(conn, None, filters)
            result['combined'].extend(result['posts'])
        
        if entity in ["comments", "all"]:
            fetched_posts = crud.get_all_categorized_posts(conn, None, filters)
            for post in fetched_posts:
                comments = crud.get_comments_for_post(conn, post["internal_post_id"])
                result['comments'].extend(comments)
                result['combined'].extend(comments)
                
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return {'posts': [], 'comments': [], 'groups': [], 'combined': []}
    
    return result

def normalize_records(records: List[Dict], record_type: str) -> Tuple[List[Dict], List[str]]:
    """
    Normalizes records to have consistent fields and returns fieldnames.
    
    Args:
        records: List of dictionaries with potentially different fields
        record_type: Type of records ('posts', 'comments', 'groups', 'combined')
        
    Returns:
        Tuple of (normalized records list, fieldnames list)
    """
    if not records:
        return [], []

    ESSENTIAL_FIELDS = {
        'posts': ['post_url', 'post_author_name', 'post_content_raw', 'posted_at', 'ai_category'],
        'comments': ['comment_id', 'commenter_name', 'comment_text'],
        'groups': ['group_id', 'group_name', 'group_url'],
        'combined': ['record_type', 'id', 'author', 'content', 'timestamp', 'category']
    }
    
    if record_type == 'combined':
        normalized = []
        for record in records:
            if 'post_content_raw' in record:
                normalized_record = {
                    'record_type': 'post',
                    'id': record.get('internal_post_id'),
                    'author': record.get('post_author_name'),
                    'content': record.get('post_content_raw'),
                    'timestamp': record.get('posted_at'),
                    'category': record.get('ai_category'),
                    'url': record.get('post_url')
                }
            elif 'comment_text' in record:
                normalized_record = {
                    'record_type': 'comment',
                    'id': record.get('comment_id'),
                    'author': record.get('commenter_name'),
                    'content': record.get('comment_text'),
                    'timestamp': record.get('commented_at'),
                    'post_id': record.get('post_id')
                }
            elif 'group_url' in record:
                normalized_record = {
                    'record_type': 'group',
                    'id': record.get('group_id'),
                    'name': record.get('group_name'),
                    'url': record.get('group_url')
                }
            else:
                continue
            normalized.append(normalized_record)
        
        fieldnames = ['record_type', 'id', 'author', 'content', 'timestamp', 'category', 'url', 'post_id', 'name']
        return normalized, fieldnames
        
    else:
        essential = set(ESSENTIAL_FIELDS.get(record_type, []))
        optional = set()
        for record in records:
            optional.update(record.keys())
        
        fieldnames = list(essential) + sorted(list(optional - essential))
        
        normalized = []
        for record in records:
            normalized_record = {field: record.get(field) for field in fieldnames}
            normalized.append(normalized_record)
            
        return normalized, fieldnames

def write_data_file(records: List[Dict], file_path: str, data_type: str, format_type: str,
                    normalize_fn=None, **kwargs) -> None:
    """Helper function to write data to a file with proper error handling and logging.
    
    Args:
        records: List of records to write
        file_path: Path to output file
        data_type: Type of data being written ('posts', 'comments', etc.)
        format_type: Format being written ('CSV' or 'JSON')
        normalize_fn: Optional function to normalize records before writing
        **kwargs: Additional arguments for specific format writers
    """
    if not records:
        return
        
    abs_path = os.path.abspath(file_path)
    try:
        logging.info(f"Attempting to export {len(records)} {data_type} to {abs_path}")
        
        if normalize_fn:
            records, fieldnames = normalize_fn(records, data_type)
            kwargs['fieldnames'] = fieldnames
            
        open_args = kwargs.pop('open_args', {})
        with open(abs_path, "w", encoding="utf-8", **open_args) as f:
            if format_type == 'CSV':
                writer = csv.DictWriter(f, **kwargs)
                writer.writeheader()
                writer.writerows(records)
            else:
                json.dump(records, f, ensure_ascii=False, indent=4)
                
        logging.info(f"Successfully exported {len(records)} {data_type} to {abs_path}")
    except Exception as e:
        logging.error(f"Failed to write {data_type} {format_type} file: {e}")
        raise

def export_to_csv(data: Dict[str, List[Dict]], output_path: str):
    """
    Exports data to separate CSV files for each table and a combined file.
    
    Args:
        data: Dictionary containing lists of posts, comments, groups and combined data
        output_path: Base path for output files
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    paths = get_output_paths(output_path, 'csv')
    
    base_dir = os.path.dirname(os.path.abspath(list(paths.values())[0]))
    try:
        ensure_base_dir(base_dir)
    except Exception as e:
        logging.error(f"Failed to create/verify export directory: {e}")
        raise

    for data_type, file_path in paths.items():
        write_data_file(
            records=data[data_type],
            file_path=file_path,
            data_type=data_type,
            format_type='CSV',
            normalize_fn=normalize_records,
            open_args={'newline': ''}
        )

def ensure_base_dir(base_path: str) -> None:
    """Create base directory if it doesn't exist and verify it's writable.
    
    Args:
        base_path: Path to create/verify
        
    Raises:
        OSError: If directory creation fails or path is not writable
    """
    os.makedirs(base_path, exist_ok=True)
    
    if not os.access(base_path, os.W_OK):
        raise OSError(f"Directory not writable: {base_path}")
    
    logging.info(f"Using export directory: {base_path}")

def export_to_json(data: Dict[str, List[Dict]], output_path: str):
    """
    Exports data to separate JSON files for each table and a combined file.
    
    Args:
        data: Dictionary containing lists of posts, comments, groups and combined data
        output_path: Base path for output files
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    paths = get_output_paths(output_path, 'json')
    
    base_dir = os.path.dirname(os.path.abspath(list(paths.values())[0]))
    try:
        ensure_base_dir(base_dir)
    except Exception as e:
        logging.error(f"Failed to create/verify export directory: {e}")
        raise

    for data_type, file_path in paths.items():
        write_data_file(
            records=data[data_type],
            file_path=file_path,
            data_type=data_type,
            format_type='JSON',
            normalize_fn=normalize_records
        )