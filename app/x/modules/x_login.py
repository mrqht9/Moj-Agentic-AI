import os
import random
import re
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright


class TwitterLoginAdvanced:
    def _safe_cookie_filename(self, username: str) -> str:
        s = (username or '').strip()
        s = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", s)
        if not s:
            s = "account"
        if not s.endswith('.json'):
            s += '.json'
        return s[:120]

    def inject_firefox_stealth(self, page):
        stealth_js = r"""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """
        page.add_init_script(stealth_js)

    def create_stealth_firefox_context(self, browser, proxy_config=None):
        args = {
            "viewport": {"width": 1280, "height": 820},
            "locale": "ar-SA",
            "timezone_id": "Asia/Riyadh",
        }
        if proxy_config:
            args["proxy"] = proxy_config
        return browser.new_context(**args)

    def human_actions(self, page):
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1100)
            y = random.randint(100, 700)
            page.mouse.move(x, y, steps=random.randint(8, 20))
            time.sleep(random.uniform(0.15, 0.4))
        page.evaluate("window.scrollTo({top: Math.random() * 200, behavior: 'smooth'});")
        time.sleep(random.uniform(0.8, 1.6))

    def type_like_human(self, element, text: str):
        element.click()
        time.sleep(random.uniform(0.4, 1.0))
        for ch in text:
            element.type(ch, delay=random.randint(60, 170))
            if random.random() < 0.08:
                time.sleep(random.uniform(0.15, 0.5))

    def check_login_success(self, page) -> bool:
        time.sleep(4)
        current_url = page.url
        checks = []
        if "home" in current_url or current_url.startswith("https://x.com/home"):
            checks.append(True)
        elif "login" not in current_url and "flow" not in current_url:
            checks.append(True)
        else:
            checks.append(False)

        try:
            tweet_button = page.locator('[data-testid="SideNav_NewTweet_Button"]')
            checks.append(bool(tweet_button.is_visible(timeout=3000)))
        except Exception:
            checks.append(False)

        try:
            cookies = page.context.cookies()
            checks.append(any(c.get('name') == 'auth_token' for c in cookies))
        except Exception:
            checks.append(False)

        return sum(checks) >= 2

    def login_twitter(self, username: str, password: str, cookies_dir: str = "cookies", headless: bool = False, proxy_config=None) -> Path:
        cookies_dir_p = Path(cookies_dir)
        cookies_dir_p.mkdir(parents=True, exist_ok=True)
        cookie_path = cookies_dir_p / self._safe_cookie_filename(username)

        print(f"[DEBUG] Starting login for user: {username}")
        print(f"[DEBUG] Headless mode: {headless}")
        
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=headless)
            print("[DEBUG] Browser launched")
            context = self.create_stealth_firefox_context(browser, proxy_config)
            page = context.new_page()
            self.inject_firefox_stealth(page)

            print("[DEBUG] Navigating to X login page...")
            page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
            time.sleep(random.uniform(3.5, 6.0))
            self.human_actions(page)
            # تأخير إضافي لمحاكاة قراءة الصفحة
            time.sleep(random.uniform(1.5, 3.0))

            print("[DEBUG] Looking for username field...")
            username_input = page.locator('input[autocomplete="username"]')
            username_input.wait_for(state="visible", timeout=20000)
            print("[DEBUG] Username field found")
            
            # انقر على الحقل أولاً
            username_input.click()
            time.sleep(random.uniform(0.3, 0.8))
            
            self.type_like_human(username_input, username)
            print("[DEBUG] Username entered")
            
            # تأخير بعد الكتابة
            time.sleep(random.uniform(0.5, 1.5))

            time.sleep(random.uniform(1.5, 3.0))
            print("[DEBUG] Clicking Next button...")
            try:
                next_btn = page.get_by_role("button", name="Next")
                # hover قبل الضغط
                next_btn.hover()
                time.sleep(random.uniform(0.2, 0.5))
                next_btn.click()
                print("[DEBUG] Next button clicked (method 1)")
            except Exception:
                btn = page.locator('button:has-text("Next")')
                if not btn.is_visible():
                    btn = page.locator('button:has-text("التالي")')
                btn.first.hover()
                time.sleep(random.uniform(0.2, 0.5))
                btn.first.click()
                print("[DEBUG] Next button clicked (method 2)")

            time.sleep(random.uniform(4.0, 7.0))

            # التحقق من رسالة "please try later"
            print("[DEBUG] Checking for rate limit or error messages...")
            try:
                error_messages = [
                    page.locator('text="Please try again later"'),
                    page.locator('text="try again later"'),
                    page.locator('text="try later"'),
                    page.locator('span:has-text("try again later")'),
                    page.locator('div:has-text("try again later")')
                ]
                
                for error_loc in error_messages:
                    if error_loc.count() > 0 and error_loc.first.is_visible():
                        print("[ERROR] X is showing 'please try later' message")
                        page.screenshot(path="rate_limit_error.png", full_page=True)
                        raise RuntimeError("❌ X يطلب المحاولة لاحقاً (Please try later).\n\n💡 **الأسباب المحتملة:**\n1. تم اكتشاف نشاط غير عادي\n2. محاولات تسجيل دخول كثيرة\n3. الحساب يحتاج تحقق يدوي\n\n🔄 **الحل:**\n1. انتظر 15-30 دقيقة ثم حاول مرة أخرى\n2. أو سجل دخول يدوياً من المتصفح العادي أولاً\n3. تحقق من الصورة: rate_limit_error.png")
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[DEBUG] No rate limit detected: {e}")

            # التحقق من وجود طلبات تحقق إضافية (رقم هاتف، بريد إلكتروني، إلخ)
            print("[DEBUG] Checking for additional verification requests...")
            try:
                # فحص إذا طلب X رقم هاتف أو بريد إلكتروني
                unusual_activity = page.locator('input[data-testid="ocfEnterTextTextInput"]')
                if unusual_activity.count() > 0 and unusual_activity.first.is_visible():
                    print("[WARNING] X is requesting additional verification (phone/email)")
                    print("[INFO] This account may need manual verification")
                    # أخذ screenshot للمستخدم
                    page.screenshot(path="verification_required.png", full_page=True)
                    raise RuntimeError("❌ X يطلب تحقق إضافي (رقم هاتف أو بريد إلكتروني).\n\n💡 **الحل:**\n1. أدخل رقم الهاتف أو البريد الإلكتروني يدوياً في نافذة المتصفح\n2. أو سجل دخول من المتصفح العادي أولاً\n3. تحقق من الصورة: verification_required.png")
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[DEBUG] No additional verification detected: {e}")

            # password
            print("[DEBUG] Looking for password field...")
            password_input = page.locator('input[type="password"]')
            try:
                password_input.wait_for(state="visible", timeout=30000)
                print("[DEBUG] Password field found")
            except Exception as e:
                print(f"[ERROR] Password field not found: {e}")
                # أخذ screenshot للتشخيص
                page.screenshot(path="password_field_not_found.png", full_page=True)
                print("[DEBUG] Screenshot saved: password_field_not_found.png")
                raise RuntimeError(f"لم يتم العثور على حقل كلمة المرور. قد يكون X طلب تحقق إضافي. تحقق من: password_field_not_found.png")
            
            # انقر على حقل كلمة المرور
            password_input.click()
            time.sleep(random.uniform(0.3, 0.8))
            
            self.type_like_human(password_input, password)
            print("[DEBUG] Password entered")
            
            # تأخير بعد كتابة كلمة المرور
            time.sleep(random.uniform(0.5, 1.5))

            time.sleep(random.uniform(2.0, 3.5))
            print("[DEBUG] Clicking login button...")
            try:
                login_btn = page.locator('button[data-testid="LoginForm_Login_Button"]')
                login_btn.hover()
                time.sleep(random.uniform(0.3, 0.7))
                login_btn.click()
                print("[DEBUG] Login button clicked (method 1)")
            except Exception:
                try:
                    login_btn = page.get_by_role("button", name="Log in")
                    login_btn.hover()
                    time.sleep(random.uniform(0.3, 0.7))
                    login_btn.click()
                    print("[DEBUG] Login button clicked (method 2)")
                except Exception:
                    login_btn = page.get_by_role("button", name="تسجيل الدخول")
                    login_btn.hover()
                    time.sleep(random.uniform(0.3, 0.7))
                    login_btn.click()
                    print("[DEBUG] Login button clicked (method 3)")

            print("[DEBUG] Waiting for login to complete...")
            time.sleep(random.uniform(10.0, 15.0))

            print("[DEBUG] Checking login success...")
            if not self.check_login_success(page):
                # Save screenshot for debugging
                screenshot_path = str(cookie_path).replace('.json','_failed.png')
                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[DEBUG] Login failed screenshot saved: {screenshot_path}")
                except Exception as e:
                    print(f"[ERROR] Could not save screenshot: {e}")
                
                # حفظ HTML للتشخيص
                try:
                    html_path = str(cookie_path).replace('.json','_failed.html')
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(page.content())
                    print(f"[DEBUG] HTML saved: {html_path}")
                except Exception as e:
                    print(f"[ERROR] Could not save HTML: {e}")
                
                browser.close()
                raise RuntimeError(f"فشل تسجيل الدخول (أو يحتاج تحقق إضافي). تحقق من الملفات: {screenshot_path}")

            # Save storage state
            print("[DEBUG] Login successful! Saving cookies...")
            context.storage_state(path=str(cookie_path))
            print(f"[DEBUG] Cookies saved to: {cookie_path}")
            browser.close()
            return cookie_path
