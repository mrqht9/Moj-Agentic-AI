import os
import re
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT = 30_000

def bookmark_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 3000):
    """Bookmark a tweet by URL (AR/EN robust)."""
    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            page.goto(tweet_url, wait_until="domcontentloaded")
            page.wait_for_timeout(6200)

            candidates = [
                "div[data-testid='bookmark']",
                "button[data-testid='bookmark']",
                "div[role='button'][data-testid='bookmark']",
            ]
            clicked = False
            for sel in candidates:
                loc = page.locator(sel)
                if loc.count() and loc.first.is_visible():
                    loc.first.scroll_into_view_if_needed()
                    try:
                        loc.first.click(timeout=5000)
                    except Exception:
                        loc.first.click(timeout=5000, force=True)
                    clicked = True
                    break

            if not clicked:
                try:
                    lab = page.get_by_label(re.compile(r"(Bookmark|Bookmarks|إشارة مرجعية|الإشارات المرجعية)", re.I))
                    if lab.count():
                        lab.first.scroll_into_view_if_needed()
                        try:
                            lab.first.click(timeout=5000)
                        except Exception:
                            lab.first.click(timeout=5000, force=True)
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                raise TimeoutError("Could not find Bookmark button")

            page.wait_for_timeout(wait_after_ms)

        finally:
            context.close()
            browser.close()


def undo_bookmark_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 3000):
    """Remove bookmark from a tweet by URL (AR/EN robust)."""
    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            page.goto(tweet_url, wait_until="domcontentloaded")
            page.wait_for_timeout(6200)

            candidates = [
                "div[data-testid='removeBookmark']",
                "button[data-testid='removeBookmark']",
                "div[role='button'][data-testid='removeBookmark']",
                "div[data-testid='bookmark']",
                "button[data-testid='bookmark']",
                "div[role='button'][data-testid='bookmark']",
            ]
            clicked = False
            for sel in candidates:
                loc = page.locator(sel)
                if loc.count() and loc.first.is_visible():
                    loc.first.scroll_into_view_if_needed()
                    try:
                        loc.first.click(timeout=5000)
                    except Exception:
                        loc.first.click(timeout=5000, force=True)
                    clicked = True
                    break

            if not clicked:
                try:
                    lab = page.get_by_label(re.compile(r"(Remove Bookmark|Remove from Bookmarks|إزالة الإشارة المرجعية|إزالة من الإشارات المرجعية|Bookmark|إشارة مرجعية)", re.I))
                    if lab.count():
                        lab.first.scroll_into_view_if_needed()
                        try:
                            lab.first.click(timeout=5000)
                        except Exception:
                            lab.first.click(timeout=5000, force=True)
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                raise TimeoutError("Could not find Remove Bookmark button")

            page.wait_for_timeout(wait_after_ms)

        finally:
            context.close()
            browser.close()
