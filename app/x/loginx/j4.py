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

    def __init__(self, log_callback=None, headless=False):

        # مسار ldconsole حسب تثبيت LDPlayer عندك

        self.ldconsole = r"D:\LDPlayer\LDPlayer9\ldconsole.exe"

        self.adb_path = None

        self.emulator_index = None

        self.playwright_cookies_path = None  # مسار ملف الكوكيز الخاص ببلاي رايت (بعد التحويل)

        self.d = None  # uiautomator2 device

        self.device_serial = None  # سيريال الجهاز المتصل عبر ADB

        self._current_account = ""  # اسم الحساب الحالي

        self._log_callback = log_callback  # callback لإرسال اللوقات للواجهة

        self.headless = headless  # تشغيل المحاكي مخفي (بدون واجهة)



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

        try:

            subprocess.run([self.adb_path, "start-server"], capture_output=True, timeout=10)

        except subprocess.TimeoutExpired:

            self.log("adb start-server علّق - قتل العملية", "ERROR")

            try:

                subprocess.run([self.adb_path, "kill-server"], capture_output=True, timeout=5)

            except Exception:

                pass



        # 1️⃣ نفحص الأجهزة الحالية

        try:

            devices = subprocess.run(

                [self.adb_path, "devices"], capture_output=True, text=True, timeout=10

            )

        except subprocess.TimeoutExpired:

            self.log("adb devices علّق", "ERROR")

            return False

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

            try:

                result = subprocess.run(

                    [self.adb_path, "connect", addr],

                    capture_output=True,

                    text=True,

                    timeout=10,

                )

            except subprocess.TimeoutExpired:

                self.log(f"adb connect {addr} علّق - تخطّي", "INFO")

                continue

            out = (result.stdout + result.stderr).strip()

            self.log(f"نتيجة adb connect {addr}: {out}", "INFO")



            if "connected" in out.lower() or "already connected" in out.lower():

                try:

                    devices = subprocess.run(

                        [self.adb_path, "devices"],

                        capture_output=True,

                        text=True,

                        timeout=10,

                    )

                except subprocess.TimeoutExpired:

                    continue

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

        killed = 0

        # نجمع PIDs أولاً ثم نقتل، لتحرير handles psutil بسرعة

        targets = []

        for proc in psutil.process_iter(["pid", "name"]):

            try:

                if proc.info["name"] in processes_to_kill:

                    targets.append(proc)

            except Exception:

                pass

        for proc in targets:

            try:

                proc.kill()

                killed += 1

            except Exception:

                pass

        # تحرير صريح لكل الـ Process objects + handles

        del targets

        try:

            import gc

            gc.collect()

        except Exception:

            pass

        self.log(f"تم قتل {killed} عمليات", "INFO")

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



        # حذف أي محاكيات سابقة بالكامل (quit ثم remove)

        emulators = self.get_emulators()

        for index, name in emulators:

            self.log(f"إيقاف محاكي قديم index={index} ({name})...", "PROGRESS")

            subprocess.run(

                [self.ldconsole, "quit", "--index", index],

                capture_output=True, timeout=15,

            )

            time.sleep(1)



        # تأكد من إغلاق كل عمليات LDPlayer قبل remove (مهم: المحاكي ما يقدر يُحذف وهو شغّال)

        self.cleanup_processes()

        time.sleep(2)



        for index, name in emulators:

            self.log(f"حذف محاكي قديم index={index} ({name}) نهائياً...", "PROGRESS")

            subprocess.run(

                [self.ldconsole, "remove", "--index", index],

                capture_output=True, timeout=15,

            )

            time.sleep(1)



        # محاولة ثانية لو بقي شي

        remaining = self.get_emulators()

        if remaining:

            self.log(f"تبقّى {len(remaining)} محاكي بعد التنظيف — إعادة المحاولة...", "INFO")

            self.cleanup_processes()

            time.sleep(2)

            for index, name in remaining:

                subprocess.run([self.ldconsole, "quit", "--index", index], capture_output=True, timeout=10)

                time.sleep(0.5)

                subprocess.run([self.ldconsole, "remove", "--index", index], capture_output=True, timeout=10)

            time.sleep(2)



        # snapshot قبل add لمعرفة الـ index الجديد بدقة

        before_indexes = {e[0] for e in self.get_emulators()}

        self.log(f"محاكيات موجودة قبل add: {before_indexes if before_indexes else 'لا شيء'}", "INFO")



        # إضافة محاكي جديد

        result = subprocess.run(

            [self.ldconsole, "add"],

            capture_output=True,

            text=True,

            timeout=60,

        )

        if result.returncode != 0:

            self.log(f"فشل إنشاء المحاكي: {result.stdout} {result.stderr}", "ERROR")

            return None



        time.sleep(5)



        # حدّد الـ index الجديد عن طريق الـ diff (ضمان أننا نأخذ الجديد فقط)

        after = self.get_emulators()

        new_emulators = [e for e in after if e[0] not in before_indexes]



        if new_emulators:

            new_index = new_emulators[0][0]

            self.log(f"✅ تم إنشاء محاكي جديد index={new_index}", "SUCCESS")

        elif after:

            # fallback: استخدم آخر واحد في القائمة (الأحدث عادةً)

            new_index = after[-1][0]

            self.log(f"⚠️ لم أميّز الجديد بالـ diff، استخدام آخر واحد index={new_index}", "INFO")

        else:

            self.log("لم يتم إنشاء المحاكي - القائمة فارغة", "ERROR")

            return None



        self.emulator_index = new_index

        self.auto_configure_emulator(new_index)

        return new_index



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

        if self.headless:

            self.log("تشغيل المحاكي في وضع مخفي (headless)...", "PROGRESS")

            result = subprocess.run(

                [self.ldconsole, "launchex", "--index", index, "--headless"],

                capture_output=True,

            )

        else:

            self.log("تشغيل المحاكي...", "PROGRESS")

            result = subprocess.run(

                [self.ldconsole, "launch", "--index", index],

                capture_output=True,

            )

        if result.returncode != 0:

            self.log("فشل تشغيل المحاكي", "ERROR")

            return False



        mode = "مخفي" if self.headless else "عادي"

        self.log(f"تم تشغيل المحاكي ({mode}) - انتظار الجاهزية...", "SUCCESS")



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

        try:

            subprocess.run(cmd, capture_output=True, timeout=15)

        except (OSError, subprocess.SubprocessError) as e:

            self.log(f"خطأ subprocess على tap: {e} — إعادة تشغيل adb وإعادة المحاولة", "ERROR")

            try:

                subprocess.run([self.adb_path, "kill-server"], capture_output=True, timeout=10)

                time.sleep(2)

                subprocess.run([self.adb_path, "start-server"], capture_output=True, timeout=10)

                time.sleep(2)

                self.quick_adb_connect()

                subprocess.run(cmd, capture_output=True, timeout=15)

            except Exception as e2:

                self.log(f"فشل tap بعد restart adb: {e2}", "ERROR")

                return False

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

        # محاولتان: لو الأولى ترجع OSError [Errno 22] نعيد تشغيل adb ونحاول

        for attempt in (1, 2):

            try:

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:

                    self.log(f"تم فتح الرابط: {url}", "SUCCESS")

                    time.sleep(5)

                    return True

                else:

                    self.log(f"فشل فتح الرابط (محاولة {attempt}): {result.stdout} {result.stderr}", "ERROR")

                    if attempt == 1:

                        time.sleep(2)

                        continue

                    time.sleep(3)

                    return False

            except (OSError, subprocess.SubprocessError) as e:

                self.log(f"خطأ subprocess على فتح الرابط (محاولة {attempt}): {e}", "ERROR")

                if attempt == 1:

                    # restart adb server وأعد المحاولة

                    try:

                        subprocess.run([self.adb_path, "kill-server"], capture_output=True, timeout=10)

                        time.sleep(2)

                        subprocess.run([self.adb_path, "start-server"], capture_output=True, timeout=10)

                        time.sleep(2)

                        self.quick_adb_connect()

                    except Exception as e2:

                        self.log(f"فشل restart adb: {e2}", "ERROR")

                    continue

                return False

        return False



    def input_text(self, text):

        if not self.adb_path or not self.quick_adb_connect():

            self.log("ADB غير مضبوط، لا يمكن إدخال النص", "ERROR")

            return False



        safe_text = text.replace(" ", "%s")

        cmd = [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_text]

        try:

            subprocess.run(cmd, capture_output=True, timeout=15)

        except (OSError, subprocess.SubprocessError) as e:

            self.log(f"خطأ subprocess على input_text: {e} — restart adb", "ERROR")

            try:

                subprocess.run([self.adb_path, "kill-server"], capture_output=True, timeout=10)

                time.sleep(2)

                subprocess.run([self.adb_path, "start-server"], capture_output=True, timeout=10)

                time.sleep(2)

                self.quick_adb_connect()

                subprocess.run(cmd, capture_output=True, timeout=15)

            except Exception as e2:

                self.log(f"فشل input_text بعد restart adb: {e2}", "ERROR")

                return False

        self.log(f"تم إدخال النص: {text}", "TASK")



        time.sleep(3)

        return True



    # ---------------- COOKIES: CONVERT & SAVE ---------------- #



    def convert_cookies_to_playwright(self, cookies_file_path, account_name=""):

        """

        يفتح ملف ChromeCookies (SQLite) ويحوّله لملف بصيغة Playwright storage_state.

        الناتج: CookiesBackup/{account_name}.json بصيغة {"cookies": [...], "origins": []}

        """

        try:

            if not os.path.exists(cookies_file_path):

                self.log(f"ملف الكوكيز غير موجود للتحويل: {cookies_file_path}", "ERROR")

                return None



            self.log("بدء تحويل ملف الكوكيز لصيغة Playwright storage_state...", "PROGRESS")



            conn = sqlite3.connect(cookies_file_path)

            cursor = conn.cursor()

            cursor.execute(

                "SELECT host_key, name, value, path, is_secure, is_httponly, expires_utc FROM cookies"

            )

            rows = cursor.fetchall()

            conn.close()



            HTTP_ONLY_NAMES = {'auth_token', 'kdt', '_twitter_sess', '__cf_bm', 'auth_multi'}

            LAX_COOKIES = {'ct0', 'auth_multi'}

            playwright_cookies = []



            for host_key, name, value, path, is_secure, is_httponly, expires_utc in rows:

                if not value:

                    continue



                # نفك ترميز URL لو فيه

                try:

                    decoded_value = urllib.parse.unquote(value)

                except Exception:

                    decoded_value = value



                # نحصرها فقط في تويتر/X

                if "x.com" not in host_key and "twitter.com" not in host_key:

                    continue



                # حساب expires بالثواني (Chrome يخزنها بالميكروثانية من 1601)

                if expires_utc and expires_utc > 0:

                    # Chrome epoch: 1601-01-01, Unix epoch: 1970-01-01

                    # الفرق = 11644473600 ثانية

                    expires = (expires_utc / 1000000) - 11644473600

                    if expires < time.time():

                        expires = time.time() + 365 * 24 * 3600

                else:

                    expires = time.time() + 365 * 24 * 3600



                # تحديد sameSite

                same_site = 'None'

                if name in LAX_COOKIES:

                    same_site = 'Lax'



                cookie_obj = {

                    "name": name,

                    "value": decoded_value,

                    "domain": host_key,

                    "path": path if path else "/",

                    "expires": float(expires),

                    "secure": bool(is_secure),

                    "httpOnly": bool(is_httponly) or name in HTTP_ONLY_NAMES,

                    "sameSite": same_site,

                }



                playwright_cookies.append(cookie_obj)



            if not playwright_cookies:

                self.log("لم يتم العثور على أي كوكيز لتويتر/X في الملف", "ERROR")

                return None



            # حفظ بصيغة Playwright storage_state

            storage_state = {"cookies": playwright_cookies, "origins": []}



            out_dir = os.path.dirname(cookies_file_path)

            filename = f"{account_name}.json" if account_name else "playwright_cookies.json"

            out_path = os.path.join(out_dir, filename)



            with open(out_path, "w", encoding="utf-8") as f:

                json.dump(storage_state, f, ensure_ascii=False, indent=2)



            self.log(f"✅ تم حفظ كوكيز Playwright ({len(playwright_cookies)} كوكيز): {out_path}", "SUCCESS")



            try:

                important = {}

                for c in playwright_cookies:

                    if c["name"] in ("auth_token", "ct0", "kdt", "twid"):

                        important[c["name"]] = c["value"][:20] + "..."

                if important:

                    self.log(

                        f"كوكيز تويتر المهمة: {list(important.keys())}",

                        "INFO",

                    )

            except Exception:

                pass



            return out_path



        except Exception as e:

            self.log(f"فشل تحويل الكوكيز لصيغة Playwright: {e}", "ERROR")

            import traceback

            traceback.print_exc()

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

        if not self.adb_path:

            self.log("adb_path غير مضبوط، لا يمكن حفظ الكوكيز", "ERROR")

            return False



        # تجديد اتصال ADB قبل العملية (مهم بعد طول وقت تسجيل الدخول)

        self.log("تجديد اتصال ADB قبل حفظ الكوكيز...", "PROGRESS")

        if not self.quick_adb_connect():

            self.log("فشل تجديد اتصال ADB قبل حفظ الكوكيز", "ERROR")

            return False



        # استخدام مسار ثابت بجانب ملف j4.py (وليس CWD المتغير)

        local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CookiesBackup")

        if not os.path.exists(local_dir):

            os.makedirs(local_dir)



        # حذف ملف ChromeCookies القديم إن وجد لتجنب التعارض

        old_cookies = os.path.join(local_dir, "ChromeCookies")

        if os.path.exists(old_cookies):

            try:

                os.remove(old_cookies)

            except Exception:

                pass



        self.log("محاولة نسخ ملف الكوكيز من المحاكي إلى /sdcard...", "PROGRESS")



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

                "exit\n"

            )



            out, err = proc.communicate(script, timeout=30)

            self.log(f"خروج adb shell:\nSTDOUT:\n{out}\nSTDERR:\n{err}", "INFO")



        except subprocess.TimeoutExpired:

            self.log("انتهى وقت الانتظار أثناء تنفيذ أوامر su/cp داخل adb shell", "ERROR")

            try:

                proc.kill()

            except Exception:

                pass

            return False

        except Exception as e:

            self.log(f"خطأ أثناء تنفيذ أوامر su/cp داخل adb shell: {e}", "ERROR")

            return False



        # سحب الملف من المحاكي

        self.log("سحب ملف الكوكيز من المحاكي...", "PROGRESS")

        try:

            pull_cmd = [self.adb_path, "-s", self.device_serial, "pull", "/sdcard/ChromeCookies", local_dir]

            result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=30)

            out = (result.stdout + " " + result.stderr).strip()

            if result.returncode != 0:

                self.log(f"فشل سحب ملف الكوكيز من /sdcard: {out}", "ERROR")

                return False

        except subprocess.TimeoutExpired:

            self.log("انتهى وقت الانتظار أثناء سحب ملف الكوكيز", "ERROR")

            return False

        except Exception as e:

            self.log(f"خطأ أثناء سحب ملف الكوكيز: {e}", "ERROR")

            return False



        self.log(f"✅ تم حفظ ملف الكوكيز في: {local_dir}", "SUCCESS")



        cookies_file_path = os.path.join(local_dir, "ChromeCookies")

        if not os.path.exists(cookies_file_path):

            self.log("تنبيه: لم أجد ملف ChromeCookies بعد السحب", "ERROR")

            return False



        # تحويله لصيغة Playwright (ملف نصّي JSON)

        out_path = self.convert_cookies_to_playwright(cookies_file_path, self._current_account)

        if not out_path:

            return False



        self.playwright_cookies_path = out_path

        return True



    # ---------------- UIAUTOMATOR2 CONNECTION ---------------- #



    def connect_u2(self):

        """الاتصال بالمحاكي عبر uiautomator2 باستخدام السيريال المكتشف."""

        self.log("الاتصال بـ uiautomator2...", "PROGRESS")

        

        # نستخدم السيريال المكتشف من quick_adb_connect

        targets = []

        if self.device_serial:

            targets.append(self.device_serial)

        # المنافذ الشائعة كاحتياط

        targets += ["127.0.0.1:5555", "127.0.0.1:5554", "127.0.0.1:5557", "emulator-5554"]

        

        for target in targets:

            try:

                self.log(f"محاولة الاتصال بـ u2 على: {target}", "INFO")

                self.d = u2.connect(target)

                info = self.d.info

                self.log(f"تم الاتصال بـ u2 على {target}: {info.get('productName', '?')}", "SUCCESS")

                return True

            except Exception as e:

                self.log(f"فشل u2 على {target}: {e}", "INFO")

                continue

        

        self.log("فشل الاتصال بـ uiautomator2 على جميع المنافذ", "ERROR")

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



    # ---------------- TWITTER LOGIN FLOW ---------------- #



    def handle_chrome_first_run(self):

        """التعامل مع نوافذ Chrome الأولى (ترحيب + خصوصية + إشعارات)."""

        self.log("التعامل مع نوافذ Chrome الأولى...", "CHROME")



        # 1) "Use without an account" أو "Accept & continue"

        self.u2_click(text="Use without an account", timeout=15) or \
        self.u2_click(textContains="Accept", timeout=5) or \
        self.u2_click(textContains="قبول", timeout=3)



        # 2) "Got it" (صفحة Enhanced ad privacy)

        self.u2_click(text="Got it", timeout=15) or \
        self.u2_click(textContains="Got it", timeout=5) or \
        self.u2_click(textContains="حسنًا", timeout=3)



        # 3) إغلاق أي نوافذ إشعارات أو طلبات إضافية

        self.u2_click(textContains="No thanks", timeout=3)

        self.u2_click(textContains="Not now", timeout=3)

        self.u2_click(textContains="لاحقاً", timeout=2)

        self.u2_click(textContains="Block", timeout=2)



        self.log("تم التعامل مع نوافذ Chrome", "SUCCESS")



    def login_twitter_and_save_cookies(self, username, password, email=""):

        self._current_account = username

        self.log(f"بدء عملية تسجيل الدخول إلى تويتر للحساب: {username}", "TASK")



        # التعامل مع نوافذ Chrome الأولى

        self.handle_chrome_first_run()



        # فتح صفحة تسجيل الدخول

        self.open_url_in_chrome("https://x.com/login")

        self.log("انتظار تحميل صفحة تسجيل الدخول...", "PROGRESS")



        # ننتظر حتى تظهر صفحة تويتر فعلياً (نص مميز للصفحة)

        page_loaded = False

        for _ in range(60):  # أقصى 30 ثانية

            if self.u2_exists(textContains="Sign in to X", timeout=0.3) or \
               self.u2_exists(textContains="Phone, email, or username", timeout=0.3) or \
               self.u2_exists(textContains="تسجيل الدخول إلى", timeout=0.3):

                page_loaded = True

                break

            time.sleep(0.5)



        if not page_loaded:

            self.log("صفحة تويتر لم تحمل بالكامل — محاولة المتابعة...", "INFO")



        # ===== إدخال اسم المستخدم =====

        self.log("إدخال اسم المستخدم...", "TASK")

        # ننقر على الحقل الصحيح (الثاني — الأول هو شريط Chrome)

        username_entered = False

        # محاولة 1: حقل فيه نص placeholder خاص بتويتر

        username_entered = self.u2_set_text(username, textContains="Phone, email, or username", timeout=5)

        # محاولة 2: ثاني EditText (الأول = شريط عنوان Chrome)

        if not username_entered:

            try:

                el = self.d(className="android.widget.EditText", instance=1)

                if el.wait(timeout=10):

                    el.click()

                    time.sleep(0.3)

                    self.d.clear_text()

                    safe_user = username.replace(" ", "%s")

                    subprocess.run(

                        [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_user],

                        capture_output=True

                    )

                    username_entered = True

                    self.log("تم إدخال اسم المستخدم (EditText instance=1)", "TASK")

            except Exception:

                pass

        if not username_entered:

            self.log("لم يتم العثور على حقل اسم المستخدم!", "ERROR")

            return False



        # إغلاق أي اقتراحات autocomplete من Chrome

        self.d.press("back")

        time.sleep(0.5)



        # زر Next / التالي

        self.log("الضغط على زر Next...", "TASK")

        next_clicked = (

            self.u2_click(text="Next", timeout=10) or

            self.u2_click(textContains="Next", timeout=5) or

            self.u2_click(textContains="التالي", timeout=5) or

            self.u2_click(text="تالي", timeout=3)

        )

        if not next_clicked:

            self.log("لم يُعثر على زر Next — محاولة Enter...", "INFO")

            self.d.press("enter")

            time.sleep(2)

            # محاولة ثانية بعد Enter

            self.u2_click(text="Next", timeout=5) or \
            self.u2_click(textContains="Next", timeout=3)



        # ===== فحص: هل يطلب إيميل/هاتف للتحقق أم ينتقل للباسورد؟ =====

        self.log("انتظار الصفحة التالية...", "PROGRESS")

        time.sleep(4)  # انتظار تحميل الصفحة بعد Next



        # ننتظر أي من الحالتين: صفحة التحقق أو صفحة الباسورد

        verification_needed = False

        for _ in range(30):  # أقصى حد 30 ثانية

            if self.u2_exists(textContains="Enter your phone number or email", timeout=0.5) or \
               self.u2_exists(textContains="Enter your email", timeout=0.3) or \
               self.u2_exists(textContains="phone number or email", timeout=0.3) or \
               self.u2_exists(textContains="أدخل رقم الهاتف أو البريد", timeout=0.3) or \
               self.u2_exists(textContains="أدخل رقم هاتفك أو بريدك", timeout=0.3):

                verification_needed = True

                break

            if self.u2_exists(textContains="Enter your password", timeout=0.5) or \
               self.u2_exists(textContains="Password", timeout=0.3) or \
               self.u2_exists(textContains="password", timeout=0.3) or \
               self.u2_exists(textContains="كلمة المرور", timeout=0.3) or \
               self.u2_exists(textContains="كلمة السر", timeout=0.3):

                break

            time.sleep(1)



        if verification_needed:

            self.log("⚠️ تويتر يطلب التحقق بالإيميل/الهاتف!", "TASK")



            if not email:

                self.log("لم يتم تحديد إيميل للتحقق! أضف email في الإعدادات", "ERROR")

                return False



            self.u2_set_text(email, className="android.widget.EditText", timeout=15)



            self.u2_click(text="Next", timeout=10) or \
            self.u2_click(textContains="Next", timeout=5) or \
            self.d.press("enter")



            self.log("تم إدخال الإيميل للتحقق", "SUCCESS")

        else:

            self.log("لم يُطلب التحقق — الانتقال للباسورد مباشرة", "INFO")



        # ===== إدخال كلمة المرور (ينتظر حتى يظهر الحقل) =====

        self.log("إدخال كلمة المرور...", "TASK")

        time.sleep(2)  # انتظار إضافي لتحميل صفحة الباسورد



        password_entered = False

        # محاولة 1: حقل فيه نص "Password" أو "كلمة المرور"

        password_entered = self.u2_set_text(password, textContains="Password", timeout=10)

        if not password_entered:

            password_entered = self.u2_set_text(password, textContains="password", timeout=5)

        if not password_entered:

            password_entered = self.u2_set_text(password, textContains="كلمة المرور", timeout=5)

        if not password_entered:

            password_entered = self.u2_set_text(password, textContains="كلمة السر", timeout=3)

        # محاولة 2: أول EditText في الصفحة (instance=0) — بعد Next حقل الباسورد يصبح الأول

        if not password_entered:

            for instance_idx in [0, 1]:

                try:

                    el = self.d(className="android.widget.EditText", instance=instance_idx)

                    if el.wait(timeout=8):

                        el.click()

                        time.sleep(0.5)

                        self.d.clear_text()

                        safe_pw = password.replace(" ", "%s").replace("&", "\\&").replace("(", "\\(").replace(")", "\\)").replace(";", "\\;")

                        subprocess.run(

                            [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_pw],

                            capture_output=True

                        )

                        password_entered = True

                        self.log(f"تم إدخال كلمة المرور (EditText instance={instance_idx})", "TASK")

                        break

                except Exception as e:

                    self.log(f"فشل محاولة EditText instance={instance_idx}: {e}", "INFO")

        # محاولة 3: نقر على إحداثيات مركز الشاشة ثم كتابة

        if not password_entered:

            try:

                self.log("محاولة أخيرة: النقر على مركز الشاشة وكتابة الباسورد...", "TASK")

                info = self.d.info

                cx = info['displayWidth'] // 2

                cy = info['displayHeight'] // 2

                self.d.click(cx, cy)

                time.sleep(0.5)

                self.d.clear_text()

                safe_pw = password.replace(" ", "%s").replace("&", "\\&")

                subprocess.run(

                    [self.adb_path, "-s", self.device_serial, "shell", "input", "text", safe_pw],

                    capture_output=True

                )

                password_entered = True

                self.log("تم إدخال كلمة المرور (نقر مركز الشاشة)", "TASK")

            except Exception as e:

                self.log(f"فشلت محاولة مركز الشاشة: {e}", "ERROR")

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



        # انتظار إضافي حتى تستقر الكوكيز في المتصفح

        self.log("انتظار استقرار الجلسة وتخزين الكوكيز...", "PROGRESS")

        time.sleep(10)



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

                cookies = json.load(f)

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



            return chrome_login_success



        except KeyboardInterrupt:

            self.log("تم إيقاف العملية يدويًا", "ERROR")

            return False

        except Exception as e:

            self.log(f"خطأ غير متوقع: {e}", "ERROR")

            import traceback

            traceback.print_exc()

            return False

        finally:

            # دائماً أغلق المحاكي مهما صار

            self.log("إغلاق المحاكي (finally)...", "PROGRESS")

            try:

                time.sleep(2)

                self.close_emulator()

            except Exception as e:

                self.log(f"خطأ أثناء إغلاق المحاكي: {e}", "ERROR")

            # انتظار ليتأكد النظام أن المحاكي أقفل

            time.sleep(3)



    def close_emulator(self):

        """إغلاق المحاكي + حذفه بالكامل (لكل حساب محاكي جديد كلياً).



        كل خطوة محاطة بـ try/except عشان لا تتعطّل الخطوة التالية لو فشلت السابقة.

        """

        idx = self.emulator_index

        if not idx:

            self.log("لا يوجد emulator_index لإغلاقه", "INFO")

            return



        self.log(f"بدء إغلاق وحذف المحاكي index={idx}...", "PROGRESS")



        # 1) quit المحاكي

        try:

            subprocess.run(

                [self.ldconsole, "quit", "--index", idx],

                capture_output=True, timeout=20

            )

            self.log(f"تم إرسال quit للمحاكي index={idx}", "INFO")

        except subprocess.TimeoutExpired:

            self.log(f"timeout على quit للمحاكي index={idx}", "ERROR")

        except Exception as e:

            self.log(f"خطأ على quit: {e}", "ERROR")



        time.sleep(4)



        # 2) قتل عمليات LDPlayer (شرط لنجاح remove)

        try:

            self.cleanup_processes()

        except Exception as e:

            self.log(f"خطأ على cleanup_processes: {e}", "ERROR")



        time.sleep(3)



        # 3) remove للمحاكي نهائياً — حتى 3 محاولات

        removed = False

        for attempt in range(1, 4):

            try:

                self.log(f"حذف المحاكي index={idx} (محاولة {attempt}/3)...", "PROGRESS")

                result = subprocess.run(

                    [self.ldconsole, "remove", "--index", idx],

                    capture_output=True, timeout=25, text=True

                )

                if result.returncode == 0:

                    self.log(f"✅ تم حذف المحاكي index={idx} نهائياً", "SUCCESS")

                    removed = True

                    break

                else:

                    self.log(f"  فشل remove (محاولة {attempt}): rc={result.returncode} out={(result.stdout or '').strip()} err={(result.stderr or '').strip()}", "INFO")

            except subprocess.TimeoutExpired:

                self.log(f"  timeout على remove (محاولة {attempt})", "INFO")

            except Exception as e:

                self.log(f"  خطأ على remove (محاولة {attempt}): {e}", "INFO")



            # بين المحاولات: نظّف العمليات وانتظر

            try:

                self.cleanup_processes()

            except Exception:

                pass

            time.sleep(3)



        if not removed:

            self.log(f"❌ تعذّر حذف المحاكي index={idx} بعد 3 محاولات", "ERROR")



        self.emulator_index = None





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

