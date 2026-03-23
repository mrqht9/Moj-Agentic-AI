"""
نسخة متزامنة (sync) من تسجيل الدخول — تُستدعى كـ subprocess
الاستخدام: python -m x_auth.login_sync username password [cookies_dir]
يطبع JSON على stdout
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import asyncio
import requests as _requests


def _get_ip():
    try:
        return _requests.get('https://api.ipify.org', timeout=5).text.strip()
    except Exception:
        return '?'


async def _do_login(username, password, cookies_dir):
    from x_auth.login import x_login
    return await x_login(username, password, cookies_dir=cookies_dir)


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Usage: python -m x_auth.login_sync username password [cookies_dir]"}))
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    cookies_dir = sys.argv[3] if len(sys.argv) > 3 else "cookies"
    cookies_dir = os.path.abspath(cookies_dir)

    ip = _get_ip()
    print(f"[*] IP: {ip}")
    print(f"[*] cookies_dir: {cookies_dir}")

    cookie_file = os.path.join(cookies_dir, f"{username}.json")

    try:
        cookies = asyncio.run(_do_login(username, password, cookies_dir))
        result = {
            "success": True,
            "username": username,
            "ip": ip,
            "auth_token": cookies.get("auth_token", ""),
            "ct0": cookies.get("ct0", ""),
            "cookies": cookies,
        }
    except Exception as e:
        # إذا حصل خطأ لكن الكوكيز محفوظة = تسجيل الدخول نجح فعلياً
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'cookies' in data:
                    cookies = {c['name']: c['value'] for c in data['cookies']}
                else:
                    cookies = data
                if cookies.get("auth_token"):
                    result = {
                        "success": True,
                        "username": username,
                        "ip": ip,
                        "auth_token": cookies.get("auth_token", ""),
                        "ct0": cookies.get("ct0", ""),
                        "cookies": cookies,
                    }
                else:
                    result = {"success": False, "username": username, "ip": ip, "error": str(e)}
            except Exception:
                result = {"success": False, "username": username, "ip": ip, "error": str(e)}
        else:
            result = {"success": False, "username": username, "ip": ip, "error": str(e)}

    print("__RESULT__" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
