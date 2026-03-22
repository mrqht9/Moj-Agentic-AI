"""
استخراج كوكيز X من المتصفح — بديل لتسجيل الدخول

الطريقة:
  1. افتح x.com في المتصفح (وأنت مسجل دخول)
  2. اضغط F12 → Application → Cookies → https://x.com
  3. انسخ قيمة auth_token و ct0
  4. شغّل هذا السكربت والصقهم

الاستخدام:
    python extract_cookies.py
    python extract_cookies.py --dir cookies
"""
import sys
import os
import json
import asyncio
import time

# add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from x_auth.login import HTTPClient, COOKIES_DOMAIN, _to_playwright_format, _save_to_coo


async def main():
    cookies_dir = "cookies"
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--dir' and i + 2 < len(sys.argv):
            cookies_dir = sys.argv[i + 2]

    print('=' * 50)
    print('  استخراج كوكيز X من المتصفح')
    print('=' * 50)
    print()
    print('الخطوات:')
    print('  1. افتح x.com في المتصفح (وأنت مسجل دخول)')
    print('  2. اضغط F12 → Application → Cookies → https://x.com')
    print('  3. انسخ قيمة auth_token و ct0')
    print()

    auth_token = input('auth_token: ').strip()
    if not auth_token:
        print('[✗] auth_token مطلوب!')
        sys.exit(1)

    ct0 = input('ct0: ').strip()
    if not ct0:
        print('[✗] ct0 مطلوب!')
        sys.exit(1)

    print()
    print('[*] التحقق من صلاحية الكوكيز...')

    # التحقق
    http = HTTPClient(impersonate='chrome142')
    http.cookies.set('auth_token', auth_token, COOKIES_DOMAIN)
    http.cookies.set('ct0', ct0, COOKIES_DOMAIN)

    try:
        resp = await http.get(
            'https://x.com/home',
            params={'prefetchTimestamp': int(time.time() * 1000)},
            headers=http.build_headers(authorization=False),
            use_transaction_id=False
        )
        # check if we got redirected to login page
        if '/login' in str(resp.url) or not http.csrf_token:
            print('[✗] الكوكيز منتهية أو غير صالحة!')
            await http.close()
            sys.exit(1)
    except Exception as e:
        print(f'[✗] خطأ في التحقق: {e}')
        await http.close()
        sys.exit(1)

    print('[+] الكوكيز صالحة!')

    # حفظ
    os.makedirs(cookies_dir, exist_ok=True)
    cookies_dict = {'auth_token': auth_token, 'ct0': ct0}

    # حفظ بصيغة Playwright
    cookie_file = os.path.join(cookies_dir, 'browser_import.json')
    playwright_cookies = _to_playwright_format(http.cookies, COOKIES_DOMAIN)
    with open(cookie_file, 'w', encoding='utf-8') as f:
        json.dump({"cookies": playwright_cookies, "origins": []}, f, ensure_ascii=False, indent=2)
    print(f'[+] تم حفظ الكوكيز في: {cookie_file}')

    # حفظ في coo.txt
    _save_to_coo(ct0, auth_token, 'browser_import', cookies_dir)

    await http.close()
    print(f'[+] تم بنجاح!')


if __name__ == '__main__':
    asyncio.run(main())
