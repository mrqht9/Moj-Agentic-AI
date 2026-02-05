import os
from typing import Optional
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT = 30_000


def build_tweet_url_by_id(tweet_id: str) -> str:
    """بناء رابط التغريدة من ID فقط باستخدام الرابط العام."""
    tweet_id = str(tweet_id).strip()
    return f"https://x.com/i/status/{tweet_id}"


def delete_tweet_by_id(storage_state_path: str, tweet_id: str, headless: bool = True, wait_after_ms: int = 3000) -> bool:
    """
    حذف تغريدة من X باستخدام ID التغريدة فقط.
    
    Args:
        storage_state_path: مسار ملف الكوكيز
        tweet_id: ID التغريدة
        headless: تشغيل بدون واجهة
        wait_after_ms: وقت الانتظار بعد الحذف
    
    Returns:
        True إذا تم الحذف بنجاح
    """
    tweet_url = build_tweet_url_by_id(tweet_id)
    return delete_tweet(storage_state_path, tweet_url, headless, wait_after_ms)


def delete_tweet(storage_state_path: str, tweet_url: str, headless: bool = True, wait_after_ms: int = 3000) -> bool:
    """
    حذف تغريدة من X باستخدام رابطها.
    
    Args:
        storage_state_path: مسار ملف الكوكيز
        tweet_url: رابط التغريدة المراد حذفها
        headless: تشغيل بدون واجهة
        wait_after_ms: وقت الانتظار بعد الحذف
    
    Returns:
        True إذا تم الحذف بنجاح، False إذا فشل
    """
    chrome_channel = os.getenv("XSUITE_CHROME_CHANNEL", "").strip() or "chrome"
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel=chrome_channel, headless=headless)
        except Exception:
            browser = p.chromium.launch(headless=headless)
        
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            # الذهاب إلى صفحة التغريدة
            page.goto(tweet_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            # انتظار ظهور التغريدة
            tweet = page.get_by_test_id("tweet")
            tweet.first.wait_for(state="visible", timeout=30_000)
            
            # الضغط على زر القائمة (caret)
            caret = tweet.get_by_test_id("caret")
            if not caret.count():
                # fallback: البحث عن زر المزيد
                caret = page.locator('[aria-label="More"]').first
                if not caret.count():
                    caret = page.locator('[aria-label="المزيد"]').first
            
            caret.first.wait_for(state="visible", timeout=15_000)
            caret.first.click()
            page.wait_for_timeout(800)
            
            # الضغط على Delete
            delete_btn = page.get_by_text("Delete")
            if not delete_btn.count():
                delete_btn = page.get_by_text("حذف")
            if not delete_btn.count():
                # fallback: البحث في menuitem
                delete_btn = page.locator("div[role='menuitem']:has-text('Delete')")
                if not delete_btn.count():
                    delete_btn = page.locator("div[role='menuitem']:has-text('حذف')")
            
            delete_btn.first.wait_for(state="visible", timeout=10_000)
            delete_btn.first.click()
            page.wait_for_timeout(800)
            
            # تأكيد الحذف
            confirm = page.get_by_test_id("confirmationSheetConfirm")
            confirm.wait_for(state="visible", timeout=10_000)
            confirm.click()
            
            page.wait_for_timeout(wait_after_ms)
            return True
            
        except Exception as e:
            try:
                page.screenshot(path="debug_delete.png", full_page=True)
            except Exception:
                pass
            raise RuntimeError(f"فشل حذف التغريدة: {e}")
        finally:
            context.close()
            browser.close()
