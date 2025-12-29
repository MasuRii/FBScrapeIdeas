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

    // Content extraction
    let contentEl = findFirstMatch(selectors.content);
    if (!contentEl) {
        contentEl = findBestMatch(['div[dir="auto"]'], el => 
            el.innerText && el.innerText.length > 50 && el.innerText.length < 5000
        );
    }
    
    // Author extraction
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
    
    // Timestamp extraction
    let timestampEl = article.querySelector('abbr');
    let rawTimestamp = null;
    
    if (timestampEl) {
        rawTimestamp = timestampEl.getAttribute('title') || timestampEl.innerText;
    } else {
        const links = article.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"]');
        for (const link of links) {
            const txt = (link.innerText || '').trim();
            if (/^\\d+[hdwmy]$/.test(txt) || txt.includes('ago') || 
                /^(Yesterday|Today|Just now)/i.test(txt)) {
                rawTimestamp = txt;
                break;
            }
        }
    }
    
    // Permalink extraction
    let permalinkEl = article.querySelector('a[href*="/posts/"]:not([href*="comment_id"])');
    if (!permalinkEl) {
        const tsEl = article.querySelector('abbr, time');
        if (tsEl) {
            const parentLink = tsEl.closest('a');
            if (parentLink && (parentLink.href.includes('/posts/') || parentLink.href.includes('/permalink/'))) {
                permalinkEl = parentLink;
            }
        }
    }
    if (!permalinkEl) {
        permalinkEl = findFirstMatch(selectors.permalink);
    }

    return {
        content_text: contentEl ? contentEl.innerText : null,
        post_author_name: authorText,
        raw_timestamp: rawTimestamp,
        post_url: permalinkEl ? permalinkEl.href : null,
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
    
    // Target common overlay/dialog patterns
    const overlays = document.querySelectorAll('div[role="presentation"], div[role="dialog"], div[style*="z-index"]');
    overlays.forEach(el => {
        const style = window.getComputedStyle(el);
        const zIndex = parseInt(style.zIndex) || 0;
        const rect = el.getBoundingClientRect();
        
        // Check for "Close" text or label in the element or its children
        const hasCloseAction = el.querySelector('[aria-label*="Close"], [aria-label*="Not now"]') || 
                               el.innerText.includes('Close') || 
                               el.innerText.includes('Not now');

        if ((zIndex > 100 || el.getAttribute('role') === 'presentation' || hasCloseAction) &&
            rect.width > window.innerWidth * 0.4 && 
            rect.height > window.innerHeight * 0.4) {
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
    const articles = document.querySelectorAll('{selector}');
    if (articles.length > 10) {{
        for (let i = 0; i < articles.length - 5; i++) {{
            articles[i].remove();
        }}
        console.log(`Pruned ${{articles.length - 5}} elements from DOM.`);
    }}
}}"""
