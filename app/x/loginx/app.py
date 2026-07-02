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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COOKIES_FOLDER, exist_ok=True)

# Global state
log_queues = {}  # session_id -> queue
tasks = {}  # session_id -> task info


def get_or_create_queue(session_id):
    if session_id not in log_queues:
        log_queues[session_id] = queue.Queue()
    return log_queues[session_id]


def _finalize_login_for_moj(username, user_id, log_fn):
    """
    بعد نجاح تسجيل الدخول عبر LDPlayer:
    1) ينسخ ملف الكوكيز من CookiesBackup/ إلى app/x/cookies/ (المسار الذي يستخدمه موج)
    2) يسجّل/يحدّث الحساب في قاعدة بيانات موج (social_accounts) إذا user_id موجود

    log_fn(message, level): دالة للتسجيل.
    يرجع True إذا تمّت العمليتان أو إحداهما، False لو الكوكيز ما وُجدت.
    """
    import shutil
    from pathlib import Path

    try:
        loginx_dir = Path(__file__).resolve().parent
        source = loginx_dir / "CookiesBackup" / f"{username}.json"

        if not source.exists():
            log_fn(f"⚠️ ملف الكوكيز غير موجود في: {source}", "ERROR")
            return False

        # المسار الرئيسي لكوكيز موج (app/x/cookies/)
        main_cookies_dir = loginx_dir.parent / "cookies"
        main_cookies_dir.mkdir(parents=True, exist_ok=True)
        dest = main_cookies_dir / f"{username}.json"

        shutil.copy2(source, dest)
        log_fn(f"✅ تم نسخ الكوكيز إلى موج: {dest.name}", "SUCCESS")

        # ─── تسجيل الكوكي في قاعدة بيانات سيرفر app/x ───
        # هذي قاعدة منفصلة يستخدمها سيرفر النشر (app/x/app.py).
        # بدون تسجيل هنا، النشر يرجع "cookie not found".
        try:
            import sys
            project_root = loginx_dir.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from app.x.modules.db import upsert_cookie
            cookie_id = upsert_cookie(username, dest.name)
            log_fn(f"✅ تم تسجيل الكوكي في قاعدة سيرفر X (id={cookie_id})", "SUCCESS")
        except Exception as e:
            import traceback
            log_fn(f"⚠️ فشل تسجيل الكوكي في قاعدة سيرفر X: {e}", "ERROR")
            print(f"[loginx upsert_cookie error] {traceback.format_exc()}")

        # ─── تسجيل الحساب في قاعدة بيانات موج الرئيسية (social_accounts) ───
        if user_id:
            try:
                import sys
                project_root = loginx_dir.parent.parent.parent  # app/x/loginx → root
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))

                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                from datetime import datetime as _dt

                db = SessionLocal()
                try:
                    existing = account_service.get_account_by_username(
                        db=db, user_id=user_id, platform="x", username=username
                    )
                    if existing:
                        account_service.update_account(
                            db=db, account_id=existing.id,
                            status="active", last_login=_dt.utcnow(),
                            cookie_filename=f"{username}.json", error_message=None
                        )
                        log_fn(f"✅ تم تحديث الحساب في DB (user_id={user_id})", "SUCCESS")
                    else:
                        account_service.create_account(
                            db=db, user_id=user_id, platform="x",
                            username=username, display_name=username,
                            account_label=username,
                            cookie_filename=f"{username}.json"
                        )
                        log_fn(f"✅ تم تسجيل الحساب في DB (user_id={user_id})", "SUCCESS")
                finally:
                    db.close()
            except Exception as e:
                import traceback
                log_fn(f"⚠️ فشل تسجيل الحساب في DB: {e}", "ERROR")
                print(f"[loginx finalize DB error] {traceback.format_exc()}")
        else:
            log_fn("ℹ️ لا يوجد user_id — تم نسخ الكوكيز فقط بدون تسجيل في DB", "INFO")

        return True
    except Exception as e:
        log_fn(f"⚠️ خطأ في finalize_login: {e}", "ERROR")
        return False


def _notify_callback(callback_url, payload):
    """يرسل إشعار اكتمال إلى موج (POST). يفشل بصمت — لأن الإشعار اختياري."""
    if not callback_url:
        return
    try:
        import requests
        requests.post(callback_url, json=payload, timeout=5)
    except Exception as e:
        print(f"[loginx callback error] {e}")


