import time
from typing import Optional
from pathlib import Path
from playwright.sync_api import sync_playwright


# =================
# Tunables
# =================
MEDIA_TIMEOUT_MS = 240_000        # للفيديو نحتاج أطول
POST_DONE_TIMEOUT_MS = 60_000
DEFAULT_TIMEOUT = 30_000

POST_CLICK_DELAY_MS = 5000        # 5 ثواني بعد الضغط كما طلبت


def _get_scope(page):
    dlg = page.locator("div[role='dialog']")
    return dlg.first if dlg.count() else page


def _is_video_file(media_path: str) -> bool:
    ext = (Path(media_path).suffix or "").lower()
    return ext in {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def _pick_composer_file_input(page):
    scope = _get_scope(page)

    loc = scope.locator('input[type="file"][data-testid="fileInput"]')
    if loc.count():
        return loc.first

    loc = scope.locator('input[type="file"]')
    if loc.count():
        for i in range(min(loc.count(), 10)):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    return item
            except Exception:
                pass
        return loc.first

    loc = page.locator('input[type="file"][data-testid="fileInput"]')
    if loc.count():
        return loc.first

    return page.locator('input[type="file"]').first


def _get_textbox(page):
    """البحث عن textbox بطرق متعددة مع انتظار أفضل"""
    # انتظر ظهور dialog أو composer
    page.wait_for_timeout(1000)
    
    scope = _get_scope(page)
    
    # الطريقة 1: data-testid مع role
    try:
        tb = scope.locator('div[data-testid="tweetTextarea_0"][role="textbox"]')
        if tb.count():
            tb.first.wait_for(state="visible", timeout=10000)
            return tb.first
    except Exception:
        pass
    
    # الطريقة 2: data-testid فقط
    try:
        tb2 = scope.locator('div[data-testid="tweetTextarea_0"]')
        if tb2.count():
            tb2.first.wait_for(state="visible", timeout=10000)
            return tb2.first
    except Exception:
        pass
    
    # الطريقة 3: أي textbox في الصفحة
    try:
        tb3 = page.locator('[contenteditable="true"][role="textbox"]').first
        tb3.wait_for(state="visible", timeout=10000)
        return tb3
    except Exception:
        pass
    
    # الطريقة 4: البحث بـ placeholder
    try:
        tb4 = page.locator('[placeholder*="What"], [placeholder*="happening"], [placeholder*="يحدث"]').first
        tb4.wait_for(state="visible", timeout=10000)
        return tb4
    except Exception:
        pass
    
    raise Exception("لم يتم العثور على textbox للكتابة")


def _media_preview_visible(page) -> bool:
    scope = _get_scope(page)
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
    ]
    for sel in candidates:
        try:
            loc = scope.locator(sel)
            if loc.count() and loc.first.is_visible():
                return True
        except Exception:
            pass
    return False


