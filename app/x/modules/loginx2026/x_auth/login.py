"""
تسجيل الدخول في X — مشروع مستقل
يدعم حساب واحد أو عدة حسابات مع حفظ الكوكيز كاملة

المتطلبات:
    pip install curl_cffi stpyv8 beautifulsoup4 lxml chompjs mmh3
"""
import json
import re
import os
import time
import random
import uuid
import asyncio
from pathlib import Path
from urllib.parse import urlparse

import curl_cffi
from curl_cffi import Response

from .castle import CastleToken
from .transaction import ClientTransaction
from .ui_metrics import solve_ui_metrics


# ============ Constants ============
AUTHORIZATION = 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
COOKIES_DOMAIN = '.x.com'

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6,ay;q=0.5,ga;q=0.4",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}

START_FLOW_PAYLOAD = {
    "input_flow_data": {
        "flow_context": {
            "debug_overrides": {},
            "start_location": {"location": "unknown"},
        }
    },
    "subtask_versions": {
        "action_list": 2, "alert_dialog": 1, "app_download_cta": 1,
        "check_logged_in_account": 1, "choice_selection": 3,
        "contacts_live_sync_permission_prompt": 0, "cta": 7,
        "email_verification": 2, "end_flow": 1, "enter_date": 1,
        "enter_email": 2, "enter_password": 5, "enter_phone": 2,
        "enter_recaptcha": 1, "enter_text": 5, "enter_username": 2,
        "generic_urt": 3, "in_app_notification": 1, "interest_picker": 3,
        "js_instrumentation": 1, "menu_dialog": 1,
        "notifications_permission_prompt": 2, "open_account": 2,
        "open_home_timeline": 1, "open_link": 1, "phone_verification": 4,
        "privacy_options": 1, "security_key": 3, "select_avatar": 4,
        "select_banner": 2, "settings_list": 7, "show_code": 1,
        "sign_up": 2, "sign_up_review": 4, "tweet_selection_urt": 1,
        "update_users": 1, "upload_media": 1, "user_recommendations_list": 4,
        "user_recommendations_urt": 1, "wait_spinner": 3, "web_modal": 1,
    },
}


# ============ HTTP Client ============
class HTTPClient(curl_cffi.AsyncSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_transaction = None

    async def request(self, method, url, *args, use_transaction_id=True, **kwargs):
        if use_transaction_id and self.client_transaction:
            transaction_id = self.client_transaction.generate_transaction_id(method, urlparse(url).path)
            headers = kwargs.get('headers') or {}
            headers['x-client-transaction-id'] = transaction_id
            kwargs['headers'] = headers

        response = await super().request(method, url, *args, **kwargs)
        if 400 <= response.status_code < 600:
            msg = ''
            try:
                msg = response.text[:2000]
            except:
                pass
            raise Exception(f'HTTP {response.status_code}: {msg}')
        return response

    def build_headers(self, authorization=True, csrf_token=True, extra_headers=None, json_content=False):
        headers = DEFAULT_HEADERS.copy()
        if authorization:
            headers['authorization'] = AUTHORIZATION
        if csrf_token:
            ct0 = self.cookies.get('ct0', domain=COOKIES_DOMAIN)
            if ct0:
                headers['x-csrf-token'] = ct0
        if extra_headers:
            headers.update(extra_headers)
        if json_content:
            headers['content-type'] = 'application/json'
        return headers

    @property
    def csrf_token(self):
        return self.cookies.get('ct0', domain=COOKIES_DOMAIN)

    @property
    def guest_token(self):
        return self.cookies.get('gt', domain=COOKIES_DOMAIN)


def parse_json(response):
    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f'Invalid JSON. Status: {response.status_code}, Body: {response.text[:200]}') from e


