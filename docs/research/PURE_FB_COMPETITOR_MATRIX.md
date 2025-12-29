# Pure Facebook Competitor Matrix (2025)

**Date:** December 29, 2025
**Focus:** Exclusive Facebook Group Scrapers & AI Analysis Tools.
**Methodology:** Filtered for 2025 updates, Facebook-only focus, and distinct scraping capabilities.

## 1. Top 3 Competitors

| Competitor | Repository | Last Update | Primary Focus |
| :--- | :--- | :--- | :--- |
| **Tarasa Extractor** | `yousef-hamda/tarasa-historic-extractor` | Dec 10, 2025 | **Full-Stack SaaS**: Archiving & Auto-Messaging. |
| **Thanh's Scraper** | `thanh2004nguyen/facebook-group-scraper` | Nov 12, 2025 | **Pure Scraper**: High-performance Playwright engine. |
| **Benzh0u Local** | `benzh0u/facebookscraper-local` | Dec 10, 2025 | **AI Alerting**: Local rental/keyword monitor with OpenAI. |

---

## 2. Detailed Comparison Matrix

| Feature | FB Scrape Ideas (Us) | Tarasa Extractor | Thanh's Scraper | Benzh0u Local |
| :--- | :--- | :--- | :--- | :--- |
| **Core Technology** | **Selenium** + Python | **Playwright** + Node.js | **Playwright** + Python | **Playwright** + Python |
| **Authentication** | Manual Login + Cookie File | Auto-Login + 2FA Handling | Manual Login + Session Save | Manual Login + Session Save |
| **Group Scraping** | **Yes** (Public & Private) | **Yes** (Historic Focus) | **Yes** (Infinite Scroll) | **Yes** (Keyword Filter) |
| **AI Integration** | **High** (Gemini/OpenAI Analysis) | **High** (GPT-4o Messaging) | **None** | **Medium** (OpenAI Filtering) |
| **Action Capability** | Read & Analyze | **Read & Message** | Read Only | Read & Notify |
| **Storage** | SQLite Database | PostgreSQL + Prisma | JSON / Text | JSON |
| **UI / Interface** | Rich Terminal (CLI) | Web Dashboard (Next.js) | Basic Terminal | Basic Terminal |

---

## 3. Technical Analysis

### A. Authentication Stability
*   **Competitors (Playwright):** All key competitors have moved to Playwright. They prioritize "Session Saving" (dumping cookies/storage state to a file) over raw credential login on every run. This reduces the 2FA/Checkpoint risk significantly.
*   **Us (Selenium):** We use a similar approach (cookies), but Selenium's detection footprint is larger.
*   **Insight:** Moving to Playwright would likely improve our "Trust Score" with Facebook's anti-bot systems.

### B. Group Privacy Handling
*   **Thanh's Scraper** has the most robust logic for "Infinite Scroll" and "Dynamic Content" loading, claiming a 100% success rate by handling DOM changes aggressively.
*   **Benzh0u Local** focuses on specific *keywords*, effectively filtering content *during* the scrape rather than after. This is efficient for "Alert" use cases (e.g., finding a flat) but less useful for "Research" (collecting everything).

### C. AI Integration Depth
*   **Tarasa** is the leader here. It doesn't just "summarize"; it uses AI to *decide* (Classify -> Message). It treats the AI as an Agent.
*   **Benzh0u** uses OpenAI primarily for *filtering* relevance, which is a smart cost-saving measure (don't process irrelevant posts).
*   **FB Scrape Ideas** (Us) sits in the middle: We analyze *after* collection. We could adopt Benzh0u's "Filter-during-scrape" model to save DB space and tokens.

---

## 4. Recommendations for FB Scrape Ideas

1.  **Migrate to Playwright:** The market clearly favors Playwright for 2025 Facebook scraping due to better evasion and speed.
2.  **Implement "Session State" Management:** Standardize on saving the full browser context (localStorage + Cookies) like Thanh's scraper, rather than just cookies.
3.  **Add "AI Filtering":** Adopt the pattern from `benzh0u` to allow users to define an "AI Gate" that only saves posts matching complex criteria (e.g., "Only posts about genuine user complaints, ignore marketing").
4.  **Explore "Action" Features:** To compete with Tarasa, we could add a "Draft Reply" feature where the AI generates a suggested response for the user to manually approve.

