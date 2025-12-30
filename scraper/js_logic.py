"""
Centralized storage for JavaScript templates used by PlaywrightScraper.
Separating JS from Python logic improves readability and maintainability.
"""

# Script to check if content is available on a page (real content vs skeletons)
CHECK_CONTENT_SCRIPT = """() => {
    const articles = document.querySelectorAll('div[role="article"], [data-pagelet^="FeedUnit"]');
    return articles.length > 0;
}"""

# Script to wait for actual text content (avoiding skeletons)
# Use double braces {{ }} to escape them for .format() if it's called on the string
WAIT_FOR_CONTENT_SCRIPT = """() => {{
    const articles = document.querySelectorAll('{selector}');
    if (articles.length === 0) return false;
    
    return Array.from(articles).some(article => {{
        const text = article.innerText || "";
        return text.length > 100;
    }});
}}"""

# Comprehensive post data extraction script
# Updated 2025-12-30: Enhanced URL and timestamp extraction with multiple strategies
# - Search data-ft attributes for hidden post IDs
# - Expanded timestamp detection patterns
# - Better handling of videos, reels, and mixed content types
EXTRACT_POST_DATA_SCRIPT = """(article, selectors) => {
    const findFirstMatch = (selectorsList) => {
        for (const selector of selectorsList) {
            try {
                const el = article.querySelector(selector);
                if (el) return el;
            } catch (e) {
                // Invalid selector, skip
            }
        }
        return null;
    };

    const findBestMatch = (selectorsList, validator) => {
        for (const selector of selectorsList) {
            try {
                const els = article.querySelectorAll(selector);
                for (const el of els) {
                    if (!validator || validator(el)) return el;
                }
            } catch (e) {
                // Invalid selector, skip
            }
        }
        return null;
    };

    // Helper: Extract post ID from any FB URL
    const extractPostId = (url) => {
        if (!url) return null;
        // Match /posts/ID, /permalink/ID, /videos/ID, /photos/ID, /reel/ID
        const match = url.match(/\\/(posts|permalink|videos|photos|watch|reel)\\/([0-9]+)/);
        if (match) return match[2];
        // Try fbid parameter (for photo links: /photo/?fbid=123)
        const fbidMatch = url.match(/[?&]fbid=([0-9]+)/);
        if (fbidMatch) return fbidMatch[1];
        // Try story_fbid parameter
        const storyMatch = url.match(/[?&]story_fbid=([0-9]+)/);
        if (storyMatch) return storyMatch[1];
        // Try multi_permalinks parameter
        const multiMatch = url.match(/[?&]multi_permalinks=([0-9]+)/);
        if (multiMatch) return multiMatch[1];
        // Try v parameter for videos
        const vMatch = url.match(/[?&]v=([0-9]+)/);
        if (vMatch) return vMatch[1];
        return null;
    };

    // Helper: Extract post ID from data-ft JSON attribute
    const extractPostIdFromDataFt = (element) => {
        try {
            const dataFt = element.getAttribute('data-ft');
            if (!dataFt) return null;

            // Parse JSON from data-ft
            let ftData;
            if (typeof dataFt === 'string') {
                ftData = JSON.parse(dataFt);
            } else {
                ftData = dataFt;
            }

            // Common keys for post IDs in data-ft (expanded)
            const idKeys = ['top_level_post_id', 'page_id', 'post_id', 'story_id', 'story_fbid',
                          'mf_story_key', 'page_fbid', 'content_id', 'object_id', 'ent_id'];
            for (const key of idKeys) {
                if (ftData[key]) {
                    return String(ftData[key]);
                }
            }

            // Check nested objects
            if (ftData.mf_story_key) return ftData.mf_story_key;
            if (ftData.page_insights) {
                for (const pageId in ftData.page_insights) {
                    return pageId;
                }
            }

            // Check for nested ID in qid (common in Facebook)
            if (ftData.qid) return String(ftData.qid);
        } catch (e) {
            // JSON parse failed, try regex (more aggressive)
            try {
                const str = String(element.getAttribute('data-ft'));
                // Match any ID-like pattern after common keys
                const idMatch = str.match(/"(?:top_level_post_id|page_id|post_id|story_id|story_fbid|mf_story_key|page_fbid|content_id|object_id|ent_id|qid)":\s*"?([0-9]+)"?/);
                if (idMatch) return idMatch[1];
            } catch (e2) {}
        }
        return null;
    };

    // Helper: Search all elements in article for post ID patterns
    const searchForPostId = (article) => {
        // Try data-ft attributes on all elements
        const allElements = article.querySelectorAll('*');
        for (const el of allElements) {
            const id = extractPostIdFromDataFt(el);
            if (id) return id;
        }

        // Try data-attributes that might contain IDs
        const idEls = article.querySelectorAll('[data-ids], [data-id], [data-post-id], [data-story-id]');
        for (const el of idEls) {
            const dataIds = el.getAttribute('data-ids') || el.getAttribute('data-id') ||
                            el.getAttribute('data-post-id') || el.getAttribute('data-story-id');
            if (dataIds) {
                const idMatch = String(dataIds).match(/([0-9]{15,})/); // FB IDs are usually 15+ digits
                if (idMatch) return idMatch[1];
            }
        }

        // Try finding ID in aria-label or aria-describedby (sometimes contains post info)
        const ariaEls = article.querySelectorAll('[aria-label*="Public"], [aria-label*="Shared"]');
        for (const el of ariaEls) {
            const label = el.getAttribute('aria-label') || '';
            const idMatch = label.match(/([0-9]{15,})/);
            if (idMatch) return idMatch[1];
        }

        return null;
    };

    // Helper: Extract group ID from URL
    const extractGroupId = (url) => {
        if (!url) return null;
        const match = url.match(/\\/groups\\/([0-9]+|[^/]+)/);
        return match ? match[1] : null;
    };

    // Helper: Construct clean permalink
    const constructPermalink = (groupId, postId) => {
        if (!groupId || !postId) return null;
        return 'https://www.facebook.com/groups/' + groupId + '/posts/' + postId + '/';
    };

    // Content extraction
    let contentEl = findFirstMatch(selectors.content);
    if (!contentEl) {
        contentEl = findBestMatch(['div[dir="auto"]'], el =>
            el.innerText && el.innerText.length > 50 && el.innerText.length < 5000
        );
    }

    // Author extraction - improved for 2025 Facebook DOM
    let authorEl = findFirstMatch(selectors.author);
    let authorText = authorEl ? authorEl.innerText : null;

    if (!authorText && authorEl && authorEl.tagName === 'A') {
        authorText = authorEl.innerText || authorEl.textContent;
    }

    if (!authorText) {
        const userLink = article.querySelector('a[href*="/user/"], a[href*="/groups/"][href*="/user/"]');
        if (userLink && userLink.innerText) {
            authorText = userLink.innerText.trim();
        }
    }

    // Enhanced URL and Timestamp extraction
    let cleanPermalink = null;
    let rawTimestamp = null;
    let postId = null;
    let groupId = null;

    // Strategy 0: Aggressive search for post ID in data-ft and other attributes
    if (!postId) {
        postId = searchForPostId(article);
        // If we found a post ID, also try to find group ID from any link
        if (postId) {
            const anyLink = article.querySelector('a[href*="/groups/"]');
            if (anyLink) {
                groupId = extractGroupId(anyLink.href);
            }
        }
    }

    // Strategy 0.5: Check data-pagelet attributes (often contain post IDs)
    if (!postId) {
        const pageletEls = article.querySelectorAll('[data-pagelet]');
        for (const el of pageletEls) {
            const pagelet = el.getAttribute('data-pagelet') || '';
            // data-pagelet often looks like: "FeedUnit_0_0" or contains ID
            const idMatch = pagelet.match(/([0-9]{15,})/);
            if (idMatch) {
                postId = idMatch[1];
                break;
            }
        }
    }

    // Strategy 1: Look for abbr element first (traditional FB timestamp element)
    const abbrEl = article.querySelector('abbr');
    if (abbrEl) {
        const abbrTitle = abbrEl.getAttribute('title');
        const abbrText = abbrEl.innerText || '';
        rawTimestamp = abbrTitle || abbrText;

        const parentLink = abbrEl.closest('a');
        if (parentLink && parentLink.href) {
            const thisPostId = extractPostId(parentLink.href);
            const thisGroupId = extractGroupId(parentLink.href);
            if (thisPostId) postId = thisPostId;
            if (thisGroupId) groupId = thisGroupId;
        }
    }

    // Helper: Validate if text looks like a timestamp (ENHANCED)
    const isTimestampText = (text) => {
        if (!text) return false;
        const trimmed = text.trim();

        // Short relative time: 1h, 2d, 3w, 50w, 1y, etc.
        if (/^\\d+[hdwmy]$/.test(trimmed)) return true;

        // Relative time phrases (expanded)
        if (/^(Yesterday|Today|Just now|Now)/i.test(trimmed)) return true;
        if (/\\b(?:hrs?|hours?|mins?|minutes?|days?|weeks?|months?|years?)\\s*ago$/i.test(trimmed)) return true;
        if (/^\\d+\\s*(?:hr|hour|min|minute|day|week|month|year)s?\\s*ago$/i.test(trimmed)) return true;
        if (/^(?:A moment|At |at |on |in |at)/i.test(trimmed)) return true;
        if (/\\b\\d+\\s*(?:hrs?|hours?|mins?|minutes?|seconds?)\\b/i.test(trimmed)) return true;

        // Date formats: January 1, 2025 or 1/1/2025
        if (/^(January|February|March|April|May|June|July|August|September|October|November|December)/i.test(trimmed)) return true;
        if (/^\\d{1,2}\\/\\d{1,2}\\/\\d{2,4}$/.test(trimmed)) return true;

        // Time formats: 5:30 PM, 10:00 AM
        if (/^\\d{1,2}:\\d{2}\\s*(?:AM|PM|am|pm)?$/i.test(trimmed)) return true;

        // Date + Time combinations
        if (/^\\d{1,2}\\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i.test(trimmed)) return true;

        // Spanish and other common languages
        if (/^(Ayer|Hoy|ahora|Ahora)$/i.test(trimmed)) return true;
        if (/\\b(?:hace|vor|il y a)\\s+\\d+\\s*(?:heure|heures|min|minute|jour|jours|semaine|semaines|mois|an|ans)/i.test(trimmed)) return true;

        // Just time (e.g., "5:30", "10:00")
        if (/^\\d{1,2}:\\d{2}$/.test(trimmed)) return true;

        return false;
    };

    // Helper: Check if text is likely NOT a timestamp (e.g., author name)
    const isLikelyAuthor = (text) => {
        if (!text) return false;
        const trimmed = text.trim();

        // Author names typically don't contain numbers or time keywords
        // They're usually just names, which can be validated by absence of time markers
        return !isTimestampText(trimmed) && trimmed.length < 50 && !/[0-9]/.test(trimmed);
    };

    // Strategy 2: Find /posts/ links (even with comment_id) and extract timestamp from them
    if (!postId || !rawTimestamp) {
        // Expanded link patterns
        const postLinks = article.querySelectorAll(
            'a[href*="/posts/"], ' +
            'a[href*="/permalink/"], ' +
            'a[href*="/videos/"], ' +
            'a[href*="/photos/"], ' +
            'a[href*="/photo/?fbid="], ' +
            'a[href*="/watch/"], ' +
            'a[href*="/reel/"], ' +
            'a[href*="story_fbid="], ' +
            'a[href*="multi_permalinks="], ' +
            'a[href*="fbid="]'
        );

        for (const link of postLinks) {
            const href = link.href || '';
            const linkText = (link.innerText || '').trim();

            // Extract post ID from this link
            const thisPostId = extractPostId(href);
            const thisGroupId = extractGroupId(href);

            if (thisPostId) {
                if (!postId) postId = thisPostId;
                if (!groupId) groupId = thisGroupId || '457688055182211';

                // Check if link text is a valid timestamp (not an author name)
                if (!rawTimestamp && isTimestampText(linkText)) {
                    rawTimestamp = linkText;
                    // If we have both ID and timestamp, we're done
                    if (postId && rawTimestamp) break;
                }
            }

            // Also check aria-label for timestamp
            if (!rawTimestamp) {
                const ariaLabel = link.getAttribute('aria-label') || '';
                if (isTimestampText(ariaLabel)) {
                    rawTimestamp = ariaLabel;
                    if (postId && rawTimestamp) break;
                }
            }
        }
    }

    // Strategy 3: Look for timestamp in time elements (NEW)
    if (!rawTimestamp) {
        const timeElements = article.querySelectorAll('time, time[datetime]');
        for (const timeEl of timeElements) {
            const dt = timeEl.getAttribute('datetime') || '';
            const txt = timeEl.innerText || '';
            if (isTimestampText(txt)) {
                rawTimestamp = txt;
                break;
            }
        }
    }

    // Strategy 4: Search broadly in spans and divs for timestamp-like text
    if (!rawTimestamp) {
        const allTextElements = article.querySelectorAll('span, div');
        for (const el of allTextElements) {
            const txt = (el.innerText || '').trim();
            // Only consider very short text (timestamps are usually short)
            if (txt.length > 0 && txt.length < 30 && isTimestampText(txt)) {
                // Make sure it's not nested too deep (likely content)
                const depth = (el, count = 0) => {
                    if (!el.parentElement || count > 10) return count;
                    return depth(el.parentElement, count + 1);
                };
                if (depth(el) < 8) {
                    rawTimestamp = txt;
                    break;
                }
            }
        }
    }

    // Strategy 5: Extract from data-date attributes (NEW)
    if (!rawTimestamp) {
        const dateElements = article.querySelectorAll('[data-date], [data-utime], [data-timestamp]');
        for (const el of dateElements) {
            const dateVal = el.getAttribute('data-date') || el.getAttribute('data-utime') || el.getAttribute('data-timestamp');
            if (dateVal) {
                rawTimestamp = dateVal;
                break;
            }
        }
    }

    // Strategy 6: Try to find URL patterns in the entire article text as fallback
    if (!postId) {
        const articleText = article.innerText || '';
        const urlMatch = articleText.match(/facebook\\.com\\/groups\\/[^/]+\\/posts\\/([0-9]+)/);
        if (urlMatch) {
            postId = urlMatch[1];
        }
    }

    // Strategy 7: Enhanced timestamp search in all elements (not just links)
    if (!rawTimestamp) {
        const allSpans = article.querySelectorAll('span, time, abbr, div');
        for (const el of allSpans) {
            const txt = (el.innerText || el.textContent || '').trim();
            // Check for timestamp-like text
            if (txt && txt.length > 0 && txt.length < 40 && isTimestampText(txt)) {
                // Make sure it's not inside content div
                const isInContent = el.closest('[data-ad-rendering-role="story_message"], div[dir="auto"]');
                if (!isInContent) {
                    rawTimestamp = txt;
                    break;
                }
            }

            // Also check data attributes
            const dt = el.getAttribute('data-tooltip-content') ||
                       el.getAttribute('data-hover') ||
                       el.getAttribute('title');
            if (dt && isTimestampText(dt)) {
                rawTimestamp = dt;
                break;
            }
        }
    }

    // Construct clean permalink from extracted IDs
    if (postId && !cleanPermalink) {
        // Try to extract group ID from any link in the article
        if (!groupId) {
            const anyLink = article.querySelector('a[href*="/groups/"]');
            if (anyLink) {
                groupId = extractGroupId(anyLink.href);
            }
        }
        // Fallback group ID
        if (!groupId) groupId = '457688055182211';

        cleanPermalink = constructPermalink(groupId, postId);
    }

    return {
        content_text: contentEl ? contentEl.innerText : null,
        post_author_name: authorText,
        raw_timestamp: rawTimestamp,
        post_url: cleanPermalink,
        extracted_post_id: postId,
        extraction_failed: !contentEl && !authorText
    };
}"""

