import subprocess
import time
import os
import psutil
from datetime import datetime
import json
import sqlite3
import urllib.parse
import uiautomator2 as u2
import csv

# محاولة استيراد Playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class LDPlayerChromeAutomation:
    def __init__(self, log_callback=None):
        # مسار ldconsole حسب تثبيت LDPlayer عندك
        self.ldconsole = r"D:\LDPlayer\LDPlayer9\ldconsole.exe"
        self.adb_path = None
        self.emulator_index = None
        self.playwright_cookies_path = None  # مسار ملف الكوكيز الخاص ببلاي رايت (بعد التحويل)
        self.d = None  # uiautomator2 device
        self.device_serial = None  # سيريال الجهاز المتصل عبر ADB
        self._current_account = ""  # اسم الحساب الحالي
        self._log_callback = log_callback  # callback لإرسال اللوقات للواجهة

    def log(self, message, level="INFO"):
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "PROGRESS": "🔄",
            "TASK": "📱",
            "CLICK": "👆",
            "CHROME": "🌐",
            "PLAY": "🎭",
        }
        log_line = f"{icons.get(level, 'ℹ️')} {message}"
        try:
            print(log_line)
        except UnicodeEncodeError:
            print(log_line.encode("utf-8", errors="replace").decode("utf-8"))
        if self._log_callback:
            self._log_callback(log_line, level, self._current_account)

    # ---------------- ADB SETUP ---------------- #

    def auto_setup_adb(self):
        self.log("البحث عن ADB...", "PROGRESS")

        possible_paths = []

        # نحاول أولًا أن نأخذ adb من نفس مجلد ldconsole
        try:
            ld_dir = os.path.dirname(self.ldconsole)
            adb_from_ld = os.path.join(ld_dir, "adb.exe")
            possible_paths.append(adb_from_ld)
        except Exception:
            pass

        # مسارات إضافية محتملة
        possible_paths += [
            r"D:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\Program Files\LDPlayer\LDPlayer9\adb.exe",
            r"C:\adb\platform-tools\adb.exe",
            "adb",
        ]

        for path in possible_paths:
            if self.test_adb_path(path):
                self.adb_path = path
                self.log(f"تم العثور على ADB: {path}", "SUCCESS")
                return True

        self.log("لم يتم العثور على ADB - لن تعمل النقرات وفتح الروابط!", "ERROR")
        return False

    def test_adb_path(self, path):
        try:
            result = subprocess.run(
                [path, "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def quick_adb_connect(self):
        """التأكد من وجود جهاز ADB متصل بالمحاكي."""
        if not self.adb_path:
            self.log("لم يتم ضبط adb_path - لا يمكن الاتصال بـ ADB", "ERROR")
            return False

        self.log("التحقق من اتصال ADB بالمحاكي...", "PROGRESS")

        # تشغيل السيرفر
        subprocess.run([self.adb_path, "start-server"], capture_output=True)

        # 1️⃣ نفحص الأجهزة الحالية
        devices = subprocess.run(
            [self.adb_path, "devices"], capture_output=True, text=True
        )
        self.log(f"خروج adb devices:\n{devices.stdout}", "INFO")

        lines = devices.stdout.splitlines()[1:]  # نتجاهل header
        for line in lines:
            line = line.strip()
            if line and "\tdevice" in line and "offline" not in line:
                self.device_serial = line.split("\t")[0]
                self.log(f"تم العثور على جهاز متصل: {self.device_serial}", "SUCCESS")
                return True

        # 2️⃣ لو ما فيه أجهزة، نحاول الاتصال على المنافذ الشائعة لـ LDPlayer
        for port in ["5555", "5554", "5557"]:
            addr = f"127.0.0.1:{port}"
            self.log(f"محاولة الاتصال بـ ADB على {addr} ...", "INFO")
            result = subprocess.run(
                [self.adb_path, "connect", addr],
                capture_output=True,
                text=True,
            )
            out = (result.stdout + result.stderr).strip()
            self.log(f"نتيجة adb connect {addr}: {out}", "INFO")

            if "connected" in out.lower() or "already connected" in out.lower():
                devices = subprocess.run(
                    [self.adb_path, "devices"],
                    capture_output=True,
                    text=True,
                )
                self.log(
                    f"خروج adb devices بعد الاتصال:\n{devices.stdout}",
                    "INFO",
                )
                lines = devices.stdout.splitlines()[1:]
                for line in lines:
                    line = line.strip()
                    if line and "\tdevice" in line and "offline" not in line:
                        self.device_serial = line.split("\t")[0]
                        self.log(f"اتصال ADB ناجح على المنفذ {port} ({self.device_serial})", "SUCCESS")
                        return True

        self.log("لا يوجد أي جهاز ADB متصل - لن تعمل النقرات وفتح الروابط", "ERROR")
        return False

    # ---------------- EMULATOR MANAGEMENT ---------------- #

    def cleanup_processes(self):
        self.log("تنظيف العمليات المتداخلة...", "PROGRESS")
        processes_to_kill = [
            "adb.exe",
            "LdVBoxHeadless.exe",
            "dnplayer.exe",
            "LdBoxHeadless.exe",
        ]
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] in processes_to_kill:
                    proc.kill()
            except Exception:
                pass
        time.sleep(3)

    def get_emulators(self):
        try:
            result = subprocess.run(
                [self.ldconsole, "list2"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            emulators = []
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "," in line.strip():
                        parts = line.strip().split(",")
                        if len(parts) >= 2:
                            index = parts[0].strip()
                            name = parts[1].strip()
                            if index.isdigit():
                                emulators.append((index, name))
            return emulators
        except Exception:
            return []

    def auto_create_emulator(self):
        self.log("إنشاء محاكي جديد تلقائياً...", "PROGRESS")

        # حذف أي محاكيات سابقة
        emulators = self.get_emulators()
        for index, name in emulators:
            subprocess.run(
                [self.ldconsole, "quit", "--index", index],
                capture_output=True,
            )
            subprocess.run(
                [self.ldconsole, "remove", "--index", index],
                capture_output=True,
            )
            time.sleep(1)

        # إضافة محاكي جديد
        result = subprocess.run(
            [self.ldconsole, "add"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            self.log("فشل إنشاء المحاكي", "ERROR")
            return None

        time.sleep(5)
        emulators = self.get_emulators()
        if emulators:
            index = emulators[0][0]
            self.emulator_index = index
            self.auto_configure_emulator(index)
            return index
        return None

    def _find_config_for_chromebot(self):
        try:
            base_dir = os.path.dirname(self.ldconsole)  # C:\LDPlayer\LDPlayer9
            config_dir = os.path.join(base_dir, "vms", "config")

            if not os.path.isdir(config_dir):
                self.log(f"مجلد الكونفيج غير موجود: {config_dir}", "ERROR")
                return None

            for fname in os.listdir(config_dir):
                if not fname.lower().startswith("leidian") or not fname.lower().endswith(
                    ".config"
                ):
                    continue

                path = os.path.join(config_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                except Exception:
                    continue

                if data.get("statusSettings.playerName") == "ChromeBot":
                    self.log(
                        f"تم العثور على ملف الكونفيج للمحاكي ChromeBot: {path}",
                        "SUCCESS",
                    )
                    return path

            self.log(
                "لم أجد ملف كونفيج فيه playerName = ChromeBot داخل vms\\config",
                "ERROR",
            )
            return None

        except Exception as e:
            self.log(f"خطأ أثناء البحث عن ملف الكونفيج: {e}", "ERROR")
            return None

    def enable_adb_debug_in_config(self):
        """
        تفعيل ADB Debug عن طريق إضافة basicSettings.adbDebug = 1
        داخل ملف الكونفيج الخاص بمحاكي ChromeBot.
        """
        cfg_path = self._find_config_for_chromebot()
        if not cfg_path:
            return False

        try:
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            if "basicSettings.adbDebug" in data and data["basicSettings.adbDebug"]:
                self.log("ADB Debug مفعّل مسبقاً في ملف الكونفيج", "INFO")
                return True

            data["basicSettings.adbDebug"] = 1

            with open(cfg_path, "w", encoding="utf-8", errors="ignore") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.log(
                f"تم تعديل ملف الكونفيج لتفعيل ADB Debug: {cfg_path}",
                "SUCCESS",
            )
            return True

        except Exception as e:
            self.log(f"فشل تعديل ملف الكونفيج لتفعيل ADB Debug: {e}", "ERROR")
            return False

    def auto_configure_emulator(self, index):
        self.log("تكوين المحاكي للأتمتة (دقة، موارد، روت، ADB)...", "PROGRESS")

        subprocess.run(
            [self.ldconsole, "quit", "--index", index],
            capture_output=True,
        )
        time.sleep(2)

        settings = [
            ["modify", "--index", index, "--resolution", "720,1280,240"],
            ["modify", "--index", index, "--memory", "2048"],
            ["modify", "--index", index, "--cpu", "2"],
            ["modify", "--index", index, "--fps", "60"],
            ["modify", "--index", index, "--root", "1"],
        ]
        for setting in settings:
            subprocess.run([self.ldconsole] + setting, capture_output=True)
            time.sleep(0.5)

        subprocess.run(
            [self.ldconsole, "rename", "--index", index, "--title", "ChromeBot"],
            capture_output=True,
        )

        self.enable_adb_debug_in_config()

        self.log("تم تكوين المحاكي بنجاح (تشمل ROOT + محاولة تفعيل ADB Debug)", "SUCCESS")

    def auto_launch_emulator(self, index):
        self.log("تشغيل المحاكي...", "PROGRESS")
        result = subprocess.run(
            [self.ldconsole, "launch", "--index", index],
            capture_output=True,
        )
        if result.returncode != 0:
            self.log("فشل تشغيل المحاكي", "ERROR")
            return False

        self.log("تم تشغيل المحاكي - انتظار الجاهزية...", "SUCCESS")

        # ننتظر حتى يظهر جهاز ADB (أقصى 60 ثانية)
        for i in range(60):
            devices = subprocess.run(
                [self.adb_path, "devices"] if self.adb_path else ["adb", "devices"],
                capture_output=True, text=True
            )
            lines = devices.stdout.splitlines()[1:]
            for line in lines:
                if "\tdevice" in line and "offline" not in line:
                    elapsed = i + 1
                    self.log(f"المحاكي جاهز خلال {elapsed} ثانية", "SUCCESS")
                    return True
            if i % 10 == 9:
                self.log(f"لا يزال ينتظر... ({i+1} ثانية)", "PROGRESS")
            time.sleep(1)

        self.log("المحاكي لم يستجب خلال 60 ثانية", "ERROR")
        return False

    # ---------------- CHROME CONTROL ---------------- #

    def force_open_chrome_with_ldplayer(self):
        self.log("فتح Chrome باستخدام LDPlayer...", "CHROME")
        if not self.emulator_index:
            self.log("لا يوجد محاكي متاح", "ERROR")
            return False

        chrome_methods = [
            {
                "method": "launchex",
                "args": ["--index", self.emulator_index, "--packagename", "com.android.chrome"],
                "name": "Chrome الأساسي",
            },
            {
                "method": "launchex",
                "args": ["--index", self.emulator_index, "--packagename", "org.chromium.chrome"],
                "name": "Chromium",
            },
            {
                "method": "launchex",
                "args": ["--index", self.emulator_index, "--packagename", "com.android.browser"],
                "name": "المتصفح الافتراضي",
            },
            {
                "method": "launchex",
                "args": [
                    "--index",
                    self.emulator_index,
                    "--packagename",
                    "com.google.android.apps.chrome",
                ],
                "name": "Chrome Google",
            },
        ]

        for method_info in chrome_methods:
            self.log(f"محاولة فتح: {method_info['name']}", "CHROME")
            cmd = [self.ldconsole, method_info["method"]] + method_info["args"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.log(f"نجح فتح {method_info['name']}", "SUCCESS")
                time.sleep(8)
                return True
            else:
                self.log(
                    f"فشل فتح {method_info['name']}: {result.stdout}",
                    "ERROR",
                )
                time.sleep(2)

        self.log("فشل في فتح Chrome بجميع الطرق", "ERROR")
        return False

    # ---------------- ADB HELPERS (TAP / URL / TEXT) ---------------- #

    def tap_screen(self, x, y):
        if not self.adb_path:
            self.log("ADB غير مضبوط، لا يمكن تنفيذ النقر", "ERROR")
            return False
        if not self.quick_adb_connect():
            return False

        cmd = [self.adb_path, "-s", self.device_serial, "shell", "input", "tap", str(x), str(y)]
        subprocess.run(cmd, capture_output=True)
        self.log(f"تم النقر على الإحداثيات: ({x}, {y})", "CLICK")

        time.sleep(3)
        return True

    def open_url_in_chrome(self, url):
        if not self.adb_path:
            self.log("ADB غير مضبوط، لا يمكن فتح الرابط", "ERROR")
            return False
        if not self.quick_adb_connect():
            return False

        cmd = [
            self.adb_path,
            "-s", self.device_serial,
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            self.log(f"تم فتح الرابط: {url}", "SUCCESS")
            time.sleep(5)
            return True
        else:
            self.log(f"فشل فتح الرابط: {result.stdout} {result.stderr}", "ERROR")
            time.sleep(3)
            return False

    def input_text(self, text):
        if not self.adb_path or not self.quick_adb_connect():
            self.log("ADB غير مضبوط، لا يمكن إدخال النص", "ERROR")
            return False

        safe_text = text.replace(" ", "%s")
        cmd = [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_text]
        subprocess.run(cmd, capture_output=True)
        self.log(f"تم إدخال النص: {text}", "TASK")

        time.sleep(3)
        return True

    # ---------------- COOKIES: CONVERT & SAVE ---------------- #

    # ─── خصائص مطلوبة لكوكيز X الحسّاسة (متطابقة مع app/api/x_routes.py) ───
    HTTP_ONLY_COOKIES = {"auth_token", "kdt", "_twitter_sess", "__cf_bm", "auth_multi"}
    LAX_COOKIES = {"ct0", "auth_multi"}

    @staticmethod
    def _chrome_ts_to_unix(chrome_ts):
        """
        Chrome يخزّن expires_utc بالميكروثانية من 1601-01-01 (Windows epoch).
        نحوّله لـ Unix timestamp (ثوانٍ من 1970-01-01).
        0 = session cookie → نرجع +365 يوم.
        """
        if not chrome_ts or chrome_ts == 0:
            return time.time() + 365 * 24 * 3600
        # الفرق بين 1601-01-01 و 1970-01-01 بالثواني = 11644473600
        return (chrome_ts / 1_000_000.0) - 11644473600

    @staticmethod
    def _chrome_samesite_to_playwright(chrome_ss):
        """
        Chrome samesite enum:  -1=Unspecified, 0=None, 1=Lax, 2=Strict
        Playwright يقبل: "None" | "Lax" | "Strict"
        """
        mapping = {0: "None", 1: "Lax", 2: "Strict"}
        return mapping.get(chrome_ss, "None")

    def convert_cookies_to_playwright(self, cookies_file_path, account_name=""):
        """
        يفتح ملف ChromeCookies (SQLite) ويحوّله لملف JSON بصيغة موج/Playwright الكاملة:
        {
          "cookies": [
            {name, value, domain, path, expires, httpOnly, secure, sameSite},
            ...
          ],
          "origins": []
        }
        هذا هو نفس التنسيق المستخدم في app/api/x_routes.py:_convert_to_playwright_format
        ليتوافق مع موج وحساباتك ٤٠٠٪.
        """
        try:
            if not os.path.exists(cookies_file_path):
                self.log(f"ملف الكوكيز غير موجود للتحويل: {cookies_file_path}", "ERROR")
                return None

            self.log("بدء تحويل ملف الكوكيز لصيغة موج/Playwright...", "PROGRESS")

            conn = sqlite3.connect(cookies_file_path)
            cursor = conn.cursor()
            # نقرأ كل الحقول المهمة:
            #   value + encrypted_value (لكشف الكوكيز المشفّرة)
            #   expires_utc (وقت انتهاء الصلاحية بصيغة Chrome)
            #   samesite (سياسة الكوكي 0/1/2/-1)
            cursor.execute(
                "SELECT host_key, name, value, encrypted_value, path, "
                "is_secure, is_httponly, expires_utc, samesite FROM cookies"
            )
            rows = cursor.fetchall()
            conn.close()

            playwright_cookies = []

            # عدّادات للتقرير التشخيصي
            x_total = 0
            x_plain = 0
            x_encrypted_only = 0
            important_target = {"auth_token", "ct0", "twid", "kdt"}
            important_found = set()
            encrypted_names = []

            for (host_key, name, value, encrypted_value, path,
                 is_secure, is_httponly, expires_utc, samesite) in rows:
                is_x = ("x.com" in host_key) or ("twitter.com" in host_key)
                if not is_x:
                    continue

                x_total += 1
                has_value = bool(value)
                has_encrypted = bool(encrypted_value)

                if has_value:
                    x_plain += 1
                    if name in important_target:
                        important_found.add(name)
                elif has_encrypted:
                    x_encrypted_only += 1
                    encrypted_names.append(name)
                else:
                    continue

                if not has_value:
                    continue

                try:
                    decoded_value = urllib.parse.unquote(value)
                except Exception:
                    decoded_value = value

                # نحدد سياسة الكوكي:
                #   httpOnly: من القاعدة + إجبار للكوكيز الحسّاسة
                #   sameSite: من القاعدة + إجبار Lax لـ ct0/auth_multi
                http_only = bool(is_httponly) or (name in self.HTTP_ONLY_COOKIES)
                same_site = self._chrome_samesite_to_playwright(samesite)
                if name in self.LAX_COOKIES:
                    same_site = "Lax"

                # نحوّل expires_utc من Chrome timestamp إلى Unix timestamp
                expires_unix = self._chrome_ts_to_unix(expires_utc)

                cookie_obj = {
                    "name": name,
                    "value": decoded_value,
                    "domain": host_key,
                    "path": path if path else "/",
                    "expires": float(expires_unix),
                    "httpOnly": http_only,
                    "secure": bool(is_secure) or name in self.HTTP_ONLY_COOKIES,
                    "sameSite": same_site,
                }

                playwright_cookies.append(cookie_obj)

            # ===== تقرير تشخيصي للكوكيز =====
            self.log("=" * 60, "INFO")
            self.log("📊 تقرير تشخيص كوكيز X/Twitter:", "INFO")
            self.log(f"  • إجمالي كوكيز x.com/twitter.com في القاعدة: {x_total}", "INFO")
            self.log(f"  • بقيمة نصية صالحة (مكتوبة لـ Playwright): {x_plain}", "INFO")
            self.log(f"  • مشفّرة فقط (encrypted_value): {x_encrypted_only}", "INFO")
            if encrypted_names:
                self.log(f"  • أسماء الكوكيز المشفّرة: {encrypted_names}", "INFO")
            self.log(
                f"  • الكوكيز الحسّاسة الموجودة نصيًا: "
                f"{sorted(important_found) if important_found else '⛔ لا يوجد!'}",
                "INFO",
            )

            missing = important_target - important_found
            if missing:
                if x_encrypted_only > 0 and any(n in encrypted_names for n in missing):
                    self.log(
                        f"⚠️ كوكيز مهمة ناقصة: {sorted(missing)}\n"
                        f"   السبب الأرجح: مشفّرة في Chrome Android (encrypted_value).\n"
                        f"   الحل: نحتاج فك تشفير بمفتاح Chrome master key (متقدّم).",
                        "ERROR",
                    )
                else:
                    self.log(
                        f"⚠️ كوكيز مهمة ناقصة: {sorted(missing)}\n"
                        f"   السبب الأرجح: تسجيل الدخول لم يكتمل (الكوكيز هذي ما تُنشأ إلا بعد دخول ناجح).",
                        "ERROR",
                    )
            else:
                self.log("✅ كل الكوكيز الحسّاسة موجودة — تسجيل الدخول ناجح", "SUCCESS")
            self.log("=" * 60, "INFO")

            if not playwright_cookies:
                self.log("لم يتم العثور على أي كوكيز نصية لتويتر/X في الملف", "ERROR")
                return None

            # ===== الصيغة النهائية المتوافقة مع موج و Playwright storage_state =====
            output = {
                "cookies": playwright_cookies,
                "origins": [],
            }

            out_dir = os.path.dirname(cookies_file_path)
            filename = f"{account_name}.json" if account_name else "playwright_cookies.json"
            out_path = os.path.join(out_dir, filename)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            self.log(
                f"تم إنشاء ملف كوكيز بصيغة موج/Playwright في: {out_path}\n"
                f"   الصيغة: {{cookies: [{len(playwright_cookies)} كوكي], origins: []}}",
                "SUCCESS",
            )

            return out_path

        except Exception as e:
            self.log(f"فشل تحويل الكوكيز لصيغة Playwright: {e}", "ERROR")
            return None

    def save_cookies_to_pc(self):
        """
        يستخدم نفس الأوامر التي جربتها يدويًا:
            adb shell
            su
            cp /data/data/com.android.chrome/app_chrome/Default/Cookies /sdcard/ChromeCookies
            exit
            adb pull /sdcard/ChromeCookies CookiesBackup
        ثم يحولها لملف Playwright JSON.
        """
        if not self.adb_path or not self.quick_adb_connect():
            self.log("ADB غير متصل، لا يمكن حفظ الكوكيز", "ERROR")
            return False

        local_dir = os.path.join(os.getcwd(), "CookiesBackup")
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        self.log("محاولة نسخ ملف الكوكيز من المحاكي إلى /sdcard بالطريقة اليدوية التي نجحت...", "PROGRESS")

        try:
            proc = subprocess.Popen(
                [self.adb_path, "-s", self.device_serial, "shell"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            script = (
                "su\n"
                "cp /data/data/com.android.chrome/app_chrome/Default/Cookies /sdcard/ChromeCookies\n"
                "exit\n"
            )

            out, err = proc.communicate(script, timeout=30)
            self.log(f"خروج adb shell:\nSTDOUT:\n{out}\nSTDERR:\n{err}", "INFO")

            if proc.returncode != 0:
                self.log("فشل نسخ ملف الكوكيز إلى /sdcard عبر su/cp", "ERROR")
                return False

            self.log("✅ تمت محاولة النسخ إلى /sdcard/ChromeCookies بنجاح (حسب مخرجات الأوامر)", "SUCCESS")

        except subprocess.TimeoutExpired:
            self.log("انتهى وقت الانتظار أثناء تنفيذ أوامر su/cp داخل adb shell", "ERROR")
            return False
        except Exception as e:
            self.log(f"خطأ أثناء تنفيذ أوامر su/cp داخل adb shell: {e}", "ERROR")
            return False

        pull_cmd = [self.adb_path, "-s", self.device_serial, "pull", "/sdcard/ChromeCookies", local_dir]
        result = subprocess.run(pull_cmd, capture_output=True, text=True)
        out = (result.stdout + " " + result.stderr).strip()
        if result.returncode != 0:
            self.log(f"فشل سحب ملف الكوكيز من /sdcard: {out}", "ERROR")
            return False

        self.log(f"✅ تم حفظ ملف الكوكيز في: {local_dir}", "SUCCESS")

        cookies_file_path = os.path.join(local_dir, "ChromeCookies")
        if not os.path.exists(cookies_file_path):
            self.log("تنبيه: لم أجد ملف ChromeCookies بعد السحب (تأكد من الاسم في المجلد)", "ERROR")
            return False

        # تحويله لصيغة Playwright (ملف نصّي JSON)
        out_path = self.convert_cookies_to_playwright(cookies_file_path, self._current_account)
        if not out_path:
            return False

        self.playwright_cookies_path = out_path
        return True

    # ---------------- UIAUTOMATOR2 CONNECTION ---------------- #

    def connect_u2(self):
        """الاتصال بالمحاكي عبر uiautomator2."""
        self.log("الاتصال بـ uiautomator2...", "PROGRESS")
        try:
            self.d = u2.connect("127.0.0.1:5555")
            info = self.d.info
            self.log(f"تم الاتصال بـ u2: {info.get('productName', '?')}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"فشل الاتصال بـ uiautomator2: {e}", "ERROR")
            return False

    def u2_click(self, timeout=10, **kwargs):
        """البحث عن عنصر والنقر عليه. يرجع True إذا نجح."""
        try:
            el = self.d(**kwargs)
            if el.wait(timeout=timeout):
                el.click()
                self.log(f"تم النقر على: {kwargs}", "CLICK")
                time.sleep(2)  # تأخير طبيعي ضد كشف البوت
                return True
        except Exception:
            pass
        self.log(f"لم يُوجد العنصر: {kwargs}", "INFO")
        return False

    def u2_set_text(self, text, timeout=10, **kwargs):
        """البحث عن حقل إدخال والنقر عليه ثم كتابة النص عبر ADB (يعمل مع WebView)."""
        try:
            el = self.d(**kwargs)
            if el.wait(timeout=timeout):
                el.click()
                time.sleep(0.3)
                # مسح النص القديم
                self.d.clear_text()
                # الكتابة عبر ADB input text لأن set_text لا يعمل في WebView
                safe_text = text.replace(" ", "%s").replace("&", "\\&")
                subprocess.run(
                    [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_text],
                    capture_output=True
                )
                self.log(f"تم إدخال النص في: {kwargs}", "TASK")
                time.sleep(2)  # تأخير طبيعي ضد كشف البوت
                return True
        except Exception:
            pass
        self.log(f"فشل إدخال النص في: {kwargs}", "ERROR")
        return False

    def u2_exists(self, timeout=3, **kwargs):
        """فحص سريع هل العنصر موجود."""
        return self.d(**kwargs).exists(timeout=timeout)

    # ---------------- ROBUST WEB FIELD INPUT ---------------- #

    def _type_via_adb(self, text):
        """
        كتابة نص عبر ADB في الحقل المركَّز حاليًا.
        يرجع True إذا اكتمل الإرسال (لا يضمن أن النص ذهب للحقل الصحيح).
        فحص التلوّث يُسحب بعد ذلك من المنادي.
        """
        safe_text = (
            text.replace(" ", "%s")
            .replace("&", "\\&")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        subprocess.run(
            [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_text],
            capture_output=True,
        )

    def _check_url_bar_contamination(self, expected_value):
        """
        يقرأ نص URL bar بعد الكتابة ويتحقق هل تلوّث بقيمتنا (يعني الكتابة راحت غلط).
        يرجع True إذا كان التلوّث محتمل (نشوف قيمتنا داخل URL bar).
        """
        try:
            time.sleep(0.5)  # نمهل لحظة عشان النص يستقر
            url_text = self._get_url_bar_text()
            if not url_text:
                return False
            # لو القيمة موجودة كاملة أو جزء كبير منها داخل URL bar = تلوّث
            if expected_value in url_text:
                return True
            # حتى لو ٧٠٪ من الحروف موجودة بالترتيب
            if len(expected_value) >= 4 and expected_value[:max(4, len(expected_value) * 7 // 10)] in url_text:
                return True
        except Exception:
            pass
        return False

    def _edittext_resourceid(self, el):
        """يرجع resourceId لعنصر بأمان (سلسلة فارغة عند الفشل)."""
        try:
            return (el.info.get("resourceName") or "")
        except Exception:
            return ""

    def dump_edittexts(self):
        """طباعة كل حقول EditText على الشاشة للتشخيص (resourceId / النص / التركيز)."""
        try:
            count = self.d(className="android.widget.EditText").count
            self.log(f"عدد حقول EditText على الشاشة: {count}", "INFO")
            for i in range(count):
                try:
                    el = self.d(className="android.widget.EditText", instance=i)
                    info = el.info
                    self.log(
                        f"[EditText {i}] resourceId={info.get('resourceName')} "
                        f"text={info.get('text')!r} focused={info.get('focused')}",
                        "INFO",
                    )
                except Exception:
                    pass
        except Exception as e:
            self.log(f"فشل طباعة حقول EditText: {e}", "ERROR")

    def _element_center(self, el):
        """يرجع (x, y) لمركز عنصر من bounds، أو None."""
        try:
            b = el.info.get("bounds") or {}
            x = (b["left"] + b["right"]) // 2
            y = (b["top"] + b["bottom"]) // 2
            return x, y
        except Exception:
            return None

    def _keyboard_shown(self):
        """هل لوحة المفاتيح ظاهرة؟ (دلالة على أن حقل إدخال صار مركَّزًا)."""
        try:
            out = subprocess.run(
                [self.adb_path, "-s", self.device_serial, "shell", "dumpsys", "input_method"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            return "mInputShown=true" in out
        except Exception:
            return False

    def _tap_xy(self, x, y):
        subprocess.run(
            [self.adb_path, "-s", self.device_serial, "shell", "input", "tap", str(x), str(y)],
            capture_output=True,
        )

    def _press_back(self):
        subprocess.run(
            [self.adb_path, "-s", self.device_serial, "shell", "input", "keyevent", "4"],
            capture_output=True,
        )

    def _focused_resourceid(self):
        """resourceId للعنصر المركَّز حاليًا (سلسلة فارغة إن لا يوجد)."""
        try:
            el = self.d(focused=True)
            if el.exists(timeout=1):
                return self._edittext_resourceid(el)
        except Exception:
            pass
        return ""

    # أنماط resourceId لشريط Chrome URL وعناصره المرتبطة (autocomplete, omnibox...)
    URL_BAR_PATTERNS = (
        "url_bar",
        "search_box_text",
        "search_box",
        "omnibox",
        "address_bar",
        "location_bar",
        "url_action_container",
        "suggestion",  # عناصر اقتراحات Google في dropdown
    )

    def _is_url_bar_focused(self):
        """يتحقق ما إذا كان شريط Chrome (أو dropdown اقتراحاته) هو المركَّز."""
        rid = self._focused_resourceid().lower()
        return any(p in rid for p in self.URL_BAR_PATTERNS)

    def _is_url_bar_autocomplete_open(self):
        """
        يكشف ما إذا كان شريط Chrome في وضع التحرير مع dropdown مفتوح
        (اقتراحات Google/تاريخ البحث). في هذه الحالة صفحة الويب مغطاة بالكامل
        ولا يمكن تسجيل الدخول. نتعرّف عليه بفحص:
          - وجود عناصر بـ resourceId يحتوي suggestion/omnibox_results
          - أو وجود EditText بـ url_bar resourceId مع focused=True
          - أو ظهور أيقونة X لمسح النص (clear) في الـ URL bar
        """
        try:
            # علامة قوية: عناصر اقتراحات omnibox
            if self.d(resourceIdMatches=".*omnibox.*").exists(timeout=0.3):
                return True
            if self.d(resourceIdMatches=".*suggest.*").exists(timeout=0.3):
                return True
            # URL bar focused
            if self.d(resourceIdMatches=".*url_bar.*", focused=True).exists(timeout=0.3):
                return True
        except Exception:
            pass
        return False

    def _get_url_bar_text(self):
        """يقرأ النص الحالي داخل شريط Chrome URL (للتحقق من التلوّث بعد الكتابة)."""
        try:
            el = self.d(resourceIdMatches=".*url_bar.*")
            if el.exists(timeout=0.3):
                return (el.info.get("text") or "").strip()
        except Exception:
            pass
        return ""

    def _defocus_url_bar(self):
        """إلغاء تركيز شريط عنوان Chrome إن كان مركَّزًا (زر رجوع لإخفاء لوحة المفاتيح)."""
        if self._is_url_bar_focused():
            self.log("شريط عنوان Chrome مركَّز — إلغاء تركيزه قبل البحث عن الحقل...", "PROGRESS")
            # ضغطة رجوع واحدة فقط: تخرج من وضع تحرير شريط العنوان دون مغادرة الصفحة
            self._press_back()
            time.sleep(0.6)

    def _force_defocus_url_bar(self, max_attempts=5):
        """
        إلغاء تركيز شريط عنوان Chrome بقوة + إغلاق dropdown الـ autocomplete إن كان مفتوحًا.
        المشكلة: حتى لما الحقل في الصفحة يبان مركَّز (إطار CSS)، شريط Chrome ممكن
        يظل محتفظًا بـ IME focus + dropdown الاقتراحات يغطي الصفحة.
        نجرّب: BACK → tap على منطقة آمنة → swipe → BACK مزدوج → keyevent ESC.
        """
        def _need_defocus():
            return self._is_url_bar_focused() or self._is_url_bar_autocomplete_open()

        for attempt in range(max_attempts):
            if not _need_defocus():
                return True

            # سجّل لأي سبب لسه نحتاج defocus
            rid = self._focused_resourceid()
            ac = self._is_url_bar_autocomplete_open()
            self.log(
                f"[Defocus #{attempt+1}] focused_rid='{rid}' autocomplete_open={ac}",
                "INFO",
            )

            if attempt == 0:
                self.log("استراتيجية ١: BACK لإغلاق وضع التحرير", "PROGRESS")
                self._press_back()
                time.sleep(0.8)

            elif attempt == 1:
                self.log("استراتيجية ٢: tap على منطقة آمنة في الصفحة", "PROGRESS")
                try:
                    w, h = self.d.window_size()
                    # نقطة وسط الشاشة عرضًا، عند 45% من الارتفاع
                    # (تحت أي dropdown اقتراحات، فوق منتصف الصفحة)
                    self._tap_xy(w // 2, int(h * 0.45))
                    time.sleep(0.7)
                    # لو الـ tap فتح كيبورد على عنصر غير مرغوب، أغلقه
                    if self._keyboard_shown() and self._is_url_bar_focused():
                        self._press_back()
                        time.sleep(0.4)
                except Exception as e:
                    self.log(f"فشل tap على منطقة آمنة: {e}", "INFO")

            elif attempt == 2:
                self.log("استراتيجية ٣: ESC (keyevent 111) لإلغاء التحرير", "PROGRESS")
                # KEYCODE_ESCAPE يغلق وضع التحرير في Chrome
                subprocess.run(
                    [self.adb_path, "-s", self.device_serial, "shell", "input", "keyevent", "111"],
                    capture_output=True,
                )
                time.sleep(0.6)

            elif attempt == 3:
                self.log("استراتيجية ٤: swipe خفيف لتحريك التركيز", "PROGRESS")
                try:
                    w, h = self.d.window_size()
                    self.d.swipe(w // 2, int(h * 0.5), w // 2, int(h * 0.55), duration=0.2)
                    time.sleep(0.6)
                except Exception:
                    pass

            else:
                self.log("استراتيجية ٥: BACK مزدوج", "PROGRESS")
                self._press_back()
                time.sleep(0.4)
                self._press_back()
                time.sleep(0.4)

        ok = not _need_defocus()
        if not ok:
            self.log(
                f"⚠️ ما قدرت ألغي تركيز/dropdown شريط Chrome بعد {max_attempts} محاولات\n"
                f"   focused_rid='{self._focused_resourceid()}'  "
                f"autocomplete={self._is_url_bar_autocomplete_open()}",
                "ERROR",
            )
        return ok

    def _wait_x_page_loaded(self, timeout=20):
        """
        ينتظر حتى تكون صفحة X (تويتر) فعلاً محمّلة ومرئية.
        يتحقق بطرق متعددة (دون أن يطبع رسائل لكل فشل):
          - وجود نص placeholder المعروف
          - أو URL bar يحتوي x.com/twitter.com (والـ dropdown مغلق)
          - أو ظهور أيقونة X logo في الصفحة
        """
        end = time.time() + timeout
        while time.time() < end:
            # طريقة ١: نص placeholder
            for txt in ("Email or username", "Phone, email, or username",
                        "Sign in to X", "See what's happening"):
                if self.d(textContains=txt).exists(timeout=0.3):
                    return True
            # طريقة ٢: URL bar يحتوي رابط X والـ dropdown مغلق
            url_text = self._get_url_bar_text().lower()
            if ("x.com" in url_text or "twitter.com" in url_text) \
                    and not self._is_url_bar_autocomplete_open():
                return True
            time.sleep(0.5)
        return False

    def _find_web_field_center(self, hints, timeout):
        """يبحث عن مركز حقل الويب (placeholder أو EditText غير url_bar) خلال المهلة."""
        end = time.time() + timeout
        while time.time() < end:
            # أولوية: نص placeholder (مثل "Email or username")
            for hint in hints:
                el = self.d(textContains=hint)
                if el.exists(timeout=0.4):
                    center = self._element_center(el)
                    if center:
                        return center, f"نص {hint!r}"
            # بديل: أول EditText ليس شريط عنوان/بحث Chrome
            try:
                count = self.d(className="android.widget.EditText").count
            except Exception:
                count = 0
            for i in range(count):
                el = self.d(className="android.widget.EditText", instance=i)
                rid = self._edittext_resourceid(el)
                if rid.endswith("url_bar") or rid.endswith("search_box_text"):
                    continue
                center = self._element_center(el)
                if center:
                    return center, f"EditText instance={i} resourceId={rid or 'بدون'}"
            time.sleep(0.5)
        return None, ""

    def enter_web_field(self, text, hints=(), timeout=20):
        """
        إدخال نص في حقل ويب داخل Chrome بأمان، مع ضمان عدم الكتابة في شريط الرابط:
          0) ينتظر صفحة X لتُحمَّل فعلاً (لا dropdown اقتراحات).
          1) يلغي تركيز شريط Chrome بقوة (٥ استراتيجيات).
          2) يجرّب نقر العنصر مباشرة عبر accessibility (el.click) — الأكثر موثوقية.
          3) Fallback: يبحث عن مركز الحقل ويستخدم adb tap.
          4) حارس مزدوج قبل الكتابة: التركيز ≠ url_bar ولوحة المفاتيح ظاهرة.
          5) يستخدم adb input text لإرسال النص للحقل المركَّز.
          6) فحص تلوّث: يقرأ نص URL bar بعد الكتابة — لو فيه قيمة الإدخال = فشل.
        """
        self.dump_edittexts()

        # 0) تأكد أن صفحة X محمّلة وليست dropdown اقتراحات
        if self._is_url_bar_autocomplete_open():
            self.log("⚠️ Chrome في وضع البحث/Autocomplete — صفحة X مخفية، محاولة إغلاق", "ERROR")
            self._force_defocus_url_bar()
            self._wait_x_page_loaded(timeout=8)

        # 1) إلغاء تركيز شريط الرابط بقوة (٥ استراتيجيات)
        self._force_defocus_url_bar()

        # 2) محاولة أولى: نقر العنصر مباشرة عبر accessibility action (el.click)
        # هذا أكثر موثوقية من tap بالإحداثيات لأنه يستخدم AccessibilityNodeInfo.performAction(CLICK)
        # ويتجاوز مشاكل تداخل الـ focus مع URL bar.
        for hint in hints:
            try:
                el = self.d(textContains=hint)
                if el.exists(timeout=1.0):
                    try:
                        el.click()
                        time.sleep(1.0)
                        # تحقق فوري: التركيز انتقل بنجاح؟
                        if self._keyboard_shown() and not self._is_url_bar_focused():
                            self.log(f"✅ نقر accessibility مباشر على {hint!r} — التركيز انتقل بنجاح", "SUCCESS")
                            try:
                                self.d.clear_text()
                            except Exception:
                                pass
                            self._type_via_adb(text)
                            # فحص تلوّث: لو النص ظهر في URL bar، تراجع
                            if self._check_url_bar_contamination(text):
                                self.log("⛔ تلوّث URL bar بعد الكتابة — التراجع وإعادة المحاولة", "ERROR")
                                self._force_defocus_url_bar()
                                # امسح URL bar من النص الملوّث
                                try:
                                    el_url = self.d(resourceIdMatches=".*url_bar.*")
                                    if el_url.exists(timeout=0.3):
                                        el_url.clear_text()
                                except Exception:
                                    pass
                            else:
                                self.log(f"تم إدخال النص (عبر accessibility): {text}", "TASK")
                                return True
                    except Exception as e:
                        self.log(f"نقر accessibility فشل على {hint!r}: {e}", "INFO")
            except Exception:
                continue

        # 3) Fallback: ابحث عن مركز الحقل واستخدم adb tap
        center, source = self._find_web_field_center(hints, timeout)
        if center is None:
            self.log("لم أعثر على حقل إدخال الويب! الصفحة قد لم تُحمَّل بعد", "ERROR")
            return False

        self.log(f"تم تحديد حقل الإدخال عبر {source} عند {center}", "SUCCESS")
        x, y = center

        # 4) النقر بالإحداثيات مع محاولات + force defocus بين كل محاولة
        for attempt in range(3):
            self._tap_xy(x, y)
            time.sleep(1.2)  # وقت أطول لانتقال التركيز فعلياً

            kb_ok = self._keyboard_shown()
            url_ok = not self._is_url_bar_focused()

            if kb_ok and url_ok:
                self.log(f"تركيز الحقل ناجح (المحاولة {attempt+1})", "SUCCESS")
                break

            self.log(
                f"المحاولة {attempt+1}: keyboard={kb_ok}, not_url_bar={url_ok} — "
                "إعادة الـ defocus ثم النقر",
                "PROGRESS",
            )
            # دفع إضافي للـ defocus قبل المحاولة التالية
            self._force_defocus_url_bar(max_attempts=2)

        # 5) حارس مزدوج: لا نكتب إذا التركيز url_bar
        if self._is_url_bar_focused():
            self.log("⛔ التركيز ما زال url_bar بعد كل المحاولات — إلغاء الكتابة (حماية)", "ERROR")
            return False

        if not self._keyboard_shown():
            self.log("⚠️ لوحة المفاتيح غير ظاهرة — احتمال كبير الكتابة ما تنفّذ، لكن نحاول", "ERROR")

        # 6) كتابة
        try:
            self.d.clear_text()
        except Exception:
            pass
        self._type_via_adb(text)

        # 7) فحص تلوّث URL bar — لو النص ظهر هناك، اعتبر الكتابة فشلت
        if self._check_url_bar_contamination(text):
            self.log(
                f"⛔ كشفت تلوّث URL bar: النص ظهر في الشريط بدل الحقل!\n"
                f"   URL bar text: '{self._get_url_bar_text()}'\n"
                f"   محاولة مسحه وإلغاء الكتابة",
                "ERROR",
            )
            # امسح URL bar من النص الملوّث
            try:
                el_url = self.d(resourceIdMatches=".*url_bar.*")
                if el_url.exists(timeout=0.3):
                    el_url.clear_text()
            except Exception:
                pass
            self._force_defocus_url_bar()
            return False

        self.log(f"تم إدخال النص في حقل الويب ({source}): {text}", "TASK")
        return True

    # ---------------- SESSION WARM-UP (إحماء قبل سحب الكوكيز) ---------------- #

    def _warm_up_session(self):
        """
        بعد تسجيل الدخول الناجح: نتفاعل مع X لتثبيت كل الكوكيز.
        تويتر يضع كوكيز مثل ct0, twid, kdt فقط بعد:
          - فتح home page
          - تنفيذ JavaScript (تايم لاين، notifications, ...)
          - تفاعل بسيط (تمرير، نقر آمن)
          - تحديث الصفحة
        بدون هذي الخطوات الكوكيز ناقصة وتسجيل الدخول في موج راح يفشل.
        """
        self.log("🍪 إحماء الجلسة لتثبيت كل الكوكيز...", "TASK")

        # ── ١) فتح الصفحة الرئيسية ──
        self.log("الانتقال للصفحة الرئيسية x.com/home ...", "PROGRESS")
        self.open_url_in_chrome("https://x.com/home")
        time.sleep(5)
        self._force_defocus_url_bar()

        # ── ٢) انتظار تحميل home (تايم لاين، تبويبات، ...) ──
        home_loaded = False
        home_hints = (
            "For you", "Following", "Home", "Latest",
            "What's happening", "What is happening",
            "Trending", "Notifications",
            "الرئيسية", "متابَعون", "لك",
        )
        end = time.time() + 20
        while time.time() < end:
            for hint in home_hints:
                if self.u2_exists(textContains=hint, timeout=0.3):
                    home_loaded = True
                    self.log(f"✅ صفحة home محمّلة (وُجد {hint!r})", "SUCCESS")
                    break
            if home_loaded:
                break
            time.sleep(0.5)

        if not home_loaded:
            self.log("⚠️ ما تأكدت من تحميل home — قد تكون الكوكيز ناقصة لكن نواصل", "ERROR")

        # وقت إضافي لـ JS لإنتاج كوكيز الجلسة (ct0 خصوصاً)
        time.sleep(3)

        # ── ٣) تمرير الصفحة لتفعيل JS handlers ──
        try:
            w, h = self.d.window_size()
            self.log("تمرير الصفحة لتفعيل JS (تايم لاين/تحليلات)...", "PROGRESS")
            for _ in range(3):
                self.d.swipe(w // 2, int(h * 0.75), w // 2, int(h * 0.25), duration=0.4)
                time.sleep(1.2)
            # رجوع لأعلى
            self.d.swipe(w // 2, int(h * 0.25), w // 2, int(h * 0.75), duration=0.4)
            time.sleep(2)
        except Exception as e:
            self.log(f"فشل التمرير (غير حرج): {e}", "INFO")

        # ── ٤) فتح صفحة الإعدادات الجانبية (يفعّل كوكيز إضافية) ──
        try:
            self.log("فتح صفحة notifications لتفعيل كوكيز إضافية...", "PROGRESS")
            self.open_url_in_chrome("https://x.com/notifications")
            time.sleep(4)
            self._force_defocus_url_bar()
        except Exception:
            pass

        # ── ٥) تحديث الصفحة الرئيسية (يثبّت الكوكيز الدائمة) ──
        self.log("تحديث home لتثبيت الكوكيز الدائمة...", "PROGRESS")
        self.open_url_in_chrome("https://x.com/home")
        time.sleep(5)
        self._force_defocus_url_bar()

        # تمرير أخير + انتظار ليستقر كل شي
        try:
            w, h = self.d.window_size()
            self.d.swipe(w // 2, int(h * 0.7), w // 2, int(h * 0.3), duration=0.4)
            time.sleep(1.5)
        except Exception:
            pass

        time.sleep(4)
        self.log("✅ إحماء الجلسة انتهى — الكوكيز جاهزة للسحب", "SUCCESS")

    # ---------------- TWITTER LOGIN FLOW ---------------- #

    def handle_chrome_first_run(self):
        """التعامل مع نوافذ Chrome الأولى (ترحيب + خصوصية)."""
        self.log("التعامل مع نوافذ Chrome الأولى...", "CHROME")

        # 1) "Use without an account" أو "Accept & continue"
        self.u2_click(text="Use without an account", timeout=15) or \
        self.u2_click(textContains="Accept", timeout=5) or \
        self.u2_click(textContains="قبول", timeout=3)

        # 2) "Got it" (صفحة Enhanced ad privacy)
        self.u2_click(text="Got it", timeout=15) or \
        self.u2_click(textContains="Got it", timeout=5) or \
        self.u2_click(textContains="حسنًا", timeout=3)

        self.log("تم التعامل مع نوافذ Chrome", "SUCCESS")

    def login_twitter_and_save_cookies(self, username, password, email=""):
        self._current_account = username
        self.log(f"بدء عملية تسجيل الدخول إلى تويتر للحساب: {username}", "TASK")

        # التعامل مع نوافذ Chrome الأولى
        self.handle_chrome_first_run()

        # فتح صفحة تسجيل الدخول
        self.open_url_in_chrome("https://x.com/login")
        self.log("انتظار تحميل صفحة تسجيل الدخول...", "PROGRESS")

        # نمهل ثانيتين لـ Chrome ثم نتأكد من عدم وجود dropdown autocomplete
        time.sleep(2)
        if self._is_url_bar_autocomplete_open():
            self.log("⚠️ Chrome فتح في وضع البحث — إغلاق الـ autocomplete", "PROGRESS")
            self._force_defocus_url_bar()

        # ننتظر حتى تظهر صفحة تويتر فعلياً (نص مميز للصفحة) + URL يحتوي x.com
        page_loaded = self._wait_x_page_loaded(timeout=30)
        if not page_loaded:
            self.log("⚠️ صفحة تويتر لم تحمل بالكامل بعد 30 ثانية — محاولة إعادة فتح الرابط", "ERROR")
            # محاولة إعادة فتح الرابط
            self._force_defocus_url_bar()
            self.open_url_in_chrome("https://x.com/login")
            time.sleep(3)
            self._force_defocus_url_bar()
            page_loaded = self._wait_x_page_loaded(timeout=15)
            if not page_loaded:
                self.log("⛔ فشل تحميل صفحة X بعد محاولتين — إلغاء العملية", "ERROR")
                return False
        self.log("✅ صفحة X محمّلة وجاهزة للإدخال", "SUCCESS")

        # ===== إدخال اسم المستخدم =====
        self.log("إدخال اسم المستخدم...", "TASK")
        # إدخال موثوق: يستبعد شريط عنوان Chrome ويتحقق من التركيز قبل الكتابة
        username_entered = self.enter_web_field(
            username,
            hints=[
                "Email or username",
                "Phone, email, or username",
                "Phone, email address, or username",
                "email or username",
                "رقم الهاتف أو البريد",
                "اسم المستخدم",
            ],
            timeout=15,
        )
        if not username_entered:
            self.log("لم يتم العثور على حقل اسم المستخدم!", "ERROR")
            return False

        # زر المتابعة بعد اسم المستخدم: Next / Continue / التالي / متابعة
        # (صفحة onboarding الحديثة قد تستخدم Continue بدل Next)
        self.u2_click(text="Next", timeout=10) or \
        self.u2_click(text="Continue", timeout=5) or \
        self.u2_click(textContains="Next", timeout=3) or \
        self.u2_click(textContains="Continue", timeout=3) or \
        self.u2_click(textContains="التالي", timeout=3) or \
        self.u2_click(textContains="متابعة", timeout=3) or \
        self.d.press("enter")

        # ===== فحص: هل يطلب إيميل/هاتف للتحقق أم ينتقل للباسورد؟ =====
        self.log("انتظار الصفحة التالية...", "PROGRESS")

        # ننتظر أي من الحالتين: صفحة التحقق أو صفحة الباسورد
        verification_needed = False
        for _ in range(20):  # أقصى حد 20 ثانية
            if self.u2_exists(textContains="Enter your phone number or email", timeout=0.5) or \
               self.u2_exists(textContains="Enter your email", timeout=0.3) or \
               self.u2_exists(textContains="phone number or email", timeout=0.3) or \
               self.u2_exists(textContains="أدخل رقم الهاتف أو البريد", timeout=0.3):
                verification_needed = True
                break
            if self.u2_exists(textContains="Enter your password", timeout=0.5) or \
               self.u2_exists(textContains="Password", timeout=0.3):
                break
            time.sleep(0.5)

        if verification_needed:
            self.log("⚠️ تويتر يطلب التحقق بالإيميل/الهاتف!", "TASK")

            if not email:
                self.log("لم يتم تحديد إيميل للتحقق! أضف email في الإعدادات", "ERROR")
                return False

            self.enter_web_field(
                email,
                hints=[
                    "Enter your phone number or email",
                    "Enter your email",
                    "phone number or email",
                    "أدخل رقم الهاتف أو البريد",
                ],
                timeout=15,
            )

            # زر المتابعة بعد إيميل التحقق
            self.u2_click(text="Next", timeout=10) or \
            self.u2_click(text="Continue", timeout=5) or \
            self.u2_click(textContains="Next", timeout=3) or \
            self.u2_click(textContains="Continue", timeout=3) or \
            self.u2_click(textContains="التالي", timeout=3) or \
            self.u2_click(textContains="متابعة", timeout=3) or \
            self.d.press("enter")

            self.log("تم إدخال الإيميل للتحقق", "SUCCESS")
        else:
            self.log("لم يُطلب التحقق — الانتقال للباسورد مباشرة", "INFO")

        # ===== إدخال كلمة المرور (ينتظر حتى يظهر الحقل) =====
        self.log("إدخال كلمة المرور...", "TASK")

        password_entered = self.enter_web_field(
            password,
            hints=["Password", "كلمة المرور", "كلمة السر"],
            timeout=15,
        )
        if not password_entered:
            self.log("لم يتم العثور على حقل كلمة المرور!", "ERROR")
            return False

        # زر Log in / تسجيل الدخول
        self.u2_click(text="Log in", timeout=10) or \
        self.u2_click(textContains="Log in", timeout=5) or \
        self.u2_click(textContains="تسجيل الدخول", timeout=3) or \
        self.d.press("enter")

        self.log("تم الضغط على زر تسجيل الدخول، انتظار تحميل الحساب...", "TASK")

        # ننتظر حتى تختفي صفحة Login أو يظهر خطأ (أقصى 30 ثانية)
        for _ in range(30):
            if self.u2_exists(textContains="Wrong password", timeout=0.5) or \
               self.u2_exists(textContains="كلمة المرور غير صحيحة", timeout=0.3):
                self.log("كلمة المرور خاطئة!", "ERROR")
                return False
            # إذا اختفى زر Log in يعني الصفحة تغيرت = نجاح
            if not self.u2_exists(text="Log in", timeout=0.5):
                break
            time.sleep(1)

        # ─── إحماء الجلسة: نتفاعل مع الصفحة الرئيسية عشان نضمن كل الكوكيز ───
        # تويتر يضع كوكيز مثل ct0/twid/kdt فقط بعد التفاعل مع home page
        self._warm_up_session()

        cookies_ok = self.save_cookies_to_pc()
        if cookies_ok:
            self.log("تم تسجيل الدخول وحفظ الكوكيز وتحويلها لـ Playwright بنجاح!", "SUCCESS")
        else:
            self.log("تم تسجيل الدخول لكن فشل حفظ أو تحويل الكوكيز!", "ERROR")
        return cookies_ok

    # ---------------- PLAYWRIGHT LAUNCH ---------------- #

    def open_x_with_playwright(self):
        """
        فتح X (تويتر) باستخدام Playwright والكوكيز المحفوظة.
        """
        if not self.playwright_cookies_path:
            self.log("لا يوجد مسار لملف كوكيز Playwright - لم يتم توليده بعد", "ERROR")
            return False

        if sync_playwright is None:
            self.log(
                "لم يتم تثبيت Playwright في بيئة بايثون. نفّذ:\n"
                "pip install playwright\n"
                "playwright install",
                "ERROR",
            )
            return False

        self.log("تشغيل Playwright واستخدام الكوكيز للدخول على X...", "PLAY")

        try:
            with open(self.playwright_cookies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # الصيغة الجديدة: {"cookies": [...], "origins": []}
            # الصيغة القديمة (legacy): [...]
            if isinstance(data, dict) and "cookies" in data:
                cookies = data["cookies"]
            elif isinstance(data, list):
                cookies = data
            else:
                self.log("⚠️ صيغة ملف الكوكيز غير معروفة", "ERROR")
                return False
        except Exception as e:
            self.log(f"فشل قراءة ملف الكوكيز الخاص بـ Playwright: {e}", "ERROR")
            return False

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                context.add_cookies(cookies)
                page = context.new_page()
                page.goto("https://x.com/home")
                self.log("تم فتح https://x.com/home باستخدام الكوكيز", "SUCCESS")
                page.wait_for_timeout(15000)  # 15 ثانية مشاهدة
            return True
        except Exception as e:
            self.log(f"فشل تشغيل Playwright أو فتح X: {e}", "ERROR")
            return False

    # ---------------- MAIN FLOW ---------------- #

    def comprehensive_chrome_opening(self, username, password, email=""):
        self.log("بدء فتح Chrome الشامل وتسجيل الدخول...", "PROGRESS")

        if not self.force_open_chrome_with_ldplayer():
            self.log(
                "تعذر فتح Chrome تلقائياً عبر LDPlayer - افتحه يدوياً ثم أعد المحاولة",
                "ERROR",
            )
            return False

        return self.login_twitter_and_save_cookies(username, password, email)

    def run_automation_with_chrome_focus(self, username, password, email=""):
        self.log("LDPlayer Chrome Automation (With ADB + uiautomator2)", "CHROME")
        self.log(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log(f"الحساب: {username}", "TASK")

        try:
            self.auto_setup_adb()
            self.cleanup_processes()

            emulator_index = self.auto_create_emulator()
            if not emulator_index:
                self.log("فشل إنشاء المحاكي", "ERROR")
                return False

            if not self.auto_launch_emulator(emulator_index):
                self.log("فشل تشغيل المحاكي", "ERROR")
                return False

            if not self.quick_adb_connect():
                self.log(
                    "فشل اتصال ADB بالمحاكي - تأكد من تفعيل USB Debugging داخل أندرويد",
                    "ERROR",
                )
                return False

            # الاتصال بـ uiautomator2
            if not self.connect_u2():
                self.log("فشل الاتصال بـ uiautomator2 - لا يمكن المتابعة", "ERROR")
                return False

            chrome_login_success = self.comprehensive_chrome_opening(
                username, password, email
            )

            if chrome_login_success:
                self.log("تم تسجيل الدخول وحفظ الكوكيز بنجاح!", "SUCCESS")
            else:
                self.log("فشل تسجيل الدخول أو حفظ الكوكيز", "ERROR")

            # إغلاق المحاكي بعد 3 ثواني
            time.sleep(3)
            self.close_emulator()

            return chrome_login_success

        except KeyboardInterrupt:
            self.log("تم إيقاف العملية يدويًا", "ERROR")
            self.close_emulator()
            return False
        except Exception as e:
            self.log(f"خطأ: {e}", "ERROR")
            self.close_emulator()
            return False

    def close_emulator(self):
        """إغلاق المحاكي بالكامل."""
        try:
            if self.emulator_index:
                self.log("إغلاق المحاكي...", "PROGRESS")
                subprocess.run(
                    [self.ldconsole, "quit", "--index", self.emulator_index],
                    capture_output=True, timeout=15
                )
                self.log("تم إغلاق المحاكي", "SUCCESS")
        except Exception as e:
            self.log(f"خطأ أثناء إغلاق المحاكي: {e}", "ERROR")


# ---------------- ENTRY POINT ---------------- #

def load_accounts(csv_path):
    """قراءة الحسابات من ملف CSV."""
    accounts = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append({
                "username": row["username"].strip(),
                "password": row["password"].strip(),
                "email": row.get("email", "").strip(),
            })
    return accounts


def main():
    print("🌐 LDPlayer Chrome Automation")
    print("=" * 35)

    # قراءة الحسابات من ملف CSV
    csv_path = r"C:\Users\pc\Desktop\accounts.csv"
    accounts = load_accounts(csv_path)
    print(f"📊 عدد الحسابات: {len(accounts)}")

    results = []
    for i, acc in enumerate(accounts, 1):
        print(f"\n{'='*60}")
        print(f"👤 الحساب {i}/{len(accounts)}: {acc['username']}")
        print(f"{'='*60}")

        automation = LDPlayerChromeAutomation()
        success = automation.run_automation_with_chrome_focus(
            acc["username"], acc["password"], acc["email"]
        )
        results.append({"username": acc["username"], "success": success})

    # ملخص النتائج
    print(f"\n{'='*60}")
    print("📊 ملخص النتائج:")
    print(f"{'='*60}")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['username']}")
    success_count = sum(1 for r in results if r["success"])
    print(f"\n✅ نجح: {success_count}/{len(results)}")
    print(f"❌ فشل: {len(results) - success_count}/{len(results)}")


if __name__ == "__main__":
    main()
