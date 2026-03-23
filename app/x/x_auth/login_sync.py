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
    print(f"[*] cookies_dir: {cookies_dir}")

    try:
        cookies = asyncio.run(_do_login(username, password, cookies_dir))
        result = {
            "success": True,
            "username": username,
            "auth_token": cookies.get("auth_token", ""),
            "ct0": cookies.get("ct0", ""),
            "cookies": cookies,
        }
    except Exception as e:
        result = {"success": False, "username": username, "error": str(e)}

    print("__RESULT__" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