# ============ Login Flow ============
class LoginFlow:
    def __init__(self, http, castle):
        self.http = http
        self.flow_token = None
        self.subtasks = []
        self.subtask_inputs = {}
        self.castle = castle

    def _get_subtask(self, subtask_id):
        return next(filter(lambda x: x.get('subtask_id') == subtask_id, self.subtasks), None)

    def _process_response(self, response):
        data = parse_json(response)
        self.flow_token = data.get('flow_token')
        self.subtasks = data.get('subtasks', [])
        if self.flow_token is None:
            raise ValueError('flow_token not found')

    async def _api_call(self, data, params=None):
        headers = self.http.build_headers(json_content=True, extra_headers={
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
            'x-guest-token': self.http.guest_token or ''
        })
        return await self.http.post(
            'https://api.x.com/1.1/onboarding/task.json',
            params=params, json=data, headers=headers
        )

    async def start_flow(self):
        response = await self._api_call(START_FLOW_PAYLOAD, {'flow_name': 'login'})
        self._process_response(response)

    async def execute_subtasks(self):
        subtask_inputs = [
            {'subtask_id': sid, **data}
            for sid, data in self.subtask_inputs.items()
        ]
        data = {'flow_token': self.flow_token, 'subtask_inputs': subtask_inputs}
        response = await self._api_call(data)
        self._process_response(response)
        self.subtask_inputs.clear()

    async def js_instrumentation(self):
        subtask = self._get_subtask('LoginJsInstrumentationSubtask')
        js_url = subtask['js_instrumentation']['url']
        headers = self.http.build_headers(authorization=False)
        js_response = await self.http.get(js_url, headers=headers, use_transaction_id=False)
        answer = solve_ui_metrics(js_response.text)
        self.subtask_inputs['LoginJsInstrumentationSubtask'] = {
            'js_instrumentation': {'response': answer, 'link': 'next_link'}
        }

    async def sso_init(self):
        headers = self.http.build_headers(json_content=True, extra_headers={
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
            'x-guest-token': self.http.guest_token or ''
        })
        await self.http.post(
            'https://api.x.com/1.1/onboarding/sso_init.json',
            json={'provider': 'apple'}, headers=headers
        )

    def enter_username(self, username):
        self.subtask_inputs['LoginEnterUserIdentifierSSO'] = {
            'settings_list': {
                'setting_responses': [{
                    'key': 'user_identifier',
                    'response_data': {'text_data': {'result': username}}
                }],
                'link': 'next_link',
                'castle_token': self.castle.create_token()
            }
        }

    def enter_alternate_identifier(self, identifier):
        self.subtask_inputs['LoginEnterAlternateIdentifierSubtask'] = {
            'enter_text': {
                'link': 'next_link',
                'text': identifier,
                'castle_token': self.castle.create_token()
            }
        }

    def enter_password(self, password):
        self.subtask_inputs['LoginEnterPassword'] = {
            'enter_password': {
                'password': password,
                'link': 'next_link',
                'castle_token': self.castle.create_token()
            }
        }

    def enter_2fa(self, code):
        self.subtask_inputs['LoginTwoFactorAuthChallenge'] = {
            'enter_text': {
                'text': code,
                'link': 'next_link',
                'castle_token': self.castle.create_token()
            }
        }

    def enter_confirmation(self, code):
        self.subtask_inputs['LoginAcid'] = {
            'enter_text': {
                'link': 'next_link',
                'text': code,
                'castle_token': self.castle.create_token()
            }
        }


# ============ Complete Login Flow ============
async def _complete_login(flow, user_identifiers, password):
    while True:
        subtask_ids = {i.get('subtask_id') for i in flow.subtasks}

        if 'LoginJsInstrumentationSubtask' in subtask_ids:
            await flow.js_instrumentation()
            await flow.sso_init()

        elif 'LoginEnterUserIdentifierSSO' in subtask_ids:
            flow.enter_username(user_identifiers[0])

        elif 'LoginEnterAlternateIdentifierSubtask' in subtask_ids:
            if len(user_identifiers) < 2:
                raise ValueError('تويتر يطلب معرف بديل (إيميل). أضف الإيميل كمعرف ثاني.')
            flow.enter_alternate_identifier(user_identifiers[1])

        elif 'LoginEnterPassword' in subtask_ids:
            flow.enter_password(password)

        elif 'LoginTwoFactorAuthChallenge' in subtask_ids:
            code = input('[?] أدخل رمز المصادقة الثنائية (2FA): ').strip()
            flow.enter_2fa(code)

        elif 'LoginAcid' in subtask_ids:
            code = input('[?] أدخل رمز التأكيد من الإيميل: ').strip()
            flow.enter_confirmation(code)

        elif 'LoginSuccessSubtask' in subtask_ids:
            print('[+] تم تسجيل الدخول بنجاح!')
            break

        elif 'DenyLoginSubtask' in subtask_ids:
            raise Exception(f'تم رفض تسجيل الدخول: {flow.subtasks}')

        else:
            raise ValueError(f'خطوة غير معروفة: {subtask_ids}')

        await flow.execute_subtasks()


