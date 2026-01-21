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

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=headless)
            context = self.create_stealth_firefox_context(browser, proxy_config)
            page = context.new_page()
            self.inject_firefox_stealth(page)

            page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
            time.sleep(random.uniform(2.5, 4.5))
            self.human_actions(page)

            username_input = page.locator('input[autocomplete="username"]')
            username_input.wait_for(state="visible", timeout=20000)
            self.type_like_human(username_input, username)

            time.sleep(random.uniform(1.0, 2.5))
            try:
                page.get_by_role("button", name="Next").click()
            except Exception:
                btn = page.locator('button:has-text("Next")')
                if not btn.is_visible():
                    btn = page.locator('button:has-text("التالي")')
                btn.first.click()

            time.sleep(random.uniform(2.5, 4.5))

            # password
            password_input = page.locator('input[type="password"]')
            password_input.wait_for(state="visible", timeout=20000)
            self.type_like_human(password_input, password)

            time.sleep(random.uniform(1.5, 3.0))
            try:
                page.locator('button[data-testid="LoginForm_Login_Button"]').click()
            except Exception:
                try:
                    page.get_by_role("button", name="Log in").click()
                except Exception:
                    page.get_by_role("button", name="تسجيل الدخول").click()

            time.sleep(8)

            if not self.check_login_success(page):
                # Save screenshot for debugging
                try:
                    page.screenshot(path=str(cookie_path).replace('.json','_failed.png'), full_page=True)
                except Exception:
                    pass
                browser.close()
                raise RuntimeError("فشل تسجيل الدخول (أو يحتاج تحقق إضافي).")

            # Save storage state
            context.storage_state(path=str(cookie_path))
            browser.close()
            return cookie_path
