#!/usr/bin/env python3
"""
HTTPX Login - نظام باستخدام HTTPX مع بصمات متقدمة
يستخدم مكتبة HTTPX بدلاً من curl_cffi لتجربة تقنية مختلفة
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

import httpx
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('httpx_login.log'),
        logging.StreamHandler()
    ]
)

class HTTPXLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.session = None
        self.flow_token = None
        self.guest_token = None
        self.current_fingerprint = None
        self.attempt_count = 0
        self.max_attempts = 25
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
        
        with open(f'httpx_analysis_{datetime.now().strftime("%Y%m%d")}.json', 'a', encoding='utf-8') as f:
            json.dump(attempt_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        
        logging.info(f"HTTPX Attempt {self.attempt_count} - {step}: {'SUCCESS' if success else 'FAILED'}")
        if error_msg:
            logging.error(f"Error: {error_msg}")
    
    def generate_httpx_fingerprint(self):
        """توليد بصمة فريدة لـ HTTPX"""
        strategies = [
            'realistic',    # بصمة واقعية جداً
            'stealth',      # بصمة خفية
            'aggressive',   # بصمة عدوانية
            'experimental'  # بصمة تجريبية
        ]
        
        strategy = random.choice(strategies)
        
        if strategy == 'realistic':
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox']),
                'os_type': random.choice(['windows', 'macos', 'linux']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900)]),
                'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo']),
                'language': random.choice(['en-US', 'en-GB', 'fr-FR', 'de-DE']),
                'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
                'architecture': random.choice(['x86', 'x64', 'arm64']),
                'device_memory': random.choice(['8', '16', '32']),
                'hardware_concurrency': random.choice(['4', '8', '12', '16']),
                'strategy': 'realistic'
            }
        elif strategy == 'stealth':
            fingerprint = {
                'browser_type': 'chrome',  # الأكثر شيوعاً
                'os_type': 'windows',      # الأكثر شيوعاً
                'screen_resolution': (1920, 1080),  # الأكثر شيوعاً
                'timezone': 'America/New_York',     # الأكثر شيوعاً
                'language': 'en-US',      # الأكثر شيوعاً
                'platform': 'Win32',
                'architecture': 'x64',
                'device_memory': '8',
                'hardware_concurrency': '4',
                'strategy': 'stealth'
            }
        elif strategy == 'aggressive':
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox', 'edge']),
                'os_type': random.choice(['windows', 'macos', 'linux', 'android', 'ios']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720), (1600, 900), (2560, 1440)]),
                'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo', 'America/Los_Angeles', 'Europe/Paris', 'Asia/Dubai', 'Australia/Sydney']),
                'language': random.choice(['en-US', 'ar-SA', 'fr-FR', 'ja-JP', 'es-ES', 'de-DE', 'zh-CN', 'ru-RU']),
                'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64', 'Linux armv7l', 'iPhone']),
                'architecture': random.choice(['x86', 'x64', 'arm64', 'arm']),
                'device_memory': random.choice(['4', '8', '16', '32', '64']),
                'hardware_concurrency': random.choice(['2', '4', '8', '12', '16', '24']),
                'strategy': 'aggressive'
            }
        else:  # experimental
            fingerprint = {
                'browser_type': random.choice(['chrome', 'firefox', 'edge', 'safari', 'opera']),
                'os_type': random.choice(['windows', 'macos', 'linux', 'freebsd', 'openbsd']),
                'screen_resolution': random.choice([(1920, 1080), (1366, 768), (1440, 900), (2560, 1440), (3840, 2160)]),
                'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo', 'America/Los_Angeles', 'Europe/Paris', 'Asia/Dubai', 'Australia/Sydney', 'America/Chicago']),
                'language': random.choice(['en-US', 'ar-SA', 'fr-FR', 'ja-JP', 'es-ES', 'de-DE', 'zh-CN', 'ru-RU', 'pt-BR', 'it-IT']),
                'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64', 'Linux armv7l', 'iPhone', 'iPad']),
                'architecture': random.choice(['x86', 'x64', 'arm64', 'arm', 'mips']),
                'device_memory': random.choice(['2', '4', '8', '16', '32', '64', '128']),
                'hardware_concurrency': random.choice(['1', '2', '4', '8', '12', '16', '24', '32', '64']),
                'strategy': 'experimental'
            }
        
        return fingerprint
    
    def get_httpx_headers(self, fingerprint):
        """توليد هيدرز متقدمة لـ HTTPX"""
        # User-Agent واقعي جداً
        if fingerprint['browser_type'] == 'chrome':
            version = random.choice(['120.0.6099.129', '121.0.6167.85', '122.0.6261.94', '123.0.6312.58'])
            if fingerprint['os_type'] == 'windows':
                user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif fingerprint['os_type'] == 'macos':
                user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif fingerprint['os_type'] == 'linux':
                user_agent = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            else:
                user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        elif fingerprint['browser_type'] == 'firefox':
            version = random.choice(['121.0', '122.0', '123.0', '124.0'])
            if fingerprint['os_type'] == 'windows':
                user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif fingerprint['os_type'] == 'macos':
                user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif fingerprint['os_type'] == 'linux':
                user_agent = f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}) Gecko/20100101 Firefox/{version}"
            else:
                user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
        elif fingerprint['browser_type'] == 'edge':
            version = random.choice(['120.0.2210.91', '121.0.2277.83', '122.0.2365.52'])
            user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
        elif fingerprint['browser_type'] == 'safari':
            version = random.choice(['16.5', '17.0', '17.1'])
            user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
        else:  # opera
            version = random.choice(['105.0.4970.44', '106.0.4998.52'])
            user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 OPR/{version}"
        
        # Accept-Language بناءً على اللغة
        accept_languages = {
            'en-US': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
            'en-GB': 'en-GB,en;q=0.9,fr;q=0.8,de;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'ar-SA': 'ar-SA,ar;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,es;q=0.5,it;q=0.4',
            'fr-FR': 'fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'ja-JP': 'ja-JP,ja;q=0.9,en;q=0.8,ko;q=0.7,zh-CN;q=0.6,zh;q=0.5,fr;q=0.4',
            'es-ES': 'es-ES,es;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,it;q=0.5,pt;q=0.4',
            'de-DE': 'de-DE,de;q=0.9,en;q=0.8,fr;q=0.7,es;q=0.6,it;q=0.5,pt;q=0.4',
            'zh-CN': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,ko;q=0.6,fr;q=0.5,de;q=0.4',
            'ru-RU': 'ru-RU,ru;q=0.9,en;q=0.8,uk;q=0.7,de;q=0.6,fr;q=0.5,it;q=0.4',
            'pt-BR': 'pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7,fr;q=0.6,it;q=0.5,de;q=0.4',
            'it-IT': 'it-IT,it;q=0.9,en;q=0.8,fr;q=0.7,de;q=0.6,es;q=0.5,pt;q=0.4'
        }
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': accept_languages.get(fingerprint['language'], accept_languages['en-US']),
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': random.choice(['1', '0']),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': f'"Chromium";v="{random.choice(["120", "121", "122", "123"])}", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{fingerprint["platform"]}"',
            'Sec-Purpose': 'prefetch',
            'Purpose': 'prefetch'
        }
        
        # إضافة هيدرز خاصة بالـ Client Hints
        if fingerprint['browser_type'] == 'chrome':
            headers.update({
                'sec-ch-ua-arch': f'"{fingerprint["architecture"]}"',
                'sec-ch-ua-bitness': f'{"64" if "64" in fingerprint["architecture"] else "32"}',
                'sec-ch-ua-full-version-list': f'"Chromium";v="{random.choice(["120.0.6099.129", "121.0.6167.85", "122.0.6261.94"])}", "Not_A Brand";v="99.0.0.0"',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-wow64': '?0'
            })
        
        return headers
    
    async def init_session(self):
        """تهيئة جلسة HTTPX ببصمة استراتيجية"""
        self.current_fingerprint = self.generate_httpx_fingerprint()
        
        headers = self.get_httpx_headers(self.current_fingerprint)
        
        logging.info(f"HTTPX Strategy: {self.current_fingerprint['strategy']}")
        logging.info(f"Browser: {self.current_fingerprint['browser_type']} on {self.current_fingerprint['os_type']}")
        logging.info(f"Platform: {self.current_fingerprint['platform']}")
        logging.info(f"Architecture: {self.current_fingerprint['architecture']}")
        logging.info(f"Screen: {self.current_fingerprint['screen_resolution'][0]}x{self.current_fingerprint['screen_resolution'][1]}")
        logging.info(f"Language: {self.current_fingerprint['language']}")
        logging.info(f"Memory: {self.current_fingerprint['device_memory']}GB")
        logging.info(f"Cores: {self.current_fingerprint['hardware_concurrency']}")
        
        # إعدادات HTTPX متقدمة
        timeout = httpx.Timeout(30.0, connect=10.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        
        self.session = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers=headers,
            http2=True,  # استخدام HTTP/2
            verify=True,  # SSL verification
            follow_redirects=True
        )
        
        self.log_attempt('httpx_session_init', {
            'fingerprint': self.current_fingerprint,
            'headers_count': len(headers),
            'http2_enabled': True,
            'timeout': 30.0
        })
    
    def generate_httpx_transaction_id(self, method, path):
        """توليد transaction ID فريد لـ HTTPX"""
        timestamp = int(time.time() * 1000)
        random_val = random.randint(100000, 999999)
        strategy = self.current_fingerprint['strategy']
        return f"httpx_{method.upper()}:{path}:{timestamp}:{random_val}:{strategy}"
    
    async def extract_guest_token(self):
        """استخراج guest token باستخدام HTTPX"""
        logging.info("[1] Extracting HTTPX guest token...")
        
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        headers = dict(self.session.headers)
        headers.update({
            'Purpose': 'prefetch',
            'Sec-Purpose': 'prefetch'
        })
        
        try:
            # محاولة استخدام endpoint مختلف
            response = await self.session.get(
                'https://x.com/i/api/1.1/guest/activate.json',
                headers=headers
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                self.guest_token = resp_data.get('guest_token')
            
            if not self.guest_token:
                # Fallback method
                response = await self.session.get(
                    'https://x.com/i/flow/login',
                    headers=headers
                )
                
                gt_match = re.search(r'gt=([0-9]+);', response.text)
                if not gt_match:
                    raise Exception("Guest token not found")
                
                self.guest_token = gt_match.group(1)
            
            self.session.cookies.set('gt', self.guest_token, '.x.com')
            
            self.log_attempt('httpx_guest_token_extract', {
                'guest_token': self.guest_token[:20] + '...',
                'success': True,
                'method': 'fallback' if not response.json().get('guest_token') else 'direct'
            }, True)
            
            logging.info(f"    HTTPX guest token: {self.guest_token[:20]}...")
            
        except Exception as e:
            self.log_attempt('httpx_guest_token_extract', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def init_httpx_client_transaction(self):
        """تهيئة client transaction لـ HTTPX"""
        logging.info("[2] Initializing HTTPX client transaction...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'Purpose': 'prefetch',
            'Sec-Purpose': 'prefetch'
        })
        
        try:
            response = await self.session.get('https://x.com', headers=headers)
            
            self.client_transaction_id = self.generate_httpx_transaction_id('POST', '/1.1/onboarding/task.json')
            
            self.log_attempt('httpx_client_transaction_init', {
                'transaction_id': self.client_transaction_id[:30] + '...',
                'status': response.status_code,
                'http2_used': response.http_version == "HTTP/2"
            }, True)
            
            logging.info(f"    HTTPX transaction ID: {self.client_transaction_id[:30]}...")
            logging.info(f"    HTTP/2 enabled: {response.http_version == 'HTTP/2'}")
            
        except Exception as e:
            self.log_attempt('httpx_client_transaction_init', {
                'error': str(e)
            }, False, str(e))
            raise
    
    def create_httpx_castle_token(self):
        """إنشاء castle token لـ HTTPX"""
        # وقت عشوائي مختلف
        if self.current_fingerprint['strategy'] == 'stealth':
            time_offset = random.randint(86400000, 604800000)  # 1-7 أيام
        elif self.current_fingerprint['strategy'] == 'aggressive':
            time_offset = random.randint(3600000, 7200000)  # 1-2 ساعات
        else:
            time_offset = random.randint(86400000, 172800000)  # 1-2 أيام
        
        init_time = int(time.time() * 1000) - time_offset
        
        # cuid فريد جداً
        cuid_parts = [
            self.current_fingerprint['strategy'],
            str(int(time.time() * 1000)),
            self.current_fingerprint['browser_type'],
            self.current_fingerprint['os_type'],
            uuid.uuid4().hex[:8]
        ]
        cuid = ''.join(cuid_parts)
        
        self.session.cookies.set('__cuid', cuid, '.x.com')
        
        try:
            castle = CastleToken(init_time, cuid)
            self.castle_token = castle.create_token()
            castle_method = 'original'
        except Exception as e:
            logging.warning(f"HTTPX castle token failed, using fallback - {e}")
            timestamp = int(time.time() * 1000)
            random_val = random.randint(0, 255)
            self.castle_token = f"httpx_castle:{timestamp}:{random_val}:{cuid[:16]}"
            castle_method = 'fallback'
        
        self.log_attempt('httpx_castle_token_create', {
            'method': castle_method,
            'time_offset_hours': -(time_offset / 1000 / 3600),
            'castle_token': self.castle_token[:30] + '...',
            'cuid': cuid[:20] + '...'
        }, True)
        
        logging.info(f"    HTTPX castle token ({castle_method}): {self.castle_token[:30]}...")
        logging.info(f"    Time offset: {-(time_offset / 1000 / 3600):.1f} hours")
    
    async def start_httpx_login_flow(self):
        """بدء تدفق تسجيل الدخول لـ HTTPX"""
        logging.info("[3] Starting HTTPX login flow...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        flow_data = {
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {"location": "httpx_login"}
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
            'x-client-transaction-id': self.client_transaction_id,
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'].split('-')[0],
            'x-csrf-token': self.session.cookies.get('ct0', ''),
        }
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                params={'flow_name': 'login'},
                json=flow_data,
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('httpx_flow_start', {
                    'status': response.status_code,
                    'response': response.text[:200],
                    'http_version': response.http_version
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to start HTTPX flow: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('httpx_flow_start', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'http_version': response.http_version
            }, True)
            
            logging.info(f"    HTTPX flow started successfully!")
            logging.info(f"    Flow token: {self.flow_token[:30]}...")
            logging.info(f"    HTTP version: {response.http_version}")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('httpx_flow_start', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_httpx_username_step(self):
        """تنفيذ خطوة اسم المستخدم لـ HTTPX"""
        logging.info("[4] Entering HTTPX username...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        self.create_httpx_castle_token()
        
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
            'x-client-transaction-id': self.generate_httpx_transaction_id('POST', '/1.1/onboarding/task.json'),
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
                    'username': self.username,
                    'strategy': self.current_fingerprint['strategy'],
                    'http_version': response.http_version
                }
                
                try:
                    resp_json = response.json()
                    if 'errors' in resp_json:
                        for error in resp_json['errors']:
                            error_code = error.get('code', 'unknown')
                            error_msg = error.get('message', 'unknown')
                            error_data['error_code'] = error_code
                            error_data['error_message'] = error_msg
                            
                            self.failure_patterns.append({
                                'attempt': self.attempt_count,
                                'strategy': self.current_fingerprint['strategy'],
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint,
                                'http_version': response.http_version
                            })
                except:
                    pass
                
                self.log_attempt('httpx_username_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"HTTPX username step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('httpx_username_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'castle_token': self.castle_token[:30] + '...',
                'http_version': response.http_version
            }, True)
            
            logging.info(f"    HTTPX username step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('httpx_username_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_httpx_password_step(self):
        """تنفيذ خطوة كلمة المرور لـ HTTPX"""
        logging.info("[5] Entering HTTPX password...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        self.create_httpx_castle_token()
        
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
            'x-client-transaction-id': self.generate_httpx_transaction_id('POST', '/1.1/onboarding/task.json'),
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'].split('-')[0],
            'x-csrf-token': self.session.cookies.get('ct0', ''),
        }
        
        logging.info(f"    Debug - HTTPX headers count: {len(headers)}")
        logging.info(f"    Debug - Has CSRF token: {'x-csrf-token' in headers}")
        logging.info(f"    Debug - Castle token: {self.castle_token[:30]}...")
        logging.info(f"    Debug - Strategy: {self.current_fingerprint['strategy']}")
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                json=subtask_data,
                headers=headers
            )
            
            logging.info(f"    Debug - Response status: {response.status_code}")
            logging.info(f"    Debug - HTTP version: {response.http_version}")
            if response.status_code != 200:
                logging.info(f"    Debug - Response body: {response.text[:300]}...")
            
            if response.status_code != 200:
                error_data = {
                    'status': response.status_code,
                    'response': response.text[:300],
                    'headers_count': len(headers),
                    'has_csrf': 'x-csrf-token' in headers,
                    'castle_token': self.castle_token[:30] + '...',
                    'password_length': len(self.password),
                    'strategy': self.current_fingerprint['strategy'],
                    'http_version': response.http_version
                }
                
                try:
                    resp_json = response.json()
                    if 'errors' in resp_json:
                        for error in resp_json['errors']:
                            error_code = error.get('code', 'unknown')
                            error_msg = error.get('message', 'unknown')
                            error_data['error_code'] = error_code
                            error_data['error_message'] = error_msg
                            
                            self.failure_patterns.append({
                                'attempt': self.attempt_count,
                                'strategy': self.current_fingerprint['strategy'],
                                'step': 'httpx_password',
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint,
                                'headers_count': len(headers),
                                'http_version': response.http_version
                            })
                except:
                    pass
                
                self.log_attempt('httpx_password_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"HTTPX password step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.success_patterns.append({
                'attempt': self.attempt_count,
                'strategy': self.current_fingerprint['strategy'],
                'fingerprint': self.current_fingerprint,
                'headers_count': len(headers),
                'http_version': response.http_version
            })
            
            self.log_attempt('httpx_password_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'headers_count': len(headers),
                'castle_token': self.castle_token[:30] + '...',
                'http_version': response.http_version
            }, True)
            
            logging.info(f"    HTTPX password step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('httpx_password_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def verify_httpx_login_success(self):
        """التحقق من نجاح تسجيل الدخول لـ HTTPX"""
        logging.info("[6] Verifying HTTPX login success...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'Purpose': 'prefetch',
            'Sec-Purpose': 'prefetch'
        })
        
        try:
            response = await self.session.get(
                'https://x.com/home',
                params={'prefetchTimestamp': int(time.time() * 1000)},
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('httpx_login_verify', {
                    'status': response.status_code,
                    'error': 'Failed to verify HTTPX login',
                    'http_version': response.http_version
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to verify HTTPX login: {response.status_code}")
            
            auth_token = self.session.cookies.get('auth_token', domain='.x.com')
            if not auth_token:
                self.log_attempt('httpx_login_verify', {
                    'error': 'auth_token not found'
                }, False, "auth_token not found")
                raise Exception("auth_token not found - HTTPX login failed")
            
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
                'attempt': self.attempt_count,
                'http_version': response.http_version
            }
            
            self.log_attempt('httpx_login_verify', {
                'auth_token': auth_token[:20] + '...',
                'ct0': ct0[:20] + '...' if ct0 else 'missing',
                'cookies_count': len(self.session.cookies),
                'strategy': self.current_fingerprint['strategy'],
                'http_version': response.http_version
            }, True)
            
            logging.info(f"    HTTPX login successful!")
            logging.info(f"    Auth token: {auth_token[:20]}...")
            logging.info(f"    CSRF token: {ct0[:20]}..." if ct0 else "    CSRF token: Missing")
            logging.info(f"    Strategy: {self.current_fingerprint['strategy']}")
            logging.info(f"    HTTP version: {response.http_version}")
            logging.info(f"    Attempt: {self.attempt_count}")
            
            return cookies_data
            
        except Exception as e:
            self.log_attempt('httpx_login_verify', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def httpx_login(self):
        """تسجيل الدخول ببصمات HTTPX متكررة"""
        logging.info("HTTPX LOGIN - Advanced HTTP/2 Fingerprint System")
        logging.info("=" * 70)
        logging.info(f"Username: {self.username}")
        logging.info(f"Max attempts: {self.max_attempts}")
        logging.info("Each attempt uses different HTTPX fingerprint with HTTP/2")
        logging.info("=" * 70)
        
        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            
            logging.info(f"\nHTTPX ATTEMPT {attempt}/{self.max_attempts}")
            logging.info("=" * 50)
            
            try:
                await self.init_session()
                await self.extract_guest_token()
                await self.init_httpx_client_transaction()
                
                # بدء التدفق
                flow_result = await self.start_httpx_login_flow()
                
                # تنفيذ الخطوات ببصمات مختلفة
                await self.execute_httpx_username_step()
                await self.execute_httpx_password_step()
                
                # التحقق من النجاح
                cookies = await self.verify_httpx_login_success()
                
                # حفظ الكوكيز والتحليل
                cookies_dir = Path("cookies")
                cookies_dir.mkdir(exist_ok=True)
                
                cookie_file = cookies_dir / f"httpx_{self.username}_{int(time.time())}.json"
                
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
                    "http_version": cookies['http_version'],
                    "success_patterns": self.success_patterns,
                    "failure_patterns": self.failure_patterns
                }
                
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, indent=2, ensure_ascii=False)
                
                logging.info(f"\nHTTPX LOGIN COMPLETED SUCCESSFULLY!")
                logging.info(f"Strategy: {cookies['strategy']}")
                logging.info(f"Attempt: {cookies['attempt']}")
                logging.info(f"HTTP version: {cookies['http_version']}")
                logging.info(f"Fingerprint: {cookies['fingerprint']['browser_type']} on {cookies['fingerprint']['os_type']}")
                logging.info(f"Cookies and analysis saved to: {cookie_file}")
                
                # حفظ التحليل النهائي
                final_analysis = {
                    'total_attempts': attempt,
                    'successful_attempt': attempt,
                    'success_strategy': cookies['strategy'],
                    'success_fingerprint': cookies['fingerprint'],
                    'success_http_version': cookies['http_version'],
                    'success_patterns': self.success_patterns,
                    'failure_patterns': self.failure_patterns,
                    'all_attempts_data': self.analysis_data
                }
                
                with open(f'httpx_final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                    json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                
                return cookies
                
            except Exception as e:
                logging.error(f"\nHTTPX attempt {attempt} failed: {e}")
                
                if attempt >= self.max_attempts:
                    logging.error(f"\nAll {self.max_attempts} HTTPX attempts failed!")
                    logging.error("HTTPX analysis complete - check the analysis files for patterns")
                    
                    final_analysis = {
                        'total_attempts': self.max_attempts,
                        'success': False,
                        'failure_patterns': self.failure_patterns,
                        'all_attempts_data': self.analysis_data,
                        'recommendations': self.generate_httpx_recommendations()
                    }
                    
                    with open(f'httpx_final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                        json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                    
                    raise Exception(f"All {self.max_attempts} HTTPX attempts failed")
                
                wait_time = random.uniform(5.0, 15.0)
                logging.info(f"Waiting {wait_time:.1f} seconds before next HTTPX attempt...")
                await asyncio.sleep(wait_time)
    
    def generate_httpx_recommendations(self):
        """توليد توصيات لـ HTTPX"""
        recommendations = []
        
        # تحليل الاستراتيجيات
        strategy_success = {}
        for pattern in self.failure_patterns:
            strategy = pattern.get('strategy', 'unknown')
            if strategy not in strategy_success:
                strategy_success[strategy] = 0
            strategy_success[strategy] += 1
        
        if strategy_success:
            best_strategy = min(strategy_success, key=strategy_success.get)
            recommendations.append(f"Strategy '{best_strategy}' had the fewest failures")
        
        # تحليل HTTP versions
        http_versions = {}
        for pattern in self.failure_patterns:
            version = pattern.get('http_version', 'unknown')
            if version not in http_versions:
                http_versions[version] = 0
            http_versions[version] += 1
        
        if http_versions:
            best_version = min(http_versions, key=http_versions.get)
            recommendations.append(f"HTTP version '{best_version}' had the fewest failures")
        
        recommendations.append("Try manual_cookies.py for guaranteed success")
        recommendations.append("HTTPX with HTTP/2 shows promise but needs refinement")
        recommendations.append("Consider combining HTTPX with residential proxy")
        
        return recommendations

async def main():
    """الوظيفة الرئيسية"""
    logging.info("HTTPX LOGIN SYSTEM")
    logging.info("Advanced HTTP/2 client with sophisticated fingerprinting")
    logging.info("=" * 80)
    
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    logging.info(f"Target account: {username}")
    logging.info(f"Max attempts: 25")
    logging.info("Press Ctrl+C to stop at any time")
    
    httpx_login = HTTPXLogin(username, password)
    
    try:
        cookies = await httpx_login.httpx_login()
        
        logging.info(f"\nHTTPX SUCCESS AFTER {httpx_login.attempt_count} ATTEMPTS!")
        logging.info(f"Strategy: {cookies['strategy']}")
        logging.info(f"HTTP version: {cookies['http_version']}")
        logging.info(f"Fingerprint: {cookies['fingerprint']['browser_type']} on {cookies['fingerprint']['os_type']}")
        
        logging.info(f"\nHTTPX ANALYSIS SUMMARY:")
        logging.info(f"Total attempts: {httpx_login.attempt_count}")
        logging.info(f"Success patterns: {len(httpx_login.success_patterns)}")
        logging.info(f"Failure patterns: {len(httpx_login.failure_patterns)}")
        logging.info(f"Analysis data points: {len(httpx_login.analysis_data)}")
        
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nHTTPX login failed: {e}")
        logging.error("\nCheck the HTTPX analysis files for detailed patterns")
        logging.error("Consider using manual_cookies.py for guaranteed success")

if __name__ == "__main__":
    asyncio.run(main())
