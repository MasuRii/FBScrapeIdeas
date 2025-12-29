import logging
from datetime import UTC, datetime, timezone

import dateparser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_fb_timestamp(timestamp_str: str) -> datetime | None:
    """
    Parse Facebook's relative or absolute timestamp string into UTC datetime.

    Args:
        timestamp_str: The timestamp string from Facebook (e.g., "2 hrs ago", "Yesterday at 5:00 PM", "2h", "50w")

    Returns:
        datetime: Parsed datetime in UTC timezone, or None if parsing fails
    """
    if not timestamp_str:
        return None

    # Handle short forms like "2h", "3d", "4w", "1y"
    short_form_match = re.match(r"^(\d+)([hdwmy])$", timestamp_str.strip())
    if short_form_match:
        val, unit = short_form_match.groups()
        val = int(val)
        unit_map = {
            "h": "hours",
            "d": "days",
            "w": "weeks",
            "m": "months",
            "y": "years",
        }
        timestamp_str = f"{val} {unit_map[unit]} ago"

    try:
        parsed = dateparser.parse(
            timestamp_str,
            settings={
                "TIMEZONE": "UTC",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "RELATIVE_BASE": datetime.now(UTC),
            },
        )

        if not parsed:
            raise ValueError(f"Unable to parse timestamp: {timestamp_str}")

        return parsed

    except Exception as e:
        logger.warning(f"Timestamp parsing error: {e} for input: {timestamp_str}")
        return None


import re