# DOM analysis script for self-healing
ANALYZE_DOM_SCRIPT = """(article) => {
    const analysis = {
        potentialContent: [],
        potentialAuthors: [],
        potentialTimestamps: [],
        potentialPermalinks: []
    };
    
    article.querySelectorAll('div[dir="auto"], div[data-ad-preview]').forEach(el => {
        const text = el.innerText || '';
        if (text.length > 50 && text.length < 5000) {
            const selector = el.getAttribute('data-ad-preview') 
                ? `div[data-ad-preview="${el.getAttribute('data-ad-preview')}"]`
                : null;
            if (selector) analysis.potentialContent.push(selector);
        }
    });
    
    article.querySelectorAll('h2 strong a, h3 strong a, h4 strong a, a[role="link"] strong').forEach(el => {
        if (el.innerText && el.innerText.length < 100) {
            analysis.potentialAuthors.push({
                tag: el.tagName,
                text: el.innerText.substring(0, 50),
                role: el.getAttribute('role')
            });
        }
    });
    
    article.querySelectorAll('abbr[title], a[href*="/posts/"] span, a[href*="/videos/"] span').forEach(el => {
        const text = el.getAttribute('title') || el.innerText || '';
        if (text && (text.includes(':') || text.includes('ago') || text.includes('/'))) {
            analysis.potentialTimestamps.push({
                tag: el.tagName,
                title: el.getAttribute('title'),
                text: text.substring(0, 50)
            });
        }
    });
    
    article.querySelectorAll('a[href*="/posts/"], a[href*="/videos/"], a[href*="/photos/"], a[href*="/permalink/"]').forEach(el => {
        analysis.potentialPermalinks.push({
            href: el.href,
            hasTimestamp: !!el.querySelector('abbr, span')
        });
    });
    
    return analysis;
}"""

