"""
تسجيل الدخول في X — عبر loginx2026 API Server
يشغّل api_server.py من app/x/loginx2026 ويرسل طلب تسجيل دخول عبر API
عند النجاح، ينسخ الكوكيز إلى app/x/cookies
"""
import os
import sys
import time
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Optional

# مسارات
LOGINX2026_DIR = Path(__file__).resolve().parent.parent / "loginx2026"
LOGINX2026_COOKIES = LOGINX2026_DIR / "cookies"
APP_X_COOKIES = Path(__file__).resolve().parent.parent / "cookies"
API_SERVER_SCRIPT = LOGINX2026_DIR / "api_server.py"
LOGINX2026_PORT = 5050
LOGINX2026_BASE = f"http://127.0.0.1:{LOGINX2026_PORT}"

# متغير عام لحفظ عملية السيرفر
_server_process = None


def _is_server_running():
    """تحقق إذا السيرفر شغال"""
    try:
        r = requests.get(f"{LOGINX2026_BASE}/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _start_server():
    """تشغيل api_server.py بالخلفية"""
    global _server_process
    if _is_server_running():
        print(f"[x_login] سيرفر loginx2026 شغال على {LOGINX2026_BASE}")
        return

    print(f"[x_login] جاري تشغيل سيرفر loginx2026 على بورت {LOGINX2026_PORT}...")
    _server_process = subprocess.Popen(
        [sys.executable, str(API_SERVER_SCRIPT), "--port", str(LOGINX2026_PORT)],
        cwd=str(LOGINX2026_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # انتظر حتى يبدأ السيرفر
    for _ in range(20):
        time.sleep(0.5)
        if _is_server_running():
            print(f"[x_login] سيرفر loginx2026 جاهز ✓")
            return

    raise RuntimeError("فشل تشغيل سيرفر loginx2026")


class TwitterLoginAdvanced:
    """تسجيل الدخول عبر loginx2026 API"""

    def login_twitter(self, username: str, password: str, cookies_dir: str = "cookies",
                      headless: bool = False, proxy_config=None, email: Optional[str] = None) -> Path:
        """
        تسجيل الدخول عبر loginx2026 API Server

        Args:
            username: اسم المستخدم
            password: كلمة المرور
            cookies_dir: مجلد حفظ الكوكيز (الوجهة النهائية)
            headless: (مُتجاهل)
            proxy_config: (مُتجاهل)
            email: الإيميل (اختياري)

        Returns:
            Path: مسار ملف الكوكيز المحفوظ
        """
        # 1. تأكد أن السيرفر شغال
        _start_server()

        # 2. إرسال طلب تسجيل الدخول عبر API
        print(f"[x_login] إرسال طلب تسجيل دخول لـ {username}...")
        payload = {"username": username, "password": password}
        if email:
            payload["email"] = email

        try:
            resp = requests.post(
                f"{LOGINX2026_BASE}/api/login",
                json=payload,
                timeout=120
            )
            result = resp.json()
        except requests.ConnectionError:
            raise RuntimeError(f"تعذر الاتصال بسيرفر loginx2026 على {LOGINX2026_BASE}")
        except requests.Timeout:
            raise RuntimeError("انتهت مهلة الانتظار (120s)")
        except Exception as e:
            raise RuntimeError(f"خطأ في الاتصال: {e}")

        # 3. تحقق من النتيجة
        if not result.get("success"):
            raise RuntimeError(result.get("error", "فشل تسجيل الدخول"))

        print(f"[x_login] تسجيل الدخول نجح لـ {username} ✓")

        # 4. نسخ ملف الكوكيز من loginx2026/cookies إلى app/x/cookies
        src = LOGINX2026_COOKIES / f"{username}.json"
        APP_X_COOKIES.mkdir(parents=True, exist_ok=True)
        dst = APP_X_COOKIES / f"{username}.json"

        if src.exists():
            shutil.copy2(str(src), str(dst))
            print(f"[x_login] تم نسخ الكوكيز: {src} → {dst}")
        else:
            raise RuntimeError(f"ملف الكوكيز غير موجود: {src}")

        # 5. أيضاً انسخ إلى cookies_dir المطلوب إذا مختلف
        cookies_dir_p = Path(cookies_dir)
        cookies_dir_p.mkdir(parents=True, exist_ok=True)
        alt_dst = cookies_dir_p / f"{username}.json"
        if alt_dst.resolve() != dst.resolve():
            shutil.copy2(str(src), str(alt_dst))

        return dst
