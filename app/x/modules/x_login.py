"""
تسجيل الدخول في X — عبر API مباشر (بدون متصفح)
يستخدم مكتبة x_auth (curl_cffi + CastleToken + ClientTransaction)
أسرع وأخف بكثير من Playwright
"""
import os
import re
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional


class TwitterLoginAdvanced:
    def _safe_cookie_filename(self, username: str) -> str:
        s = (username or '').strip()
        s = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", s)
        if not s:
            s = "account"
        if not s.endswith('.json'):
            s += '.json'
        return s[:120]

    def _run_login_subprocess(self, username: str, password: str, cookies_dir: str) -> dict:
        """تشغيل تسجيل الدخول كـ subprocess منفصل عبر x_auth"""
        x_auth_dir = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, "-m", "x_auth.login_sync", username, password, cookies_dir],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
            cwd=str(x_auth_dir)
        )
        output = result.stdout + result.stderr
        # البحث عن النتيجة
        for line in output.split("\n"):
            if line.startswith("__RESULT__"):
                return json.loads(line[10:])
        raise RuntimeError(f"فشل تسجيل الدخول عبر API: {output[-500:]}")

    def _run_login_async(self, username: str, password: str, email: Optional[str], cookies_dir: str) -> dict:
        """تشغيل تسجيل الدخول async مباشرة"""
        from .x_auth.login import x_login

        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            # نحن داخل event loop — نستخدم subprocess
            return self._run_login_subprocess(username, password, cookies_dir)
        else:
            # لا يوجد event loop — نشغل مباشرة
            cookies_dict = asyncio.run(x_login(username, password, email, cookies_dir))
            return {
                "success": True,
                "username": username,
                "auth_token": cookies_dict.get("auth_token", ""),
                "ct0": cookies_dict.get("ct0", ""),
                "cookies": cookies_dict,
            }

    def login_twitter(self, username: str, password: str, cookies_dir: str = "cookies",
                      headless: bool = False, proxy_config=None, email: Optional[str] = None) -> Path:
        """
        تسجيل دخول X عبر API مباشر (بدون متصفح).

        Args:
            username: اسم المستخدم
            password: كلمة المرور
            cookies_dir: مجلد حفظ الكوكيز
            headless: (مُتجاهل — موجود للتوافق مع الواجهة القديمة)
            proxy_config: (مُتجاهل حالياً)
            email: الإيميل (اختياري — يُستخدم إذا طلب X تحقق بديل)

        Returns:
            Path: مسار ملف الكوكيز المحفوظ (بصيغة Playwright storage_state)
        """
        cookies_dir_p = Path(cookies_dir)
        cookies_dir_p.mkdir(parents=True, exist_ok=True)
        cookie_path = cookies_dir_p / self._safe_cookie_filename(username)

        try:
            result = self._run_login_async(username, password, email, str(cookies_dir_p))
        except Exception:
            # fallback: subprocess
            try:
                result = self._run_login_subprocess(username, password, str(cookies_dir_p))
            except Exception as e:
                raise RuntimeError(f"فشل تسجيل الدخول: {e}")

        if not result.get("success"):
            raise RuntimeError(result.get("error", "فشل تسجيل الدخول (سبب غير معروف)"))

        # x_auth يحفظ الكوكيز باسم username.json داخل cookies_dir
        # نعيد تسمية الملف إذا كان الاسم مختلفاً
        expected_file = cookies_dir_p / f"{username}.json"
        if expected_file.exists() and expected_file != cookie_path:
            try:
                expected_file.replace(cookie_path)
            except Exception:
                # إذا فشلت إعادة التسمية، نستخدم الملف الأصلي
                cookie_path = expected_file
        elif expected_file.exists():
            cookie_path = expected_file

        if not cookie_path.exists():
            raise RuntimeError(f"تم تسجيل الدخول لكن ملف الكوكيز غير موجود: {cookie_path}")

        return cookie_path

    def login_twitter_multi(self, accounts: list, cookies_dir: str = "cookies") -> list:
        """
        تسجيل دخول عدة حسابات دفعة واحدة.

        Args:
            accounts: قائمة من dict، كل واحد فيه:
                {"username": "...", "password": "...", "label": "..." (اختياري)}
            cookies_dir: مجلد حفظ الكوكيز

        Returns:
            list: نتائج كل حساب [{"username": ..., "success": bool, "error": ...}, ...]
        """
        import time as _time

        results = []
        for i, acc in enumerate(accounts):
            username = (acc.get("username") or "").strip()
            password = (acc.get("password") or "").strip()
            label = (acc.get("label") or "").strip() or username
            email = (acc.get("email") or "").strip() or None

            if not username or not password:
                results.append({"username": username or f"row_{i+1}", "label": label, "success": False, "error": "اسم المستخدم أو كلمة المرور فارغ"})
                continue

            try:
                cookie_path = self.login_twitter(
                    username=username, password=password,
                    cookies_dir=cookies_dir, email=email
                )
                # إعادة تسمية للـ label
                from modules.utils import safe_label as _safe_label
                safe_lbl = _safe_label(label)
                dst = Path(cookies_dir) / f"{safe_lbl}.json"
                if cookie_path != dst:
                    try:
                        Path(cookie_path).replace(dst)
                        cookie_path = dst
                    except Exception:
                        pass
                results.append({"username": username, "label": safe_lbl, "success": True, "file": str(cookie_path)})
            except Exception as e:
                results.append({"username": username, "label": label, "success": False, "error": str(e)})

            # تأخير بين الحسابات
            if i < len(accounts) - 1:
                _time.sleep(3)

        return results