# Selector discovery script
DISCOVER_SELECTORS_SCRIPT = """() => {
    const candidates = [];
    
    if (document.querySelector('div[role="article"]')) {
        candidates.push('div[role="article"]');
    }
    
    document.querySelectorAll('[data-pagelet]').forEach(el => {
        const pagelet = el.getAttribute('data-pagelet');
        if (pagelet && (pagelet.includes('Feed') || pagelet.includes('Story'))) {
            candidates.push(`[data-pagelet="${pagelet}"]`);
        }
    });
    
    document.querySelectorAll('div').forEach(el => {
        const classes = el.className;
        if (typeof classes === 'string' && classes.includes('x1yztbdb') && el.innerText && el.innerText.length > 100) {
            candidates.push('div.' + classes.split(' ').join('.'));
        }
    });
    
    return [...new Set(candidates)].slice(0, 5);
}"""

# Force scrollable script
FORCE_SCROLLABLE_SCRIPT = """() => {
    document.body.style.overflow = 'visible';
    document.body.style.overflowY = 'scroll';
    document.documentElement.style.overflow = 'visible';
    document.documentElement.style.overflowY = 'scroll';
}"""

# Nuke blocking elements script
NUKE_BLOCKING_SCRIPT = """() => {
    let removedCount = 0;
    const feedSelector = 'div[role="feed"], [data-testid="post_scroller"], [aria-posinset], [data-pagelet^="FeedUnit"]';
    
    // Target common overlay/dialog patterns
    const overlays = document.querySelectorAll('div[role="presentation"], div[role="dialog"], div[style*="z-index"]');
    overlays.forEach(el => {
        const style = window.getComputedStyle(el);
        const zIndex = parseInt(style.zIndex) || 0;
        const rect = el.getBoundingClientRect();
        
        // PROTECTION: Never nuke if it contains the feed or matches article patterns
        if (el.querySelector(feedSelector) || el.matches(feedSelector)) return;
        
        // PROTECTION: High text density usually means content
        if (el.innerText.length > 800) return;

        const hasCloseAction = el.querySelector('[aria-label*="Close"], [aria-label*="Not now"]') || 
                               el.innerText.includes('Close') || 
                               el.innerText.includes('Not now');

        if ((zIndex > 100 || el.getAttribute('role') === 'presentation' || hasCloseAction) &&
            rect.width > window.innerWidth * 0.4 && 
            rect.height > window.innerHeight * 0.4) {
            
            // Final layout protection for known FB container classes
            if (el.id === 'mount_0_0' || el.classList.contains('x1n2onr6')) return;

            console.log('Nuking overlay:', el);
            el.remove();
            removedCount++;
        }
    });
    
    // Target fixed/absolute elements covering the top or center
    const fixedElements = document.querySelectorAll('div[style*="position: fixed"], div[style*="position: absolute"]');
    fixedElements.forEach(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const zIndex = parseInt(style.zIndex) || 0;
        
        // PROTECTION: Never nuke if it contains the feed
        if (el.querySelector(feedSelector) || el.matches(feedSelector)) return;

        // Specifically look for top-left or top-centered blocking elements
        const isBlockingTop = rect.top < 100 && rect.width > window.innerWidth * 0.7;
        const hasCloseText = el.innerText.includes('Close') || el.getAttribute('aria-label') === 'Close';

        if ((zIndex > 50 && isBlockingTop) || (hasCloseText && zIndex > 0)) {
            // Avoid nuking the main navigation bar if it has Facebook branding
            if (!el.querySelector('[aria-label="Facebook"]') && !el.querySelector('a[href="/"]')) {
                el.remove();
                removedCount++;
            }
        }
    });
    
    return removedCount;
}"""

