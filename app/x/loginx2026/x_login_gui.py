"""
واجهة Flask لتسجيل الدخول في X عبر API
يدعم: إدخال يوزر واحد يدوياً + رفع ملف CSV (username,pass)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import csv
import json
import subprocess
import threading
import time
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# حالة العمليات الجارية
login_tasks = {}
task_counter = 0
task_lock = threading.Lock()

COOKIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #15202B;
            color: #E7E9EA;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container { max-width: 520px; margin: 0 auto; }
        .logo { font-size: 42px; font-weight: 900; color: #fff; text-align: center; }
        .subtitle { color: #71767B; font-size: 14px; text-align: center; margin-bottom: 28px; }

        /* Tabs */
        .tabs { display: flex; gap: 4px; margin-bottom: 20px; }
        .tab {
            flex: 1; padding: 11px; text-align: center; border-radius: 10px;
            cursor: pointer; font-size: 14px; font-weight: 600;
            background: #1E2D3D; color: #8B98A5; transition: all 0.2s;
        }
        .tab.active { background: #1D9BF0; color: #fff; }

        /* Card */
        .card {
            background: #1E2D3D; border-radius: 16px; padding: 28px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        }
        .panel { display: none; }
        .panel.active { display: block; }

        /* Fields */
        .field { margin-bottom: 16px; }
        .field label { display: block; font-size: 13px; color: #8B98A5; margin-bottom: 5px; }
        .field input, .field select {
            width: 100%; padding: 11px 14px; border-radius: 8px;
            border: 1px solid #38444D; background: #273340;
            color: #E7E9EA; font-size: 15px; outline: none;
        }
        .field input:focus { border-color: #1D9BF0; }

        /* File Upload */
        .file-zone {
            border: 2px dashed #38444D; border-radius: 12px; padding: 30px;
            text-align: center; cursor: pointer; transition: border-color 0.2s;
            margin-bottom: 16px;
        }
        .file-zone:hover, .file-zone.dragover { border-color: #1D9BF0; }
        .file-zone input { display: none; }
        .file-zone .icon { font-size: 32px; margin-bottom: 8px; }
        .file-zone .text { color: #8B98A5; font-size: 13px; }
        .file-zone .filename { color: #1D9BF0; font-size: 14px; font-weight: 600; margin-top: 6px; }
        .file-hint { color: #71767B; font-size: 12px; margin-bottom: 16px; text-align: center; }

        /* Button */
        .btn {
            width: 100%; padding: 13px; border-radius: 28px; border: none;
            background: #1D9BF0; color: #fff; font-size: 16px; font-weight: 700;
            cursor: pointer; transition: background 0.2s;
        }
        .btn:hover { background: #1A8CD8; }
        .btn:disabled { background: #38444D; cursor: not-allowed; }

        /* Status */
        .status {
            margin-top: 18px; padding: 14px; border-radius: 10px;
            font-size: 14px; display: none; text-align: center; line-height: 1.7;
        }
        .status.loading { display: block; background: #1C3A50; color: #1D9BF0; }
        .status.success { display: block; background: #0D3B2E; color: #00BA7C; }
        .status.error   { display: block; background: #3B1C1C; color: #F4212E; }
        .spinner {
            display: inline-block; width: 16px; height: 16px;
            border: 2px solid #1D9BF0; border-top-color: transparent;
            border-radius: 50%; animation: spin 0.8s linear infinite;
            vertical-align: middle; margin-left: 6px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Progress */
        .progress-bar {
            height: 6px; background: #273340; border-radius: 3px;
            margin-top: 12px; overflow: hidden; display: none;
        }
        .progress-bar .fill {
            height: 100%; background: #1D9BF0; border-radius: 3px;
            transition: width 0.3s;
        }

        /* Results */
        .results { margin-top: 24px; }
        .results h3 { font-size: 15px; margin-bottom: 10px; color: #8B98A5; }
        .acc-card {
            background: #1E2D3D; border-radius: 10px; padding: 12px 16px;
            margin-bottom: 6px; display: flex; justify-content: space-between;
            align-items: center; font-size: 14px;
        }
        .acc-card .user { color: #1D9BF0; font-weight: 600; }
        .badge {
            padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
        }
        .badge.ok { background: #0D3B2E; color: #00BA7C; }
        .badge.fail { background: #3B1C1C; color: #F4212E; }
        .badge.wait { background: #1C3A50; color: #1D9BF0; }

        /* API Docs */
        .api-title { color: #E7E9EA; font-size: 16px; margin-bottom: 8px; }
        .api-desc { color: #71767B; font-size: 13px; margin-bottom: 18px; }
        .api-endpoint {
            display: flex; align-items: center; gap: 10px;
            padding: 10px 0; border-bottom: 1px solid #273340;
        }
        .api-method {
            padding: 3px 10px; border-radius: 6px; font-size: 11px;
            font-weight: 700; font-family: monospace; min-width: 58px; text-align: center;
        }
        .api-method.get { background: #0D3B2E; color: #00BA7C; }
        .api-method.post { background: #1C3A50; color: #1D9BF0; }
        .api-method.delete { background: #3B1C1C; color: #F4212E; }
        .api-url { color: #E7E9EA; font-size: 13px; font-family: monospace; flex: 1; }
        .api-label { color: #71767B; font-size: 12px; }
        .api-code {
            background: #0D1117; border-radius: 8px; padding: 12px 14px;
            margin: 8px 0 14px; overflow-x: auto;
        }
        .api-code pre {
            color: #79C0FF; font-size: 12px; font-family: 'Consolas', monospace;
            margin: 0; white-space: pre; line-height: 1.6;
        }
        .api-test { margin-top: 20px; padding-top: 18px; border-top: 1px solid #273340; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">𝕏</div>
    <div class="subtitle">تسجيل الدخول واستخراج الكوكيز</div>

    <div class="tabs">
        <div class="tab active" onclick="switchTab('single', this)">حساب واحد</div>
        <div class="tab" onclick="switchTab('bulk', this)">عدة حسابات (CSV)</div>
        <div class="tab" onclick="switchTab('api', this)">API</div>
    </div>

    <div class="card">
        <!-- حساب واحد -->
        <div class="panel active" id="panel-single">
            <form id="singleForm">
                <div class="field">
                    <label>اسم المستخدم</label>
                    <input type="text" id="username" placeholder="username" required autocomplete="off">
                </div>
                <div class="field">
                    <label>كلمة المرور</label>
                    <input type="password" id="password" placeholder="••••••••" required>
                </div>
                <button type="submit" class="btn" id="singleBtn">تسجيل الدخول</button>
            </form>
            <div class="status" id="singleStatus"></div>
        </div>

        <!-- عدة حسابات -->
        <div class="panel" id="panel-bulk">
            <div class="file-zone" id="fileZone" onclick="document.getElementById('csvFile').click()">
                <input type="file" id="csvFile" accept=".csv,.txt">
                <div class="icon">📄</div>
                <div class="text">اضغط أو اسحب ملف CSV هنا</div>
                <div class="filename" id="fileName"></div>
            </div>
            <div class="file-hint">صيغة الملف: username,pass (سطر لكل حساب)</div>
            <button class="btn" id="bulkBtn" onclick="startBulk()" disabled>بدء تسجيل الدخول</button>
            <div class="progress-bar" id="progressBar"><div class="fill" id="progressFill"></div></div>
            <div class="status" id="bulkStatus"></div>
        </div>
        <!-- API -->
        <div class="panel" id="panel-api">
            <div class="api-section">
                <h3 class="api-title">API Endpoints</h3>
                <p class="api-desc">استخدم هذه الروابط لتسجيل الدخول برمجياً عبر أي لغة</p>

                <div class="api-endpoint">
                    <div class="api-method post">POST</div>
                    <code class="api-url">/api/login</code>
                    <div class="api-label">تسجيل دخول حساب واحد</div>
                </div>
                <div class="api-code"><pre>{
  "username": "your_user",
  "password": "your_pass"
}</pre></div>

                <div class="api-endpoint">
                    <div class="api-method post">POST</div>
                    <code class="api-url">/api/login/bulk</code>
                    <div class="api-label">تسجيل عدة حسابات</div>
                </div>
                <div class="api-code"><pre>{
  "accounts": [
    {"username": "u1", "password": "p1"},
    {"username": "u2", "password": "p2"}
  ],
  "delay": 5
}</pre></div>

                <div class="api-endpoint">
                    <div class="api-method get">GET</div>
                    <code class="api-url">/api/tasks/{task_id}</code>
                    <div class="api-label">حالة مهمة تسجيل جماعي</div>
                </div>

                <div class="api-endpoint">
                    <div class="api-method get">GET</div>
                    <code class="api-url">/api/accounts</code>
                    <div class="api-label">قائمة الحسابات المسجلة</div>
                </div>

                <div class="api-endpoint">
                    <div class="api-method get">GET</div>
                    <code class="api-url">/api/cookies/{username}</code>
                    <div class="api-label">جلب كوكيز حساب</div>
                </div>

                <div class="api-endpoint">
                    <div class="api-method delete">DELETE</div>
                    <code class="api-url">/api/cookies/{username}</code>
                    <div class="api-label">حذف كوكيز حساب</div>
                </div>

                <div class="api-endpoint">
                    <div class="api-method get">GET</div>
                    <code class="api-url">/api/health</code>
                    <div class="api-label">فحص حالة السيرفر</div>
                </div>

                <h3 class="api-title" style="margin-top:24px">Python Example</h3>
                <div class="api-code"><pre>import requests

BASE = "http://127.0.0.1:5000"

# تسجيل دخول
r = requests.post(f"{BASE}/api/login", json={
    "username": "user123",
    "password": "pass123"
})
print(r.json())

# جلب كوكيز
r = requests.get(f"{BASE}/api/cookies/user123")
data = r.json()
print(data["auth_token"])
print(data["ct0"])</pre></div>

                <h3 class="api-title" style="margin-top:18px">cURL Example</h3>
                <div class="api-code"><pre>curl -X POST http://127.0.0.1:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'</pre></div>

                <div class="api-test">
                    <h3 class="api-title">اختبار سريع</h3>
                    <div class="field">
                        <input type="text" id="apiTestUser" placeholder="username">
                    </div>
                    <div class="field">
                        <input type="password" id="apiTestPass" placeholder="password">
                    </div>
                    <button class="btn" onclick="testApi()" id="apiTestBtn">ارسال طلب API</button>
                    <div class="api-code" id="apiResult" style="display:none;margin-top:12px"><pre id="apiResultPre"></pre></div>
                </div>
            </div>
        </div>
    </div>

    <div class="results" id="results"></div>
</div>

<script>
let csvAccounts = [];

// Tabs
function switchTab(tab, el) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('panel-' + tab).classList.add('active');
}

// CSV Upload
const csvFile = document.getElementById('csvFile');
const fileZone = document.getElementById('fileZone');

csvFile.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    document.getElementById('fileName').textContent = file.name;
    const reader = new FileReader();
    reader.onload = (ev) => {
        const lines = ev.target.result.trim().split('\\n');
        csvAccounts = [];
        lines.forEach(line => {
            line = line.trim();
            if (!line || line.startsWith('username')) return;
            const parts = line.split(',');
            if (parts.length >= 2) {
                csvAccounts.push({username: parts[0].trim(), password: parts[1].trim()});
            }
        });
        document.getElementById('fileName').textContent = file.name + ' (' + csvAccounts.length + ' حساب)';
        document.getElementById('bulkBtn').disabled = csvAccounts.length === 0;
    };
    reader.readAsText(file);
});

fileZone.addEventListener('dragover', (e) => { e.preventDefault(); fileZone.classList.add('dragover'); });
fileZone.addEventListener('dragleave', () => fileZone.classList.remove('dragover'));
fileZone.addEventListener('drop', (e) => {
    e.preventDefault(); fileZone.classList.remove('dragover');
    csvFile.files = e.dataTransfer.files;
    csvFile.dispatchEvent(new Event('change'));
});

// Single Login
document.getElementById('singleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    if (!username || !password) return;

    const btn = document.getElementById('singleBtn');
    const status = document.getElementById('singleStatus');
    btn.disabled = true;
    btn.textContent = 'جاري تسجيل الدخول...';
    status.className = 'status loading';
    status.innerHTML = '<span class="spinner"></span> جاري تسجيل الدخول عبر API...';

    try {
        const resp = await fetch('/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await resp.json();
        if (data.success) {
            status.className = 'status success';
            status.innerHTML = '✓ تم تسجيل الدخول بنجاح!<br><small>auth_token: ' +
                data.auth_token.substring(0, 25) + '...</small>';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
        } else {
            status.className = 'status error';
            status.innerHTML = '✗ ' + (data.error || 'فشل تسجيل الدخول');
        }
    } catch (err) {
        status.className = 'status error';
        status.innerHTML = '✗ خطأ: ' + err.message;
    }
    btn.disabled = false;
    btn.textContent = 'تسجيل الدخول';
    loadHistory();
});

// Bulk Login
async function startBulk() {
    if (csvAccounts.length === 0) return;
    const btn = document.getElementById('bulkBtn');
    const status = document.getElementById('bulkStatus');
    const bar = document.getElementById('progressBar');
    const fill = document.getElementById('progressFill');

    btn.disabled = true;
    bar.style.display = 'block';
    fill.style.width = '0%';
    status.className = 'status loading';
    status.innerHTML = '<span class="spinner"></span> جاري تسجيل ' + csvAccounts.length + ' حساب...';

    try {
        const resp = await fetch('/login_bulk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({accounts: csvAccounts})
        });
        const data = await resp.json();

        // Poll for progress
        if (data.task_id) {
            pollTask(data.task_id);
        }
    } catch (err) {
        status.className = 'status error';
        status.innerHTML = '✗ خطأ: ' + err.message;
        btn.disabled = false;
    }
}

async function pollTask(taskId) {
    const status = document.getElementById('bulkStatus');
    const fill = document.getElementById('progressFill');
    const btn = document.getElementById('bulkBtn');

    const interval = setInterval(async () => {
        try {
            const resp = await fetch('/task_status/' + taskId);
            const data = await resp.json();
            const pct = Math.round((data.done / data.total) * 100);
            fill.style.width = pct + '%';
            status.className = 'status loading';
            status.innerHTML = '<span class="spinner"></span> ' + data.done + '/' + data.total +
                ' (' + data.success + ' نجح، ' + data.failed + ' فشل)';

            if (data.finished) {
                clearInterval(interval);
                if (data.failed === 0) {
                    status.className = 'status success';
                    status.innerHTML = '✓ تم تسجيل ' + data.success + ' حساب بنجاح!';
                } else {
                    status.className = data.success > 0 ? 'status success' : 'status error';
                    status.innerHTML = 'نجح: ' + data.success + ' | فشل: ' + data.failed;
                }
                btn.disabled = false;
                loadHistory();
            }
        } catch(e) {}
    }, 2000);
}

// History
async function loadHistory() {
    try {
        const resp = await fetch('/history');
        const data = await resp.json();
        const el = document.getElementById('results');
        if (data.accounts && data.accounts.length > 0) {
            let html = '<h3>الحسابات المسجلة (' + data.accounts.length + ')</h3>';
            data.accounts.forEach(a => {
                html += '<div class="acc-card"><span class="user">@' + a.username +
                    '</span><span class="badge ok">✓ متصل</span></div>';
            });
            el.innerHTML = html;
        } else {
            el.innerHTML = '';
        }
    } catch(e) {}
}
loadHistory();

// API Test
async function testApi() {
    const user = document.getElementById('apiTestUser').value.trim();
    const pass = document.getElementById('apiTestPass').value;
    if (!user || !pass) return;

    const btn = document.getElementById('apiTestBtn');
    const result = document.getElementById('apiResult');
    const pre = document.getElementById('apiResultPre');

    btn.disabled = true;
    btn.textContent = 'جاري الارسال...';
    result.style.display = 'block';
    pre.textContent = '⏳ جاري تسجيل الدخول...';

    try {
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: user, password: pass})
        });
        const data = await resp.json();
        pre.textContent = JSON.stringify(data, null, 2);
        loadHistory();
    } catch (err) {
        pre.textContent = 'Error: ' + err.message;
    }
    btn.disabled = false;
    btn.textContent = 'ارسال طلب API';
}
</script>
</body>
</html>
"""


