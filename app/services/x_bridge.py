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


def _has_latest_endpoints() -> bool:
    """
    يتحقق أن السيرفر الشغّال يحتوي على الـ endpoints الجديدة (scheduled_post).
    لو رجع 404 → النسخة قديمة ولازم نقتل العملية ونشغّل الجديدة.
    لو رجع 200/401/403 → النسخة محدّثة.
    """
    try:
        r = requests.get(f"{XSUITE_BASE_URL}/api/scheduled_posts",
                         headers=_HEADERS, timeout=5)
        # 404 = endpoint غير موجود → نسخة قديمة
        # 200/401/403/405 = endpoint موجود → نسخة محدّثة
        return r.status_code != 404
    except Exception:
        return False


def _kill_process_on_port(port: int) -> bool:
    """يقتل أي عملية تستمع على البورت المُحدد (Windows + Linux)."""
    try:
        if sys.platform == "win32":
            # ابحث عن PID على البورت
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True, timeout=5
            )
            pids_to_kill = set()
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        pids_to_kill.add(parts[-1])
            killed = False
            for pid in pids_to_kill:
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=5)
                    killed = True
                    print(f"[X-Bridge] قتل العملية القديمة PID={pid} على بورت {port}")
                except Exception as e:
                    print(f"[X-Bridge] فشل قتل PID={pid}: {e}")
            return killed
        else:
            # Linux/Mac
            result = subprocess.run(["lsof", "-ti", f":{port}"],
                                    capture_output=True, text=True, timeout=5)
            pids = [p.strip() for p in result.stdout.splitlines() if p.strip()]
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], capture_output=True, timeout=5)
                    print(f"[X-Bridge] قتل العملية القديمة PID={pid} على بورت {port}")
                except Exception:
                    pass
            return bool(pids)
    except Exception as e:
        print(f"[X-Bridge] _kill_process_on_port error: {e}")
        return False


def start_xsuite_server() -> bool:
    """تشغيل سيرفر app/x بالخلفية (دائماً يحاول يشغّل إذا ما في process محلي)"""
    global _process

    # إذا عندنا process محلي شغال + يستجيب + يحتوي الـ endpoints الجديدة، استخدمه
    if _process and _process.poll() is None and _is_running() and _has_latest_endpoints():
        print(f"[X-Bridge] سيرفر app/x شغال بالفعل على بورت {XSUITE_PORT}")
        return True

    # إذا في سيرفر شغال على البورت لكنه نسخة قديمة (بدون _process لدينا) → اقتله
    if _is_running() and not _has_latest_endpoints():
        print(f"[X-Bridge] ⚠️ سيرفر app/x القديم شغّال على بورت {XSUITE_PORT} — قتله للتحديث")
        _kill_process_on_port(XSUITE_PORT)
        time.sleep(2)

    # أوقف أي process محلي قديم نمتلكه
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


# ─── LoginX سيرفر ──────────────────────────────────────────
LOGINX_PORT = int(os.getenv("LOGINX_PORT", "5000"))
LOGINX_DIR = XSUITE_DIR / "loginx"   # app/x/loginx
_loginx_process: Optional[subprocess.Popen] = None


