import os
import csv
import json
import threading
import queue
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from werkzeug.utils import secure_filename
from j4 import LDPlayerChromeAutomation, load_accounts

app = Flask(__name__)
app.secret_key = "x_automation_2026"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
COOKIES_FOLDER = os.path.join(os.path.dirname(__file__), "CookiesBackup")
# مجلد الكوكيز الرئيسي لـ X Suite (للتفاعل مع المنصة)
XSUITE_COOKIES_FOLDER = os.path.join(os.path.dirname(__file__), "..", "cookies")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COOKIES_FOLDER, exist_ok=True)
os.makedirs(XSUITE_COOKIES_FOLDER, exist_ok=True)

# API Key for authentication
LOGINX_API_KEY = os.environ.get("LOGINX_API_KEY", "sk-loginx-2026-secret")

# Global state
log_queues = {}  # session_id -> queue
tasks = {}  # session_id -> task info


def get_or_create_queue(session_id):
    if session_id not in log_queues:
        log_queues[session_id] = queue.Queue()
    return log_queues[session_id]


def require_api_key(f):
    """ديكوريتور للتحقق من API Key"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        if api_key != LOGINX_API_KEY:
            return jsonify({"success": False, "error": "Unauthorized - invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated


def copy_cookies_to_xsuite(username):
    """نسخ ملف الكوكيز من CookiesBackup إلى مجلد app/x/cookies + تسجيله في DB"""
    import shutil
    
    src = os.path.join(COOKIES_FOLDER, f"{username}.json")
    if not os.path.exists(src):
        return False, f"ملف الكوكيز غير موجود: {src}"
    
    # تأكد من وجود مجلد الوجهة
    os.makedirs(XSUITE_COOKIES_FOLDER, exist_ok=True)
    
    # قراءة الملف للتحقق من الصيغة
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # إذا بصيغة storage_state الصحيحة — انسخ مباشرة
    if isinstance(data, dict) and 'cookies' in data:
        # تحقق من وجود auth_token
        cookie_names = [c.get('name') for c in data['cookies']]
        if 'auth_token' not in cookie_names:
            return False, f"الكوكيز لا تحتوي على auth_token — تسجيل الدخول لم يكتمل"
        dst = os.path.join(XSUITE_COOKIES_FOLDER, f"{username}.json")
        shutil.copy2(src, dst)
        cookie_count = len(data.get('cookies', []))
    else:
        # صيغة قديمة (مصفوفة) — حوّلها
        import time as _time
        HTTP_ONLY = {'auth_token', 'kdt', '_twitter_sess', '__cf_bm', 'auth_multi'}
        LAX_COOKIES = {'ct0', 'auth_multi'}
        
        cookie_list = data if isinstance(data, list) else []
        playwright_cookies = []
        for c in cookie_list:
            name = c.get('name', '')
            if not name or not c.get('value'):
                continue
            expires = c.get('expires') or c.get('expirationDate') or (_time.time() + 365 * 24 * 3600)
            same_site = 'Lax' if name in LAX_COOKIES else 'None'
            playwright_cookies.append({
                "name": name,
                "value": c.get('value', ''),
                "domain": c.get('domain', '.x.com'),
                "path": c.get('path', '/'),
                "expires": float(expires),
                "httpOnly": c.get('httpOnly', name in HTTP_ONLY),
                "secure": c.get('secure', True),
                "sameSite": same_site,
            })
        
        if not playwright_cookies:
            return False, "لا توجد كوكيز صالحة في الملف"
        
        storage_state = {"cookies": playwright_cookies, "origins": []}
        dst = os.path.join(XSUITE_COOKIES_FOLDER, f"{username}.json")
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)
        cookie_count = len(playwright_cookies)
    
    print(f"[LoginX] ✅ تم نسخ كوكيز '{username}' لـ X Suite ({cookie_count} كوكيز)")
    
    # تسجيل الكوكيز في قاعدة بيانات X Suite
    try:
        import sys
        modules_dir = os.path.join(os.path.dirname(__file__), "..", "modules")
        if modules_dir not in sys.path:
            sys.path.insert(0, modules_dir)
        from db import upsert_cookie
        upsert_cookie(username, f"{username}.json")
    except Exception as e:
        print(f"[LoginX] Warning: Could not register cookie in DB: {e}")
    
    return True, dst


def run_automation(session_id, accounts, headless=False):
    q = get_or_create_queue(session_id)
    tasks[session_id]["status"] = "running"
    tasks[session_id]["results"] = []

    total = len(accounts)
    print(f"[LoginX] 🚀 بدء تسجيل دخول {total} حساب (headless={headless})")

    for i, acc in enumerate(accounts):
        username = acc["username"]
        password = acc["password"]
        email = acc.get("email", "")

        q.put(json.dumps({
            "type": "account_start",
            "account": username,
            "index": i + 1,
            "total": total,
        }))

        success = False
        cookie_path = None

        try:
            def log_callback(message, level, account):
                q.put(json.dumps({
                    "type": "log",
                    "message": message,
                    "level": level,
                    "account": account,
                    "time": datetime.now().strftime("%H:%M:%S"),
                }))

            automation = LDPlayerChromeAutomation(log_callback=log_callback, headless=headless)
            success = automation.run_automation_with_chrome_focus(username, password, email)

            # إذا نجح التسجيل، انسخ الكوكيز لمجلد X Suite
            if success:
                try:
                    ok, path_or_err = copy_cookies_to_xsuite(username)
                    if ok:
                        cookie_path = path_or_err
                        print(f"[LoginX] ✅ تم نسخ كوكيز {username} لـ X Suite")
                    else:
                        print(f"[LoginX] ⚠️ فشل نسخ كوكيز {username}: {path_or_err}")
                except Exception as e:
                    print(f"[LoginX] ⚠️ خطأ نسخ كوكيز {username}: {e}")

        except Exception as e:
            print(f"[LoginX] ❌ خطأ غير متوقع في حساب {username}: {e}")
            import traceback
            traceback.print_exc()
            # تأكد من إغلاق المحاكي حتى لو حصل خطأ
            try:
                automation.close_emulator()
            except Exception:
                pass

        result = {"username": username, "success": success, "cookie_path": cookie_path}
        tasks[session_id]["results"].append(result)

        q.put(json.dumps({
            "type": "account_done",
            "account": username,
            "success": success,
            "cookie_path": cookie_path,
            "index": i + 1,
            "total": total,
        }))

        # انتظار بين الحسابات ليتعافى النظام
        if i < total - 1:
            wait_sec = 10
            print(f"[LoginX] ⏳ انتظار {wait_sec} ثواني قبل الحساب التالي...")
            q.put(json.dumps({
                "type": "log",
                "message": f"انتظار {wait_sec} ثواني قبل الحساب التالي...",
                "level": "PROGRESS",
                "account": username,
                "time": datetime.now().strftime("%H:%M:%S"),
            }))
            time.sleep(wait_sec)

    tasks[session_id]["status"] = "done"
    successful = sum(1 for r in tasks[session_id]["results"] if r["success"])
    print(f"[LoginX] 🏁 انتهت العملية: {successful}/{total} حساب نجح")
    q.put(json.dumps({"type": "done", "results": tasks[session_id]["results"]}))


@app.route("/")
def index():
    cookies_files = []
    if os.path.exists(COOKIES_FOLDER):
        for f in os.listdir(COOKIES_FOLDER):
            if f.endswith(".json"):
                fpath = os.path.join(COOKIES_FOLDER, f)
                account_name = f.replace(".json", "")
                size = os.path.getsize(fpath)
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
                cookies_files.append({
                    "filename": f,
                    "account": account_name,
                    "size": size,
                    "date": mtime,
                })
    cookies_files.sort(key=lambda x: x["date"], reverse=True)
    return render_template("index.html", cookies=cookies_files)


@app.route("/start_single", methods=["POST"])
def start_single():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    email = request.form.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

    session_id = f"s_{int(time.time()*1000)}"
    accounts = [{"username": username, "password": password, "email": email}]

    tasks[session_id] = {"status": "starting", "accounts": accounts, "results": []}
    get_or_create_queue(session_id)

    t = threading.Thread(target=run_automation, args=(session_id, accounts), daemon=True)
    t.start()

    return jsonify({"session_id": session_id})


@app.route("/start_bulk", methods=["POST"])
def start_bulk():
    if "file" not in request.files:
        return jsonify({"error": "لم يتم رفع ملف"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "لم يتم اختيار ملف"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        accounts = load_accounts(filepath)
    except Exception as e:
        return jsonify({"error": f"خطأ في قراءة الملف: {e}"}), 400

    if not accounts:
        return jsonify({"error": "الملف فارغ أو بصيغة خاطئة"}), 400

    session_id = f"s_{int(time.time()*1000)}"
    tasks[session_id] = {"status": "starting", "accounts": accounts, "results": []}
    get_or_create_queue(session_id)

    t = threading.Thread(target=run_automation, args=(session_id, accounts), daemon=True)
    t.start()

    return jsonify({"session_id": session_id, "count": len(accounts)})


@app.route("/stream/<session_id>")
def stream(session_id):
    def generate():
        q = get_or_create_queue(session_id)
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {msg}\n\n"
                data = json.loads(msg)
                if data.get("type") == "done":
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/cookies/<filename>")
def view_cookie(filename):
    fpath = os.path.join(COOKIES_FOLDER, filename)
    if not os.path.exists(fpath):
        return "الملف غير موجود", 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/cookies/download/<filename>")
def download_cookie(filename):
    fpath = os.path.join(COOKIES_FOLDER, filename)
    if not os.path.exists(fpath):
        return "الملف غير موجود", 404
    from flask import send_file
    return send_file(fpath, as_attachment=True)


@app.route("/status/<session_id>")
def task_status(session_id):
    if session_id not in tasks:
        return jsonify({"error": "الجلسة غير موجودة"}), 404
    return jsonify(tasks[session_id])


# =====================
# API Endpoints (for external integration)
# =====================

@app.route("/api/login", methods=["POST"])
@require_api_key
def api_login():
    """
    تسجيل دخول حساب واحد عبر API.
    
    Headers:
        X-API-Key: sk-loginx-2026-secret
    
    Body (JSON):
        {
            "username": "...",
            "password": "...",
            "email": "..." (optional)
        }
    
    Returns:
        {"success": true, "session_id": "...", "message": "..."}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()
    headless = data.get("headless", False)  # افتراضياً ظاهر

    if not username or not password:
        return jsonify({"success": False, "error": "username و password مطلوبين"}), 400

    session_id = f"api_{int(time.time()*1000)}"
    accounts = [{"username": username, "password": password, "email": email}]

    tasks[session_id] = {"status": "starting", "accounts": accounts, "results": []}
    get_or_create_queue(session_id)

    t = threading.Thread(target=run_automation, args=(session_id, accounts, headless), daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "message": f"بدأت عملية تسجيل الدخول للحساب {username}"
    })


