#!/usr/bin/env python3
"""
Mobile Login - نظام محاكاة الجوال/تطبيق لتجاوز حماية تويتر
يستخدم بصمات الهاتف والتطبيقات بدلاً من المتصفح
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

import curl_cffi
from curl_cffi import AsyncSession
from x_auth.castle import CastleToken
from x_auth.transaction import ClientTransaction

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mobile_login.log'),
        logging.StreamHandler()
    ]
)

class MobileLogin:
    def __init__(self, username="Ga6rsah", password="Mm8221809@@"):
        self.username = username
        self.password = password
        self.session = None
        self.flow_token = None
        self.guest_token = None
        self.current_fingerprint = None
        self.attempt_count = 0
        self.max_attempts = 30
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
        
        with open(f'mobile_analysis_{datetime.now().strftime("%Y%m%d")}.json', 'a', encoding='utf-8') as f:
            json.dump(attempt_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        
        logging.info(f"Mobile Attempt {self.attempt_count} - {step}: {'SUCCESS' if success else 'FAILED'}")
        if error_msg:
            logging.error(f"Error: {error_msg}")
    
    def generate_mobile_fingerprint(self):
        """توليد بصمة هاتف/تطبيق فريدة"""
        device_types = [
            'android_phone', 'android_tablet', 'iphone', 'ipad', 'mobile_web'
        ]
        
        device_type = random.choice(device_types)
        
        if device_type == 'android_phone':
            fingerprint = {
                'device_type': 'android_phone',
                'device_name': random.choice([
                    'SM-G998B', 'SM-S918B', 'Pixel 7 Pro', 'OnePlus 11', 
                    'Xiaomi 13 Pro', 'Samsung Galaxy S23', 'Google Pixel 8'
                ]),
                'os_version': random.choice(['13', '14', '15']),
                'app_version': random.choice(['10.15.0', '10.16.1', '10.17.0', '10.18.2']),
                'screen_resolution': random.choice([
                    (1080, 2400), (1440, 3120), (1200, 2640), (1080, 2340)
                ]),
                'language': random.choice(['en', 'ar', 'es', 'fr', 'ja', 'zh']),
                'country': random.choice(['US', 'SA', 'ES', 'FR', 'JP', 'CN']),
                'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'STC', 'Etisalat']),
                'device_id': hashlib.md5(f"android_{time.time()}".encode()).hexdigest()[:16],
                'install_id': uuid.uuid4().hex[:16],
                'advertising_id': uuid.uuid4().hex[:16],
                'strategy': 'mobile_android'
            }
        elif device_type == 'iphone':
            fingerprint = {
                'device_type': 'iphone',
                'device_name': random.choice([
                    'iPhone14,3', 'iPhone15,2', 'iPhone15,4', 'iPhone15,5',
                    'iPhone16,1', 'iPhone16,2'
                ]),
                'os_version': random.choice(['16.5', '16.6', '17.0', '17.1']),
                'app_version': random.choice(['10.15.0', '10.16.1', '10.17.0', '10.18.2']),
                'screen_resolution': random.choice([
                    (1179, 2556), (1284, 2778), (1290, 2796), (1440, 3200)
                ]),
                'language': random.choice(['en', 'ar', 'es', 'fr', 'ja', 'zh']),
                'country': random.choice(['US', 'SA', 'ES', 'FR', 'JP', 'CN']),
                'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'STC', 'Etisalat']),
                'device_id': hashlib.md5(f"ios_{time.time()}".encode()).hexdigest()[:16],
                'install_id': uuid.uuid4().hex[:16],
                'advertising_id': uuid.uuid4().hex[:16],
                'strategy': 'mobile_ios'
            }
        elif device_type == 'android_tablet':
            fingerprint = {
                'device_type': 'android_tablet',
                'device_name': random.choice([
                    'SM-X900', 'Pixel Tablet', 'Galaxy Tab S9', 'Surface Pro'
                ]),
                'os_version': random.choice(['13', '14', '15']),
                'app_version': random.choice(['10.15.0', '10.16.1', '10.17.0']),
                'screen_resolution': random.choice([
                    (1600, 2560), (1800, 2880), (2048, 2732)
                ]),
                'language': random.choice(['en', 'ar', 'es', 'fr', 'ja']),
                'country': random.choice(['US', 'SA', 'ES', 'FR', 'JP']),
                'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'STC']),
                'device_id': hashlib.md5(f"tablet_{time.time()}".encode()).hexdigest()[:16],
                'install_id': uuid.uuid4().hex[:16],
                'advertising_id': uuid.uuid4().hex[:16],
                'strategy': 'mobile_tablet'
            }
        elif device_type == 'ipad':
            fingerprint = {
                'device_type': 'ipad',
                'device_name': random.choice([
                    'iPad14,1', 'iPad14,2', 'iPad13,18', 'iPad13,19'
                ]),
                'os_version': random.choice(['16.5', '16.6', '17.0', '17.1']),
                'app_version': random.choice(['10.15.0', '10.16.1', '10.17.0']),
                'screen_resolution': random.choice([
                    (1640, 2360), (1668, 2388), (2048, 2732), (2732, 2048)
                ]),
                'language': random.choice(['en', 'ar', 'es', 'fr', 'ja']),
                'country': random.choice(['US', 'SA', 'ES', 'FR', 'JP']),
                'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'STC']),
                'device_id': hashlib.md5(f"ipad_{time.time()}".encode()).hexdigest()[:16],
                'install_id': uuid.uuid4().hex[:16],
                'advertising_id': uuid.uuid4().hex[:16],
                'strategy': 'mobile_ipad'
            }
        else:  # mobile_web
            fingerprint = {
                'device_type': 'mobile_web',
                'device_name': random.choice([
                    'Mobile Safari', 'Chrome Mobile', 'Samsung Browser'
                ]),
                'os_version': random.choice(['iOS 17.1', 'Android 14', 'Android 15']),
                'app_version': random.choice(['10.15.0', '10.16.1', '10.17.0']),
                'screen_resolution': random.choice([
                    (375, 667), (414, 896), (390, 844), (428, 926)
                ]),
                'language': random.choice(['en', 'ar', 'es', 'fr', 'ja']),
                'country': random.choice(['US', 'SA', 'ES', 'FR', 'JP']),
                'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'STC']),
                'device_id': hashlib.md5(f"mobile_web_{time.time()}".encode()).hexdigest()[:16],
                'install_id': uuid.uuid4().hex[:16],
                'advertising_id': uuid.uuid4().hex[:16],
                'strategy': 'mobile_web'
            }
        
        return fingerprint
    
    def get_mobile_headers(self, fingerprint):
        """توليد هيدرز التطبيق/الموبايل"""
        
        # User-Agent للتطبيق المحمول
        if fingerprint['device_type'] in ['android_phone', 'android_tablet']:
            user_agent = f"TwitterAndroid/{fingerprint['app_version']} (Linux; Android {fingerprint['os_version']}; {fingerprint['device_name']}; Build/{random.choice(['RD1A', 'RD2A', 'RD3A'])})"
        elif fingerprint['device_type'] in ['iphone', 'ipad']:
            user_agent = f"Twitter/{fingerprint['app_version']} CFNetwork/1490.0.4 Darwin/23.3.0"
        else:  # mobile_web
            if 'Safari' in fingerprint['device_name']:
                user_agent = f"Mozilla/5.0 (iPhone; CPU iPhone OS {fingerprint['os_version'].replace('.', '_')} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.choice(['17.1', '17.0', '16.6'])} Mobile/15E148 Safari/604.1"
            elif 'Chrome' in fingerprint['device_name']:
                user_agent = f"Mozilla/5.0 (Linux; Android {fingerprint['os_version']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(['120.0.6099', '121.0.6167', '122.0.6261'])} Mobile Safari/537.36"
            else:
                user_agent = f"Mozilla/5.0 (Linux; Android {fingerprint['os_version']}; {fingerprint['device_name']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(['120.0.6099', '121.0.6167'])} Mobile Safari/537.36"
        
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': f"{fingerprint['language']}-{fingerprint['country']},{fingerprint['language']};q=0.9",
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Twitter-Client-Version': fingerprint['app_version'],
            'X-Twitter-Client-Platform': fingerprint['device_type'].upper(),
            'X-Twitter-Active-User': 'yes',
            'X-Twitter-API-Version': '2.0',
            'X-Client-UUID': fingerprint['device_id'],
            'X-Installation-ID': fingerprint['install_id'],
            'X-Advertising-ID': fingerprint['advertising_id'],
            'X-Device-ID': fingerprint['device_id'],
            'X-OS-Version': fingerprint['os_version'],
            'X-Device-Name': fingerprint['device_name'],
            'X-Carrier': fingerprint['carrier'],
            'X-Screen-Resolution': f"{fingerprint['screen_resolution'][0]}x{fingerprint['screen_resolution'][1]}",
            'X-Language': fingerprint['language'],
            'X-Country': fingerprint['country']
        }
        
        # إضافة هيدرز خاصة بنوع الجهاز
        if fingerprint['device_type'] in ['android_phone', 'android_tablet']:
            headers.update({
                'X-Platform': 'Android',
                'X-App-Version': fingerprint['app_version'],
                'X-Package-Name': 'com.twitter.android'
            })
        elif fingerprint['device_type'] in ['iphone', 'ipad']:
            headers.update({
                'X-Platform': 'iOS',
                'X-App-Version': fingerprint['app_version'],
                'X-Package-Name': 'com.atebits.Tweetie2'
            })
        
        return headers
    
    def get_mobile_impersonate(self, fingerprint):
        """الحصول على إعدادات curl_cffi للموبايل"""
        if fingerprint['device_type'] in ['android_phone', 'android_tablet']:
            return random.choice(['chrome99', 'chrome100', 'chrome101', 'chrome104', 'chrome107'])
        elif fingerprint['device_type'] in ['iphone', 'ipad']:
            return random.choice(['safari15', 'safari16'])
        else:  # mobile_web
            return random.choice(['chrome99', 'chrome100', 'chrome101', 'safari15'])
    
    async def init_session(self):
        """تهيئة جلسة ببصمة موبايل"""
        self.current_fingerprint = self.generate_mobile_fingerprint()
        
        headers = self.get_mobile_headers(self.current_fingerprint)
        impersonate = self.get_mobile_impersonate(self.current_fingerprint)
        
        logging.info(f"Mobile Strategy: {self.current_fingerprint['strategy']}")
        logging.info(f"Device: {self.current_fingerprint['device_type']} - {self.current_fingerprint['device_name']}")
        logging.info(f"OS: {self.current_fingerprint['os_version']}")
        logging.info(f"Screen: {self.current_fingerprint['screen_resolution'][0]}x{self.current_fingerprint['screen_resolution'][1]}")
        logging.info(f"Language: {self.current_fingerprint['language']}-{self.current_fingerprint['country']}")
        logging.info(f"Carrier: {self.current_fingerprint['carrier']}")
        logging.info(f"Using: {impersonate}")
        
        self.session = AsyncSession(
            impersonate=impersonate,
            timeout=30,
            headers=headers
        )
        
        self.log_attempt('mobile_session_init', {
            'fingerprint': self.current_fingerprint,
            'impersonate': impersonate,
            'headers_count': len(headers)
        })
    
    def generate_mobile_transaction_id(self, method, path):
        """توليد transaction ID للموبايل"""
        timestamp = int(time.time() * 1000)
        random_val = random.randint(100000, 999999)
        device_id = self.current_fingerprint['device_id']
        return f"mobile_{method.upper()}:{path}:{timestamp}:{random_val}:{device_id}"
    
    async def extract_guest_token(self):
        """استخراج guest token للموبايل"""
        logging.info("[1] Extracting mobile guest token...")
        
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        headers = dict(self.session.headers)
        headers.update({
            'X-Twitter-Poll-ID': str(int(time.time() * 1000)),
            'X-Twitter-Device-ID': self.current_fingerprint['device_id']
        })
        
        try:
            # استخدام endpoint موبايل مختلف
            response = await self.session.get(
                'https://x.com/i/api/1.1/guest/activate.json',
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('mobile_guest_token_extract', {
                    'status': response.status_code,
                    'error': 'Failed to activate guest'
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to activate guest: {response.status_code}")
            
            resp_data = response.json()
            self.guest_token = resp_data.get('guest_token')
            
            if not self.guest_token:
                # Fallback to regular method
                response = await self.session.get(
                    'https://x.com/i/flow/login',
                    headers=headers
                )
                
                gt_match = re.search(r'gt=([0-9]+);', response.text)
                if not gt_match:
                    raise Exception("Guest token not found")
                
                self.guest_token = gt_match.group(1)
            
            self.session.cookies.set('gt', self.guest_token, '.x.com')
            
            self.log_attempt('mobile_guest_token_extract', {
                'guest_token': self.guest_token[:20] + '...',
                'success': True
            }, True)
            
            logging.info(f"    Mobile guest token: {self.guest_token[:20]}...")
            
        except Exception as e:
            self.log_attempt('mobile_guest_token_extract', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def init_mobile_client_transaction(self):
        """تهيئة client transaction للموبايل"""
        logging.info("[2] Initializing mobile client transaction...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'X-Twitter-Poll-ID': str(int(time.time() * 1000)),
            'X-Twitter-Device-ID': self.current_fingerprint['device_id']
        })
        
        try:
            response = await self.session.get('https://x.com', headers=headers)
            
            self.client_transaction_id = self.generate_mobile_transaction_id('POST', '/1.1/onboarding/task.json')
            
            self.log_attempt('mobile_client_transaction_init', {
                'transaction_id': self.client_transaction_id[:30] + '...',
                'status': response.status_code
            }, True)
            
            logging.info(f"    Mobile transaction ID: {self.client_transaction_id[:30]}...")
            
        except Exception as e:
            self.log_attempt('mobile_client_transaction_init', {
                'error': str(e)
            }, False, str(e))
            raise
    
    def create_mobile_castle_token(self):
        """إنشاء castle token للموبايل"""
        # وقت عشوائي للموبايل
        time_offset = random.randint(86400000, 172800000)  # 1-2 أيام
        
        init_time = int(time.time() * 1000) - time_offset
        
        # cuid فريد للموبايل
        cuid_parts = [
            self.current_fingerprint['device_id'],
            self.current_fingerprint['install_id'],
            str(int(time.time() * 1000)),
            self.current_fingerprint['strategy']
        ]
        cuid = ''.join(cuid_parts)
        
        self.session.cookies.set('__cuid', cuid, '.x.com')
        
        try:
            castle = CastleToken(init_time, cuid)
            self.castle_token = castle.create_token()
            castle_method = 'original'
        except Exception as e:
            logging.warning(f"Mobile castle token failed, using fallback - {e}")
            timestamp = int(time.time() * 1000)
            random_val = random.randint(0, 255)
            self.castle_token = f"mobile_castle:{timestamp}:{random_val}:{cuid[:16]}"
            castle_method = 'fallback'
        
        self.log_attempt('mobile_castle_token_create', {
            'method': castle_method,
            'time_offset_hours': -(time_offset / 1000 / 3600),
            'castle_token': self.castle_token[:30] + '...',
            'cuid': cuid[:20] + '...'
        }, True)
        
        logging.info(f"    Mobile castle token ({castle_method}): {self.castle_token[:30]}...")
        logging.info(f"    Time offset: {-(time_offset / 1000 / 3600):.1f} hours")
    
    async def start_mobile_login_flow(self):
        """بدء تدفق تسجيل الدخول للموبايل"""
        logging.info("[3] Starting mobile login flow...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # بيانات خاصة بالموبايل
        flow_data = {
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {"location": "mobile_login"}
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
            'x-twitter-client-language': self.current_fingerprint['language'],
            'x-twitter-client-version': self.current_fingerprint['app_version'],
            'x-twitter-client-platform': self.current_fingerprint['device_type'].upper(),
            'x-client-uuid': self.current_fingerprint['device_id'],
            'x-device-id': self.current_fingerprint['device_id']
        }
        
        try:
            response = await self.session.post(
                'https://api.x.com/1.1/onboarding/task.json',
                params={'flow_name': 'login'},
                json=flow_data,
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('mobile_flow_start', {
                    'status': response.status_code,
                    'response': response.text[:200]
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to start mobile flow: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('mobile_flow_start', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', [])
            }, True)
            
            logging.info(f"    Mobile flow started successfully!")
            logging.info(f"    Flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('mobile_flow_start', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_mobile_username_step(self):
        """تنفيذ خطوة اسم المستخدم للموبايل"""
        logging.info("[4] Entering mobile username...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        self.create_mobile_castle_token()
        
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
            'x-client-transaction-id': self.generate_mobile_transaction_id('POST', '/1.1/onboarding/task.json'),
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'],
            'x-twitter-client-version': self.current_fingerprint['app_version'],
            'x-twitter-client-platform': self.current_fingerprint['device_type'].upper(),
            'x-client-uuid': self.current_fingerprint['device_id'],
            'x-device-id': self.current_fingerprint['device_id'],
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
                    'device_type': self.current_fingerprint['device_type']
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
                                'device_type': self.current_fingerprint['device_type'],
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint
                            })
                except:
                    pass
                
                self.log_attempt('mobile_username_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"Mobile username step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.log_attempt('mobile_username_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'castle_token': self.castle_token[:30] + '...'
            }, True)
            
            logging.info(f"    Mobile username step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('mobile_username_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def execute_mobile_password_step(self):
        """تنفيذ خطوة كلمة المرور للموبايل"""
        logging.info("[5] Entering mobile password...")
        
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        self.create_mobile_castle_token()
        
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
            'x-client-transaction-id': self.generate_mobile_transaction_id('POST', '/1.1/onboarding/task.json'),
            'x-guest-token': self.guest_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': self.current_fingerprint['language'],
            'x-twitter-client-version': self.current_fingerprint['app_version'],
            'x-twitter-client-platform': self.current_fingerprint['device_type'].upper(),
            'x-client-uuid': self.current_fingerprint['device_id'],
            'x-device-id': self.current_fingerprint['device_id'],
            'x-csrf-token': self.session.cookies.get('ct0', ''),
        }
        
        logging.info(f"    Debug - Mobile headers count: {len(headers)}")
        logging.info(f"    Debug - Has CSRF token: {'x-csrf-token' in headers}")
        logging.info(f"    Debug - Castle token: {self.castle_token[:30]}...")
        logging.info(f"    Debug - Device type: {self.current_fingerprint['device_type']}")
        
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
                    'password_length': len(self.password),
                    'device_type': self.current_fingerprint['device_type']
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
                                'device_type': self.current_fingerprint['device_type'],
                                'step': 'mobile_password',
                                'error_code': error_code,
                                'error_message': error_msg,
                                'fingerprint': self.current_fingerprint,
                                'headers_count': len(headers)
                            })
                except:
                    pass
                
                self.log_attempt('mobile_password_step', error_data, False, f"Status {response.status_code}")
                raise Exception(f"Mobile password step failed: {response.status_code} - {response.text}")
            
            resp_data = response.json()
            self.flow_token = resp_data.get('flow_token')
            
            self.success_patterns.append({
                'attempt': self.attempt_count,
                'strategy': self.current_fingerprint['strategy'],
                'device_type': self.current_fingerprint['device_type'],
                'fingerprint': self.current_fingerprint,
                'headers_count': len(headers)
            })
            
            self.log_attempt('mobile_password_step', {
                'status': response.status_code,
                'flow_token': self.flow_token[:30] + '...',
                'subtasks': resp_data.get('subtasks', []),
                'headers_count': len(headers),
                'castle_token': self.castle_token[:30] + '...'
            }, True)
            
            logging.info(f"    Mobile password step completed!")
            logging.info(f"    New flow token: {self.flow_token[:30]}...")
            
            return resp_data
            
        except Exception as e:
            self.log_attempt('mobile_password_step', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def verify_mobile_login_success(self):
        """التحقق من نجاح تسجيل الدخول للموبايل"""
        logging.info("[6] Verifying mobile login success...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        headers = dict(self.session.headers)
        headers.update({
            'x-twitter-poll-id': str(int(time.time() * 1000)),
            'x-twitter-device-id': self.current_fingerprint['device_id']
        })
        
        try:
            response = await self.session.get(
                'https://x.com/home',
                params={'prefetchTimestamp': int(time.time() * 1000)},
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_attempt('mobile_login_verify', {
                    'status': response.status_code,
                    'error': 'Failed to verify mobile login'
                }, False, f"Status {response.status_code}")
                raise Exception(f"Failed to verify mobile login: {response.status_code}")
            
            auth_token = self.session.cookies.get('auth_token', domain='.x.com')
            if not auth_token:
                self.log_attempt('mobile_login_verify', {
                    'error': 'auth_token not found'
                }, False, "auth_token not found")
                raise Exception("auth_token not found - mobile login failed")
            
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
                'device_type': self.current_fingerprint['device_type'],
                'attempt': self.attempt_count
            }
            
            self.log_attempt('mobile_login_verify', {
                'auth_token': auth_token[:20] + '...',
                'ct0': ct0[:20] + '...' if ct0 else 'missing',
                'cookies_count': len(self.session.cookies),
                'strategy': self.current_fingerprint['strategy'],
                'device_type': self.current_fingerprint['device_type']
            }, True)
            
            logging.info(f"    Mobile login successful!")
            logging.info(f"    Auth token: {auth_token[:20]}...")
            logging.info(f"    CSRF token: {ct0[:20]}..." if ct0 else "    CSRF token: Missing")
            logging.info(f"    Device: {self.current_fingerprint['device_type']}")
            logging.info(f"    Strategy: {self.current_fingerprint['strategy']}")
            logging.info(f"    Attempt: {self.attempt_count}")
            
            return cookies_data
            
        except Exception as e:
            self.log_attempt('mobile_login_verify', {
                'error': str(e)
            }, False, str(e))
            raise
    
    async def mobile_login(self):
        """تسجيل الدخول ببصمات موبايل متكررة"""
        logging.info("MOBILE LOGIN - Device/App Fingerprint System")
        logging.info("=" * 70)
        logging.info(f"Username: {self.username}")
        logging.info(f"Max attempts: {self.max_attempts}")
        logging.info("Each attempt uses a different mobile device fingerprint")
        logging.info("=" * 70)
        
        for attempt in range(1, self.max_attempts + 1):
            self.attempt_count = attempt
            
            logging.info(f"\nMOBILE ATTEMPT {attempt}/{self.max_attempts}")
            logging.info("=" * 50)
            
            try:
                await self.init_session()
                await self.extract_guest_token()
                await self.init_mobile_client_transaction()
                
                # بدء التدفق
                flow_result = await self.start_mobile_login_flow()
                
                # تنفيذ الخطوات ببصمات مختلفة
                await self.execute_mobile_username_step()
                await self.execute_mobile_password_step()
                
                # التحقق من النجاح
                cookies = await self.verify_mobile_login_success()
                
                # حفظ الكوكيز والتحليل
                cookies_dir = Path("cookies")
                cookies_dir.mkdir(exist_ok=True)
                
                cookie_file = cookies_dir / f"mobile_{self.username}_{int(time.time())}.json"
                
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
                    "device_type": cookies['device_type'],
                    "attempt": cookies['attempt'],
                    "success_patterns": self.success_patterns,
                    "failure_patterns": self.failure_patterns
                }
                
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, indent=2, ensure_ascii=False)
                
                logging.info(f"\nMOBILE LOGIN COMPLETED SUCCESSFULLY!")
                logging.info(f"Device: {cookies['device_type']}")
                logging.info(f"Strategy: {cookies['strategy']}")
                logging.info(f"Attempt: {cookies['attempt']}")
                logging.info(f"Fingerprint: {cookies['fingerprint']['device_name']} on {cookies['fingerprint']['os_version']}")
                logging.info(f"Cookies and analysis saved to: {cookie_file}")
                
                # حفظ التحليل النهائي
                final_analysis = {
                    'total_attempts': attempt,
                    'successful_attempt': attempt,
                    'success_strategy': cookies['strategy'],
                    'success_device_type': cookies['device_type'],
                    'success_fingerprint': cookies['fingerprint'],
                    'success_patterns': self.success_patterns,
                    'failure_patterns': self.failure_patterns,
                    'all_attempts_data': self.analysis_data
                }
                
                with open(f'mobile_final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                    json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                
                return cookies
                
            except Exception as e:
                logging.error(f"\nMobile attempt {attempt} failed: {e}")
                
                if attempt >= self.max_attempts:
                    logging.error(f"\nAll {self.max_attempts} mobile attempts failed!")
                    logging.error("Mobile analysis complete - check the analysis files for patterns")
                    
                    final_analysis = {
                        'total_attempts': self.max_attempts,
                        'success': False,
                        'failure_patterns': self.failure_patterns,
                        'all_attempts_data': self.analysis_data,
                        'recommendations': self.generate_mobile_recommendations()
                    }
                    
                    with open(f'mobile_final_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                        json.dump(final_analysis, f, ensure_ascii=False, indent=2)
                    
                    raise Exception(f"All {self.max_attempts} mobile attempts failed")
                
                wait_time = random.uniform(5.0, 15.0)
                logging.info(f"Waiting {wait_time:.1f} seconds before next mobile attempt...")
                await asyncio.sleep(wait_time)
    
    def generate_mobile_recommendations(self):
        """توليد توصيات للموبايل"""
        recommendations = []
        
        # تحليل أنواع الأجهزة
        device_success = {}
        for pattern in self.failure_patterns:
            device = pattern.get('device_type', 'unknown')
            if device not in device_success:
                device_success[device] = 0
            device_success[device] += 1
        
        if device_success:
            best_device = min(device_success, key=device_success.get)
            recommendations.append(f"Device '{best_device}' had the fewest failures")
        
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
        
        recommendations.append("Try manual_cookies.py for guaranteed success")
        recommendations.append("Consider using real mobile device for better results")
        recommendations.append("Try different mobile carriers/networks")
        
        return recommendations

async def main():
    """الوظيفة الرئيسية"""
    logging.info("MOBILE LOGIN SYSTEM")
    logging.info("Advanced mobile device/app fingerprinting")
    logging.info("=" * 80)
    
    username = "Ga6rsah"
    password = "Mm8221809@@"
    
    logging.info(f"Target account: {username}")
    logging.info(f"Max attempts: 30")
    logging.info("Press Ctrl+C to stop at any time")
    
    mobile = MobileLogin(username, password)
    
    try:
        cookies = await mobile.mobile_login()
        
        logging.info(f"\nMOBILE SUCCESS AFTER {mobile.attempt_count} ATTEMPTS!")
        logging.info(f"Device: {cookies['device_type']}")
        logging.info(f"Strategy: {cookies['strategy']}")
        logging.info(f"Fingerprint: {cookies['fingerprint']['device_name']} on {cookies['fingerprint']['os_version']}")
        
        logging.info(f"\nMOBILE ANALYSIS SUMMARY:")
        logging.info(f"Total attempts: {mobile.attempt_count}")
        logging.info(f"Success patterns: {len(mobile.success_patterns)}")
        logging.info(f"Failure patterns: {len(mobile.failure_patterns)}")
        logging.info(f"Analysis data points: {len(mobile.analysis_data)}")
        
    except KeyboardInterrupt:
        logging.info("\nStopped by user")
    except Exception as e:
        logging.error(f"\nMobile login failed: {e}")
        logging.error("\nCheck the mobile analysis files for detailed patterns")
        logging.error("Consider using manual_cookies.py for guaranteed success")

if __name__ == "__main__":
    asyncio.run(main())
