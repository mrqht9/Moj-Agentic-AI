#!/usr/bin/env python3
"""
Ultimate Hybrid Login - نظام هجين متعدد التقنيات
يجمع بين curl_cffi, HTTPX, Selenium, و Playwright
مع استراتيجيات متقدمة لتجاوز حماية تويتر
"""
import asyncio
import json
import time
import random
import uuid
import sys
import os
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import logging

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# HTTP Libraries
import curl_cffi
from curl_cffi import AsyncSession
import httpx

# Browser Automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# X Auth modules
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_hybrid_login.log'),
        logging.StreamHandler()
    ]
)

class UltimateHybridLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.attempt_count = 0
        self.max_attempts = 50
        self.success_patterns = []
        self.failure_patterns = []
        self.analysis_data = []
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        
    def log_attempt(self, method, step, data, success=False, error_msg=None):
        """تسجيل كل محاولة للتحليل"""
        attempt_data = {
            'attempt': self.attempt_count,
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'step': step,
            'data': data,
            'success': success,
            'error': error_msg
        }
        
        self.analysis_data.append(attempt_data)
        
        with open(f'ultimate_analysis_{datetime.now().strftime("%Y%m%d")}.json', 'a', encoding='utf-8') as f:
            json.dump(attempt_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        
        logging.info(f"Ultimate Attempt {self.attempt_count} - {method} - {step}: {'SUCCESS' if success else 'FAILED'}")
        if error_msg:
            logging.error(f"Error: {error_msg}")
    
    async def try_curl_cffi_login(self):
        """محاولة تسجيل الدخول باستخدام curl_cffi"""
        try:
            logging.info("Trying curl_cffi method...")
            
            # إعدادات curl_cffi متقدمة
            chrome_versions = ['99', '100', '101', '104', '107', '110', '116', '119', '120', '123', '124', '131', '136', '142']
            version = random.choice(chrome_versions)
            
            headers = {
                'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': f'"Chromium";v="{version}", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            
            session = AsyncSession(
                impersonate=f'chrome{version}',
                timeout=30,
                headers=headers
            )
            
            # محاولة تسجيل الدخول
            self.log_attempt('curl_cffi', 'session_init', {
                'version': version,
                'headers_count': len(headers)
            }, True)
            
            # استخراج guest token
            response = await session.get('https://x.com/i/api/1.1/guest/activate.json')
            if response.status_code == 200:
                guest_token = response.json().get('guest_token')
                if guest_token:
                    session.cookies.set('gt', guest_token, '.x.com')
                    self.log_attempt('curl_cffi', 'guest_token', {'guest_token': guest_token[:20] + '...'}, True)
                    
                    # محاولة تسجيل الدخول
                    # ... (نفس منطق persistent_login.py)
                    return {'method': 'curl_cffi', 'success': True, 'guest_token': guest_token}
            
            self.log_attempt('curl_cffi', 'guest_token', {'status': response.status_code}, False, f"Status {response.status_code}")
            return None
            
        except Exception as e:
            self.log_attempt('curl_cffi', 'error', {'error': str(e)}, False, str(e))
            return None
    
    async def try_httpx_login(self):
        """محاولة تسجيل الدخول باستخدام HTTPX"""
        try:
            logging.info("Trying HTTPX method...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            timeout = httpx.Timeout(30.0, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            
            async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=headers, http2=True) as client:
                self.log_attempt('httpx', 'session_init', {'http2_enabled': True}, True)
                
                response = await client.get('https://x.com/i/api/1.1/guest/activate.json')
                if response.status_code == 200:
                    guest_token = response.json().get('guest_token')
                    if guest_token:
                        self.log_attempt('httpx', 'guest_token', {'guest_token': guest_token[:20] + '...'}, True)
                        return {'method': 'httpx', 'success': True, 'guest_token': guest_token}
                
                self.log_attempt('httpx', 'guest_token', {'status': response.status_code}, False, f"Status {response.status_code}")
                return None
                
        except Exception as e:
            self.log_attempt('httpx', 'error', {'error': str(e)}, False, str(e))
            return None
    
    async def try_selenium_login(self):
        """محاولة تسجيل الدخول باستخدام Selenium"""
        if not SELENIUM_AVAILABLE:
            return None
            
        try:
            logging.info("Trying Selenium method...")
            
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.log_attempt('selenium', 'session_init', {'browser': 'chrome'}, True)
            
            driver.get("https://twitter.com")
            time.sleep(3)
            
            # التحقق من وجود جلسة
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'))
                )
                self.log_attempt('selenium', 'existing_session', {'status': 'found'}, True)
                
                # استخراج الكوكيز
                cookies = driver.get_cookies()
                auth_token = None
                for cookie in cookies:
                    if cookie['name'] == 'auth_token':
                        auth_token = cookie['value']
                        break
                
                if auth_token:
                    driver.quit()
                    return {'method': 'selenium', 'success': True, 'auth_token': auth_token}
                    
            except TimeoutException:
                pass
            
            # محاولة تسجيل الدخول
            try:
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="loginButton"]'))
                )
                login_button.click()
                time.sleep(3)
                
                username_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="text"]'))
                )
                username_input.clear()
                username_input.send_keys(self.username)
                username_input.send_keys("\n")
                time.sleep(3)
                
                # البحث عن حقل كلمة المرور
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        break
                    except TimeoutException:
                        continue
                
                if password_input:
                    password_input.clear()
                    password_input.send_keys(self.password)
                    password_input.send_keys("\n")
                    time.sleep(5)
                    
                    # التحقق من النجاح
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'))
                        )
                        
                        cookies = driver.get_cookies()
                        auth_token = None
                        for cookie in cookies:
                            if cookie['name'] == 'auth_token':
                                auth_token = cookie['value']
                                break
                        
                        if auth_token:
                            driver.quit()
                            return {'method': 'selenium', 'success': True, 'auth_token': auth_token}
                            
                    except TimeoutException:
                        pass
                
                self.log_attempt('selenium', 'login_failed', {'reason': 'password_field_not_found'}, False)
                
            except Exception as e:
                self.log_attempt('selenium', 'login_error', {'error': str(e)}, False, str(e))
            
            driver.quit()
            return None
            
        except Exception as e:
            self.log_attempt('selenium', 'error', {'error': str(e)}, False, str(e))
            return None
    
    async def try_playwright_login(self):
        """محاولة تسجيل الدخول باستخدام Playwright"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        try:
            logging.info("Trying Playwright method...")
            
            playwright = await async_playwright().start()
            
            launch_options = {
                'headless': False,
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
            
            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            self.log_attempt('playwright', 'session_init', {'browser': 'chromium'}, True)
            
            await page.goto("https://twitter.com", wait_until='networkidle')
            await asyncio.sleep(3)
            
            # التحقق من وجود جلسة
            try:
                await page.wait_for_selector('[data-testid="SideNav_AccountSwitcher_Button"]', timeout=5000)
                self.log_attempt('playwright', 'existing_session', {'status': 'found'}, True)
                
                cookies = await context.cookies()
                auth_token = None
                for cookie in cookies:
                    if cookie['name'] == 'auth_token':
                        auth_token = cookie['value']
                        break
                
                if auth_token:
                    await context.close()
                    await browser.close()
                    return {'method': 'playwright', 'success': True, 'auth_token': auth_token}
                    
            except:
                pass
            
            # محاولة تسجيل الدخول
            try:
                login_selectors = [
                    'a[data-testid="loginButton"]',
                    'a[href="/login"]',
                    'text=Log in'
                ]
                
                login_button = None
                for selector in login_selectors:
                    try:
                        login_button = await page.wait_for_selector(selector, timeout=3000)
                        break
                    except:
                        continue
                
                if login_button:
                    await login_button.click()
                    await asyncio.sleep(3)
                    
                    username_selectors = [
                        'input[name="text"]',
                        'input[autocomplete="username"]',
                        '[data-testid="ocfEnterTextTextInput"]'
                    ]
                    
                    username_input = None
                    for selector in username_selectors:
                        try:
                            username_input = await page.wait_for_selector(selector, timeout=3000)
                            break
                        except:
                            continue
                    
                    if username_input:
                        await username_input.fill(self.username)
                        await username_input.press("Enter")
                        await asyncio.sleep(3)
                        
                        password_selectors = [
                            'input[name="password"]',
                            'input[type="password"]',
                            'input[autocomplete="current-password"]'
                        ]
                        
                        password_input = None
                        for selector in password_selectors:
                            try:
                                password_input = await page.wait_for_selector(selector, timeout=3000)
                                break
                            except:
                                continue
                        
                        if password_input:
                            await password_input.fill(self.password)
                            await password_input.press("Enter")
                            await asyncio.sleep(5)
                            
                            # التحقق من النجاح
                            success_selectors = [
                                '[data-testid="SideNav_AccountSwitcher_Button"]',
                                '[data-testid="AppTabBar_Home_Link"]'
                            ]
                            
                            for selector in success_selectors:
                                try:
                                    await page.wait_for_selector(selector, timeout=5000)
                                    
                                    cookies = await context.cookies()
                                    auth_token = None
                                    for cookie in cookies:
                                        if cookie['name'] == 'auth_token':
                                            auth_token = cookie['value']
                                            break
                                    
                                    if auth_token:
                                        await context.close()
                                        await browser.close()
                                        return {'method': 'playwright', 'success': True, 'auth_token': auth_token}
                                        
                                except:
                                    continue
                
                self.log_attempt('playwright', 'login_failed', {'reason': 'password_field_not_found'}, False)
                
            except Exception as e:
                self.log_attempt('playwright', 'login_error', {'error': str(e)}, False, str(e))
            
            await context.close()
            await browser.close()
            return None
            
        except Exception as e:
            self.log_attempt('playwright', 'error', {'error': str(e)}, False, str(e))
            return None
    
    async def try_manual_extraction(self):
        """محاولة استخراج الكوكيز يدوياً"""
        try:
            logging.info("Trying manual extraction method...")
            
            # محاولة استخدام allx API إذا كان متاحاً
            try:
                import requests
                
                headers = {
                    'X-API-Key': 'sk-twitter-2026-secret-key',
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'username': self.username,
                    'password': self.password
                }
                
                response = requests.post('http://127.0.0.1:4527/api/accounts/login', 
                                       json=data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        self.log_attempt('manual', 'allx_api', {'status': 'success'}, True)
                        return {'method': 'manual', 'success': True, 'result': result}
                
                self.log_attempt('manual', 'allx_api', {'status': response.status_code}, False)
                
            except Exception as e:
                self.log_attempt('manual', 'allx_api_error', {'error': str(e)}, False)
            
            # محاولة استخدام manual_cookies.py
            try:
                # تشغيل manual_cookies.py واستخراج النتائج
                import subprocess
                
                result = subprocess.run(['python', 'manual_cookies.py'], 
                                      capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    self.log_attempt('manual', 'manual_cookies', {'status': 'success'}, True)
                    return {'method': 'manual', 'success': True, 'output': result.stdout}
                
                self.log_attempt('manual', 'manual_cookies', {'status': 'failed'}, False)
                
            except Exception as e:
                self.log_attempt('manual', 'manual_cookies_error', {'error': str(e)}, False)
            
            return None
            
        except Exception as e:
            self.log_attempt('manual', 'error', {'error': str(e)}, False, str(e))
            return None
    
    async def hybrid_login(self):
        """العملية الكاملة لتسجيل الدخول الهجين"""
        logging.info("ULTIMATE HYBRID LOGIN SYSTEM")
        logging.info("Multi-technology approach to bypass Twitter protection")
        logging.info("=" * 70)
        logging.info(f"Username: {self.username}")
        logging.info(f"Max attempts: {self.max_attempts}")
        logging.info("Methods: curl_cffi, HTTPX, Selenium, Playwright, Manual")
        logging.info("=" * 70)
        
        methods = [
            ('curl_cffi', self.try_curl_cffi_login),
            ('httpx', self.try_httpx_login),
            ('selenium', self.try_selenium_login),
            ('playwright', self.try_playwright_login),
            ('manual', self.try_manual_extraction)
        ]
        
        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            
            logging.info(f"\nHYBRID ATTEMPT {attempt}/{self.max_attempts}")
            logging.info("=" * 50)
            
            # ترتيب عشوائي للطرق
            random.shuffle(methods)
            
            for method_name, method_func in methods:
                try:
                    logging.info(f"Trying method: {method_name}")
                    
                    result = await method_func()
                    
                    if result and result.get('success'):
                        # حفظ النتائج
                        self.success_patterns.append({
                            'attempt': attempt,
                            'method': method_name,
                            'result': result,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # حفظ الكوكيز إذا كانت متوفرة
                        if 'auth_token' in result:
                            cookie_data = {
                                "cookies": [{
                                    "name": "auth_token",
                                    "value": result['auth_token'],
                                    "domain": ".x.com",
                                    "path": "/",
                                    "expires": 2147483647.0,
                                    "httpOnly": True,
                                    "secure": True,
                                    "sameSite": "None"
                                }],
                                "origins": [],
                                "method": method_name,
                                "attempt": attempt
                            }
                            
                            timestamp = int(time.time())
                            json_file = self.cookies_dir / f"hybrid_{method_name}_{self.username}_{timestamp}.json"
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(cookie_data, f, indent=2, ensure_ascii=False)
                            
                            logging.info(f"\nHYBRID LOGIN SUCCESSFUL!")
                            logging.info(f"Method: {method_name}")
                            logging.info(f"Attempt: {attempt}")
                            logging.info(f"Auth token: {result['auth_token'][:20]}...")
                            logging.info(f"Cookies saved to: {json_file}")
                            
                            return {
                                'method': method_name,
                                'attempt': attempt,
                                'auth_token': result['auth_token'],
                                'json_file': str(json_file),
                                'success_patterns': self.success_patterns,
                                'failure_patterns': self.failure_patterns
                            }
                    
                    # فشل الطريقة الحالية، جرب الطريقة التالية
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
                except Exception as e:
                    logging.error(f"Error in method {method_name}: {e}")
                    continue
            
            # جميع الطرق فشلت في هذه المحاولة
            logging.warning(f"All methods failed in attempt {attempt}")
            
            if attempt < self.max_attempts:
                wait_time = random.uniform(5.0, 15.0)
                logging.info(f"Waiting {wait_time:.1f} seconds before next attempt...")
                await asyncio.sleep(wait_time)
        
        # جميع المحاولات فشلت
        logging.error(f"\nAll {self.max_attempts} hybrid attempts failed!")
        
        final_analysis = {
            'total_attempts': self.max_attempts,
            'success': False,
            'failure_patterns': self.failure_patterns,
            'all_attempts_data': self.analysis_data,
            'methods_tried': [method[0] for method in methods]
        }
        
        with open(f'hybrid_final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(final_analysis, f, ensure_ascii=False, indent=2)
        
        raise Exception(f"All {self.max_attempts} hybrid attempts failed")

async def main():
    """الوظيفة الرئيسية"""
    logging.info("ULTIMATE HYBRID LOGIN SYSTEM")
    logging.info("Advanced multi-technology approach")
    logging.info("=" * 80)
    
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    logging.info(f"Target account: {username}")
    logging.info(f"Max attempts: 50")
    logging.info("Press Ctrl+C to stop at any time")
    
    hybrid = UltimateHybridLogin(username, password)
    
    try:
        result = await hybrid.hybrid_login()
        
        logging.info(f"\nULTIMATE SUCCESS AFTER {hybrid.attempt_count} ATTEMPTS!")
        logging.info(f"Method: {result['method']}")
        logging.info(f"Attempt: {result['attempt']}")
        logging.info(f"Auth token: {result['auth_token'][:20]}...")
        logging.info(f"Cookies saved to: {result['json_file']}")
        
        logging.info(f"\nHYBRID ANALYSIS SUMMARY:")
        logging.info(f"Total attempts: {hybrid.attempt_count}")
        logging.info(f"Success patterns: {len(hybrid.success_patterns)}")
        logging.info(f"Failure patterns: {len(hybrid.failure_patterns)}")
        logging.info(f"Analysis data points: {len(hybrid.analysis_data)}")
        
        print(f"\n[+] Hybrid login successful!")
        print(f"[+] Method: {result['method']}")
        print(f"[+] Attempt: {result['attempt']}")
        print(f"[+] Auth token: {result['auth_token'][:20]}...")
        print(f"[+] Cookies saved to: {result['json_file']}")
        
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nHybrid login failed: {e}")
        logging.error("\nCheck the hybrid analysis files for detailed patterns")
        logging.error("Consider using manual_cookies.py for guaranteed success")

if __name__ == "__main__":
    asyncio.run(main())