@app.route("/api/login/bulk", methods=["POST"])
@require_api_key
def api_login_bulk():
    """
    تسجيل دخول جماعي عبر API.
    
    Body (JSON):
        {
            "accounts": [
                {"username": "...", "password": "...", "email": "..."},
                ...
            ]
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    accounts = data.get("accounts", [])
    headless = data.get("headless", False)  # افتراضياً ظاهر

    if not accounts:
        return jsonify({"success": False, "error": "لا توجد حسابات"}), 400

    # تحقق من صحة البيانات
    for acc in accounts:
        if not acc.get("username") or not acc.get("password"):
            return jsonify({"success": False, "error": f"حساب بدون username أو password"}), 400

    session_id = f"api_bulk_{int(time.time()*1000)}"
    tasks[session_id] = {"status": "starting", "accounts": accounts, "results": []}
    get_or_create_queue(session_id)

    t = threading.Thread(target=run_automation, args=(session_id, accounts, headless), daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "count": len(accounts),
        "message": f"بدأت عملية تسجيل الدخول لـ {len(accounts)} حساب"
    })


@app.route("/api/status/<session_id>", methods=["GET"])
@require_api_key
def api_task_status(session_id):
    """معرفة حالة عملية تسجيل الدخول"""
    if session_id not in tasks:
        return jsonify({"success": False, "error": "الجلسة غير موجودة"}), 404
    
    task = tasks[session_id]
    return jsonify({
        "success": True,
        "session_id": session_id,
        "status": task["status"],
        "results": task.get("results", [])
    })


@app.route("/api/cookies", methods=["GET"])
@require_api_key
def api_list_cookies():
    """عرض جميع ملفات الكوكيز المحفوظة"""
    cookies_files = []
    if os.path.exists(COOKIES_FOLDER):
        for f in os.listdir(COOKIES_FOLDER):
            if f.endswith(".json"):
                fpath = os.path.join(COOKIES_FOLDER, f)
                cookies_files.append({
                    "filename": f,
                    "account": f.replace(".json", ""),
                    "size": os.path.getsize(fpath),
                    "date": datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M"),
                })
    return jsonify({"success": True, "cookies": cookies_files})


@app.route("/api/health", methods=["GET"])
def api_health():
    """فحص صحة السيرفر"""
    return jsonify({"status": "healthy", "service": "LoginX", "port": 5000})


if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)
