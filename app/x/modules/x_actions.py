import os
import time
from typing import Optional

from playwright.sync_api import Page, sync_playwright


DEFAULT_TIMEOUT = 30_000


def _launch_browser(p, headless: bool):
    """Launch Chromium with optional Chrome channel (defaults to installed Chrome)."""
    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"
    try:
        return p.chromium.launch(channel=chrome_channel, headless=headless)
    except Exception:
        # Fallback if channel isn't available
        return p.chromium.launch(headless=headless)


def _norm_tweet_url(url: str) -> str:
    url = (url or "").strip()
    # Accept x.com or twitter.com
    if url.startswith("https://twitter.com/"):
        url = url.replace("https://twitter.com/", "https://x.com/", 1)
    return url


def _goto_tweet(page: Page, tweet_url: str):
    tweet_url = _norm_tweet_url(tweet_url)
    if not tweet_url:
        raise ValueError("tweet_url required")
    page.goto(tweet_url, wait_until="domcontentloaded")
    # Ensure tweet page is ready
    page.wait_for_timeout(6200)
    # Sometimes content loads after initial DOMContentLoaded
    page.locator("article").first.wait_for(state="visible", timeout=60_000)


def _click_first_visible(page: Page, selectors: list[str], timeout_ms: int = 30_000):
    deadline = time.time() + (timeout_ms / 1000.0)
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if loc.count() and loc.first.is_visible():
                    loc.first.scroll_into_view_if_needed()
                    try:
                        loc.first.click(timeout=3_000)
                    except Exception:
                        loc.first.click(timeout=3_000, force=True)
                    return
            except Exception as e:
                last_err = e
        page.wait_for_timeout(250)
    if last_err:
        raise last_err
    raise TimeoutError("Could not find a clickable element")


def _wait_any(page: Page, selectors: list[str], timeout_ms: int = 30_000):
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if loc.count() and loc.first.is_visible():
                    return
            except Exception:
                pass
        page.wait_for_timeout(200)
    raise TimeoutError("Timeout waiting for expected UI")


def _get_scope(page: Page):
    dlg = page.locator("div[role='dialog']")
    return dlg.first if dlg.count() else page


def _pick_file_input(scope: Page):
    # Prefer testid fileInput when present
    loc = scope.locator("input[type='file'][data-testid='fileInput']")
    if loc.count():
        return loc.first
    loc = scope.locator("input[type='file']")
    if loc.count():
        for i in range(min(loc.count(), 10)):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    return item
            except Exception:
                pass
        return loc.first
    return None


def _media_preview_visible(scope: Page) -> bool:
    candidates = [
        'div[data-testid="attachments"]',
        'div[data-testid="tweetPhoto"]',
        'div[data-testid="tweetPhotoContainer"]',
        'div[data-testid="mediaContainer"]',
        'div[data-testid="videoPlayer"]',
        'div[data-testid="videoComponent"]',
        'video',
        '#layers img',
        '#layers video',
        'img[src*="twimg"]',
    ]
    for sel in candidates:
        try:
            loc = scope.locator(sel)
            if loc.count() and loc.first.is_visible():
                return True
        except Exception:
            pass
    return False


def _media_uploading_indicator_visible(scope: Page) -> bool:
    # Avoid general countdown-circle; focus inside attachments containers when possible
    candidates = [
        'div[data-testid="mediaUploadProgress"]',
        '#layers div[data-testid="mediaUploadProgress"]',
        'div[data-testid="attachments"] div[role="progressbar"]',
        'div[data-testid="mediaContainer"] div[role="progressbar"]',
        'div[data-testid="tweetPhotoContainer"] div[role="progressbar"]',
        # Localized aria labels
        'div[aria-label*="Uploading"]',
        'div[aria-label*="Processing"]',
        'div[aria-label*="رفع"]',
        'div[aria-label*="معالجة"]',
        'svg[aria-label*="Uploading"]',
        'svg[aria-label*="Processing"]',
        'svg[aria-label*="رفع"]',
        'svg[aria-label*="معالجة"]',
    ]
    for sel in candidates:
        try:
            loc = scope.locator(sel)
            if loc.count() and loc.first.is_visible():
                return True
        except Exception:
            pass
    return False


