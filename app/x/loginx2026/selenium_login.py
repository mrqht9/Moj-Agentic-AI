#!/usr/bin/env python3
"""
Selenium Login - نظام تسجيل دخول باستخدام متصفح حقيقي
يعتمد على Selenium مع Chrome للحصول على جلسة حقيقية وحفظ الكوكيز
"""
import time
import os
import json
import pickle
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('selenium_login.log'),
        logging.StreamHandler()
    ]
)

class SeleniumLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.driver = None
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        self.user_data_dir = self.cookies_dir / "chrome_profile"
        
    def setup_chrome_options(self):
        """إعداد خيارات Chrome"""
        options = Options()
        
        # خيارات إضافية لتجنب الكشف
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # إعداد الـ User-Agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # تعطيل بعض الميزات التي قد تسبب الكشف
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        
        return options
    
    def init_driver(self):
        """تهيئة المتصفح"""
        try:
            options = self.setup_chrome_options()
            self.driver = webdriver.Chrome(options=options)
            
            # إخفاء أتمتة Selenium
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logging.info("Chrome driver initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def check_existing_session(self):
        """التحقق من وجود جلسة محفوظة"""
        try:
            self.driver.get("https://twitter.com")
            time.sleep(3)
            
            # التحقق من تسجيل الدخول عن طريق البحث عن زر التغريد
            try:
                tweet_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'))
                )
                logging.info("Existing session found - already logged in")
                return True
            except TimeoutException:
                logging.info("No existing session found")
                return False
                
        except Exception as e:
            logging.error(f"Error checking existing session: {e}")
            return False
    
    def perform_login(self):
        """تنفيذ عملية تسجيل الدخول"""
        try:
            # الذهاب إلى تويتر
            self.driver.get("https://twitter.com")
            time.sleep(3)
            
            # البحث عن زر تسجيل الدخول
            try:
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="loginButton"]'))
                )
                login_button.click()
                logging.info("Login button clicked")
            except TimeoutException:
                # إذا لم يتم العثور على زر تسجيل الدخول، جرب الطريقة الجديدة
                try:
                    login_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '[href="/login"]'))
                    )
                    login_button.click()
                    logging.info("Alternative login button clicked")
                except TimeoutException:
                    logging.error("Could not find login button")
                    return False
            
            time.sleep(3)
            
            # إدخال اسم المستخدم
            try:
                username_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="text"]'))
                )
                username_input.clear()
                username_input.send_keys(self.username)
                logging.info(f"Username entered: {self.username}")
                
                # الضغط على Enter للمتابعة
                username_input.send_keys("\n")
                time.sleep(3)
                
            except TimeoutException:
                logging.error("Could not find username input")
                return False
            
            # إدخال كلمة المرور
            try:
                # جرب عدة селектورات مختلفة لحقل كلمة المرور
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]',
                    'input[data-testid="password"]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        break
                    except TimeoutException:
                        continue
                
                if not password_input:
                    # جرب البحث عن طريق XPath
                    try:
                        password_input = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
                        )
                    except TimeoutException:
                        logging.error("Could not find password input with any selector")
                        return False
                
                password_input.clear()
                password_input.send_keys(self.password)
                logging.info("Password entered")
                
                # الضغط على Enter لتسجيل الدخول
                password_input.send_keys("\n")
                time.sleep(5)
                
            except Exception as e:
                logging.error(f"Error entering password: {e}")
                return False
            
            # التحقق من نجاح تسجيل الدخول
            try:
                # البحث عن دليل على تسجيل الدخول الناجح
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]'))
                )
                logging.info("Login successful!")
                return True
                
            except TimeoutException:
                # جرب طريقة أخرى للتحقق
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="AppTabBar_Home_Link"]'))
                    )
                    logging.info("Login successful (alternative verification)!")
                    return True
                except TimeoutException:
                    logging.error("Login verification failed")
                    return False
                    
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return False
    
    def extract_cookies(self):
        """استخراج الكوكيز وحفظها"""
        try:
            # الحصول على الكوكيز من Selenium
            selenium_cookies = self.driver.get_cookies()
            
            # تحويل الكوكيز إلى صيغة Playwright
            playwright_cookies = []
            auth_token = None
            ct0 = None
            
            for cookie in selenium_cookies:
                if cookie['domain'] in ['.twitter.com', '.x.com']:
                    playwright_cookie = {
                        "name": cookie['name'],
                        "value": cookie['value'],
                        "domain": ".x.com",
                        "path": cookie.get('path', '/'),
                        "expires": cookie.get('expiry', 2147483647.0),
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
            
            # حفظ الكوكيز بصيغة Playwright
            cookie_data = {
                "cookies": playwright_cookies,
                "origins": []
            }
            
            # حفظ بصيغة JSON
            timestamp = int(time.time())
            json_file = self.cookies_dir / f"selenium_{self.username}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, indent=2, ensure_ascii=False)
            
            # حفظ بصيغة pickle (للاستخدام مع Selenium لاحقاً)
            pickle_file = self.cookies_dir / f"selenium_{self.username}_{timestamp}.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump(selenium_cookies, f)
            
            logging.info(f"Cookies saved to: {json_file}")
            logging.info(f"Pickle file saved to: {pickle_file}")
            logging.info(f"Auth token: {auth_token[:20]}...")
            logging.info(f"CSRF token: {ct0[:20] if ct0 else 'N/A'}...")
            
            return {
                'json_file': str(json_file),
                'pickle_file': str(pickle_file),
                'auth_token': auth_token,
                'ct0': ct0,
                'cookies_count': len(playwright_cookies)
            }
            
        except Exception as e:
            logging.error(f"Error extracting cookies: {e}")
            return None
    
    def save_session_info(self):
        """حفظ معلومات الجلسة"""
        try:
            # الحصول على معلومات الجلسة
            session_info = {
                'username': self.username,
                'login_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_data_dir': str(self.user_data_dir),
                'current_url': self.driver.current_url,
                'title': self.driver.title
            }
            
            # حفظ معلومات الجلسة
            session_file = self.cookies_dir / f"session_{self.username}_{int(time.time())}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Session info saved to: {session_file}")
            return session_file
            
        except Exception as e:
            logging.error(f"Error saving session info: {e}")
            return None
    
    def login(self):
        """العملية الكاملة لتسجيل الدخول"""
        logging.info("Starting Selenium login process")
        logging.info(f"Username: {self.username}")
        logging.info(f"User data directory: {self.user_data_dir}")
        
        try:
            # تهيئة المتصفح
            if not self.init_driver():
                return None
            
            # التحقق من وجود جلسة محفوظة
            if self.check_existing_session():
                # استخراج الكوكيز من الجلسة الحالية
                cookies_data = self.extract_cookies()
                if cookies_data:
                    self.save_session_info()
                    return cookies_data
            
            # تنفيذ تسجيل الدخول
            if self.perform_login():
                # استخراج الكوكيز بعد تسجيل الدخول الناجح
                cookies_data = self.extract_cookies()
                if cookies_data:
                    self.save_session_info()
                    return cookies_data
            
            logging.error("Login process failed")
            return None
            
        except Exception as e:
            logging.error(f"Login process error: {e}")
            return None
        
        finally:
            # إغلاق المتصفح
            if self.driver:
                self.driver.quit()
                logging.info("Browser closed")

def main():
    """الوظيفة الرئيسية"""
    logging.info("SELENIUM LOGIN SYSTEM")
    logging.info("Real browser automation with cookie extraction")
    logging.info("=" * 60)
    
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    selenium_login = SeleniumLogin(username, password)
    
    try:
        result = selenium_login.login()
        
        if result:
            logging.info("\nSELENIUM LOGIN SUCCESSFUL!")
            logging.info(f"Auth token: {result['auth_token'][:20]}...")
            logging.info(f"CSRF token: {result['ct0'][:20] if result['ct0'] else 'N/A'}...")
            logging.info(f"Cookies saved: {result['cookies_count']}")
            logging.info(f"JSON file: {result['json_file']}")
            logging.info(f"Pickle file: {result['pickle_file']}")
            
            print(f"\n[+] Login successful!")
            print(f"[+] Cookies saved to: {result['json_file']}")
            print(f"[+] Auth token: {result['auth_token'][:20]}...")
            
        else:
            logging.error("\nSELENIUM LOGIN FAILED!")
            print(f"\n[-] Login failed!")
            print("Check the log file for details: selenium_login.log")
            
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()