def run_login(username, password, cookies_dir=COOKIES_DIR):
    """تشغيل تسجيل الدخول كـ subprocess منفصل"""
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "x_auth.login_sync", username, password, cookies_dir],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        cwd=str(Path(__file__).parent)
    )
    output = result.stdout + result.stderr
    # البحث عن النتيجة
    for line in output.split("\n"):
        if line.startswith("__RESULT__"):
            return json.loads(line[10:])
    # إذا لم نجد النتيجة
    raise Exception(f"فشل تسجيل الدخول: {output[-500:]}")



@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/login", methods=["POST"])
def do_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "error": "أدخل اسم المستخدم وكلمة المرور"})

    try:
        result = run_login(username, password)
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/login_bulk", methods=["POST"])
def do_login_bulk():
    global task_counter
    data = request.get_json()
    accounts = data.get("accounts", [])

    if not accounts:
        return jsonify({"success": False, "error": "لا توجد حسابات"})

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
            username = acc.get("username", "").strip()
            password = acc.get("password", "").strip()
            try:
                result = run_login(username, password)
                if result.get("success"):
                    login_tasks[task_id]["success"] += 1
                    login_tasks[task_id]["results"][username] = {"success": True}
                    print(f"[OK] {username}")
                else:
                    login_tasks[task_id]["failed"] += 1
                    login_tasks[task_id]["results"][username] = result
                    print(f"[FAIL] {username}: {result.get('error','')}")
            except Exception as e:
                login_tasks[task_id]["failed"] += 1
                login_tasks[task_id]["results"][username] = {"success": False, "error": str(e)}
                print(f"[FAIL] {username}: {e}")
            login_tasks[task_id]["done"] += 1
            # تأخير بين الحسابات
            if i < len(accounts) - 1:
                time.sleep(5)
        login_tasks[task_id]["finished"] = True

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    return jsonify({"success": True, "task_id": task_id})


