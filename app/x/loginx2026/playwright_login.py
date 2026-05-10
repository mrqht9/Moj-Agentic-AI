#!/usr/bin/env python3
"""
Playwright Login - نظام تسجيل دخول باستخدام Playwright
يعتمد على Playwright مع متصفح حقيقي للحصول على جلسة حقيقية وحفظ الكوكيز
"""
import asyncio
import time
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
import logging

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('playwright_login.log'),
        logging.StreamHandler()
    ]
)

class PlaywrightLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        self.user_data_dir = self.cookies_dir / "playwright_profile"
        
    async def setup_browser(self):
        """إعداد المتصفح"""
        try:
            self.playwright = await async_playwright().start()
            
            # إعداد خيارات Chrome
            launch_options = {
                'headless': False,  # تشغيل المتصفح بشكل مرئي
                'args': [
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            }
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # إعداد context مع user data directory
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ignore_https_errors': True
            }
            
            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()
            
            # إخفاء أتمتة Playwright
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            logging.info("Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Playwright browser: {e}")
            return False
    
    async def check_existing_session(self):
        """التحقق من وجود جلسة محفوظة"""
        try:
            await self.page.goto("https://twitter.com", wait_until='networkidle')
            await asyncio.sleep(3)
            
            # التحقق من تسجيل الدخول عن طريق البحث عن زر التغريد
            try:
                await self.page.wait_for_selector('[data-testid="SideNav_AccountSwitcher_Button"]', timeout=5000)
                logging.info("Existing session found - already logged in")
                return True
            except:
                logging.info("No existing session found")
                return False
                
        except Exception as e:
            logging.error(f"Error checking existing session: {e}")
            return False
    
    async def perform_login(self):
        """تنفيذ عملية تسجيل الدخول"""
        try:
            # الذهاب إلى تويتر
            await self.page.goto("https://twitter.com", wait_until='networkidle')
            await asyncio.sleep(3)
            
            # البحث عن زر تسجيل الدخول
            login_selectors = [
                'a[data-testid="loginButton"]',
                'a[href="/login"]',
                '[data-testid="login"]',
                'text=Log in'
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=3000)
                    break
                except:
                    continue
            
            if not login_button:
                logging.error("Could not find login button")
                return False
            
            await login_button.click()
            logging.info("Login button clicked")
            await asyncio.sleep(3)
            
            # إدخال اسم المستخدم
            try:
                username_selectors = [
                    'input[name="text"]',
                    'input[autocomplete="username"]',
                    'input[data-testid="loginIdentifier"]',
                    '[data-testid="ocfEnterTextTextInput"]'
                ]
                
                username_input = None
                for selector in username_selectors:
                    try:
                        username_input = await self.page.wait_for_selector(selector, timeout=3000)
                        break
                    except:
                        continue
                
                if not username_input:
                    logging.error("Could not find username input")
                    return False
                
                await username_input.fill(self.username)
                logging.info(f"Username entered: {self.username}")
                
                # الضغط على Enter للمتابعة
                await username_input.press("Enter")
                await asyncio.sleep(3)
                
            except Exception as e:
                logging.error(f"Error entering username: {e}")
                return False
            
            # إدخال كلمة المرور
            try:
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]',
                    'input[data-testid="password"]',
                    '[data-testid="ocfEnterTextTextInput"]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = await self.page.wait_for_selector(selector, timeout=3000)
                        break
                    except:
                        continue
                
                if not password_input:
                    # جرب البحث عن طريق XPath
                    try:
                        password_input = await self.page.wait_for_selector('xpath=//input[@type="password"]', timeout=5000)
                    except:
                        logging.error("Could not find password input with any selector")
                        return False
                
                await password_input.fill(self.password)
                logging.info("Password entered")
                
                # الضغط على Enter لتسجيل الدخول
                await password_input.press("Enter")
                await asyncio.sleep(5)
                
            except Exception as e:
                logging.error(f"Error entering password: {e}")
                return False
            
            # التحقق من نجاح تسجيل الدخول
            try:
                # البحث عن دليل على تسجيل الدخول الناجح
                success_selectors = [
                    '[data-testid="SideNav_AccountSwitcher_Button"]',
                    '[data-testid="AppTabBar_Home_Link"]',
                    '[data-testid="primaryColumn"]'
                ]
                
                for selector in success_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logging.info("Login successful!")
                        return True
                    except:
                        continue
                
                logging.error("Login verification failed")
                return False
                
            except Exception as e:
                logging.error(f"Error verifying login: {e}")
                return False
                
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return False
    
    async def extract_cookies(self):
        """استخراج الكوكيز وحفظها"""
        try:
            # الحصول على الكوكيز من Playwright
            cookies = await self.context.cookies()
            
            # تحويل الكوكيز إلى صيغة Playwright
            playwright_cookies = []
            auth_token = None
            ct0 = None
            
            for cookie in cookies:
                if 'twitter.com' in cookie['domain'] or 'x.com' in cookie['domain']:
                    playwright_cookie = {
                        "name": cookie['name'],
                        "value": cookie['value'],
                        "domain": ".x.com",
                        "path": cookie.get('path', '/'),
                        "expires": cookie.get('expires', 2147483647.0),
                        "httpOnly": cookie.get('httpOnly', False),
                        "secure": cookie.get('secure', True),
                        "sameSite": "Lax" if cookie['name'] == 'ct0' else "None"
                    }
                    playwright_cookies.append(playwright_cookie)
                    
                    # حفظ القيم المهمة
                    if cookie['name'] == 'auth_token':
                        auth_token = cookie['value']
                    elif cookie['name'] == 'ct0':
                        ct0 = cookie['value']
            
            if not auth_token:
                logging.warning("auth_token not found in cookies")
                return None
            
            # حفظ الكوكيز بصيغة JSON
            cookie_data = {
                "cookies": playwright_cookies,
                "origins": []
            }
            
            timestamp = int(time.time())
            json_file = self.cookies_dir / f"playwright_{self.username}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, indent=2, ensure_ascii=False)
            
            # حفظ معلومات الجلسة
            session_info = {
                'username': self.username,
                'login_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'current_url': self.page.url,
                'title': await self.page.title()
            }
            
            session_file = self.cookies_dir / f"playwright_session_{self.username}_{timestamp}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Cookies saved to: {json_file}")
            logging.info(f"Session info saved to: {session_file}")
            logging.info(f"Auth token: {auth_token[:20]}...")
            logging.info(f"CSRF token: {ct0[:20] if ct0 else 'N/A'}...")
            
            return {
                'json_file': str(json_file),
                'session_file': str(session_file),
                'auth_token': auth_token,
                'ct0': ct0,
                'cookies_count': len(playwright_cookies)
            }
            
        except Exception as e:
            logging.error(f"Error extracting cookies: {e}")
            return None
    
    async def login(self):
        """العملية الكاملة لتسجيل الدخول"""
        logging.info("Starting Playwright login process")
        logging.info(f"Username: {self.username}")
        
        try:
            # تهيئة المتصفح
            if not await self.setup_browser():
                return None
            
            # التحقق من وجود جلسة محفوظة
            if await self.check_existing_session():
                # استخراج الكوكيز من الجلسة الحالية
                cookies_data = await self.extract_cookies()
                if cookies_data:
                    return cookies_data
            
            # تنفيذ تسجيل الدخول
            if await self.perform_login():
                # استخراج الكوكيز بعد تسجيل الدخول الناجح
                cookies_data = await self.extract_cookies()
                if cookies_data:
                    return cookies_data
            
            logging.error("Login process failed")
            return None
            
        except Exception as e:
            logging.error(f"Login process error: {e}")
            return None
        
        finally:
            # إغلاق المتصفح
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logging.info("Browser closed")

async def main():
    """الوظيفة الرئيسية"""
    logging.info("PLAYWRIGHT LOGIN SYSTEM")
    logging.info("Real browser automation with cookie extraction")
    logging.info("=" * 60)
    
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    playwright_login = PlaywrightLogin(username, password)
    
    try:
        result = await playwright_login.login()
        
        if result:
            logging.info("\nPLAYWRIGHT LOGIN SUCCESSFUL!")
            logging.info(f"Auth token: {result['auth_token'][:20]}...")
            logging.info(f"CSRF token: {result['ct0'][:20] if result['ct0'] else 'N/A'}...")
            logging.info(f"Cookies saved: {result['cookies_count']}")
            logging.info(f"JSON file: {result['json_file']}")
            logging.info(f"Session file: {result['session_file']}")
            
            print(f"\n[+] Login successful!")
            print(f"[+] Cookies saved to: {result['json_file']}")
            print(f"[+] Auth token: {result['auth_token'][:20]}...")
            
        else:
            logging.error("\nPLAYWRIGHT LOGIN FAILED!")
            print(f"\n[-] Login failed!")
            print("Check the log file for details: playwright_login.log")
            
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
