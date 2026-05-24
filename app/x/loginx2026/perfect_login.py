#!/usr/bin/env python3
"""
Perfect Login - حل مثالي يعتمد على تحليل عميق لطلبات تويتر
"""
import asyncio
import json
import time
import random
import uuid
import re
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import curl_cffi
from curl_cffi import AsyncSession

class PerfectLogin:
    def __init__(self):
        self.session = None
        self.flow_token = None
        self.guest_token = None
        self.csrf_token = None
        self.client_transaction_id = None
        self.castle_token = None
        
    async def init_session(self):
        """تهيئة جلسة مثالية"""
        # استخدام إصدار Chrome مدعوم فقط
        chrome_versions = ["99", "100", "101", "104", "107", "110", "116", "119", "120", "123", "124", "131", "136", "142"]
        version = random.choice(chrome_versions)
        
        self.session = AsyncSession(
            impersonate=f'chrome{version}',
            timeout=30,
            headers={
                'User-Agent': f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'sec-ch-ua': f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
        )
        print(f"    Using Chrome {version}")
        
    def generate_transaction_id(self, method, path):
        """توليد transaction ID مثالي"""
        # محاكاة توليد الـ ID الحقيقي
        timestamp = int(time.time() * 1000)
        random_val = random.randint(100000, 999999)
        return f"{method.upper()}:{path}:{timestamp}:{random_val}"
    
    async def extract_guest_token(self):
        """استخراج guest token من صفحة تسجيل الدخول"""
        print("[1] Extracting guest token...")
        
        # تأخير عشوائي لمحاكاة السلوك البشري
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        response = await self.session.get(
            'https://x.com/i/flow/login',
            headers={
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get login page: {response.status_code}")
        
        # استخراج guest token
        gt_match = re.search(r'gt=([0-9]+);', response.text)
        if not gt_match:
            raise Exception("Guest token not found in login page")
        
        self.guest_token = gt_match.group(1)
        self.session.cookies.set('gt', self.guest_token, '.x.com')
        
        print(f"    Guest token: {self.guest_token[:20]}...")
        
    async def init_client_transaction(self):
        """تهيئة client transaction"""
        print("[2] Initializing client transaction...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # زيارة الصفحة الرئيسية لتهيئة الـ transaction
        response = await self.session.get(
            'https://x.com',
            headers={
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
            }
        )
        
        # توليد transaction ID
        self.client_transaction_id = self.generate_transaction_id('POST', '/1.1/onboarding/task.json')
        
        print(f"    Transaction ID: {self.client_transaction_id[:30]}...")
        
    def create_perfect_castle_token(self):
        """إنشاء castle token مثالي باستخدام المنطق الأصلي"""
        # استخدام castle token الأصلي من x_auth بدلاً من المحاكاة البسيطة
        try:
            from x_auth.castle import CastleToken
            
            # استخدام وقت عشوائي مع تنوع
            init_time = int(time.time() * 1000) - random.randint(30000, 60000)
            cuid = uuid.uuid4().hex
            
            # حفظ الـ cuid في الكوكيز
            self.session.cookies.set('__cuid', cuid, '.x.com')
            
            # استخدام CastleToken الأصلي
            castle = CastleToken(init_time, cuid)
            self.castle_token = castle.create_token()
            
            print(f"    Castle token (original): {self.castle_token[:30]}...")
            
        except Exception as e:
            print(f"    Warning: Using fallback castle token - {e}")
            # استخدام backup method
            init_time = int(time.time() * 1000) - random.randint(30000, 60000)
            cuid = uuid.uuid4().hex
            self.session.cookies.set('__cuid', cuid, '.x.com')
            
            timestamp = int(time.time() * 1000)
            random_val = random.randint(0, 255)
            self.castle_token = f"castle:{timestamp}:{random_val}:{cuid[:16]}"
            
            print(f"    Castle token (fallback): {self.castle_token[:30]}...")
        
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
            'accept-language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
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
            'x-twitter-client-language': 'en'
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
        """تنفيذ خطوة إدخال اسم المستخدم"""
        print("[4] Entering username...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # إنشاء castle token جديد لهذه الخطوة
        self.create_perfect_castle_token()
        
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
            'accept-language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
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
            'x-twitter-client-language': 'en',
            # إضافة هيدرز إضافية
            'x-csrf-token': self.session.cookies.get('ct0', ''),
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
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
        """تنفيذ خطوة إدخال كلمة المرور"""
        print("[5] Entering password...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # إنشاء castle token جديد لهذه الخطوة
        self.create_perfect_castle_token()
        
        # إضافة المزيد من البيانات المطلوبة لخطوة كلمة المرور
        subtask_data = {
            'flow_token': self.flow_token,
            'subtask_inputs': [
                {
                    'subtask_id': 'LoginEnterPassword',
                    'enter_password': {
                        'password': password,
                        'link': 'next_link',
                        'castle_token': self.castle_token,
                        # إضافة حقول إضافية قد تكون مطلوبة
                        'verification': False,
                        'trusted': True,
                        'remember_me': False
                    }
                }
            ]
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
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
            'x-twitter-client-language': 'en',
            # إضافة هيدرز إضافية قد تكون مطلوبة
            'x-csrf-token': self.session.cookies.get('ct0', ''),
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
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
        
        # زيارة الصفحة الرئيسية للتحقق من الكوكيز
        response = await self.session.get(
            'https://x.com/home',
            params={'prefetchTimestamp': int(time.time() * 1000)},
            headers={
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to verify login: {response.status_code}")
        
        # التحقق من وجود auth_token
        auth_token = self.session.cookies.get('auth_token', domain='.x.com')
        if not auth_token:
            raise Exception("auth_token not found - login failed")
        
        # التحقق من ct0
        ct0 = self.session.cookies.get('ct0', domain='.x.com')
        if not ct0:
            # محاولة جلب ct0 مرة أخرى
            print("    Getting ct0 token...")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            response = await self.session.get('https://x.com/home')
            ct0 = self.session.cookies.get('ct0', domain='.x.com')
        
        print(f"    ✅ Login successful!")
        print(f"    Auth token: {auth_token[:20]}...")
        print(f"    CSRF token: {ct0[:20]}..." if ct0 else "    CSRF token: Missing")
        
        return {
            'auth_token': auth_token,
            'ct0': ct0,
            'all_cookies': dict(self.session.cookies)
        }
    
    async def login(self, username, password):
        """تسجيل الدخول الكامل"""
        print("🎯 PERFECT LOGIN ATTEMPT")
        print("=" * 50)
        
        try:
            await self.init_session()
            await self.extract_guest_token()
            await self.init_client_transaction()
            
            # بدء التدفق
            flow_result = await self.start_login_flow()
            
            # تنفيذ الخطوات
            await self.execute_username_step(username)
            await self.execute_password_step(password)
            
            # التحقق من النجاح
            cookies = await self.verify_login_success()
            
            print("\n🎉 LOGIN COMPLETED SUCCESSFULLY!")
            return cookies
            
        except Exception as e:
            print(f"\n❌ Login failed: {e}")
            raise

async def main():
    """الوظيفة الرئيسية"""
    print("🎯 PERFECT TWITTER LOGIN")
    print("Based on deep analysis of real browser requests")
    print("=" * 60)
    
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required!")
        return
    
    perfect_login = PerfectLogin()
    
    try:
        cookies = await perfect_login.login(username, password)
        
        # حفظ الكوكيز
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        cookie_file = cookies_dir / f"perfect_{username}.json"
        
        # حفظ بصيغة Playwright
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
            "origins": []
        }
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Cookies saved to: {cookie_file}")
        
    except Exception as e:
        print(f"\n❌ Perfect login failed: {e}")
        print("\n💡 Try these solutions:")
        print("1. Run deep_analysis.py first to understand requirements")
        print("2. Check if your IP is blocked")
        print("3. Try different network/VPN")
        print("4. Use manual_cookies.py as fallback")

if __name__ == "__main__":
    asyncio.run(main())