@app.route("/task_status/<task_id>")
def task_status(task_id):
    task = login_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/history")
def history():
    cookies_dir = Path(COOKIES_DIR)
    accounts = []
    if cookies_dir.exists():
        for f in sorted(cookies_dir.glob("*.json")):
            accounts.append({"username": f.stem, "file": str(f)})
    return jsonify({"accounts": accounts})


# ============================================================
#  API Endpoints
# ============================================================

@app.route("/api/login", methods=["POST"])
def api_login():
    """POST /api/login — تسجيل دخول حساب واحد"""
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
    """POST /api/login/bulk — تسجيل عدة حسابات (غير متزامن)"""
    global task_counter
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body مطلوب"}), 400

    accounts = data.get("accounts", [])
    delay = data.get("delay", 5)

    if not accounts:
        return jsonify({"success": False, "error": "accounts مطلوب"}), 400

    for i, acc in enumerate(accounts):
        if not acc.get("username") or not acc.get("password"):
            return jsonify({"success": False, "error": f"الحساب {i+1} ينقصه username أو password"}), 400

    with task_lock:
        task_counter += 1
        task_id = str(task_counter)

    login_tasks[task_id] = {
        "total": len(accounts), "done": 0, "success": 0,
        "failed": 0, "finished": False, "results": {}
    }

    def worker():
        for i, acc in enumerate(accounts):
            username = acc["username"].strip()
            password = acc["password"].strip()
            try:
                result = run_login(username, password)
                if result.get("success"):
                    login_tasks[task_id]["success"] += 1
                    login_tasks[task_id]["results"][username] = {"success": True}
                else:
                    login_tasks[task_id]["failed"] += 1
                    login_tasks[task_id]["results"][username] = {"success": False, "error": result.get("error", "")}
            except Exception as e:
                login_tasks[task_id]["failed"] += 1
                login_tasks[task_id]["results"][username] = {"success": False, "error": str(e)}
            login_tasks[task_id]["done"] += 1
            if i < len(accounts) - 1:
                time.sleep(delay)
        login_tasks[task_id]["finished"] = True

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"success": True, "task_id": task_id, "total": len(accounts)})


