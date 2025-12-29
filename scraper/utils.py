import re
from urllib.parse import urlparse, parse_qs


def derive_post_id(url: str | None) -> str | None:
    """
    Unified helper to extract numeric or alphanumeric ID from various Facebook URL formats.
    Works for both Selenium and Playwright scraped URLs.
    """
    if not url:
        return None

    try:
        parsed_url = urlparse(url)
        path = parsed_url.path

        # 1. Try standard patterns in path: /posts/ID, /permalink/ID, /videos/ID, /photos/ID, /story/ID
        # Handle numeric and alphanumeric IDs
        match = re.search(r"/(?:posts|permalink|videos|photos|story|watch)/([a-zA-Z0-9._-]+)", path)
        if match:
            return match.group(1)

        # 2. Try to find a long numeric ID anywhere in path
        id_match = re.search(r"/(\d{10,})/?", path)
        if id_match:
            return id_match.group(1)

        # 3. Check query parameters: story_fbid, fbid, id, v, photo_id
        query_params = parse_qs(parsed_url.query)
        for q_param in ["story_fbid", "fbid", "id", "v", "photo_id"]:
            if q_param in query_params and query_params[q_param][0].strip():
                return query_params[q_param][0]

    except Exception:
        pass

    return None