def _media_uploading_indicator_visible(page) -> bool:
    scope = _get_scope(page)

    candidates = [
        # مؤشرات واضحة للميديا
        'div[data-testid="mediaUploadProgress"]',
        '#layers div[data-testid="mediaUploadProgress"]',

        # progressbar داخل منطقة attachments (أفضل من العام)
        'div[data-testid="attachments"] div[role="progressbar"]',
        'div[data-testid="mediaContainer"] div[role="progressbar"]',
        'div[data-testid="tweetPhotoContainer"] div[role="progressbar"]',
        'div[data-testid="videoPlayer"] div[role="progressbar"]',

        # نصوص/ARIA شائعة (عربي/انجليزي)
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


def _wait_media_uploaded_or_ready(page, timeout_ms: int = MEDIA_TIMEOUT_MS):
    """
    انتظار عام: ظهور الميديا + اختفاء مؤشرات الرفع (إن وجدت).
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    scope = _get_scope(page)

    remove_btn = scope.locator(
        '#layers [aria-label="Remove"], #layers [aria-label="Remove media"], '
        '#layers [aria-label="إزالة"], #layers [aria-label="حذف"], '
        '#layers [data-testid*="remove"]'
    )

    saw_preview = False
    while time.time() < deadline:
        if _media_preview_visible(page) or (remove_btn.count() and remove_btn.first.is_visible()):
            saw_preview = True

        if not saw_preview:
            page.wait_for_timeout(250)
            continue

        if not _media_uploading_indicator_visible(page):
            page.wait_for_timeout(700)
            return True

        page.wait_for_timeout(400)

    raise TimeoutError("انتهت مهلة انتظار رفع/معالجة الميديا.")


def _wait_media_processed_video(page, timeout_ms: int = MEDIA_TIMEOUT_MS):
    """
    للفيديو تحديدًا: ننتظر “اختفاء” أي مؤشرات رفع/Processing لفترة مستقرة.
    لأن الفيديو أحيانًا يختفي المؤشر ثم يرجع.
    """
    deadline = time.time() + (timeout_ms / 1000.0)

    stable_needed = 3          # عدد مرات متتالية نرى فيها "لا يوجد مؤشر" قبل اعتباره جاهز
    stable_hits = 0

    while time.time() < deadline:
        if _media_uploading_indicator_visible(page):
            stable_hits = 0
            page.wait_for_timeout(600)
            continue

        # لا يوجد مؤشر => نزيد العد
        stable_hits += 1
        if stable_hits >= stable_needed:
            # تهدئة إضافية للفيديو
            page.wait_for_timeout(1200)
            return True

        page.wait_for_timeout(500)

    raise TimeoutError("انتهت مهلة انتظار اكتمال معالجة الفيديو.")


def _wait_publish_button_enabled(page, timeout_ms: int = MEDIA_TIMEOUT_MS):
    """
    أهم شرط عندك:
    انتظر حتى زر النشر يصبح متاحًا (enabled + aria-disabled != true)
    ثم ارجع فورًا.
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    scope = _get_scope(page)

    while time.time() < deadline:
        btn = scope.locator('button[data-testid="tweetButtonInline"]')
        if not (btn.count() and btn.first.is_visible()):
            btn = scope.locator('button[data-testid="tweetButton"]')

        try:
            if btn.count() and btn.first.is_visible():
                aria = btn.first.get_attribute("aria-disabled")
                disabled = (aria == "true")
                # is_enabled غالبًا أدق
                try:
                    if btn.first.is_enabled() and not disabled:
                        return True
                except Exception:
                    if not disabled:
                        return True
        except Exception:
            pass

        page.wait_for_timeout(400)

    raise TimeoutError("زر النشر لم يصبح متاحًا ضمن المهلة.")


def _click_publish(page):
    """البحث عن زر النشر والضغط عليه بطرق متعددة"""
    # انتظر قليلاً للتأكد من تحميل الزر
    page.wait_for_timeout(1000)
    
    scope = _get_scope(page)
    btn = None
    
    # الطريقة 1: tweetButtonInline (في dialog)
    try:
        btn_inline = scope.locator('button[data-testid="tweetButtonInline"]')
        if btn_inline.count() > 0 and btn_inline.first.is_visible():
            btn = btn_inline.first
            print("[DEBUG] Found tweetButtonInline")
    except Exception as e:
        print(f"[DEBUG] tweetButtonInline not found: {e}")
    
    # الطريقة 2: tweetButton (العادي)
    if not btn:
        try:
            btn_normal = scope.locator('button[data-testid="tweetButton"]')
            if btn_normal.count() > 0:
                btn_normal.first.wait_for(state="visible", timeout=10000)
                btn = btn_normal.first
                print("[DEBUG] Found tweetButton")
        except Exception as e:
            print(f"[DEBUG] tweetButton not found: {e}")
    
    # الطريقة 3: البحث بالنص "Post" أو "Tweet"
    if not btn:
        try:
            btn_text = scope.locator('button:has-text("Post"), button:has-text("Tweet"), button:has-text("نشر")')
            if btn_text.count() > 0:
                btn = btn_text.first
                print("[DEBUG] Found button by text")
        except Exception as e:
            print(f"[DEBUG] Button by text not found: {e}")
    
    # الطريقة 4: البحث في الصفحة كاملة (خارج dialog)
    if not btn:
        try:
            btn_page = page.locator('button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"]')
            if btn_page.count() > 0:
                btn = btn_page.first
                print("[DEBUG] Found button in page")
        except Exception as e:
            print(f"[DEBUG] Button in page not found: {e}")
    
    if not btn:
        # أخذ screenshot للتشخيص
        try:
            page.screenshot(path="debug_no_button.png", full_page=True)
            print("[DEBUG] Screenshot saved to debug_no_button.png")
        except Exception:
            pass
        raise Exception("لم يتم العثور على زر النشر. تم حفظ screenshot للتشخيص.")
    
    # محاولة الضغط
    btn.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    
    # المحاولة 1: click عادي
    try:
        btn.click(timeout=8_000)
        print("[DEBUG] Button clicked successfully")
        return
    except Exception as e:
        print(f"[DEBUG] Normal click failed: {e}")
    
    # المحاولة 2: force click
    try:
        btn.click(timeout=8_000, force=True)
        print("[DEBUG] Button force clicked successfully")
        return
    except Exception as e:
        print(f"[DEBUG] Force click failed: {e}")
    
    # المحاولة 3: mouse click على الإحداثيات
    try:
        box = btn.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            print("[DEBUG] Button clicked via mouse coordinates")
            return
    except Exception as e:
        print(f"[DEBUG] Mouse click failed: {e}")
    
    raise Exception("فشل الضغط على زر النشر بجميع الطرق")


def _wait_post_done(page, timeout_ms: int = POST_DONE_TIMEOUT_MS):
    deadline = time.time() + (timeout_ms / 1000.0)
    dialog = page.locator("div[role='dialog']")
    toast = page.locator("div[role='status'], div[aria-live='polite'], div[aria-live='assertive']")

    while time.time() < deadline:
        try:
            if dialog.count() == 0:
                return True
            if dialog.first.is_visible() is False:
                return True
        except Exception:
            pass

        try:
            if toast.count() and toast.first.is_visible():
                return True
        except Exception:
            pass

        page.wait_for_timeout(300)

    return False


def post_to_x(storage_state_path: str, text: str, media_path: Optional[str], headless: bool):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            page.goto("https://x.com/home", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            
            # التحقق من تسجيل الدخول
            print("[DEBUG] Checking if logged in...")
            if page.locator('input[name="text"]').count() > 0 or "login" in page.url.lower() or "signin" in page.url.lower():
                print("[ERROR] Not logged in - session expired!")
                raise Exception("الجلسة منتهية. يجب إعادة تسجيل الدخول.")
            
            print("[DEBUG] Login verified, proceeding to post...")

            # محاولة الضغط على زر New Tweet بطرق متعددة
            new_tweet_clicked = False
            
            # الطريقة 1: data-testid
            try:
                btn = page.get_by_test_id("SideNav_NewTweet_Button")
                if btn.count() > 0:
                    btn.click(timeout=5000)
                    new_tweet_clicked = True
            except Exception:
                pass
            
            # الطريقة 2: البحث بالنص
            if not new_tweet_clicked:
                try:
                    # ابحث عن زر يحتوي على "Post" أو "Tweet"
                    btn = page.locator('a[href="/compose/tweet"], a[href="/compose/post"]')
                    if btn.count() > 0:
                        btn.first.click(timeout=5000)
                        new_tweet_clicked = True
                except Exception:
                    pass
            
            # الطريقة 3: البحث بـ aria-label
            if not new_tweet_clicked:
                try:
                    btn = page.locator('[aria-label*="Post"], [aria-label*="Tweet"], [aria-label*="New"]')
                    if btn.count() > 0:
                        btn.first.click(timeout=5000)
                        new_tweet_clicked = True
                except Exception:
                    pass
            
            # الطريقة 4: استخدام الاختصار (Ctrl+N أو Cmd+N)
            if not new_tweet_clicked:
                try:
                    page.keyboard.press("Control+N")
                    new_tweet_clicked = True
                except Exception:
                    pass
            
            if not new_tweet_clicked:
                raise Exception("لم يتم العثور على زر New Tweet. قد تحتاج إلى إعادة تسجيل الدخول.")
            
            page.wait_for_timeout(2000)
            
            print("[DEBUG] Looking for textbox...")
            textbox = _get_textbox(page)
            print("[DEBUG] Textbox found, clicking...")
            textbox.click()
            page.wait_for_timeout(500)

            # اكتب النص أولاً
            print(f"[DEBUG] Writing text: {text[:50]}...")
            try:
                textbox.fill(text)
                print("[DEBUG] Text filled successfully")
            except Exception as e:
                print(f"[DEBUG] Fill failed, trying type: {e}")
                textbox.click()
                textbox.press("Control+A")
                textbox.type(text, delay=10)
                print("[DEBUG] Text typed successfully")
            
            # انتظر قليلاً بعد الكتابة
            page.wait_for_timeout(1000)

            # لو فيه ميديا
            if media_path and str(media_path).strip():
                file_input = _pick_composer_file_input(page)
                file_input.wait_for(state="attached", timeout=DEFAULT_TIMEOUT)
                file_input.set_input_files(media_path)

                # 1) انتظر ظهور الميديا بشكل عام
                _wait_media_uploaded_or_ready(page, timeout_ms=MEDIA_TIMEOUT_MS)

                # 2) إذا فيديو: انتظر معالجة “أثبت”
                if _is_video_file(media_path):
                    _wait_media_processed_video(page, timeout_ms=MEDIA_TIMEOUT_MS)

                # 3) الشرط الأهم: انتظر زر النشر يصبح متاح
                _wait_publish_button_enabled(page, timeout_ms=MEDIA_TIMEOUT_MS)

            # انشر
            _click_publish(page)

            # انتظر 5 ثواني بعد الضغط ثم اخرج
            page.wait_for_timeout(POST_CLICK_DELAY_MS)

            # (اختياري) تأكيد سريع
            _wait_post_done(page, timeout_ms=POST_DONE_TIMEOUT_MS)

            print("[DEBUG] Post completed successfully!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Post failed: {e}")
            try:
                page.screenshot(path="debug_post.png", full_page=True)
            except Exception:
                pass
            try:
                with open("debug_post.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
            except Exception:
                pass
            raise
        finally:
            context.close()
            browser.close()
