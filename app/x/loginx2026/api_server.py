"""
X Login API Server
==================
API لتسجيل دخول حسابات X عبر HTTP

Endpoints:
    POST /api/login          — تسجيل دخول حساب واحد
    POST /api/login/bulk     — تسجيل دخول عدة حسابات
    GET  /api/tasks/<id>     — حالة مهمة تسجيل جماعي
    GET  /api/accounts       — قائمة الحسابات المسجلة
    GET  /api/cookies/<user> — جلب كوكيز حساب معين
    DELETE /api/cookies/<user> — حذف كوكيز حساب

الاستخدام:
    python api_server.py
    python api_server.py --port 8080 --host 0.0.0.0
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import subprocess
import threading
import time
import argparse
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============ Config ============
COOKIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")
BASE_DIR = Path(__file__).parent

# ============ Task Storage ============
login_tasks = {}
task_counter = 0
task_lock = threading.Lock()


# ============ Helper ============
def run_login(username, password, cookies_dir=COOKIES_DIR):
    """تشغيل تسجيل الدخول كـ subprocess"""
    result = subprocess.run(
        [sys.executable, "-m", "x_auth.login_sync", username, password, cookies_dir],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        cwd=str(BASE_DIR)
    )
    output = result.stdout + result.stderr
    for line in output.split("\n"):
        if line.startswith("__RESULT__"):
            return json.loads(line[10:])
    raise Exception(f"فشل تسجيل الدخول: {output[-500:]}")


# ============ API Endpoints ============

@app.route("/api/login", methods=["POST"])
def api_login():
    """
    تسجيل دخول حساب واحد

    Body JSON:
        {
            "username": "user123",
            "password": "pass123",
            "email": "user@example.com"  // اختياري
        }

    Response:
        {
            "success": true,
            "username": "user123",
            "cookies": {"auth_token": "...", "ct0": "..."}
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body مطلوب"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "error": "username و password مطلوبين"}), 400

    try:
        result = run_login(username, password)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/login/bulk", methods=["POST"])
def api_login_bulk():
    """
    تسجيل دخول عدة حسابات (غير متزامن)

    Body JSON:
        {
            "accounts": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "password": "pass2"}
            ],
            "delay": 5  // اختياري — تأخير بالثواني بين كل حساب (افتراضي 5)
        }

    Response:
        {"success": true, "task_id": "1", "total": 2}
    """
    global task_counter

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body مطلوب"}), 400

    accounts = data.get("accounts", [])
    delay = data.get("delay", 5)

    if not accounts:
        return jsonify({"success": False, "error": "accounts مطلوب (قائمة حسابات)"}), 400

    # التحقق من صحة البيانات
    for i, acc in enumerate(accounts):
        if not acc.get("username") or not acc.get("password"):
            return jsonify({
                "success": False,
                "error": f"الحساب رقم {i+1} ينقصه username أو password"
            }), 400

    with task_lock:
        task_counter += 1
        task_id = str(task_counter)

    login_tasks[task_id] = {
        "total": len(accounts),
        "done": 0,
        "success": 0,
        "failed": 0,
        "finished": False,
        "results": {}
    }

    def worker():
        for i, acc in enumerate(accounts):
            username = acc["username"].strip()
            password = acc["password"].strip()
            try:
                result = run_login(username, password)
                if result.get("success"):
                    login_tasks[task_id]["success"] += 1
                    login_tasks[task_id]["results"][username] = {
                        "success": True,
                        "cookies_file": result.get("cookies_file", "")
                    }
                else:
                    login_tasks[task_id]["failed"] += 1
                    login_tasks[task_id]["results"][username] = {
                        "success": False,
                        "error": result.get("error", "خطأ غير معروف")
                    }
            except Exception as e:
                login_tasks[task_id]["failed"] += 1
                login_tasks[task_id]["results"][username] = {
                    "success": False,
                    "error": str(e)
                }
            login_tasks[task_id]["done"] += 1

            if i < len(accounts) - 1:
                time.sleep(delay)

        login_tasks[task_id]["finished"] = True

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "task_id": task_id,
        "total": len(accounts)
    })


