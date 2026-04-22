#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
X Bridge — جسر التواصل مع سيرفر app/x عبر API
يشغّل سيرفر app/x بالخلفية ويوفر دوال لإرسال الطلبات له
"""

import os
import sys
import time
import atexit
import signal
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional


# ─── إعدادات ───────────────────────────────────────────────
XSUITE_PORT = int(os.getenv("XSUITE_PORT", "5789"))
XSUITE_BASE_URL = f"http://127.0.0.1:{XSUITE_PORT}"
XSUITE_TOKEN = os.getenv("XSUITE_API_TOKENS", "your-secure-token-here")
XSUITE_DIR = Path(__file__).resolve().parent.parent / "x"   # app/x

_HEADERS = {
    "Authorization": f"Bearer {XSUITE_TOKEN}",
    "Content-Type": "application/json",
}

_process: Optional[subprocess.Popen] = None
API_TIMEOUT = 600  # 10 دقائق — الـ Playwright يحتاج وقت


# ─── إدارة السيرفر ─────────────────────────────────────────
def _is_running() -> bool:
    """تحقق إذا سيرفر app/x شغال فعلاً"""
    try:
        r = requests.get(f"{XSUITE_BASE_URL}/api/stats", headers=_HEADERS, timeout=5)
        return r.status_code in (200, 401, 403)
    except Exception:
        return False


def start_xsuite_server() -> bool:
    """تشغيل سيرفر app/x بالخلفية (دائماً يحاول يشغّل إذا ما في process محلي)"""
    global _process

    # إذا عندنا process محلي شغال، تحقق أنه فعلاً يستجيب
    if _process and _process.poll() is None and _is_running():
        print(f"[X-Bridge] سيرفر app/x شغال بالفعل على بورت {XSUITE_PORT}")
        return True

    # أوقف أي process قديم
    if _process and _process.poll() is None:
        try:
            _process.terminate()
            _process.wait(timeout=5)
        except Exception:
            _process.kill()
        _process = None

    print(f"[X-Bridge] تشغيل سيرفر app/x على بورت {XSUITE_PORT} ...")

    python_exe = sys.executable
    app_py = str(XSUITE_DIR / "app.py")

    env = os.environ.copy()
    env["PORT"] = str(XSUITE_PORT)

    try:
        _process = subprocess.Popen(
            [python_exe, app_py],
            cwd=str(XSUITE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        atexit.register(stop_xsuite_server)

        # انتظر حتى يبدأ السيرفر
        for _ in range(30):
            time.sleep(1)
            if _is_running():
                print(f"[X-Bridge] ✅ سيرفر app/x جاهز على بورت {XSUITE_PORT}")
                return True
            if _process.poll() is not None:
                out = _process.stdout.read().decode(errors="ignore")[:500]
                print(f"[X-Bridge] ❌ سيرفر app/x توقف مبكراً:\n{out}")
                return False

        print("[X-Bridge] ❌ تجاوز وقت انتظار تشغيل سيرفر app/x")
        return False

    except Exception as e:
        print(f"[X-Bridge] ❌ فشل تشغيل سيرفر app/x: {e}")
        return False


def stop_xsuite_server():
    """إيقاف سيرفر app/x"""
    global _process
    if _process and _process.poll() is None:
        print("[X-Bridge] إيقاف سيرفر app/x ...")
        try:
            if sys.platform == "win32":
                _process.terminate()
            else:
                _process.send_signal(signal.SIGTERM)
            _process.wait(timeout=10)
        except Exception:
            _process.kill()
        _process = None


# ─── دوال API ──────────────────────────────────────────────
def _api_call(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """استدعاء API عام مع معالجة الأخطاء"""
    url = f"{XSUITE_BASE_URL}{endpoint}"
    kwargs.setdefault("timeout", API_TIMEOUT)
    kwargs.setdefault("headers", _HEADERS)

    try:
        resp = requests.request(method, url, **kwargs)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.status_code >= 400:
            error = data.get("error", data.get("raw", f"HTTP {resp.status_code}"))
            return {"success": False, "message": str(error), "status_code": resp.status_code}

        # أضف success إذا ما كان موجود
        if "success" not in data:
            data["success"] = True
        return data

    except requests.ConnectionError as e:
        print(f"[X-Bridge] ConnectionError: {e}", flush=True)
        return {"success": False, "message": f"سيرفر app/x غير متاح ({XSUITE_BASE_URL}). تأكد أنه شغال."}
    except requests.Timeout:
        return {"success": False, "message": "انتهت مهلة انتظار الرد من سيرفر app/x"}
    except Exception as e:
        print(f"[X-Bridge] API error: {e}", flush=True)
        return {"success": False, "message": f"خطأ في الاتصال: {str(e)}"}


# ── تسجيل دخول ──
def login(label: str, username: str, password: str, headless: bool = True) -> Dict[str, Any]:
    """تسجيل دخول عبر API"""
    return _api_call("POST", "/api/login", json={
        "label": label,
        "username": username,
        "password": password,
        "headless": headless,
    })


# ── نشر تغريدة ──
def post_tweet(cookie_label: str, text: str, media_url: str = "", headless: bool = True) -> Dict[str, Any]:
    """نشر تغريدة عبر API"""
    payload = {
        "cookie_label": cookie_label,
        "text": text,
        "headless": headless,
    }
    if media_url:
        payload["media_url"] = media_url
    return _api_call("POST", "/api/post", json=payload)


# ── حذف تغريدة ──
def delete_tweet(cookie_label: str, tweet_id: str, headless: bool = True) -> Dict[str, Any]:
    """حذف تغريدة عبر API"""
    payload = {
        "cookie_label": cookie_label,
        "tweet_id": tweet_id,
        "headless": headless,
    }
    return _api_call("POST", "/api/delete-tweet", json=payload)


# ── تحديث الملف الشخصي ──
def update_profile(cookie_label: str, name: str = "", bio: str = "",
                   location: str = "", website: str = "",
                   avatar_url: str = "", banner_url: str = "",
                   headless: bool = True) -> Dict[str, Any]:
    """تحديث الملف الشخصي عبر API (multipart form)"""
    data = {"cookie_label": cookie_label, "headless": "1" if headless else "0"}
    if name:     data["name"] = name
    if bio:      data["bio"] = bio
    if location: data["location"] = location
    if website:  data["website"] = website
    if avatar_url: data["avatar_url"] = avatar_url
    if banner_url: data["banner_url"] = banner_url

    return _api_call("POST", "/api/profile/update",
                     headers={"Authorization": f"Bearer {XSUITE_TOKEN}"},
                     data=data)


# ── لايك ──
def like(cookie_label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/like", json={
        "cookie_label": cookie_label, "tweet_url": tweet_url, "headless": headless,
    })


# ── ريبوست ──
def repost(cookie_label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/repost", json={
        "cookie_label": cookie_label, "tweet_url": tweet_url, "headless": headless,
    })


# ── رد ──
def reply(cookie_label: str, tweet_url: str, reply_text: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/reply", json={
        "cookie_label": cookie_label, "tweet_url": tweet_url,
        "reply_text": reply_text, "headless": headless,
    })


# ── متابعة ──
def follow(cookie_label: str, profile_url: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/follow", json={
        "cookie_label": cookie_label, "profile_url": profile_url, "headless": headless,
    })


# ── إلغاء متابعة ──
def unfollow(cookie_label: str, profile_url: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/unfollow", json={
        "cookie_label": cookie_label, "profile_url": profile_url, "headless": headless,
    })


# ── بوكمارك ──
def bookmark(cookie_label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    return _api_call("POST", "/api/bookmark", json={
        "cookie_label": cookie_label, "tweet_url": tweet_url, "headless": headless,
    })




# ── قائمة الكوكيز ──
def list_cookies() -> Dict[str, Any]:
    return _api_call("GET", "/api/cookies")


# ── إحصائيات ──
def get_stats() -> Dict[str, Any]:
    return _api_call("GET", "/api/stats")
