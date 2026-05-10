#!/usr/bin/env python3
"""
Persistent Login - نظام تحليلي متقدم لتسجيل الدخول المتكرر
يحلل كل طلب ويجرب repeatedly حتى النجاح
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
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import logging

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import curl_cffi
from curl_cffi import AsyncSession
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('persistent_login.log'),
        logging.StreamHandler()
    ]
)

class PersistentLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.session = None
        self.flow_token = None
        self.guest_token = None
        self.current_fingerprint = None
        self.attempt_count = 0
        self.max_attempts = 50  # أقصى عدد من المحاولات
        self.success_patterns = []
        self.failure_patterns = []
        self.analysis_data = []
        
    def log_attempt(self, step, data, success=False, error_msg=None):
        """تسجيل كل محاولة للتحليل"""
        attempt_data = {
            'attempt': self.attempt_count,
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'fingerprint': self.current_fingerprint,
            'data': data,
            'success': success,
            'error': error_msg
        }
        
        self.analysis_data.append(attempt_data)
        
        # حفظ في ملف
        with open(f'login_analysis_{datetime.now().strftime("%Y%m%d")}.json', 'a', encoding='utf-8') as f:
            json.dump(attempt_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        
        logging.info(f"Attempt {self.attempt_count} - {step}: {'SUCCESS' if success else 'FAILED'}")
        if error_msg:
            logging.error(f"Error: {error_msg}")
    
    def generate_advanced_fingerprint(self):
        """توليد بصمة فائقة التقدم"""
        # استراتيجيات مختلفة للبصمات
        strategies = [
            'minimal',      # بصمة بسيطة
            'standard',     # بصمة قياسية  
            'advanced',     # بصمة متقدمة
            'stealth',      # بصمة خفية
            'aggressive'    # بصمة عدوانية
        ]
        
        strategy = random.choice(strategies)
        
        if strategy == 'minimal':
            fingerprint = {
                'browser_type': 'chrome',
                'os_type': 'windows',
                'screen_resolution': (1920, 1080),
                'timezone': 'America/New_York',
                'language': 'en-US',
                'hardware_id': hashlib.md5(f"min_{time.time()}".encode()).hexdigest()[:16],
                'strategy': 'minimal'
            }
        elif strategy == 'standard':
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox']),
                'os_type': random.choice(['windows', 'macos']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900)]),
                'timezone': random.choice(['America/New_York', 'Europe/London']),
                'language': random.choice(['en-US', 'en-GB']),
                'hardware_id': hashlib.md5(f"std_{time.time()}".encode()).hexdigest()[:16],
                'strategy': 'standard'
            }
        elif strategy == 'advanced':
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox', 'edge']),
                'os_type': random.choice(['windows', 'macos', 'linux']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900), (1600, 900)]),
                'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo', 'America/Los_Angeles']),
                'language': random.choice(['en-US', 'en-GB', 'fr-FR', 'de-DE']),
                'hardware_id': hashlib.md5(f"adv_{time.time()}".encode()).hexdigest()[:16],
                'strategy': 'advanced'
            }
        elif strategy == 'stealth':
            fingerprint = {
                'browser_type': 'chrome',  # الأكثر شيوعاً
                'os_type': 'windows',      # الأكثر شيوعاً
                'screen_resolution': (1920, 1080),  # الأكثر شيوعاً
                'timezone': 'America/New_York',     # الأكثر شيوعاً
                'language': 'en-US',      # الأكثر شيوعاً
                'hardware_id': hashlib.md5(f"ste_{time.time()}".encode()).hexdigest()[:16],
                'strategy': 'stealth'
            }
        else:  # aggressive
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox', 'edge']),
                'os_type': random.choice(['windows', 'macos', 'linux']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720), (1600, 900)]),
                'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo', 'America/Los_Angeles', 'Europe/Paris', 'Asia/Dubai']),
                'language': random.choice(['en-US', 'ar-SA', 'fr-FR', 'ja-JP', 'es-ES', 'de-DE', 'zh-CN']),
                'hardware_id': hashlib.md5(f"agg_{time.time()}".encode()).hexdigest()[:16],
                'strategy': 'aggressive'
            }
        
        return fingerprint
    
    def get_browser_config(self, fingerprint):
        """الحصول على إعدادات المتصفح بناءً على البصمة والاستراتيجية"""
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
                'versions': ['91', '92', '93', '94', '95', '99', '100', '101', '102', '103', '104'],  # إصدارات مدعومة فقط
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}.0) Gecko/20100101 Firefox/{version}.0',
                    'Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0'
                ]
            },
            'edge': {
                'versions': ['99', '100', '101', '104', '107', '110', '116', '119', '120', '123', '124', '131', '136', '142'],
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0'
                ]
            }
        }
        
        return configs.get(fingerprint['browser_type'], configs['chrome'])
    
    def generate_headers(self, fingerprint):
        """توليد هيدرز فريدة بناءً على البصمة والاستراتيجية"""
        browser_config = self.get_browser_config(fingerprint)
        version = random.choice(browser_config['versions'])
        user_agent = random.choice(browser_config['user_agents']).format(version=version)
        
        # Accept-Language بناءً على لغة البصمة
        accept_languages = {
            'en-US': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
            'en-GB': 'en-GB,en;q=0.9,fr;q=0.8,de;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'ar-SA': 'ar-SA,ar;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,es;q=0.5,it;q=0.4',
            'fr-FR': 'fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'ja-JP': 'ja-JP,ja;q=0.9,en;q=0.8,ko;q=0.7,zh-CN;q=0.6,zh;q=0.5,fr;q=0.4',
            'es-ES': 'es-ES,es;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,pt;q=0.4',
            'de-DE': 'de-DE,de;q=0.9,en;q=0.8,fr;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'zh-CN': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,ko;q=0.6,fr;q=0.5,de;q=0.4'
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
        """تهيئة جلسة ببصمة استراتيجية"""
        self.current_fingerprint = self.generate_advanced_fingerprint()
        
        headers, impersonate = self.generate_headers(self.current_fingerprint)
        
        logging.info(f"Strategy: {self.current_fingerprint['strategy']}")
        logging.info(f"Generated fingerprint: {self.current_fingerprint['browser_type']} on {self.current_fingerprint['os_type']}")
        logging.info(f"Screen: {self.current_fingerprint['screen_resolution'][0]}x{self.current_fingerprint['screen_resolution'][1]}")
        logging.info(f"Language: {self.current_fingerprint['language']}")
        logging.info(f"Timezone: {self.current_fingerprint['timezone']}")
        logging.info(f"Using: {impersonate}")
        
        self.session = AsyncSession(
            impersonate=impersonate,
            timeout=30,
            headers=headers
        )
        
        self.log_attempt('session_init', {
            'fingerprint': self.current_fingerprint,
            'impersonate': impersonate,
            'headers_count': len(headers)
        })
    
    def generate_transaction_id(self, method, path):
        """توليد transaction ID فريد لكل طلب"""
        timestamp = int(time.time() * 1000)
        random_val = random.randint(100000, 999999)
        hardware_id = self.current_fingerprint['hardware_id']
        return f"{method.upper()}:{path}:{timestamp}:{random_val}:{hardware_id}"
    
    async def extract_guest_token(self):
        """استخراج guest token"""
        logging.info("[1] Extracting guest token...")
        
        # تأخير استراتيجي بناءً على الاستراتيجية
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(2.0, 5.0))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 1.0))
        else:
            await asyncio.sleep(random.uniform(1.0, 3.0))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        try:
            response = await self.session.get(
                'https://x.com/i/flow/login',
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('guest_token_extract', {
                    'status': response.status_code,
                    'error': 'Failed to get login page'
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to get login page: {response.status_code}")
            
            gt_match = re.search(r'gt=([0-9]+);', response.text)
            if not gt_match:
                self.log_attempt('guest_token_extract', {
                    'error': 'Guest token not found in page'
                }, False, "Guest token not found")
                raise Exception("Guest token not found in login page")
            
            self.guest_token = gt_match.group(1)
            self.session.cookies.set('gt', self.guest_token, '.x.com')
            
            self.log_attempt('guest_token_extract', {
                'guest_token': self.guest_token[:20] + '...',
                'success': True
            }, True)
            
            logging.info(f"    Guest token: {self.guest_token[:20]}...")
            
        except Exception as e:
            self.log_attempt('guest_token_extract', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def init_client_transaction(self):
        """تهيئة client transaction ببصمة مختلفة"""
        logging.info("[2] Initializing client transaction...")
        
        # تأخير استراتيجي
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(1.5, 3.0))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 0.5))
        else:
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        try:
            response = await self.session.get('https://x.com', headers=headers)
            
            # تغيير بصمة الـ transaction
            self.client_transaction_id = self.generate_transaction_id('POST', '/1.1/onboarding/task.json')
            
            self.log_attempt('client_transaction_init', {
                'transaction_id': self.client_transaction_id[:30] + '...',
                'status': response.status_code
            }, True)
            
            logging.info(f"    Transaction ID: {self.client_transaction_id[:30]}...")
            
        except Exception as e:
            self.log_attempt('client_transaction_init', {
                'error': str(e)
            }, False, str(e))
            raise
    
    def create_strategic_castle_token(self):
        """إنشاء castle token ببصمة استراتيجية"""
        # وقت عشوائي مختلف جداً بناءً على الاستراتيجية
        if self.current_fingerprint['strategy'] == 'stealth':
            time_offset = random.randint(86400000, 604800000)  # 1-7 أيام
        elif self.current_fingerprint['strategy'] == 'aggressive':
            time_offset = random.randint(3600000, 7200000)  # 1-2 ساعات
        else:
            time_offset = random.randint(86400000, 172800000)  # 1-2 أيام
        
        init_time = int(time.time() * 1000) - time_offset
        
        # cuid فريد جداً بدون رموز قد تسبب مشاكل
        cuid_parts = [
            self.current_fingerprint['hardware_id'],
            str(int(time.time() * 1000)),
            self.current_fingerprint['strategy'],
            uuid.uuid4().hex[:8]
        ]
        cuid = ''.join(cuid_parts)  # إزالة الشرطات
        
        self.session.cookies.set('__cuid', cuid, '.x.com')
        
        # استخدام CastleToken الأصلي مع معلمات مختلفة
        try:
            castle = CastleToken(init_time, cuid)
            self.castle_token = castle.create_token()
            castle_method = 'original'
        except Exception as e:
            logging.warning(f"Castle token failed, using fallback - {e}")
            # fallback method
            timestamp = int(time.time() * 1000)
            random_val = random.randint(0, 255)
            self.castle_token = f"castle:{timestamp}:{random_val}:{cuid[:16]}"
            castle_method = 'fallback'
        
        self.log_attempt('castle_token_create', {
            'method': castle_method,
            'time_offset_hours': -(time_offset / 1000 / 3600),
            'castle_token': self.castle_token[:30] + '...',
            'cuid': cuid[:20] + '...'
        }, True)
        
        logging.info(f"    Castle token ({castle_method}): {self.castle_token[:30]}...")
        logging.info(f"    Time offset: {-(time_offset / 1000 / 3600):.1f} hours")
    
    async def start_login_flow(self):
        """بدء تدفق تسجيل الدخول"""
        logging.info("[3] Starting login flow...")
        
        # تأخير استراتيجي
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(1.0, 2.5))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 0.5))
        else:
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
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                params={'flow_name': 'login'},
                json=flow_data,
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('flow_start', {
                    'status': response.status_code,
                    'response': response.text[:200]
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to start flow: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('flow_start', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', [])
            }, True)
            
            logging.info(f"    Flow started successfully!")
            logging.info(f"    Flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('flow_start', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_username_step(self):
        """تنفيذ خطوة اسم المستخدم ببصمة استراتيجية"""
        logging.info("[4] Entering username...")
        
        # تأخير استراتيجي
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(2.0, 4.0))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 1.0))
        else:
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # تغيير البصمة لهذه الخطوة
        self.create_strategic_castle_token()
        
        subtask_data = {
            'flow_token': self.flow_token,
            'subtask_inputs': [
                {
                    'subtask_id': 'LoginEnterUserIdentifierSSO',
                    'settings_list': {
                        'setting_responses': [{
                            'key': 'user_identifier',
                            'response_data': {'text_data': {'result': self.username}}
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
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                json=subtask_data,
                headers=headers
            )
            
            if response.status_code != 200:
                error_data = {
                    'status': response.status_code,
                    'response': response.text[:300],
                    'castle_token': self.castle_token[:30] + '...',
                    'username': self.username
                }
                
                # تحليل الخطأ
                try:
                    resp_json = response.json()
                    if 'errors' in resp_json:
                        for error in resp_json['errors']:
                            error_code = error.get('code', 'unknown')
                            error_msg = error.get('message', 'unknown')
                            error_data['error_code'] = error_code
                            error_data['error_message'] = error_msg
                            
                            # تسجيل نمط الخطأ
                            self.failure_patterns.append({
                                'attempt': self.attempt_count,
                                'strategy': self.current_fingerprint['strategy'],
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint
                            })
                except:
                    pass
                
                self.log_attempt('username_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"Username step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('username_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'castle_token': self.castle_token[:30] + '...'
            }, True)
            
            logging.info(f"    Username step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('username_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_password_step(self):
        """تنفيذ خطوة كلمة المرور ببصمة استراتيجية"""
        logging.info("[5] Entering password...")
        
        # تأخير استراتيجي
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(3.0, 6.0))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 1.0))
        else:
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # تغيير البصمة مرة أخرى لهذه الخطوة
        self.create_strategic_castle_token()
        
        subtask_data = {
            'flow_token': self.flow_token,
            'subtask_inputs': [
                {
                    'subtask_id': 'LoginEnterPassword',
                    'enter_password': {
                        'password': self.password,
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
        
        logging.info(f"    Debug - Headers count: {len(headers)}")
        logging.info(f"    Debug - Has CSRF token: {'x-csrf-token' in headers}")
        logging.info(f"    Debug - Castle token: {self.castle_token[:30]}...")
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                json=subtask_data,
                headers=headers
            )
            
            logging.info(f"    Debug - Response status: {response.status_code}")
            if response.status_code != 200:
                logging.info(f"    Debug - Response body: {response.text[:300]}...")
            
            if response.status_code != 200:
                error_data = {
                    'status': response.status_code,
                    'response': response.text[:300],
                    'headers_count': len(headers),
                    'has_csrf': 'x-csrf-token' in headers,
                    'castle_token': self.castle_token[:30] + '...',
                    'password_length': len(self.password)
                }
                
                # تحليل الخطأ
                try:
                    resp_json = response.json()
                    if 'errors' in resp_json:
                        for error in resp_json['errors']:
                            error_code = error.get('code', 'unknown')
                            error_msg = error.get('message', 'unknown')
                            error_data['error_code'] = error_code
                            error_data['error_message'] = error_msg
                            
                            # تسجيل نمط الخطأ
                            self.failure_patterns.append({
                                'attempt': self.attempt_count,
                                'strategy': self.current_fingerprint['strategy'],
                                'step': 'password',
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint,
                                'headers_count': len(headers),
                                'castle_method': 'original' if hasattr(self, 'castle_method') and self.castle_method == 'original' else 'fallback'
                            })
                except:
                    pass
                
                self.log_attempt('password_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"Password step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            # تسجيل نمط النجاح
            self.success_patterns.append({
                'attempt': self.attempt_count,
                'strategy': self.current_fingerprint['strategy'],
                'fingerprint': self.current_fingerprint,
                'headers_count': len(headers),
                'castle_method': 'original' if hasattr(self, 'castle_method') and self.castle_method == 'original' else 'fallback'
            })
            
            self.log_attempt('password_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'headers_count': len(headers),
                'castle_token': self.castle_token[:30] + '...'
            }, True)
            
            logging.info(f"    Password step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('password_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def verify_login_success(self):
        """التحقق من نجاح تسجيل الدخول"""
        logging.info("[6] Verifying login success...")
        
        # تأخير استراتيجي
        if self.current_fingerprint['strategy'] == 'stealth':
            await asyncio.sleep(random.uniform(2.0, 4.0))
        elif self.current_fingerprint['strategy'] == 'aggressive':
            await asyncio.sleep(random.uniform(0.1, 0.5))
        else:
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        try:
            response = await self.session.get(
                'https://x.com/home',
                params={'prefetchTimestamp': int(time.time() * 1000)},
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('login_verify', {
                    'status': response.status_code,
                    'error': 'Failed to verify login'
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to verify login: {response.status_code}")
            
            auth_token = self.session.cookies.get('auth_token', domain='.x.com')
            if not auth_token:
                self.log_attempt('login_verify', {
                    'error': 'auth_token not found'
                }, False, "auth_token not found")
                raise Exception("auth_token not found - login failed")
            
            ct0 = self.session.cookies.get('ct0', domain='.x.com')
            if not ct0:
                await asyncio.sleep(random.uniform(0.5, 1.0))
                response = await self.session.get('https://x.com/home')
                ct0 = self.session.cookies.get('ct0', domain='.x.com')
            
            cookies_data = {
                'auth_token': auth_token,
                'ct0': ct0,
                'all_cookies': dict(self.session.cookies),
                'fingerprint': self.current_fingerprint,
                'strategy': self.current_fingerprint['strategy'],
                'attempt': self.attempt_count
            }
            
            self.log_attempt('login_verify', {
                'auth_token': auth_token[:20] + '...',
                'ct0': ct0[:20] + '...' if ct0 else 'missing',
                'cookies_count': len(self.session.cookies),
                'strategy': self.current_fingerprint['strategy']
            }, True)
            
            logging.info(f"    ✅ Login successful!")
            logging.info(f"    Auth token: {auth_token[:20]}...")
            logging.info(f"    CSRF token: {ct0[:20]}..." if ct0 else "    CSRF token: Missing")
            logging.info(f"    Strategy: {self.current_fingerprint['strategy']}")
            logging.info(f"    Attempt: {self.attempt_count}")
            
            return cookies_data
            
        except Exception as e:
            self.log_attempt('login_verify', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def login(self):
        """تسجيل الدخول ببصمات استراتيجية متكررة"""
        logging.info("PERSISTENT LOGIN - Strategic Analysis System")
        logging.info("=" * 70)
        logging.info(f"Username: {self.username}")
        logging.info(f"Max attempts: {self.max_attempts}")
        logging.info("Each attempt uses a different strategic fingerprint")
        logging.info("=" * 70)
        
        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            
            logging.info(f"\nATTEMPT {attempt}/{self.max_attempts}")
            logging.info("=" * 50)
            
            try:
                await self.init_session()
                await self.extract_guest_token()
                await self.init_client_transaction()
                
                # بدء التدفق
                flow_result = await self.start_login_flow()
                
                # تنفيذ الخطوات ببصمات مختلفة
                await self.execute_username_step()
                await self.execute_password_step()
                
                # التحقق من النجاح
                cookies = await self.verify_login_success()
                
                # حفظ الكوكيز والتحليل
                cookies_dir = Path("cookies")
                cookies_dir.mkdir(exist_ok=True)
                
                cookie_file = cookies_dir / f"persistent_{self.username}_{int(time.time())}.json"
                
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
                    "fingerprint": cookies['fingerprint'],
                    "strategy": cookies['strategy'],
                    "attempt": cookies['attempt'],
                    "success_patterns": self.success_patterns,
                    "failure_patterns": self.failure_patterns
                }
                
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, indent=2, ensure_ascii=False)
                
                logging.info(f"PERSISTENT LOGIN COMPLETED SUCCESSFULLY!")
                logging.info(f"Strategy: {cookies['strategy']}")
                logging.info(f"Attempt: {cookies['attempt']}")
                logging.info(f"Fingerprint: {cookies['fingerprint']['browser_type']} on {cookies['fingerprint']['os_type']}")
                logging.info(f"Cookies and analysis saved to: {cookie_file}")
                
                # حفظ التحليل النهائي
                final_analysis = {
                    'total_attempts': attempt,
                    'successful_attempt': attempt,
                    'success_strategy': cookies['strategy'],
                    'success_fingerprint': cookies['fingerprint'],
                    'success_patterns': self.success_patterns,
                    'failure_patterns': self.failure_patterns,
                    'all_attempts_data': self.analysis_data
                }
                
                with open(f'final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                    json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                
                return cookies
                
            except Exception as e:
                logging.error(f"\n❌ Attempt {attempt} failed: {e}")
                
                # تحليل ما إذا يجب الاستمرار
                if attempt >= self.max_attempts:
                    logging.error(f"All {self.max_attempts} attempts failed!")
                    logging.error("Analysis complete - check the analysis files for patterns")
                    
                    # حفظ التحليل النهائي حتى لو فشل
                    final_analysis = {
                        'total_attempts': self.max_attempts,
                        'success': False,
                        'failure_patterns': self.failure_patterns,
                        'all_attempts_data': self.analysis_data,
                        'recommendations': self.generate_recommendations()
                    }
                    
                    with open(f'final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                        json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                    
                    raise Exception(f"All {self.max_attempts} attempts failed")
                
                # انتظار قبل المحاولة التالية
                wait_time = random.uniform(5.0, 15.0)
                logging.info(f"Waiting {wait_time:.1f} seconds before next attempt...")
                await asyncio.sleep(wait_time)
    
    def generate_recommendations(self):
        """توليد توصيات بناءً على التحليل"""
        recommendations = []
        
        # تحليل الاستراتيجيات الأكثر نجاحاً
        strategy_success = {}
        for pattern in self.failure_patterns:
            strategy = pattern.get('strategy', 'unknown')
            if strategy not in strategy_success:
                strategy_success[strategy] = 0
            strategy_success[strategy] += 1
        
        if strategy_success:
            best_strategy = min(strategy_success, key=strategy_success.get)
            recommendations.append(f"Strategy '{best_strategy}' had the fewest failures")
        
        # تحليل أنواع الأخطاء
        error_codes = {}
        for pattern in self.failure_patterns:
            code = pattern.get('error_code', 'unknown')
            if code not in error_codes:
                error_codes[code] = 0
            error_codes[code] += 1
        
        if error_codes:
            most_common = max(error_codes, key=error_codes.get)
            recommendations.append(f"Most common error: {most_common} ({error_codes[most_common]} times)")
            
            if most_common == '399':
                recommendations.append("Error 399 indicates IP/account restriction - try different IP/VPN")
            elif most_common == '366':
                recommendations.append("Error 366 indicates missing data - check headers and castle token")
        
        # توصيات عامة
        recommendations.append("Try manual_cookies.py for guaranteed success")
        recommendations.append("Consider changing IP/VPN for better results")
        recommendations.append("Wait 24-48 hours if account is temporarily restricted")
        
        return recommendations

async def main():
    """الوظيفة الرئيسية"""
    logging.info("PERSISTENT LOGIN SYSTEM")
    logging.info("Advanced strategic analysis with repeated attempts")
    logging.info("=" * 80)
    
    # استخدام بيانات الحساب المحددة
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    logging.info(f"Target account: {username}")
    logging.info(f"Max attempts: 50")
    logging.info("Press Ctrl+C to stop at any time")
    
    persistent = PersistentLogin(username, password)
    
    try:
        cookies = await persistent.login()
        
        logging.info(f"SUCCESS AFTER {persistent.attempt_count} ATTEMPTS!")
        logging.info(f"Strategy: {cookies['strategy']}")
        logging.info(f"Fingerprint: {cookies['fingerprint']['browser_type']} on {cookies['fingerprint']['os_type']}")
        
        # عرض التحليل
        logging.info(f"\nANALYSIS SUMMARY:")
        logging.info(f"Total attempts: {persistent.attempt_count}")
        logging.info(f"Success patterns: {len(persistent.success_patterns)}")
        logging.info(f"Failure patterns: {len(persistent.failure_patterns)}")
        logging.info(f"Analysis data points: {len(persistent.analysis_data)}")
        
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nPersistent login failed: {e}")
        logging.error("\nCheck the analysis files for detailed patterns")
        logging.error("Consider using manual_cookies.py for guaranteed success")

if __name__ == "__main__":
    asyncio.run(main())