# Check for overlays script
HAS_OVERLAYS_SCRIPT = """() => {
    const dialogs = document.querySelectorAll('div[role="dialog"], div[role="presentation"]');
    return Array.from(dialogs).some(d => {
        const style = window.getComputedStyle(d);
        return style.display !== 'none' && style.visibility !== 'hidden';
    });
}"""

# JS click script
JS_CLICK_SCRIPT = """(selector) => {
    const btn = document.querySelector(selector);
    if (btn) btn.click();
}"""

# Dispatch ESC key script
DISPATCH_ESC_SCRIPT = """() => {
    document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape', 'code': 'Escape', 'keyCode': 27}));
    document.dispatchEvent(new KeyboardEvent('keyup', {'key': 'Escape', 'code': 'Escape', 'keyCode': 27}));
}"""

# DOM pruning script
PRUNE_DOM_SCRIPT = """() => {{
    const selector = '{selector}';
    const allMatches = Array.from(document.querySelectorAll(selector));
    if (allMatches.length <= 15) return;

    // Filter to only leaf elements matching the selector
    // (Elements that don't contain other elements matching the same selector)
    const leafNodes = allMatches.filter(el => {{
        // Check if any other match is a child of this match
        return !allMatches.some(other => other !== el && el.contains(other));
    }});

    if (leafNodes.length > 10) {{
        const toPrune = leafNodes.slice(0, leafNodes.length - 10);
        let count = 0;
        toPrune.forEach(el => {{
            // Safety: don't prune if it's too high up or has certain roles
            const role = el.getAttribute('role');
            if (role !== 'feed' && role !== 'main' && el.parentElement !== document.body) {{
                el.remove();
                count++;
            }}
        }});
        console.log(`Pruned ${{count}} leaf posts, kept ${{leafNodes.length - count}}.`);
    }}
}}"""