@app.route("/api/tasks/<task_id>", methods=["GET"])
def api_task_status(task_id):
    """GET /api/tasks/<id> — حالة مهمة"""
    task = login_tasks.get(task_id)
    if not task:
        return jsonify({"error": "المهمة غير موجودة"}), 404
    return jsonify(task)


@app.route("/api/accounts", methods=["GET"])
def api_accounts():
    """GET /api/accounts — قائمة الحسابات"""
    cookies_dir = Path(COOKIES_DIR)
    accounts = []
    if cookies_dir.exists():
        for f in sorted(cookies_dir.glob("*.json")):
            accounts.append({"username": f.stem, "cookies_file": str(f)})
    return jsonify({"accounts": accounts, "total": len(accounts)})


@app.route("/api/cookies/<username>", methods=["GET"])
def api_get_cookies(username):
    """GET /api/cookies/<user> — جلب كوكيز"""
    cookie_file = Path(COOKIES_DIR) / f"{username}.json"
    if not cookie_file.exists():
        return jsonify({"error": f"كوكيز {username} غير موجودة"}), 404

    with open(cookie_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    auth_token = ""
    ct0 = ""
    all_cookies = {}
    if isinstance(data, dict) and 'cookies' in data:
        for c in data['cookies']:
            all_cookies[c['name']] = c['value']
            if c['name'] == 'auth_token': auth_token = c['value']
            elif c['name'] == 'ct0': ct0 = c['value']
    else:
        all_cookies = data
        auth_token = data.get('auth_token', '')
        ct0 = data.get('ct0', '')

    return jsonify({"username": username, "auth_token": auth_token, "ct0": ct0, "all_cookies": all_cookies})


@app.route("/api/cookies/<username>", methods=["DELETE"])
def api_delete_cookies(username):
    """DELETE /api/cookies/<user> — حذف كوكيز"""
    cookie_file = Path(COOKIES_DIR) / f"{username}.json"
    if not cookie_file.exists():
        return jsonify({"error": f"كوكيز {username} غير موجودة"}), 404
    os.remove(cookie_file)
    return jsonify({"success": True, "message": f"تم حذف كوكيز {username}"})


@app.route("/api/health", methods=["GET"])
def api_health():
    """GET /api/health — حالة السيرفر"""
    cookies_dir = Path(COOKIES_DIR)
    count = len(list(cookies_dir.glob("*.json"))) if cookies_dir.exists() else 0
    return jsonify({
        "status": "ok",
        "accounts_count": count,
        "active_tasks": sum(1 for t in login_tasks.values() if not t["finished"])
    })


if __name__ == "__main__":
    print("=" * 45)
    print("  X Login - Flask GUI")
    print("  http://127.0.0.1:5000")
    print("=" * 45)
    app.run(debug=False, port=5000)
