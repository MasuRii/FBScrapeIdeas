import dateparser
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_fb_timestamp(timestamp_str: str) -> datetime:
    """
    Parse Facebook's relative or absolute timestamp string into UTC datetime.
    
    Args:
        timestamp_str: The timestamp string from Facebook (e.g., "2 hrs ago", "Yesterday at 5:00 PM")
    
    Returns:
        datetime: Parsed datetime in UTC timezone, or None if parsing fails
    """
    try:
        parsed = dateparser.parse(
            timestamp_str,
            settings={
                'TIMEZONE': 'UTC',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'RELATIVE_BASE': datetime.utcnow()
            }
        )
        
        if not parsed:
            raise ValueError(f"Unable to parse timestamp: {timestamp_str}")
            
        return parsed
        
    except Exception as e:
        logger.warning(f"Timestamp parsing error: {e} for input: {timestamp_str}")
        return None