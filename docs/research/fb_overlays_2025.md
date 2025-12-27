# Facebook Overlay Selectors & Stealth Research (Late 2025)

**Date:** December 27, 2025
**Target:** Facebook Groups (Public/Private)
**Context:** Selenium/Python Automation

## 1. Executive Summary

Facebook's frontend architecture in late 2025 relies heavily on **Atomic CSS** (classes like `x1n2onr6`) and **React-driven dynamic DOMs**. Relying on class names is fragile and discouraged. The most robust selectors for 2025 target **Accessibility Attributes** (`aria-label`, `role`) and **Data Test IDs** (`data-testid`), which remain relatively stable for screen readers and internal testing.

The "Stuck" scraper issue is likely caused by a combination of:
1.  **Native Browser Popups**: Cannot be handled by DOM selectors (require `ChromeOptions`).
2.  **New "Join Group" Prompts**: Often shadow DOM or bottom-sheet layers not covered by old `div[role='dialog']` logic.
3.  **"Login to see more" Blocker**: A hard wall that requires session rotation, not just a close button.

---

## 2. Critical Selectors (2025 Edition)

### A. Notification & Permission Prompts
**Context:** "www.facebook.com wants to show notifications"
**Strategy:** These are native browser prompts, NOT HTML. You cannot click them with Xpath. You must disable them in ChromeOptions.

| Type | Strategy / Selector |
|------|-------------------|
| **Native Prompt** | **Disable via ChromeOptions** (See Section 3) |
| **HTML Fallback** | `//div[@aria-label='Turn on notifications' and @role='dialog']` |
| **Dismiss Button** | `.//div[@role='button'][contains(., 'Not Now')]` |

### B. Cookie Consent (GDPR/CCPA)
**Context:** "Allow all cookies" bottom sheet or modal.

| Specificity | Selector (XPath/CSS) | Notes |
|-------------|----------------------|-------|
| **High** | `button[data-testid="cookie-policy-manage-dialog-accept-button"]` | Most stable internal ID. |
| **High** | `div[aria-label="Allow all cookies"][role="button"]` | Reliable due to a11y requirements. |
| **Medium** | `//span[contains(text(), 'Allow all cookies')]/ancestor::div[@role='button']` | Text-based fallback. |
| **Low (Last Resort)** | `//button[contains(., 'Allow')][contains(., 'cookie')]` | Generic text match. |

### C. "Not Now" / General Interventions
**Context:** "Save Password?", "Switch to App?", "Join Group?"
**Primary Target:** Look for the container `div[role='dialog']` first.

| Target | Selector |
|--------|----------|
| **"Not Now" Btn** | `//div[@role='button']//span[text()='Not now']` |
| **"Close" Icon** | `div[aria-label="Close"][role="button"]` |
| **"Close" (Alt)** | `i[data-visualcompletion="css-img"][style*="x19dipnz"]` |
| **Generic Dismiss** | `//div[@role='dialog']//div[@role='button'][contains(., 'Dismiss') or contains(., 'Close')]` |

### D. Blocking Overlays ("Login to see more")
**Context:** Full-screen blur preventing scrolling on public pages.
**Action:** This often cannot be "closed" without logging in. If it appears on a logged-in session, it's a bug or flag.

| Component | Selector |
|-----------|----------|
| **The Blocker** | `div.x1n2onr6.x1ja2u2z.x78zum5.x2lah0s.xl56j7k` (Obfuscated - highly variable) |
| **The Header** | `//div[contains(text(), 'Log into Facebook')]` |
| **The Detection** | `body[class*="generic_dialog"]` or `div[id="generic_dialog_wrapper"]` |

### E. Group-Specific Overlays (New 2025)
**Context:** "Join this group to post", "Answer questions", "Chats".

| Type | Selector |
|------|----------|
| **Join Prompt** | `//div[@aria-label='Join Group'][@role='button']` |
| **Related Chats** | `//div[contains(@aria-label, 'Chats') and @role='dialog']` |
| **Dismiss Chats** | `//div[@aria-label='Close chat'][@role='button']` |

---

## 3. Recommended "Stealth" Configuration

To prevent these overlays from appearing in the first place, apply these `ChromeOptions` in Python.

```python
from selenium.webdriver.chrome.options import Options

def get_stealth_options():
    options = Options()
    
    # 1. DISABLE NATIVE NOTIFICATIONS (Critical)
    # 2 = Block, 1 = Allow, 0 = Default
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # 2. REMOVE AUTOMATION FLAGS
    # Prevents FB from detecting Selenium immediately and serving "challenge" popups
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 3. SUPPRESS "SAVE PASSWORD" BUBBLES
    options.add_argument("--disable-save-password-bubble")
    options.add_argument("--disable-infobars")

    return options
```

## 4. Implementation Logic Updates

The current `facebook_scraper.py` loop handles overlays, but needs two logic updates:

1.  **Z-Index Check:** Facebook sometimes places transparent `div` layers over the feed. If `click()` fails, use `driver.execute_script("arguments[0].click();", element)` to force-click specific buttons even if obscured.
2.  **Stale Element Retry:** FB DOM updates in real-time. If an overlay is detected but vanishes (StaleReference), catch the exception and **continue immediately** rather than logging an error. The goal is to clear the path, not analyze the debris.

### Recommended `overlay_container_selectors` Update
Add these broad `role` based catch-alls to your existing list:

```python
overlay_container_selectors = [
    "//div[@role='dialog']",
    "//div[@role='banner']",
    "//div[contains(@data-testid, 'dialog')]"
]
```

### Recommended `dismiss_button_xpaths` Update
Prioritize `aria-label` over text text content:

```python
dismiss_button_xpaths = [
    ".//div[@role='button'][@aria-label='Close']",
    ".//div[@role='button'][@aria-label='Not now']",
    ".//span[text()='Not now']",
    ".//span[text()='Close']"
]
```
