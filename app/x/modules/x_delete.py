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
        # إعدادات أفضل للـ headless
        launch_args = {
            "channel": chrome_channel,
            "headless": headless,
        }
        
        # في وضع headless، أضف إعدادات إضافية لتجنب المشاكل
        if headless:
            launch_args.update({
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--window-size=1920,1080"
                ]
            })
        
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception:
            browser = p.chromium.launch(headless=headless)
        
        # إعدادات السياق مع viewport مناسب
        context = browser.new_context(
            storage_state=storage_state_path,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            # الذهاب إلى صفحة التغريدة
            print(f"[DEBUG] Navigating to: {tweet_url}")
            page.goto(tweet_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            # تحقق إذا كانت الصفحة تعرض خطأ (تغريدة محذوفة)
            current_url = page.url
            print(f"[DEBUG] Current URL after navigation: {current_url}")
            
            if "status" not in current_url and "i/web/status" not in current_url:
                print("[DEBUG] Tweet not found or deleted")
                return False
            
            # انتظار ظهور التغريدة مع تحقق أفضل
            tweet = page.get_by_test_id("tweet")
            if tweet.count() == 0:
                print("[DEBUG] No tweet elements found with test_id='tweet'")
                # جرب selectors أخرى
                tweet = page.locator('[data-testid="tweet"]')
                if tweet.count() == 0:
                    tweet = page.locator('article[role="article"]')
                    if tweet.count() == 0:
                        print("[DEBUG] No tweet found with any selector")
                        return False
            
            print(f"[DEBUG] Found {tweet.count()} tweet elements")
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
            if not delete_btn.count():
                # fallback: البحث بأي طريقة ممكنة
                delete_btn = page.locator("[role='menuitem']").filter(has_text="Delete")
                if not delete_btn.count():
                    delete_btn = page.locator("[role='menuitem']").filter(has_text="حذف")
            if not delete_btn.count():
                # fallback: بحث عام
                delete_btn = page.locator("text=Delete")
                if not delete_btn.count():
                    delete_btn = page.locator("text=حذف")
            
            print(f"[DEBUG] Found {delete_btn.count()} delete buttons")
            if delete_btn.count() == 0:
                print("[DEBUG] No delete button found, taking screenshot for debug")
                page.screenshot(path="debug_delete_menu.png")
                return False
            
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
