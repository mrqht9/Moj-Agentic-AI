#!/usr/bin/env python3
"""
Chameleon Login - تغيير البصمة مع كل طلب لتجاوز حماية تويتر
"""
import asyncio
import json
import time
import random
import uuid
import sys
import os
import hashlib
from pathlib import Path
from urllib.parse import urlparse

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import curl_cffi
from curl_cffi import AsyncSession
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

class ChameleonLogin:
    def __init__(self):
        self.session = None
        self.flow_token = None
        self.guest_token = None
        self.current_fingerprint = None
        
    def generate_fingerprint(self):
        """توليد بصمة فريدة لكل جلسة"""
        fingerprint = {
            'browser_type': random.choice(['chrome', 'firefox', 'edge']),  # إزالة safari
            'os_type': random.choice(['windows', 'macos', 'linux']),
            'screen_resolution': random.choice([
                (1920, 1080), (1366, 768), (1440, 900), 
                (1536, 864), (1280, 720), (1600, 900)
            ]),
            'timezone': random.choice([
                'America/New_York', 'Europe/London', 'Asia/Tokyo',
                'America/Los_Angeles', 'Europe/Paris', 'Asia/Dubai'
            ]),
            'language': random.choice(['en-US', 'ar-SA', 'fr-FR', 'ja-JP', 'es-ES']),
            'hardware_id': hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
        }
        return fingerprint
    
    def get_browser_config(self, fingerprint):
        """الحصول على إعدادات المتصفح بناءً على البصمة"""
        configs = {
            'chrome': {
                'versions': ['99', '100', '101', '104', '107', '110', '116', '119', '120', '123', '124', '131', '136', '142'],
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36'
                ]
            },
            'firefox': {
                'versions': ['91', '92', '93', '94', '95', '99', '100', '101', '102', '103', '104', '105'],  # إصدارات مدعومة فقط
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
                    'Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0'
                ]
            },
            'edge': {
                'versions': ['99', '100', '101', '104', '107', '110', '116', '119', '120', '123', '124', '131', '136', '142'],  # إصدارات مدعومة
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0'
                ]
            }
        }
        
        return configs.get(fingerprint['browser_type'], configs['chrome'])
    
    def generate_headers(self, fingerprint):
        """توليد هيدرز فريدة بناءً على البصمة"""
        browser_config = self.get_browser_config(fingerprint)
        version = random.choice(browser_config['versions'])
        user_agent = random.choice(browser_config['user_agents']).format(version=version)
        
        # Accept-Language بناءً على لغة البصمة
        accept_languages = {
            'en-US': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
            'ar-SA': 'ar-SA,ar;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,es;q=0.5,it;q=0.4',
            'fr-FR': 'fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'ja-JP': 'ja-JP,ja;q=0.9,en;q=0.8,ko;q=0.7,zh-CN;q=0.6,zh;q=0.5,fr;q=0.4',
            'es-ES': 'es-ES,es;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,pt;q=0.4'
        }
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': accept_languages.get(fingerprint['language'], accept_languages['en-US']),
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': random.choice(['1', '0']),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # إضافة هيدرز خاصة بالمتصفح
        if fingerprint['browser_type'] == 'chrome':
            headers.update({
                'sec-ch-ua': f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{fingerprint["os_type"].capitalize()}"'
            })
        elif fingerprint['browser_type'] == 'firefox':
            headers.update({
                'DNT': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            })
        elif fingerprint['browser_type'] == 'edge':
            headers.update({
                'sec-ch-ua': f'"Chromium";v="{version}", "Microsoft Edge";v="{version}", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{fingerprint["os_type"].capitalize()}"'
            })
        
        return headers, f"{fingerprint['browser_type']}{version}"
    
    async def init_session(self):
        """تهيئة جلسة ببصمة عشوائية"""
        # توليد بصمة جديدة لكل جلسة
        self.current_fingerprint = self.generate_fingerprint()
        
        headers, impersonate = self.generate_headers(self.current_fingerprint)
        
        print(f"🎭 Generated fingerprint: {self.current_fingerprint['browser_type']} on {self.current_fingerprint['os_type']}")
        print(f"🖥️  Screen: {self.current_fingerprint['screen_resolution'][0]}x{self.current_fingerprint['screen_resolution'][1]}")
        print(f"🌍 Language: {self.current_fingerprint['language']}")
        print(f"🌐 Timezone: {self.current_fingerprint['timezone']}")
        print(f"🔧 Using: {impersonate}")
        
        self.session = AsyncSession(
            impersonate=impersonate,
            timeout=30,
            headers=headers
        )
    
    def generate_transaction_id(self, method, path):
        """توليد transaction ID فريد لكل طلب"""
        timestamp = int(time.time() * 1000)
        random_val = random.randint(100000, 999999)
        hardware_id = self.current_fingerprint['hardware_id']
        return f"{method.upper()}:{path}:{timestamp}:{random_val}:{hardware_id}"
    
    async def extract_guest_token(self):
        """استخراج guest token"""
        print("[1] Extracting guest token...")
        
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        response = await self.session.get(
            'https://x.com/i/flow/login',
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get login page: {response.status_code}")
        
        import re
        gt_match = re.search(r'gt=([0-9]+);', response.text)
        if not gt_match:
            raise Exception("Guest token not found in login page")
        
        self.guest_token = gt_match.group(1)
        self.session.cookies.set('gt', self.guest_token, '.x.com')
        
        print(f"    Guest token: {self.guest_token[:20]}...")
    
    async def init_client_transaction(self):
        """تهيئة client transaction ببصمة مختلفة"""
        print("[2] Initializing client transaction...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        response = await self.session.get('https://x.com', headers=headers)
        
        # تغيير بصمة الـ transaction
        self.client_transaction_id = self.generate_transaction_id('POST', '/1.1/onboarding/task.json')
        
        print(f"    Transaction ID: {self.client_transaction_id[:30]}...")
    
    def create_chameleon_castle_token(self):
        """إنشاء castle token ببصمة فريدة"""
        # استخدام وقت عشوائي مختلف جداً
        time_variations = [
            random.randint(3600000, 7200000),  # 1-2 ساعات
            random.randint(86400000, 172800000),  # 1-2 أيام
            random.randint(604800000, 1209600000)  # 1-2 أسابيع
        ]
        
        init_time = int(time.time() * 1000) - random.choice(time_variations)
        
        # cuid فريد جداً بدون رموز قد تسبب مشاكل
        cuid_parts = [
            self.current_fingerprint['hardware_id'],
            str(int(time.time() * 1000)),
            random.choice(['alpha', 'beta', 'gamma', 'delta', 'epsilon']),
            uuid.uuid4().hex[:8]
        ]
        cuid = ''.join(cuid_parts)  # إزالة الشرطات
        
        self.session.cookies.set('__cuid', cuid, '.x.com')
        
        # استخدام CastleToken الأصلي مع معلمات مختلفة
        try:
            castle = CastleToken(init_time, cuid)
            self.castle_token = castle.create_token()
        except Exception as e:
            print(f"    Warning: Castle token failed, using fallback - {e}")
            # fallback method
            timestamp = int(time.time() * 1000)
            random_val = random.randint(0, 255)
            self.castle_token = f"castle:{timestamp}:{random_val}:{cuid[:16]}"
        
        print(f"    Castle token (chameleon): {self.castle_token[:30]}...")
        print(f"    Time offset: {-(time.time() * 1000 - init_time) / 1000 / 3600:.1f} hours")
    
    async def start_login_flow(self):
        """بدء تدفق تسجيل الدخول"""
        print("[3] Starting login flow...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        flow_data = {
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {"location": "unknown"}
                }
            },
            "subtask_versions": {
                "action_list": 2, "alert_dialog": 1, "app_download_cta": 1,
                "check_logged_in_account": 1, "choice_selection": 3,
                "contacts_live_sync_permission_prompt": 0, "cta": 7,
                "email_verification": 2, "end_flow": 1, "enter_date": 1,
                "enter_email": 2, "enter_password": 5, "enter_phone": 2,
                "enter_recaptcha": 1, "enter_text": 5, "enter_username": 2,
                "generic_urt": 3, "in_app_notification": 1,
                "interest_picker": 3, "js_instrumentation": 1,
                "menu_dialog": 1, "notifications_permission_prompt": 2,
                "open_account": 2, "open_home_timeline": 1,
                "open_link": 1, "phone_verification": 4,
                "privacy_options": 1, "security_key": 3,
                "select_avatar": 4, "select_banner": 2,
                "settings_list": 7, "show_code": 1,
                "sign_up": 2, "sign_up_review": 4,
                "tweet_selection_urt": 1, "update_users": 1,
                "upload_media": 1, "user_recommendations_list": 4,
                "user_recommendations_urt": 1, "wait_spinner": 3,
                "web_modal": 1
            }
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': self.session.headers.get('Accept-Language', 'en-US,en;q=0.9'),
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'content-type': 'application/json',
            'origin': 'https://x.com',
            'referer': 'https://x.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-client-transaction-id': self.client_transaction_id,
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'].split('-')[0]
        }
        
        response = await self.session.post(
            'https://api.x.com/1.1/onboarding/task.json',
            params={'flow_name': 'login'},
            json=flow_data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to start flow: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        self.flow_token = resp_data.get('flow_token')
        
        print(f"    Flow started successfully!")
        print(f"    Flow token: {self.flow_token[:30]}...")
        
        return resp_data
    
    async def execute_username_step(self, username):
        """تنفيذ خطوة اسم المستخدم ببصمة جديدة"""
        print("[4] Entering username...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # تغيير البصمة لهذه الخطوة
        self.create_chameleon_castle_token()
        
        subtask_data = {
            'flow_token': self.flow_token,
            'subtask_inputs': [
                {
                    'subtask_id': 'LoginEnterUserIdentifierSSO',
                    'settings_list': {
                        'setting_responses': [{
                            'key': 'user_identifier',
                            'response_data': {'text_data': {'result': username}}
                        }],
                        'link': 'next_link',
                        'castle_token': self.castle_token
                    }
                }
            ]
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': self.session.headers.get('Accept-Language', 'en-US,en;q=0.9'),
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'content-type': 'application/json',
            'origin': 'https://x.com',
            'referer': 'https://x.com/i/flow/login',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-client-transaction-id': self.generate_transaction_id('POST', '/1.1/onboarding/task.json'),
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'].split('-')[0],
            'x-csrf-token': self.session.cookies.get('ct0', ''),
        }
        
        response = await self.session.post(
            'https://api.x.com/1.1/onboarding/task.json',
            json=subtask_data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Username step failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        self.flow_token = resp_data.get('flow_token')
        
        print(f"    Username step completed!")
        print(f"    New flow token: {self.flow_token[:30]}...")
        
        return resp_data
    
    async def execute_password_step(self, password):
        """تنفيذ خطوة كلمة المرور ببصمة جديدة"""
        print("[5] Entering password...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # تغيير البصمة مرة أخرى لهذه الخطوة
        self.create_chameleon_castle_token()
        
        subtask_data = {
            'flow_token': self.flow_token,
            'subtask_inputs': [
                {
                    'subtask_id': 'LoginEnterPassword',
                    'enter_password': {
                        'password': password,
                        'link': 'next_link',
                        'castle_token': self.castle_token,
                        'verification': random.choice([True, False]),
                        'trusted': random.choice([True, False]),
                        'remember_me': random.choice([True, False])
                    }
                }
            ]
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': self.session.headers.get('Accept-Language', 'en-US,en;q=0.9'),
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'content-type': 'application/json',
            'origin': 'https://x.com',
            'referer': 'https://x.com/i/flow/login',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-client-transaction-id': self.generate_transaction_id('POST', '/1.1/onboarding/task.json'),
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'].split('-')[0],
            'x-csrf-token': self.session.cookies.get('ct0', ''),
        }
        
        print(f"    Debug - Headers count: {len(headers)}")
        print(f"    Debug - Has CSRF token: {'x-csrf-token' in headers}")
        print(f"    Debug - Castle token: {self.castle_token[:30]}...")
        
        response = await self.session.post(
            'https://api.x.com/1.1/onboarding/task.json',
            json=subtask_data,
            headers=headers
        )
        
        print(f"    Debug - Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"    Debug - Response body: {response.text[:300]}...")
        
        if response.status_code != 200:
            raise Exception(f"Password step failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        self.flow_token = resp_data.get('flow_token')
        
        print(f"    Password step completed!")
        print(f"    New flow token: {self.flow_token[:30]}...")
        
        return resp_data
    
    async def verify_login_success(self):
        """التحقق من نجاح تسجيل الدخول"""
        print("[6] Verifying login success...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        response = await self.session.get(
            'https://x.com/home',
            params={'prefetchTimestamp': int(time.time() * 1000)},
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to verify login: {response.status_code}")
        
        auth_token = self.session.cookies.get('auth_token', domain='.x.com')
        if not auth_token:
            raise Exception("auth_token not found - login failed")
        
        ct0 = self.session.cookies.get('ct0', domain='.x.com')
        if not ct0:
            await asyncio.sleep(random.uniform(0.5, 1.0))
            response = await self.session.get('https://x.com/home')
            ct0 = self.session.cookies.get('ct0', domain='.x.com')
        
        print(f"    ✅ Login successful!")
        print(f"    Auth token: {auth_token[:20]}...")
        print(f"    CSRF token: {ct0[:20]}..." if ct0 else "    CSRF token: Missing")
        
        return {
            'auth_token': auth_token,
            'ct0': ct0,
            'all_cookies': dict(self.session.cookies),
            'fingerprint': self.current_fingerprint
        }
    
    async def login(self, username, password):
        """تسجيل الدخول ببصمات متغيرة"""
        print("🦎 CHAMELEON LOGIN - Variable Fingerprint System")
        print("=" * 60)
        print("Each request uses a unique device fingerprint")
        print("=" * 60)
        
        try:
            await self.init_session()
            await self.extract_guest_token()
            await self.init_client_transaction()
            
            # بدء التدفق
            flow_result = await self.start_login_flow()
            
            # تنفيذ الخطوات ببصمات مختلفة
            await self.execute_username_step(username)
            await self.execute_password_step(password)
            
            # التحقق من النجاح
            cookies = await self.verify_login_success()
            
            print("\n🎉 CHAMELEON LOGIN COMPLETED SUCCESSFULLY!")
            print(f"Used fingerprint: {self.current_fingerprint['browser_type']} on {self.current_fingerprint['os_type']}")
            
            return cookies
            
        except Exception as e:
            print(f"\n❌ Chameleon login failed: {e}")
            raise

async def main():
    """الوظيفة الرئيسية"""
    print("🦎 CHAMELEON LOGIN SYSTEM")
    print("Advanced fingerprint randomization to bypass Twitter protection")
    print("=" * 70)
    
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required!")
        return
    
    chameleon = ChameleonLogin()
    
    try:
        cookies = await chameleon.login(username, password)
        
        # حفظ الكوكيز والبصمة
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        cookie_file = cookies_dir / f"chameleon_{username}_{int(time.time())}.json"
        
        # حفظ بصمة Playwright
        playwright_cookies = []
        for name, value in cookies['all_cookies'].items():
            if '.x.com' in name or name in ['auth_token', 'ct0', 'gt']:
                playwright_cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".x.com",
                    "path": "/",
                    "expires": 2147483647.0,
                    "httpOnly": name in ['auth_token'],
                    "secure": True,
                    "sameSite": "Lax" if name == 'ct0' else "None"
                })
        
        cookie_data = {
            "cookies": playwright_cookies,
            "origins": [],
            "fingerprint": cookies['fingerprint']
        }
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Cookies and fingerprint saved to: {cookie_file}")
        
    except Exception as e:
        print(f"\n❌ Chameleon login failed: {e}")
        print("\n💡 If this still fails, Twitter's protection is very strong.")
        print("Consider:")
        print("1. Using manual_cookies.py (100% reliable)")
        print("2. Changing your actual IP/VPN")
        print("3. Waiting 24-48 hours")
        print("4. Using a different device/network")

if __name__ == "__main__":
    asyncio.run(main())
