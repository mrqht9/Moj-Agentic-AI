#!/usr/bin/env python3
"""
Deep Analysis - تحليل عميق لطلبات تويتر المطلوبة
"""
import asyncio
import json
import time
import random
import uuid
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# إضافة مجلد x_auth للـ path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import curl_cffi
from curl_cffi import AsyncSession, BrowserType

class DeepAnalyzer:
    def __init__(self):
        self.session = None
        self.captured_requests = []
        
    async def init_session(self, browser_type='chrome142'):
        """تهيئة جلسة curl_cffi"""
        self.session = AsyncSession(
            impersonate=browser_type,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
            }
        )
        
    async def capture_request(self, method, url, **kwargs):
        """تسجيل تفاصيل الطلب"""
        request_data = {
            'timestamp': time.time(),
            'method': method,
            'url': url,
            'headers': dict(kwargs.get('headers', {})),
            'cookies': dict(self.session.cookies),
            'body': kwargs.get('json', kwargs.get('data', ''))
        }
        self.captured_requests.append(request_data)
        
        print(f"\n🔍 CAPTURED REQUEST:")
        print(f"  Method: {method}")
        print(f"  URL: {url}")
        print(f"  Headers: {len(request_data['headers'])} headers")
        print(f"  Cookies: {len(request_data['cookies'])} cookies")
        if request_data['body']:
            print(f"  Body: {str(request_data['body'])[:100]}...")
            
        return await self.session.request(method, url, **kwargs)
    
    async def analyze_real_browser_flow(self):
        """تحليل تدفق المتصفح الحقيقي"""
        print("🌐 REAL BROWSER FLOW ANALYSIS")
        print("=" * 60)
        
        # 1. زيارة الصفحة الرئيسية
        print("\n[1] Visiting x.com homepage...")
        try:
            response = await self.capture_request(
                'GET', 
                'https://x.com',
                allow_redirects=True
            )
            print(f"  Status: {response.status_code}")
            print(f"  Final URL: {response.url}")
            
            # استخراج معلومات من الصفحة
            if 'gt=' in response.text:
                import re
                gt_match = re.search(r'gt=([0-9]+);', response.text)
                if gt_match:
                    guest_token = gt_match.group(1)
                    print(f"  Guest Token Found: {guest_token[:20]}...")
                    self.session.cookies.set('gt', guest_token, '.x.com')
                    
        except Exception as e:
            print(f"  Error: {e}")
            
        # 2. زيارة صفحة تسجيل الدخول
        print("\n[2] Visiting login page...")
        try:
            response = await self.capture_request(
                'GET',
                'https://x.com/i/flow/login',
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
            print(f"  Status: {response.status_code}")
            
            # تحليل JavaScript في الصفحة
            js_files = []
            import re
            js_matches = re.findall(r'src="([^"]*\.js[^"]*)"', response.text)
            for js_url in js_matches:
                if 'x.com' in js_url or 'twitter.com' in js_url:
                    js_files.append(js_url)
            print(f"  JS files found: {len(js_files)}")
            
        except Exception as e:
            print(f"  Error: {e}")
            
        # 3. بدء تدفق تسجيل الدخول
        print("\n[3] Starting login flow...")
        try:
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
            
            response = await self.capture_request(
                'POST',
                'https://api.x.com/1.1/onboarding/task.json',
                params={'flow_name': 'login'},
                json=flow_data,
                headers={
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                    'content-type': 'application/json',
                    'origin': 'https://x.com',
                    'referer': 'https://x.com/',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'x-guest-token': self.session.cookies.get('gt', ''),
                    'x-twitter-active-user': 'yes',
                    'x-twitter-client-language': 'en'
                }
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                print(f"  Flow started successfully!")
                print(f"  Flow Token: {resp_data.get('flow_token', 'N/A')[:30]}...")
                subtasks = resp_data.get('subtasks', [])
                print(f"  Subtasks: {[st.get('subtask_id', '?') for st in subtasks]}")
                
                return resp_data
            else:
                print(f"  Error: {response.status_code}")
                print(f"  Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  Error: {e}")
            
        return None
    
    def analyze_missing_elements(self):
        """تحليل العناصر المفقودة"""
        print("\n🔍 MISSING ELEMENTS ANALYSIS")
        print("=" * 60)
        
        missing_elements = {
            'headers': [],
            'cookies': [],
            'body_fields': [],
            'timing': []
        }
        
        # تحليل الهيدرز المطلوبة
        required_headers = [
            'authorization', 'x-csrf-token', 'x-client-transaction-id',
            'x-guest-token', 'x-twitter-active-user', 'x-twitter-client-language',
            'sec-ch-ua', 'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
            'origin', 'referer', 'user-agent'
        ]
        
        for request in self.captured_requests:
            headers = request['headers']
            for header in required_headers:
                if header not in headers and header not in missing_elements['headers']:
                    missing_elements['headers'].append(header)
        
        # تحليل الكوكيز المطلوبة
        required_cookies = ['gt', 'ct0', 'auth_token', '__cuid']
        
        for request in self.captured_requests:
            cookies = request['cookies']
            for cookie in required_cookies:
                if cookie not in cookies and cookie not in missing_elements['cookies']:
                    missing_elements['cookies'].append(cookie)
        
        print("\n📊 Analysis Results:")
        print(f"  Total requests captured: {len(self.captured_requests)}")
        print(f"  Missing headers: {missing_elements['headers']}")
        print(f"  Missing cookies: {missing_elements['cookies']}")
        
        return missing_elements
    
    def generate_perfect_request_template(self):
        """إنشاء قالب طلب مثالي"""
        print("\n🎯 PERFECT REQUEST TEMPLATE")
        print("=" * 60)
        
        template = {
            'method': 'POST',
            'url': 'https://api.x.com/1.1/onboarding/task.json',
            'params': {'flow_name': 'login'},
            'headers': {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4',
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'content-type': 'application/json',
                'origin': 'https://x.com',
                'referer': 'https://x.com/i/flow/login',
                'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'x-client-transaction-id': 'NEEDS_DYNAMIC_GENERATION',
                'x-csrf-token': 'NEEDS_FROM_COOKIES',
                'x-guest-token': 'NEEDS_FROM_LOGIN_PAGE',
                'x-twitter-active-user': 'yes',
                'x-twitter-client-language': 'en'
            },
            'cookies': {
                'gt': 'FROM_LOGIN_PAGE',
                'ct0': 'FROM_PREVIOUS_REQUEST',
                '__cuid': 'GENERATED_UUID',
                'guest_token_marketing': 'OPTIONAL',
                'lang': 'en'
            },
            'body': {
                'flow_token': 'FROM_PREVIOUS_RESPONSE',
                'subtask_inputs': [
                    {
                        'subtask_id': 'LoginEnterUserIdentifierSSO',
                        'settings_list': {
                            'setting_responses': [{
                                'key': 'user_identifier',
                                'response_data': {'text_data': {'result': 'USERNAME'}}
                            }],
                            'link': 'next_link',
                            'castle_token': 'COMPLEX_ENCRYPTED_TOKEN'
                        }
                    }
                ]
            }
        }
        
        print("\n📝 Perfect Request Template:")
        print(json.dumps(template, indent=2, ensure_ascii=False))
        
        return template
    
    async def run_full_analysis(self):
        """تشغيل التحليل الكامل"""
        print("🔬 DEEP TWITTER LOGIN ANALYSIS")
        print("=" * 60)
        
        await self.init_session()
        
        # تحليل تدفق المتصفح
        flow_result = await self.analyze_real_browser_flow()
        
        # تحليل العناصر المفقودة
        missing = self.analyze_missing_elements()
        
        # إنشاء قالب مثالي
        template = self.generate_perfect_request_template()
        
        # حفظ النتائج
        results = {
            'timestamp': time.time(),
            'captured_requests': self.captured_requests,
            'missing_elements': missing,
            'perfect_template': template,
            'flow_result': flow_result
        }
        
        results_file = Path(f"deep_analysis_results_{int(time.time())}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        return results

async def main():
    """الوظيفة الرئيسية"""
    analyzer = DeepAnalyzer()
    
    print("🔬 DEEP TWITTER LOGIN ANALYSIS")
    print("This tool will analyze what Twitter REALLY expects from requests")
    print("and identify missing elements that cause login failures.")
    
    input("\nPress Enter to start analysis...")
    
    try:
        results = await analyzer.run_full_analysis()
        
        print("\n🎯 KEY FINDINGS:")
        print("1. Check the 'missing_elements' section")
        print("2. Compare your current requests with 'perfect_template'")
        print("3. Look at captured_requests to see real browser behavior")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        print("This might be due to network issues or Twitter blocking")

if __name__ == "__main__":
    asyncio.run(main())