def _wait_media_uploaded_in_composer(page: Page, timeout_ms: int = 180_000):
    """ديناميكي: ينتظر preview للميديا ثم ينتظر انتهاء الرفع/المعالجة (خصوصًا للفيديو)."""
    deadline = time.time() + (timeout_ms / 1000.0)
    scope = _get_scope(page)

    # Remove button is a strong hint media is attached
    remove_btn = scope.locator(
        '#layers [aria-label="Remove"], #layers [aria-label="Remove media"], '
        '#layers [aria-label="إزالة"], #layers [aria-label="حذف"], '
        '#layers [data-testid*="remove"]'
    )

    saw_preview = False
    stable_ticks = 0

    while time.time() < deadline:
        if _media_preview_visible(scope) or (remove_btn.count() and remove_btn.first.is_visible()):
            saw_preview = True

        if not saw_preview:
            page.wait_for_timeout(250)
            continue

        # If still uploading/processing -> keep waiting
        if _media_uploading_indicator_visible(scope):
            stable_ticks = 0
            page.wait_for_timeout(450)
            continue

        # No indicator: require a short stable window (video often flips states)
        stable_ticks += 1
        if stable_ticks >= 4:  # ~1.2s stable
            page.wait_for_timeout(700)
            return
        page.wait_for_timeout(300)

    raise TimeoutError("انتهت مهلة انتظار رفع/معالجة الميديا.")


def _wait_button_enabled(scope: Page, selectors: list[str], timeout_ms: int = 120_000):
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        for sel in selectors:
            try:
                btn = scope.locator(sel)
                if btn.count() and btn.first.is_visible():
                    aria = btn.first.get_attribute("aria-disabled")
                    try:
                        enabled = btn.first.is_enabled()
                    except Exception:
                        enabled = (aria != "true")
                    if enabled and aria != "true":
                        return True
            except Exception:
                pass
        scope.page.wait_for_timeout(250)
    return False