# ============ Main Login Function ============
async def x_login(username, password, email=None, cookies_dir="cookies"):
    """
    تسجيل دخول حساب واحد

    Args:
        username: اسم المستخدم
        password: كلمة المرور
        email: الإيميل (اختياري — يُستخدم إذا طلب تويتر تحقق)
        cookies_dir: مجلد حفظ الكوكيز

    Returns:
        dict: الكوكيز الكاملة
    """
    cookies_dir = os.path.abspath(cookies_dir)
    os.makedirs(cookies_dir, exist_ok=True)
    cookie_file = os.path.join(cookies_dir, f"{username}.json")

    # إذا الكوكيز موجودة، حاول استخدامها
    if os.path.exists(cookie_file):
        print(f'[*] كوكيز موجودة لـ {username}، جاري التحقق...')
        try:
            return await x_login_with_cookies(cookie_file)
        except Exception:
            print(f'[!] الكوكيز منتهية، جاري تسجيل دخول جديد...')

    http = HTTPClient(impersonate='chrome142')

    # 1. جلب guest_token من صفحة تسجيل الدخول
    print(f'[1] جلب guest_token...')
    response = await http.get(
        'https://x.com/i/flow/login',
        headers=http.build_headers(authorization=False)
    )
    guest_token_match = re.search(r'gt=([0-9]+);', response.text)
    if not guest_token_match:
        raise ValueError('لم يتم العثور على guest_token')
    http.cookies.set('gt', guest_token_match.group(1), COOKIES_DOMAIN)
    print(f'    guest_token: {guest_token_match.group(1)[:20]}...')

    # 2. تهيئة ClientTransaction
    print(f'[2] تهيئة ClientTransaction...')
    client_transaction = ClientTransaction()
    await client_transaction.init(http, http.build_headers(authorization=False))
    http.client_transaction = client_transaction

    # 3. تهيئة CastleToken
    init_time = int(time.time() * 1000) - random.randint(10000, 20000)
    cuid = uuid.uuid4().hex
    http.cookies.set('__cuid', cuid, COOKIES_DOMAIN)
    castle = CastleToken(init_time, cuid)

    # 4. بدء تسجيل الدخول
    print(f'[3] بدء login flow...')
    flow = LoginFlow(http, castle)
    await flow.start_flow()

    user_identifiers = [username]
    if email:
        user_identifiers.append(email)

    await _complete_login(flow, user_identifiers, password)

    # 5. التأكد من وجود auth_token
    auth_token = http.cookies.get('auth_token', domain=COOKIES_DOMAIN)
    if not auth_token:
        raise Exception('لم يتم العثور على auth_token بعد تسجيل الدخول')

    # جلب ct0 إذا لم يكن موجوداً
    if not http.csrf_token:
        await http.get(
            'https://x.com/home',
            params={'prefetchTimestamp': int(time.time() * 1000)},
            headers=http.build_headers(authorization=False)
        )

    # 6. حفظ الكوكيز بصيغة Playwright
    playwright_cookies = _to_playwright_format(http.cookies, COOKIES_DOMAIN)
    with open(cookie_file, 'w', encoding='utf-8') as f:
        json.dump({"cookies": playwright_cookies, "origins": []}, f, ensure_ascii=False, indent=2)
    print(f'[+] تم حفظ الكوكيز في: {cookie_file}')

    # حفظ في coo.txt
    cookies_dict = {c['name']: c['value'] for c in playwright_cookies}
    ct0 = cookies_dict.get('ct0', '')
    at = cookies_dict.get('auth_token', '')
    if ct0 and at:
        _save_to_coo(ct0, at, username, cookies_dir)

    await http.close()
    return cookies_dict