@app.route("/api/tasks/<task_id>", methods=["GET"])
def api_task_status(task_id):
    """
    حالة مهمة تسجيل جماعي

    Response:
        {
            "total": 5,
            "done": 3,
            "success": 2,
            "failed": 1,
            "finished": false,
            "results": { "user1": {"success": true}, ... }
        }
    """
    task = login_tasks.get(task_id)
    if not task:
        return jsonify({"error": "المهمة غير موجودة"}), 404
    return jsonify(task)


@app.route("/api/accounts", methods=["GET"])
def api_accounts():
    """
    قائمة الحسابات المسجلة

    Response:
        {
            "accounts": [
                {"username": "user1", "cookies_file": "cookies/user1.json"},
                ...
            ]
        }
    """
    cookies_dir = Path(COOKIES_DIR)
    accounts = []
    if cookies_dir.exists():
        for f in sorted(cookies_dir.glob("*.json")):
            accounts.append({
                "username": f.stem,
                "cookies_file": str(f)
            })
    return jsonify({"accounts": accounts, "total": len(accounts)})


@app.route("/api/cookies/<username>", methods=["GET"])
def api_get_cookies(username):
    """
    جلب كوكيز حساب معين

    Response:
        {
            "username": "user1",
            "auth_token": "...",
            "ct0": "...",
            "all_cookies": {...}
        }
    """
    cookie_file = Path(COOKIES_DIR) / f"{username}.json"
    if not cookie_file.exists():
        return jsonify({"error": f"كوكيز {username} غير موجودة"}), 404

    with open(cookie_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # استخراج auth_token و ct0
    auth_token = ""
    ct0 = ""
    all_cookies = {}

    if isinstance(data, dict) and 'cookies' in data:
        for c in data['cookies']:
            all_cookies[c['name']] = c['value']
            if c['name'] == 'auth_token':
                auth_token = c['value']
            elif c['name'] == 'ct0':
                ct0 = c['value']
    else:
        all_cookies = data
        auth_token = data.get('auth_token', '')
        ct0 = data.get('ct0', '')

    return jsonify({
        "username": username,
        "auth_token": auth_token,
        "ct0": ct0,
        "all_cookies": all_cookies
    })


@app.route("/api/cookies/<username>", methods=["DELETE"])
def api_delete_cookies(username):
    """حذف كوكيز حساب"""
    cookie_file = Path(COOKIES_DIR) / f"{username}.json"
    if not cookie_file.exists():
        return jsonify({"error": f"كوكيز {username} غير موجودة"}), 404

    os.remove(cookie_file)
    return jsonify({"success": True, "message": f"تم حذف كوكيز {username}"})


@app.route("/api/health", methods=["GET"])
def api_health():
    """فحص حالة السيرفر"""
    cookies_dir = Path(COOKIES_DIR)
    count = len(list(cookies_dir.glob("*.json"))) if cookies_dir.exists() else 0
    return jsonify({
        "status": "ok",
        "accounts_count": count,
        "active_tasks": sum(1 for t in login_tasks.values() if not t["finished"])
    })


# ============ Main ============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X Login API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    os.makedirs(COOKIES_DIR, exist_ok=True)

    print("=" * 50)
    print("  X Login API Server")
    print(f"  http://{args.host}:{args.port}")
    print("=" * 50)
    print()
    print("  Endpoints:")
    print("    POST /api/login          — تسجيل دخول حساب")
    print("    POST /api/login/bulk     — تسجيل عدة حسابات")
    print("    GET  /api/tasks/<id>     — حالة مهمة")
    print("    GET  /api/accounts       — قائمة الحسابات")
    print("    GET  /api/cookies/<user> — جلب كوكيز")
    print("    DELETE /api/cookies/<user> — حذف كوكيز")
    print("    GET  /api/health         — حالة السيرفر")
    print("=" * 50)

    app.run(host=args.host, port=args.port, debug=args.debug)