def like_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Like a tweet by URL."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Prefer stable testids
            selectors = [
                "div[data-testid='like']",
                "button[data-testid='like']",
                "div[role='button'][data-testid='like']",
                # Fallback to aria-label (EN/AR)
                "[aria-label*='Like']",
                "[aria-label*='إعجاب']",
                "[aria-label*='أعجب']",
            ]
            _click_first_visible(page, selectors, timeout_ms=60_000)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def repost_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Repost (retweet) a tweet by URL."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Step 1: open repost menu
            open_menu_selectors = [
                "div[data-testid='retweet']",
                "button[data-testid='retweet']",
                "div[role='button'][data-testid='retweet']",
                # recorded: aria label contains reposts. Repost
                "[aria-label*='reposts'][aria-label*='Repost']",
                "[aria-label*='Repost']",
                "[aria-label*='إعادة النشر']",
                "[aria-label*='إعاده النشر']",
                "[aria-label*='إعادة نشر']",
            ]
            _click_first_visible(page, open_menu_selectors, timeout_ms=60_000)

            # Step 2: choose "Repost" from menu
            menu_item_selectors = [
                "div[role='menuitem']:has-text('Repost')",
                "div[role='menuitem']:has-text('إعادة النشر')",
                "div[role='menuitem']:has-text('إعاده النشر')",
                "div[role='menuitem']:has-text('إعادة نشر')",
                "span:has-text('Repost')",
                "span:has-text('إعادة النشر')",
                "span:has-text('إعاده النشر')",
                "span:has-text('إعادة نشر')",
            ]
            # Wait for menu to appear then click
            _wait_any(page, ["div[role='menu']", "div[role='menuitem']"], timeout_ms=15_000)
            _click_first_visible(page, menu_item_selectors, timeout_ms=30_000)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def undo_repost_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Undo repost (unretweet) a tweet by URL."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Step 1: click unretweet button
            page.get_by_test_id("unretweet").click()
            page.wait_for_timeout(1000)

            # Step 2: click "Undo repost" text
            page.get_by_text("Undo repost").click()

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def undo_like_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Undo like (unlike) a tweet by URL."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Same selectors - clicking again will unlike
            selectors = [
                "div[data-testid='unlike']",
                "button[data-testid='unlike']",
                "div[role='button'][data-testid='unlike']",
                "div[data-testid='like']",
                "button[data-testid='like']",
                "[aria-label*='Unlike']",
                "[aria-label*='Liked']",
                "[aria-label*='إلغاء الإعجاب']",
                "[aria-label*='أعجبني']",
            ]
            _click_first_visible(page, selectors, timeout_ms=60_000)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def reply_to_tweet(
    storage_state_path: str,
    tweet_url: str,
    reply_text: str,
    headless: bool,
    media_path: Optional[str] = None,
    media_timeout_ms: int = 180_000,
    wait_after_ms: int = 5_000,
):
    """Reply to a tweet by URL."""
    reply_text = (reply_text or "").strip()
    if not reply_text:
        raise ValueError("reply_text required")

    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Open reply composer (if needed)
            reply_btn_selectors = [
                "div[data-testid='reply']",
                "button[data-testid='reply']",
                "div[role='button'][data-testid='reply']",
                "[aria-label*='Reply']",
                "[aria-label*='رد']",
            ]
            # If textbox already visible, skip clicking reply
            textbox = page.locator("div[data-testid='tweetTextarea_0']")
            if not (textbox.count() and textbox.first.is_visible()):
                _click_first_visible(page, reply_btn_selectors, timeout_ms=30_000)

            # Textbox
            tb = page.locator("div[data-testid='tweetTextarea_0'][role='textbox']")
            if not tb.count():
                tb = page.locator("div[data-testid='tweetTextarea_0']")
            tb.first.wait_for(state="visible", timeout=60_000)
            tb.first.click()
            try:
                tb.first.fill(reply_text)
            except Exception:
                tb.first.press("Control+A")
                

            # Attach media (optional) for reply
            if media_path and str(media_path).strip():
                scope = _get_scope(page)
                file_input = _pick_file_input(scope)
                if file_input is None:
                    raise RuntimeError("Could not find file input for reply composer.")
                file_input.wait_for(state="attached", timeout=60_000)
                file_input.set_input_files(media_path)
                _wait_media_uploaded_in_composer(page, timeout_ms=media_timeout_ms)
            
            
            # Publish reply: tweetButtonInline preferred
            publish_selectors = [
                "button[data-testid='tweetButtonInline']",
                "button[data-testid='tweetButton']",
                # fallback by visible text (EN/AR)
                "button:has-text('Reply')",
                "button:has-text('رد')",
                "button:has-text('نشر')",
                "button:has-text('Post')",
            ]

            # Wait until enabled (no eval/CSP-safe). For video replies this matters.
            scope = _get_scope(page)
            _wait_button_enabled(scope, ["button[data-testid='tweetButtonInline']", "button[data-testid='tweetButton']", "button:has-text('Reply')", "button:has-text('رد')", "button:has-text('نشر')", "button:has-text('Post')"], timeout_ms=120_000)

            # If it never becomes enabled, we'll still attempt the click (X UI can be flaky)
            _click_first_visible(page, publish_selectors, timeout_ms=30_000)

            # Wait 5s as requested then exit
            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def bookmark_tweet(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Bookmark a tweet by URL."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)
            selectors = [
                "div[data-testid='bookmark']",
                "button[data-testid='bookmark']",
                "div[role='button'][data-testid='bookmark']",
                "[aria-label*='Bookmark']",
                "[aria-label*='Bookmarks']",
                "[aria-label*='إشارة مرجعية']",
                "[aria-label*='الإشارات المرجعية']",
            ]
            _click_first_visible(page, selectors, timeout_ms=60_000)
            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def quote_tweet(
    storage_state_path: str,
    tweet_url: str,
    text: str,
    headless: bool,
    media_path: Optional[str] = None,
    media_timeout_ms: int = 180_000,
    wait_after_ms: int = 5_000,
):
    """Quote a tweet (Repost with comment) by URL."""
    text = (text or '').strip()
    if not text:
        raise ValueError("text required for quote")

    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            # Open repost menu
            open_menu_selectors = [
                "div[data-testid='retweet']",
                "button[data-testid='retweet']",
                "div[role='button'][data-testid='retweet']",
                "[aria-label*='Repost']",
                "[aria-label*='إعادة النشر']",
                "[aria-label*='إعاده النشر']",
                "[aria-label*='إعادة نشر']",
            ]
            _click_first_visible(page, open_menu_selectors, timeout_ms=60_000)
            _wait_any(page, ["div[role='menu']", "div[role='menuitem']"], timeout_ms=15_000)

            # Click Quote (EN/AR)
            quote_selectors = [
                "div[role='menuitem']:has-text('Quote')",
                "div[role='menuitem']:has-text('اقتباس')",
                "div[role='menuitem']:has-text('اقتبس')",
                "span:has-text('Quote')",
                "span:has-text('اقتباس')",
                "span:has-text('اقتبس')",
            ]
            _click_first_visible(page, quote_selectors, timeout_ms=30_000)

            scope = _get_scope(page)
            tb = scope.locator("div[data-testid='tweetTextarea_0'][role='textbox']")
            if not tb.count():
                tb = scope.locator("div[data-testid='tweetTextarea_0']")
            tb.first.wait_for(state="visible", timeout=60_000)
            tb.first.click()
            try:
                tb.first.fill(text)
            except Exception:
                tb.first.press("Control+A")
                tb.first.type(text, delay=10)

            if media_path and str(media_path).strip():
                file_input = _pick_file_input(scope)
                if file_input is None:
                    raise RuntimeError("Could not find file input for quote composer.")
                file_input.wait_for(state="attached", timeout=60_000)
                file_input.set_input_files(media_path)
                _wait_media_uploaded_in_composer(page, timeout_ms=media_timeout_ms)

            # Publish
            publish_selectors = [
                "button[data-testid='tweetButtonInline']",
                "button[data-testid='tweetButton']",
                "button:has-text('Post')",
                "button:has-text('نشر')",
            ]
            _wait_button_enabled(scope, ["button[data-testid='tweetButtonInline']", "button[data-testid='tweetButton']"], timeout_ms=120_000)
            _click_first_visible(page, publish_selectors, timeout_ms=30_000)
            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def share_copy_link(storage_state_path: str, tweet_url: str, headless: bool, wait_after_ms: int = 2_000):
    """Open share menu and click 'Copy link' (share via OS sheet is not reliable in automation)."""
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            _goto_tweet(page, tweet_url)

            share_btn_selectors = [
                "div[data-testid='share']",
                "button[data-testid='share']",
                "div[role='button'][data-testid='share']",
                "[aria-label*='Share']",
                "[aria-label*='Share post']",
                "[aria-label*='مشاركة']",
                "[aria-label*='شارك']",
            ]
            _click_first_visible(page, share_btn_selectors, timeout_ms=60_000)

            # Copy link option (EN/AR)
            copy_selectors = [
                "div[role='menuitem']:has-text('Copy link')",
                "div[role='menuitem']:has-text('Copy link to post')",
                "div[role='menuitem']:has-text('نسخ الرابط')",
                "div[role='menuitem']:has-text('نسخ رابط')",
                "span:has-text('Copy link')",
                "span:has-text('نسخ الرابط')",
            ]
            _wait_any(page, ["div[role='menu']", "div[role='menuitem']"], timeout_ms=15_000)
            _click_first_visible(page, copy_selectors, timeout_ms=30_000)
            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def follow_user(storage_state_path: str, profile_url: str, headless: bool = True, wait_after_ms: int = 2000):
    """
    Follow user by visiting their profile and clicking Follow.
    Supports Arabic/English because it relies on data-testid patterns when possible.
    """
    from playwright.sync_api import sync_playwright

    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(60_000)

        try:
            page.goto(profile_url, wait_until="domcontentloaded")
            page.wait_for_timeout(6200)

            # Prefer testid like "*-follow"
            btn = page.locator('[data-testid$="-follow"]')
            if not (btn.count() and btn.first.is_visible()):
                # fallback: any button containing Arabic "متابعة" or English "Follow"
                btn = page.locator('button:has-text("متابعة"), button:has-text("Follow")')

            btn.first.wait_for(state="visible", timeout=30_000)
            btn.first.scroll_into_view_if_needed()

            try:
                btn.first.click(timeout=8_000)
            except Exception:
                btn.first.click(timeout=8_000, force=True)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()


def unfollow_user(storage_state_path: str, profile_url: str, headless: bool = True, wait_after_ms: int = 2000):
    """
    Unfollow user by visiting their profile and clicking Following -> confirm.
    Uses data-testid '*-unfollow' and confirmationSheetConfirm.
    """
    from playwright.sync_api import sync_playwright

    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(60_000)

        try:
            page.goto(profile_url, wait_until="domcontentloaded")
            page.wait_for_timeout(6200)

            btn = page.locator('[data-testid$="-unfollow"]')
            if not (btn.count() and btn.first.is_visible()):
                # Sometimes shows "Following" or "متابَع" etc.
                btn = page.locator('button:has-text("إلغاء المتابعة"), button:has-text("Unfollow"), button:has-text("Following"), button:has-text("متابَع")')

            btn.first.wait_for(state="visible", timeout=30_000)
            btn.first.scroll_into_view_if_needed()

            try:
                btn.first.click(timeout=8_000)
            except Exception:
                btn.first.click(timeout=8_000, force=True)

            # confirm sheet
            confirm = page.locator('[data-testid="confirmationSheetConfirm"]')
            if confirm.count():
                confirm.first.wait_for(state="visible", timeout=15_000)
                try:
                    confirm.first.click(timeout=8_000)
                except Exception:
                    confirm.first.click(timeout=8_000, force=True)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()