async def x_login_with_cookies(cookie_file):
    """تسجيل دخول بكوكيز محفوظة (صيغة Playwright)"""
    with open(cookie_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # دعم الصيغتين: Playwright {cookies: [...]} أو dict قديم {key: value}
    if isinstance(data, dict) and 'cookies' in data:
        cookie_list = data['cookies']
        cookies_dict = {c['name']: c['value'] for c in cookie_list}
    else:
        cookies_dict = data

    http = HTTPClient(impersonate='chrome142')
    for k, v in cookies_dict.items():
        http.cookies.set(k, str(v), COOKIES_DOMAIN)

    if not http.cookies.get('auth_token', domain=COOKIES_DOMAIN):
        raise KeyError('auth_token غير موجود في الكوكيز')

    if not http.csrf_token:
        await http.get(
            'https://x.com/home',
            params={'prefetchTimestamp': int(time.time() * 1000)},
            headers=http.build_headers(authorization=False)
        )
        if not http.csrf_token:
            raise KeyError('فشل الحصول على ct0 — الكوكيز منتهية')

    print(f'[+] تم تسجيل الدخول بالكوكيز المحفوظة')
    await http.close()
    return cookies_dict


async def x_login_multi(accounts, cookies_dir="cookies"):
    """
    تسجيل دخول عدة حسابات

    Args:
        accounts: قائمة من dict كل واحد فيه:
            {"username": "...", "password": "...", "email": "..."}
        cookies_dir: مجلد حفظ الكوكيز

    Returns:
        dict: {username: cookies_dict}
    """
    results = {}
    for i, account in enumerate(accounts):
        username = account['username']
        password = account['password']
        email = account.get('email')

        print(f'\n{"="*50}')
        print(f'  [{i+1}/{len(accounts)}] تسجيل دخول: {username}')
        print(f'{"="*50}')

        try:
            cookies = await x_login(username, password, email, cookies_dir)
            results[username] = {"success": True, "cookies": cookies}
            print(f'[✓] {username} — نجح')
        except Exception as e:
            results[username] = {"success": False, "error": str(e)}
            print(f'[✗] {username} — فشل: {e}')

        # تأخير بين الحسابات
        if i < len(accounts) - 1:
            delay = random.uniform(5, 15)
            print(f'[*] انتظار {delay:.1f} ثانية...')
            await asyncio.sleep(delay)

    # ملخص
    print(f'\n{"="*50}')
    print(f'  النتائج:')
    success = sum(1 for v in results.values() if v['success'])
    print(f'  نجح: {success}/{len(accounts)}')
    for username, result in results.items():
        status = '✓' if result['success'] else '✗'
        print(f'  {status} {username}')
    print(f'{"="*50}')

    return results


def _to_playwright_format(cookie_jar, domain):
    """تحويل الكوكيز من curl_cffi إلى صيغة Playwright"""
    playwright_cookies = []
    # الكوكيز اللي نعرف أنها httpOnly
    HTTP_ONLY = {'auth_token', 'kdt', '_twitter_sess', '__cf_bm'}
    # الكوكيز اللي sameSite = Lax
    LAX_COOKIES = {'ct0'}

    for cookie in cookie_jar.jar:
        expires = cookie.expires if cookie.expires else time.time() + 365 * 24 * 3600
        name = cookie.name
        playwright_cookies.append({
            "name": name,
            "value": cookie.value,
            "domain": cookie.domain or domain,
            "path": cookie.path or "/",
            "expires": float(expires),
            "httpOnly": name in HTTP_ONLY,
            "secure": True,
            "sameSite": "Lax" if name in LAX_COOKIES else "None"
        })
    return playwright_cookies


def _save_to_coo(ct0, auth_token, username, cookies_dir="cookies"):
    """حفظ الكوكيز في coo.txt بجانب مجلد الكوكيز"""
    coo_path = os.path.join(os.path.dirname(os.path.abspath(cookies_dir)), "coo.txt")
    line = f"{ct0},{auth_token}"
    existing = ""
    if os.path.exists(coo_path):
        existing = open(coo_path, 'r', encoding='utf-8').read()
    if line not in existing:
        with open(coo_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{line}")
        print(f'[+] تم إضافة الكوكيز إلى coo.txt ({username})')
    else:
        print(f'[*] الكوكيز موجودة مسبقاً في coo.txt')
