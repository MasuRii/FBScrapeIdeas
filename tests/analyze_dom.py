"""DOM analysis script for Facebook group scraping."""

import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)

from playwright.async_api import async_playwright

from scraper.session_manager import SessionManager
from config import SESSION_STATE_PATH


async def analyze_group():
    async with async_playwright() as p:
        session_manager = SessionManager(SESSION_STATE_PATH)
        context = await session_manager.get_context(p, headless=True)
        page = await context.new_page()

        await page.goto(
            "https://www.facebook.com/groups/mumairryk/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await asyncio.sleep(5)
        await page.evaluate("window.scrollBy(0, 1500)")
        await asyncio.sleep(4)

        # Analysis script - find permalinks and timestamps
        js_code = """() => {
            const result = {
                allPermalinks: [],
                allTimestampElements: [],
                postsWithBothProfileAndMessage: []
            };
            
            // Find all permalink-like links
            document.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"]').forEach((el, i) => {
                if (i >= 10) return;
                result.allPermalinks.push({
                    href: el.href?.substring(0, 120),
                    text: el.innerText?.substring(0, 30),
                    hasCommentId: el.href?.includes('comment_id')
                });
            });
            
            // Find all abbr elements
            document.querySelectorAll('abbr').forEach((el, i) => {
                if (i >= 10) return;
                result.allTimestampElements.push({
                    tag: 'abbr',
                    text: el.innerText,
                    title: el.getAttribute('title')
                });
            });
            
            // Find containers that have BOTH profile_name and story_message
            const profileNames = document.querySelectorAll('[data-ad-rendering-role="profile_name"]');
            profileNames.forEach((pn, idx) => {
                if (idx >= 5) return;
                
                // Walk up to find a container that also has story_message
                let container = pn.parentElement;
                let depth = 0;
                
                while (container && depth < 20) {
                    const story = container.querySelector('[data-ad-rendering-role="story_message"]');
                    if (story) {
                        // Found a good container - now look for permalink and timestamp WITHIN this container
                        const permalink = container.querySelector('a[href*="/posts/"], a[href*="/permalink/"]');
                        const abbr = container.querySelector('abbr');
                        
                        // Also look for time-like text in links
                        let timeText = null;
                        const links = container.querySelectorAll('a');
                        for (const link of links) {
                            const txt = (link.innerText || '').trim();
                            if (/^[0-9]+[hdwmy]$/.test(txt) || txt.includes('ago')) {
                                timeText = txt;
                                break;
                            }
                        }
                        
                        result.postsWithBothProfileAndMessage.push({
                            author: pn.innerText?.substring(0, 30),
                            content: story.innerText?.substring(0, 60),
                            containerDepth: depth,
                            permalink: permalink?.href?.substring(0, 100),
                            abbrText: abbr?.innerText,
                            abbrTitle: abbr?.getAttribute('title'),
                            timeText: timeText
                        });
                        break;
                    }
                    container = container.parentElement;
                    depth++;
                }
            });
            
            return result;
        }"""

        analysis = await page.evaluate(js_code)

        print("=== MUMAIRRYK GROUP ANALYSIS ===")
        print(json.dumps(analysis, indent=2))

        await page.close()
        browser = context.browser
        await context.close()
        if browser:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_group())