def _is_loginx_running() -> bool:
    """تحقق إذا سيرفر loginx شغال"""
    try:
        r = requests.get(f"http://127.0.0.1:{LOGINX_PORT}/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_loginx_server() -> bool:
    """تشغيل سيرفر loginx بالخلفية"""
    global _loginx_process

    if _loginx_process and _loginx_process.poll() is None and _is_loginx_running():
        print(f"[X-Bridge] سيرفر loginx شغال بالفعل على بورت {LOGINX_PORT}")
        return True

    if _loginx_process and _loginx_process.poll() is None:
        try:
            _loginx_process.terminate()
            _loginx_process.wait(timeout=5)
        except Exception:
            _loginx_process.kill()
        _loginx_process = None

    loginx_app = LOGINX_DIR / "app.py"
    if not loginx_app.exists():
        print(f"[X-Bridge] ⚠️ ملف loginx/app.py غير موجود: {loginx_app}")
        return False

    print(f"[X-Bridge] تشغيل سيرفر loginx على بورت {LOGINX_PORT} ...")

    python_exe = sys.executable
    env = os.environ.copy()

    try:
        print(f"[X-Bridge] loginx path: {loginx_app}")
        print(f"[X-Bridge] loginx dir: {LOGINX_DIR}")
        print(f"[X-Bridge] python exe: {python_exe}")

        _loginx_process = subprocess.Popen(
            [python_exe, str(loginx_app)],
            cwd=str(LOGINX_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        atexit.register(stop_loginx_server)

        for i in range(15):
            time.sleep(1)
            if _is_loginx_running():
                print(f"[X-Bridge] ✅ سيرفر loginx جاهز على بورت {LOGINX_PORT}")
                return True
            if _loginx_process.poll() is not None:
                out = _loginx_process.stdout.read().decode(errors="ignore")[:1000]
                print(f"[X-Bridge] ❌ سيرفر loginx توقف مبكراً (exit code: {_loginx_process.returncode}):\n{out}")
                return False
            if i == 5:
                print(f"[X-Bridge] loginx لا يزال يبدأ... (انتظار)")

        # آخر محاولة قراءة الخطأ
        if _loginx_process.poll() is not None:
            out = _loginx_process.stdout.read().decode(errors="ignore")[:1000]
            print(f"[X-Bridge] ❌ loginx output:\n{out}")
        print("[X-Bridge] ❌ تجاوز وقت انتظار تشغيل سيرفر loginx")
        return False

    except Exception as e:
        import traceback
        print(f"[X-Bridge] ❌ فشل تشغيل سيرفر loginx: {e}")
        traceback.print_exc()
        return False


def stop_loginx_server():
    """إيقاف سيرفر loginx"""
    global _loginx_process
    if _loginx_process and _loginx_process.poll() is None:
        print("[X-Bridge] إيقاف سيرفر loginx ...")
        try:
            if sys.platform == "win32":
                _loginx_process.terminate()
            else:
                _loginx_process.send_signal(signal.SIGTERM)
            _loginx_process.wait(timeout=10)
        except Exception:
            _loginx_process.kill()
        _loginx_process = None


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


# ── تسجيل دخول (معطّل) ──
def login(label: str, username: str, password: str, headless: bool = True) -> Dict[str, Any]:
    """تسجيل الدخول بالباسورد معطّل. يرجى رفع كوكيز الحساب بدلاً من ذلك."""
    return {
        "success": False,
        "message": "تسجيل الدخول بكلمة المرور معطّل. يرجى رفع ملف كوكيز الحساب عبر /api/x/upload-cookies"
    }


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


# ── جدولة تغريدة (مع نشر تلقائي في app/x) ──
def schedule_post(
    event_id: str,
    cookie_label: str,
    content: str,
    run_at: str,                      # ISO UTC "YYYY-MM-DD HH:MM:SS"
    media_url: Optional[str] = None,
    callback_url: Optional[str] = None,
    callback_payload: Optional[Dict[str, Any]] = None,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """يرسل طلب جدولة تغريدة لسيرفر app/x ليتولى النشر التلقائي."""
    return _api_call("POST", "/api/scheduled_post", json={
        "event_id": event_id,
        "cookie_label": cookie_label,
        "content": content,
        "run_at": run_at,
        "media_url": media_url,
        "callback_url": callback_url,
        "callback_payload": callback_payload,
        "max_attempts": max_attempts,
    })


def get_scheduled_post(event_id: str) -> Dict[str, Any]:
    return _api_call("GET", f"/api/scheduled_post/{event_id}")


def cancel_scheduled_post(event_id: str) -> Dict[str, Any]:
    return _api_call("DELETE", f"/api/scheduled_post/{event_id}")


def list_scheduled_posts(status: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _api_call("GET", "/api/scheduled_posts", params=params)


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
