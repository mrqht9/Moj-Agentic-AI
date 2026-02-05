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
    scope = _get_scope(page)

    tb = scope.locator('div[data-testid="tweetTextarea_0"][role="textbox"]')
    if tb.count():
        tb.first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        return tb.first

    tb2 = scope.locator('div[data-testid="tweetTextarea_0"]')
    if tb2.count():
        tb2.first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        return tb2.first

    tb3 = page.get_by_role("textbox")
    tb3.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
    return tb3


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
    scope = _get_scope(page)

    btn = scope.locator('button[data-testid="tweetButtonInline"]')
    if not (btn.count() and btn.first.is_visible()):
        btn = scope.locator('button[data-testid="tweetButton"]')

    btn.first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
    btn.first.scroll_into_view_if_needed()

    try:
        btn.first.click(timeout=8_000)
        return
    except Exception:
        pass

    try:
        btn.first.click(timeout=8_000, force=True)
        return
    except Exception:
        pass

    box = btn.first.bounding_box()
    if box:
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


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


def _copy_tweet_link(page, timeout_ms: int = 30_000) -> Optional[str]:
    """
    بعد النشر، اضغط على التغريدة من الـ toast ثم انسخ رابطها.
    يُرجع رابط التغريدة أو None إذا فشل.
    """
    import re
    try:
        # انتظر ظهور الـ toast ثم اضغط على رابط التغريدة
        page.wait_for_timeout(2000)
        
        # اضغط على رابط التغريدة في الـ toast
        toast_link = page.get_by_test_id("toast").locator("a")
        toast_link.wait_for(state="visible", timeout=timeout_ms)
        toast_link.click()
        page.wait_for_timeout(2500)
        
        # اضغط على زر المشاركة
        share_btn = page.get_by_role("button", name="Share post")
        share_btn.wait_for(state="visible", timeout=15_000)
        share_btn.click()
        page.wait_for_timeout(1000)
        
        # اضغط على نسخ الرابط
        copy_link = page.locator("div").filter(has_text=re.compile(r"^Copy link$")).nth(2)
        copy_link.wait_for(state="visible", timeout=10_000)
        copy_link.click()
        page.wait_for_timeout(500)
        
        # الحصول على الرابط من URL الحالي
        current_url = page.url
        if "/status/" in current_url:
            return current_url
        
        return None
    except Exception as e:
        print(f"فشل نسخ رابط التغريدة: {e}")
        return None


def post_to_x(storage_state_path: str, text: str, media_path: Optional[str], headless: bool) -> Optional[str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=headless)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            page.goto("https://x.com/home", wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            page.get_by_test_id("SideNav_NewTweet_Button").click(timeout=DEFAULT_TIMEOUT)
            page.wait_for_timeout(900)

            textbox = _get_textbox(page)
            textbox.click()

            # اكتب النص أولاً
            try:
                textbox.fill(text)
            except Exception:
                textbox.click()
                textbox.press("Control+A")
                textbox.type(text, delay=10)

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

            # انتظر ثانيتين بعد النشر
            page.wait_for_timeout(2000)

            # نسخ رابط التغريدة بعد النشر
            tweet_url = _copy_tweet_link(page, timeout_ms=30_000)
            return tweet_url

        except Exception:
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
    
    return None