def run_automation(session_id, accounts, user_id=None, callback_url=None):
    q = get_or_create_queue(session_id)
    tasks[session_id]["status"] = "running"
    tasks[session_id]["results"] = []

    total = len(accounts)

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

        def log_callback(message, level, account):
            q.put(json.dumps({
                "type": "log",
                "message": message,
                "level": level,
                "account": account,
                "time": datetime.now().strftime("%H:%M:%S"),
            }))

        automation = LDPlayerChromeAutomation(log_callback=log_callback)
        try:
            success = automation.run_automation_with_chrome_focus(username, password, email)
            error_msg = ""
        except Exception as e:
            success = False
            error_msg = str(e)

        # ── بعد نجاح الدخول: انسخ الكوكيز لموج + سجّل الحساب في DB ──
        finalized = False
        if success:
            def _flog(msg, lvl):
                log_callback(msg, lvl, username)
            finalized = _finalize_login_for_moj(username, user_id, _flog)

        result = {
            "username": username,
            "success": success,
            "finalized": finalized,
        }
        if error_msg:
            result["error"] = error_msg
        tasks[session_id]["results"].append(result)

        q.put(json.dumps({
            "type": "account_done",
            "account": username,
            "success": success,
            "finalized": finalized,
            "index": i + 1,
            "total": total,
        }))

        # ── إشعار موج بنتيجة هذا الحساب (لإظهارها في الشات) ──
        _notify_callback(callback_url, {
            "user_id": user_id,
            "account": username,
            "username": username,
            "success": success,
            "finalized": finalized,
            "error": error_msg,
            "session_id": session_id,
        })

    tasks[session_id]["status"] = "done"
    q.put(json.dumps({"type": "done", "results": tasks[session_id]["results"]}))


@app.route("/api/health")
def health_check():
    """Endpoint للتحقق من أن سيرفر loginx شغّال (يستخدمه x_bridge)."""
    return jsonify({"status": "ok", "service": "loginx", "port": 5000}), 200


# ─── API endpoints يستخدمها موج (app/agents/tools.py + app/main.py) ───
# تقبل JSON وترجع {success, session_id, error}

@app.route("/api/login", methods=["POST"])
def api_login_single():
    """
    تسجيل دخول حساب واحد (JSON API).
    Body: {"username": "...", "password": "...", "email": "...", "headless": false, "user_id": 123}
    Returns: {"success": True, "session_id": "..."} أو {"success": False, "error": "..."}
    user_id (اختياري): يُستخدم لتسجيل الحساب في قاعدة بيانات موج بعد الدخول.
    """
    try:
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        email = (data.get("email") or "").strip()
        user_id = data.get("user_id")  # int أو None
        callback_url = (data.get("callback_url") or "").strip() or None

        if not username or not password:
            return jsonify({"success": False, "error": "اسم المستخدم وكلمة المرور مطلوبان"}), 400

        session_id = f"s_{int(time.time() * 1000)}"
        accounts = [{"username": username, "password": password, "email": email}]

        tasks[session_id] = {
            "status": "starting", "accounts": accounts, "results": [],
            "user_id": user_id, "callback_url": callback_url,
        }
        get_or_create_queue(session_id)

        t = threading.Thread(
            target=run_automation,
            args=(session_id, accounts, user_id, callback_url),
            daemon=True,
        )
        t.start()

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/login/bulk", methods=["POST"])
def api_login_bulk():
    """
    تسجيل دخول جماعي (JSON API).
    Body: {"accounts": [{"username": "...", "password": "...", "email": "..."}, ...], "user_id": 123}
    Returns: {"success": True, "session_id": "...", "count": N}
    """
    try:
        data = request.get_json(silent=True) or {}
        accounts = data.get("accounts") or []
        user_id = data.get("user_id")
        callback_url = (data.get("callback_url") or "").strip() or None

        if not accounts or not isinstance(accounts, list):
            return jsonify({"success": False, "error": "قائمة الحسابات فارغة أو غير صالحة"}), 400

        # تنظيف وتحقق
        clean_accounts = []
        for acc in accounts:
            u = (acc.get("username") or "").strip()
            p = (acc.get("password") or "").strip()
            e = (acc.get("email") or "").strip()
            if u and p:
                clean_accounts.append({"username": u, "password": p, "email": e})

        if not clean_accounts:
            return jsonify({"success": False, "error": "لا يوجد حسابات صالحة"}), 400

        session_id = f"s_{int(time.time() * 1000)}"
        tasks[session_id] = {
            "status": "starting", "accounts": clean_accounts, "results": [],
            "user_id": user_id, "callback_url": callback_url,
        }
        get_or_create_queue(session_id)

        t = threading.Thread(
            target=run_automation,
            args=(session_id, clean_accounts, user_id, callback_url),
            daemon=True,
        )
        t.start()

        return jsonify({"success": True, "session_id": session_id, "count": len(clean_accounts)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/status/<session_id>", methods=["GET"])
def api_status(session_id):
    """استعلام عن حالة جلسة تسجيل دخول معينة."""
    task = tasks.get(session_id)
    if not task:
        return jsonify({"success": False, "error": "جلسة غير معروفة"}), 404
    return jsonify({
        "success": True,
        "session_id": session_id,
        "status": task["status"],
        "results": task.get("results", []),
        "total": len(task.get("accounts", [])),
    })


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


if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)
