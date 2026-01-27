import os
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT = 30_000

def unfollow_user(storage_state_path: str, profile_url: str, headless: bool, wait_after_ms: int = 3000):
    """Unfollow a user profile then confirm (confirmationSheetConfirm)."""
    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        try:
            page.goto(profile_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)

            btn = page.locator('[data-testid$="-unfollow"]')
            if not (btn.count() and btn.first.is_visible()):
                btn = page.locator(
                    'button:has-text("إلغاء المتابعة"), button:has-text("Unfollow"), button:has-text("Following")'
                )

            btn.first.wait_for(state="visible", timeout=30_000)
            btn.first.scroll_into_view_if_needed()
            try:
                btn.first.click(timeout=8000)
            except Exception:
                btn.first.click(timeout=8000, force=True)

            confirm = page.locator('[data-testid="confirmationSheetConfirm"]')
            if confirm.count():
                confirm.first.wait_for(state="visible", timeout=15_000)
                try:
                    confirm.first.click(timeout=8000)
                except Exception:
                    confirm.first.click(timeout=8000, force=True)

            page.wait_for_timeout(wait_after_ms)
        finally:
            context.close()
            browser.close()
