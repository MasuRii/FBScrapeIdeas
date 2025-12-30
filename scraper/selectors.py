import json
import logging
import os
from pathlib import Path
from config import SESSION_STATE_PATH

logger = logging.getLogger(__name__)


class SelectorRegistry:
    """
    Self-healing selector registry that maintains fallback selectors and learns
    from failures by extracting DOM structure when selectors fail.
    """

    # Updated 2025-12-29: Based on live DOM analysis and legacy Selenium unification
    DEFAULT_SELECTORS = {
        "article": [
            # FeedUnit pagelets - extremely reliable for full posts
            '[data-pagelet^="FeedUnit"]',
            # Positional index in feed - very stable for post containers
            "div[aria-posinset]",
            # Container divs with story_message (main post content)
            'div:has(> div > div > [data-ad-rendering-role="story_message"])',
            'div:has([data-ad-rendering-role="story_message"])',
            # Primary: role="article" - often used for posts
            'div[role="article"]',
            # Comet feed unit
            'div[data-testid="comet_feed_unit"]',
        ],
        "content": [
            # Primary: data-ad-rendering-role="story_message" is the 2025 standard
            'div[data-ad-rendering-role="story_message"]',
            # Comet preview (alternative)
            'div[data-ad-comet-preview="message"]',
            # Legacy ad preview
            'div[data-ad-preview="message"]',
            # Fallback to dir="auto" divs with substantial text
            'div[dir="auto"]',
        ],
        "author": [
            # Primary: data-ad-rendering-role="profile_name" is the 2025 standard
            'div[data-ad-rendering-role="profile_name"]',
            '[data-ad-rendering-role="profile_name"]',
            # Name in H2/H3 (common in feed)
            "h2 strong a",
            "h3 strong a",
            'h2 a[role="link"] strong',
            'h3 a[role="link"] strong',
            # 2025-12-29: Added simpler strong tags for static/minimal HTML
            "h2 strong",
            "h3 strong",
            "h2",
            "h3",
            # Links to user profiles (for comments and some posts)
            'a[href*="/user/"]',
            'a[href*="/groups/"][href*="/user/"]',
            'a[href*="/profile.php"]',
        ],
        "author_pic": [
            "div:first-child svg image",
            'div:first-child img[alt*="profile picture"]',
            'div:first-child img[data-imgperflogname*="profile"]',
            'div[role="button"] svg image',
        ],
        "timestamp": [
            # Primary: abbr elements (with or without title attribute)
            "abbr",
            "abbr[title]",
            # Links containing time-like text (1h, 2d, 3w, etc.)
            'a[href*="/posts/"] span[data-lexical-text="true"]',
            'a[href*="/posts/"]',
            'a[href*="/permalink/"]',
            'a[href*="/videos/"] span',
            'a[href*="/photos/"] span',
        ],
        "permalink": [
            # Primary: /posts/ URLs explicitly excluding comment_id links
            'a[href*="/posts/"]:not([href*="comment_id"]):not([href*="reply_comment_id"])',
            # Permalink URLs (also exclude comment links)
            'a[href*="/permalink/"]:not([href*="comment_id"])',
            # Video/photo/watch posts
            'a[href*="/videos/"]:not([href*="comment_id"])',
            'a[href*="/photos/"]:not([href*="comment_id"])',
            'a[href*="/watch/"]:not([href*="comment_id"])',
            # Legacy story.php format
            'a[href*="/story.php"]:not([href*="comment_id"])',
        ],
        "post_image": [
            "img.x168nmei",
            'div[data-imgperflogname="MediaGridPhoto"] img',
            'div[style*="background-image"]',
        ],
        "comment_container": [
            'div[aria-label*="Comment by"]',
            "ul > li div[role='article']",
        ],
        "comment_text": [
            'div[data-ad-preview="message"] > span',
            'div[dir="auto"][style="text-align: start;"]',
            ".xmjcpbm.xtq9sad + div",
            ".xv55zj0 + div",
            'div[dir="auto"]',
            'span[dir="auto"]',
        ],
        "comment_id": [
            "a[href*='comment_id=']",
            "[data-commentid]",
        ],
        "see_more": [
            'div[role="button"]:contains("See more")',
            'div[role="button"]:contains("Show more")',
            'a:contains("See more")',
            'a:contains("Show more")',
        ],
        "feed_container": [
            'div[role="feed"]',
            "div[data-testid='post_scroller']",
        ],
        "dismiss_button": [
            'div[role="dialog"] div[role="button"][aria-label="Close"]',
            'div[role="dialog"] div[role="button"][aria-label="Not now"]',
            'div[role="dialog"] button[aria-label="Close"]',
            'div[role="dialog"] div[role="button"]:has-text("Close")',
            'div[role="dialog"] button:has-text("Close")',
            'button[data-cookiebanner="accept_button"]',
            'div[aria-label="Close"]',
            'div[aria-label="Not now"]',
            'button[aria-label="Allow all cookies"]',
            'div[role="button"][aria-label="Decline optional cookies"]',
        ],
        "close_button": [
            'div[role="dialog"] div[role="button"][aria-label="Close"]',
            'div[role="button"][aria-label="Close"]',
            'button[aria-label="Close"]',
            'div[role="dialog"] i.x1n2onr6',  # Common icon-only close button
        ],
        "overlay": [
            'div[role="dialog"]',
            'div[role="presentation"]',
            'div[data-testid*="dialog"]',
            'div[data-testid*="cookie"]',
        ],
        "view_more_comments": [
            # Primary: role="button" with text containing "View" and "comment"
            'div[role="button"]:has-text("View")',
            'div[role="button"]:has-text("View more comments")',
            'div[role="button"]:has-text("View previous comments")',
            # Fallback: span elements with the text
            'span:has-text("View more comments")',
            'span:has-text("View previous comments")',
            # Pattern-based: "View X more comments" where X is a number
            'div[role="button"]:has-text("View")',
            'a:has-text("View")',
            # Generic comment expanders
            'div:has-text("View")',
            'span:has-text("View")',
        ],
    }

    def __init__(self, learned_selectors_path: str | None = None):
        """Initialize with default selectors and optionally load learned ones."""
        self.selectors = {k: list(v) for k, v in self.DEFAULT_SELECTORS.items()}
        self.failed_selectors: dict[str, list[str]] = {}
        self.learned_selectors_path = learned_selectors_path or self._get_default_path()
        self._load_learned_selectors()

    def _get_default_path(self) -> str:
        """Get default path for storing learned selectors."""
        state_dir = Path(SESSION_STATE_PATH).parent
        return str(state_dir / "learned_selectors.json")

    def _load_learned_selectors(self) -> None:
        """Load previously learned selectors from disk."""
        try:
            if os.path.exists(self.learned_selectors_path):
                with open(self.learned_selectors_path, "r") as f:
                    learned = json.load(f)
                    for element_type, selectors in learned.items():
                        if element_type in self.selectors:
                            for sel in selectors:
                                if sel not in self.selectors[element_type]:
                                    self.selectors[element_type].append(sel)
                    logger.debug(f"Loaded learned selectors from {self.learned_selectors_path}")
        except Exception as e:
            logger.debug(f"Could not load learned selectors: {e}")

    def _save_learned_selectors(self) -> None:
        """Persist newly learned selectors to disk."""
        try:
            # Only save selectors that were added beyond defaults
            learned = {}
            for element_type, current in self.selectors.items():
                defaults = self.DEFAULT_SELECTORS.get(element_type, [])
                new_selectors = [s for s in current if s not in defaults]
                if new_selectors:
                    learned[element_type] = new_selectors

            if learned:
                os.makedirs(os.path.dirname(self.learned_selectors_path), exist_ok=True)
                with open(self.learned_selectors_path, "w") as f:
                    json.dump(learned, f, indent=2)
                logger.info(f"Saved learned selectors to {self.learned_selectors_path}")
        except Exception as e:
            logger.warning(f"Could not save learned selectors: {e}")

    def get_selector(self, element_type: str) -> str:
        """Get a combined CSS selector string for the element type."""
        selectors = self.selectors.get(element_type, [])
        return ", ".join(selectors) if selectors else ""

    def get_selectors_list(self, element_type: str) -> list[str]:
        """Get the list of selectors for an element type."""
        return self.selectors.get(element_type, [])

    def add_alternative(self, element_type: str, selector: str) -> None:
        """Add a new alternative selector that was discovered to work."""
        if element_type not in self.selectors:
            self.selectors[element_type] = []
        if selector and selector not in self.selectors[element_type]:
            self.selectors[element_type].append(selector)
            logger.info(f"Learned new selector for '{element_type}': {selector}")
            self._save_learned_selectors()

    def record_failure(self, element_type: str, selector: str) -> None:
        """Record that a selector failed (for debugging/analysis)."""
        if element_type not in self.failed_selectors:
            self.failed_selectors[element_type] = []
        if selector not in self.failed_selectors[element_type]:
            self.failed_selectors[element_type].append(selector)
            logger.warning(f"Selector failed for '{element_type}': {selector}")


# Global selector registry instance
_selector_registry = SelectorRegistry()


def get_selector_registry() -> SelectorRegistry:
    """Get the global selector registry instance."""
    return _selector_registry
