import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from modules.auth import login_required, require_api_token
from modules.db import (
    delete_cookie,
    get_cookie_by_label,
    get_cookie_by_id,
    get_operation,
    init_db,
    list_cookies,
    list_operations,
    log_operation,
    stats as db_stats,
    upsert_cookie,
)
from modules.utils import download_to_temp, is_url, safe_label
from modules.x_login import TwitterLoginAdvanced
from modules.x_post import post_to_x
from modules.x_profile import update_profile_on_x

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
COOKIES_DIR = BASE_DIR / 'cookies'
COOKIES_DIR.mkdir(exist_ok=True)

ADMIN_USER = os.getenv('XSUITE_ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('XSUITE_ADMIN_PASS', 'Mm112233@@')
DEFAULT_HEADLESS = os.getenv('XSUITE_DEFAULT_HEADLESS', '0') == '1'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me')


@app.before_request
def _ensure_db():
    init_db()


# =====================
# System Login (Dashboard)
# =====================
@app.route('/system-login', methods=['GET', 'POST'])
def system_login():
    if request.method == 'GET':
        return render_template('login_system.html')

    u = (request.form.get('username') or '').strip()
    p = (request.form.get('password') or '').strip()
    if u == ADMIN_USER and p == ADMIN_PASS:
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    flash('بيانات الدخول غير صحيحة', 'error')
    return redirect(url_for('system_login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('system_login'))


# =====================
# Dashboard Pages
# =====================
@app.route('/')
def dashboard():
    s = db_stats()
    recent = list_operations(limit=20)
    return render_template('dashboard.html', title='لوحة التحكم', header='لوحة التحكم', subtitle='ملخص سريع للعمليات', active='dashboard', stats=s, recent=recent)


@app.route('/cookies', methods=['GET', 'POST'])
def cookies_page():
    if request.method == 'POST':
        label = safe_label(request.form.get('label', ''))
        f = request.files.get('file')
        if not label:
            flash('اكتب اسم الحساب', 'error')
            return redirect(url_for('cookies_page'))
        if not f or not f.filename:
            flash('ارفع ملف JSON', 'error')
            return redirect(url_for('cookies_page'))
        dst = COOKIES_DIR / f"{label}.json"
        f.save(dst)
        upsert_cookie(label, dst.name)
        log_operation('cookie_upload', label, 'success', f'تم حفظ الكوكيز: {dst.name}')
        flash('تم حفظ الكوكيز ✅', 'success')
        return redirect(url_for('cookies_page'))

    cookies = list_cookies()
    return render_template('cookies.html', title='الكوكيز', header='إدارة الكوكيز', subtitle='إضافة/حذف الحسابات', active='cookies', cookies=cookies)


@app.route('/cookies/<int:cookie_id>/delete', methods=['POST'])
def cookie_delete(cookie_id: int):
    c = get_cookie_by_id(cookie_id)
    if not c:
        flash('الحساب غير موجود', 'error')
        return redirect(url_for('cookies_page'))

    deleted = delete_cookie(cookie_id)
    try:
        (COOKIES_DIR / deleted['filename']).unlink(missing_ok=True)
    except Exception:
        pass
    log_operation('cookie_delete', deleted.get('label'), 'success', f"تم حذف {deleted.get('filename')}")
    flash('تم حذف الحساب ✅', 'success')
    return redirect(url_for('cookies_page'))


@app.route('/x-login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('x_login.html', title='تسجيل دخول X', header='تسجيل دخول X', subtitle='حفظ storage_state باسم الحساب', active='login')

    label = safe_label(request.form.get('label', ''))
    username = (request.form.get('username') or '').strip()
    password = (request.form.get('password') or '').strip()
    headless = (request.form.get('headless') == '1')

    op_id = log_operation('login', label, 'pending', 'بدأت عملية تسجيل الدخول', meta_json=json.dumps({'headless': headless}))

    try:
        engine = TwitterLoginAdvanced()
        cookie_path = engine.login_twitter(username=username, password=password, cookies_dir=str(COOKIES_DIR), headless=headless)
        # rename file to label.json if needed
        dst = COOKIES_DIR / f"{label}.json"
        try:
            if cookie_path.name != dst.name:
                Path(cookie_path).replace(dst)
        except Exception:
            pass

        upsert_cookie(label, dst.name)
        log_operation('login', label, 'success', f'تم حفظ الكوكيز: {dst.name}')
        flash('تم تسجيل الدخول وحفظ الكوكيز ✅', 'success')
        return redirect(url_for('cookies_page'))
    except Exception as e:
        log_operation('login', label, 'error', f'فشل تسجيل الدخول: {e}')
        flash(f'فشل تسجيل الدخول: {e}', 'error')
        return redirect(url_for('login_page'))


@app.route('/post', methods=['GET', 'POST'])
def post_page():
    cookies = list_cookies()
    if request.method == 'GET':
        return render_template('post.html', title='نشر منشور', header='نشر منشور', subtitle='اختر حساب ثم انشر', active='post', cookies=cookies)

    cookie_label = (request.form.get('cookie_label') or '').strip()
    text = (request.form.get('text') or '').strip()
    headless = (request.form.get('headless') == '1')
    media_url = (request.form.get('media_url') or '').strip()
    media_file = request.files.get('media_file')

    if not cookie_label:
        flash('اختر حساب', 'error')
        return redirect(url_for('post_page'))
    if not text:
        flash('اكتب نص المنشور', 'error')
        return redirect(url_for('post_page'))

    c = get_cookie_by_label(cookie_label)
    if not c:
        flash('هذا الحساب غير موجود', 'error')
        return redirect(url_for('post_page'))

    storage_state_path = str(COOKIES_DIR / c['filename'])

    with tempfile.TemporaryDirectory() as tmp:
        media_path = None
        if media_file and media_file.filename:
            media_path = os.path.join(tmp, media_file.filename)
            media_file.save(media_path)
        elif media_url and is_url(media_url):
            try:
                media_path = download_to_temp(media_url, tmp)
            except Exception as e:
                flash(f'فشل تنزيل الميديا: {e}', 'error')
                return redirect(url_for('post_page'))

        try:
            post_to_x(storage_state_path=storage_state_path, text=text, media_path=media_path, headless=headless)
            log_operation('post', cookie_label, 'success', 'تمت محاولة النشر ✅', meta_json=json.dumps({'headless': headless}))
            flash('تمت محاولة النشر ✅', 'success')
        except Exception as e:
            log_operation('post', cookie_label, 'error', f'فشل النشر: {e}', meta_json=json.dumps({'headless': headless}))
            flash(f'فشل النشر: {e}', 'error')

    return redirect(url_for('post_page'))


@app.route('/profile', methods=['GET', 'POST'])
def profile_page():
    cookies = list_cookies()
    if request.method == 'GET':
        return render_template('profile.html', title='تعديل بروفايل', header='تعديل بروفايل', subtitle='اختر حساب ثم عدّل البيانات', active='profile', cookies=cookies)

    cookie_label = (request.form.get('cookie_label') or '').strip()
    c = get_cookie_by_label(cookie_label)
    if not c:
        flash('اختر حساب صحيح', 'error')
        return redirect(url_for('profile_page'))

    name = (request.form.get('name') or '').strip()
    bio = (request.form.get('bio') or '').strip()
    location = (request.form.get('location') or '').strip()
    website = (request.form.get('website') or '').strip()
    headless = (request.form.get('headless') == '1')

    avatar_url = (request.form.get('avatar_url') or '').strip()
    banner_url = (request.form.get('banner_url') or '').strip()
    avatar_file = request.files.get('avatar_file')
    banner_file = request.files.get('banner_file')

    storage_state_path = str(COOKIES_DIR / c['filename'])

    with tempfile.TemporaryDirectory() as tmp:
        avatar_path = None
        banner_path = None
        try:
            if avatar_file and avatar_file.filename:
                avatar_path = os.path.join(tmp, avatar_file.filename)
                avatar_file.save(avatar_path)
            elif avatar_url and is_url(avatar_url):
                avatar_path = download_to_temp(avatar_url, tmp)

            if banner_file and banner_file.filename:
                banner_path = os.path.join(tmp, banner_file.filename)
                banner_file.save(banner_path)
            elif banner_url and is_url(banner_url):
                banner_path = download_to_temp(banner_url, tmp)

            update_profile_on_x(
                storage_state_path=storage_state_path,
                name=name,
                bio=bio,
                location=location,
                website=website,
                avatar_path=avatar_path,
                banner_path=banner_path,
                headless=headless,
            )
            log_operation('profile', cookie_label, 'success', 'تم تعديل البروفايل (أو تمت المحاولة) ✅', meta_json=json.dumps({'headless': headless}))
            flash('تمت محاولة تعديل البروفايل ✅', 'success')
        except Exception as e:
            log_operation('profile', cookie_label, 'error', f'فشل تعديل البروفايل: {e}', meta_json=json.dumps({'headless': headless}))
            flash(f'فشل تعديل البروفايل: {e}', 'error')

    return redirect(url_for('profile_page'))


@app.route('/logs')
def logs_page():
    rows = list_operations(limit=200)
    return render_template('logs.html', title='السجل', header='سجل العمليات', subtitle='آخر 200 عملية', active='logs', rows=rows)


@app.route('/api')
def api_docs():
    return render_template('api.html', title='API', header='API', subtitle='توثيق سريع', active='')


# =====================
# API
# =====================
@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({'status': 'healthy', 'service': 'X Suite', 'version': '1.0'}), 200


@app.route('/api/cookies', methods=['GET'])
@require_api_token
def api_cookies():
    return jsonify({'success': True, 'cookies': list_cookies()}), 200


@app.route('/api/cookies/upload', methods=['POST'])
@require_api_token
def api_cookie_upload():
    label = safe_label(request.form.get('label', ''))
    f = request.files.get('file')
    if not label:
        return jsonify({'success': False, 'error': 'label required'}), 400
    if not f or not f.filename:
        return jsonify({'success': False, 'error': 'file required'}), 400
    dst = COOKIES_DIR / f"{label}.json"
    f.save(dst)
    upsert_cookie(label, dst.name)
    op_id = log_operation('cookie_upload', label, 'success', f'تم حفظ الكوكيز: {dst.name}')
    return jsonify({'success': True, 'id': op_id, 'label': label, 'filename': dst.name}), 200


@app.route('/api/login', methods=['POST'])
@require_api_token
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    label = safe_label(data.get('label', ''))
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    headless = bool(data.get('headless', False))

    if not label or not username or not password:
        return jsonify({'success': False, 'error': 'label/username/password required'}), 400

    op_id = log_operation('login', label, 'pending', 'بدأت عملية تسجيل الدخول', meta_json=json.dumps({'headless': headless}))
    try:
        engine = TwitterLoginAdvanced()
        cookie_path = engine.login_twitter(username=username, password=password, cookies_dir=str(COOKIES_DIR), headless=headless)
        dst = COOKIES_DIR / f"{label}.json"
        try:
            if Path(cookie_path).name != dst.name:
                Path(cookie_path).replace(dst)
        except Exception:
            pass
        upsert_cookie(label, dst.name)
        log_operation('login', label, 'success', f'تم حفظ الكوكيز: {dst.name}')
        return jsonify({'success': True, 'task_id': op_id, 'cookie_label': label, 'filename': dst.name}), 200
    except Exception as e:
        log_operation('login', label, 'error', f'فشل تسجيل الدخول: {e}')
        return jsonify({'success': False, 'task_id': op_id, 'error': str(e)}), 500


@app.route('/api/post', methods=['POST'])
@require_api_token
def api_post():
    # supports JSON or multipart
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json(force=True, silent=True) or {}
        cookie_label = (data.get('cookie_label') or '').strip()
        text = (data.get('text') or '').strip()
        headless = bool(data.get('headless', True))
        media_url = (data.get('media_url') or '').strip()
        if not cookie_label or not text:
            return jsonify({'success': False, 'error': 'cookie_label and text required'}), 400
        c = get_cookie_by_label(cookie_label)
        if not c:
            return jsonify({'success': False, 'error': 'cookie not found'}), 404
        storage_state_path = str(COOKIES_DIR / c['filename'])
        op_id = log_operation('post', cookie_label, 'pending', 'بدأت عملية النشر', meta_json=json.dumps({'headless': headless}))
        with tempfile.TemporaryDirectory() as tmp:
            media_path = None
            if media_url and is_url(media_url):
                try:
                    media_path = download_to_temp(media_url, tmp)
                except Exception as e:
                    log_operation('post', cookie_label, 'error', f'فشل تنزيل الميديا: {e}')
                    return jsonify({'success': False, 'task_id': op_id, 'error': f'فشل تنزيل الميديا: {e}'}), 400
            try:
                post_to_x(storage_state_path, text, media_path, headless=headless)
                log_operation('post', cookie_label, 'success', 'تمت محاولة النشر ✅')
                return jsonify({'success': True, 'task_id': op_id, 'message': 'تمت محاولة النشر ✅'}), 200
            except Exception as e:
                log_operation('post', cookie_label, 'error', f'فشل النشر: {e}')
                return jsonify({'success': False, 'task_id': op_id, 'error': str(e)}), 500

    # multipart
    cookie_label = (request.form.get('cookie_label') or '').strip()
    text = (request.form.get('text') or '').strip()
    headless = (request.form.get('headless') == '1')
    media_url = (request.form.get('media_url') or '').strip()
    media_file = request.files.get('media_file')

    if not cookie_label or not text:
        return jsonify({'success': False, 'error': 'cookie_label and text required'}), 400
    c = get_cookie_by_label(cookie_label)
    if not c:
        return jsonify({'success': False, 'error': 'cookie not found'}), 404
    storage_state_path = str(COOKIES_DIR / c['filename'])

    op_id = log_operation('post', cookie_label, 'pending', 'بدأت عملية النشر', meta_json=json.dumps({'headless': headless}))

    with tempfile.TemporaryDirectory() as tmp:
        media_path = None
        if media_file and media_file.filename:
            media_path = os.path.join(tmp, media_file.filename)
            media_file.save(media_path)
        elif media_url and is_url(media_url):
            try:
                media_path = download_to_temp(media_url, tmp)
            except Exception as e:
                log_operation('post', cookie_label, 'error', f'فشل تنزيل الميديا: {e}')
                return jsonify({'success': False, 'task_id': op_id, 'error': f'فشل تنزيل الميديا: {e}'}), 400

        try:
            post_to_x(storage_state_path, text, media_path, headless=headless)
            log_operation('post', cookie_label, 'success', 'تمت محاولة النشر ✅')
            return jsonify({'success': True, 'task_id': op_id, 'message': 'تمت محاولة النشر ✅'}), 200
        except Exception as e:
            log_operation('post', cookie_label, 'error', f'فشل النشر: {e}')
            return jsonify({'success': False, 'task_id': op_id, 'error': str(e)}), 500


@app.route('/api/profile/update', methods=['POST'])
@require_api_token
def api_profile_update():
    cookie_label = (request.form.get('cookie_label') or '').strip()
    c = get_cookie_by_label(cookie_label)
    if not c:
        return jsonify({'success': False, 'error': 'cookie not found'}), 404

    name = (request.form.get('name') or '').strip()
    bio = (request.form.get('bio') or '').strip()
    location = (request.form.get('location') or '').strip()
    website = (request.form.get('website') or '').strip()
    headless = (request.form.get('headless') == '1')

    avatar_url = (request.form.get('avatar_url') or '').strip()
    banner_url = (request.form.get('banner_url') or '').strip()
    avatar_file = request.files.get('avatar_file')
    banner_file = request.files.get('banner_file')

    storage_state_path = str(COOKIES_DIR / c['filename'])
    op_id = log_operation('profile', cookie_label, 'pending', 'بدأت عملية تعديل البروفايل', meta_json=json.dumps({'headless': headless}))

    with tempfile.TemporaryDirectory() as tmp:
        avatar_path = None
        banner_path = None
        try:
            if avatar_file and avatar_file.filename:
                avatar_path = os.path.join(tmp, avatar_file.filename)
                avatar_file.save(avatar_path)
            elif avatar_url and is_url(avatar_url):
                avatar_path = download_to_temp(avatar_url, tmp)

            if banner_file and banner_file.filename:
                banner_path = os.path.join(tmp, banner_file.filename)
                banner_file.save(banner_path)
            elif banner_url and is_url(banner_url):
                banner_path = download_to_temp(banner_url, tmp)

            update_profile_on_x(
                storage_state_path=storage_state_path,
                name=name,
                bio=bio,
                location=location,
                website=website,
                avatar_path=avatar_path,
                banner_path=banner_path,
                headless=headless,
            )
            log_operation('profile', cookie_label, 'success', 'تم تعديل البروفايل (أو تمت المحاولة) ✅')
            return jsonify({'success': True, 'task_id': op_id, 'message': 'تمت محاولة تعديل البروفايل ✅'}), 200
        except Exception as e:
            log_operation('profile', cookie_label, 'error', f'فشل تعديل البروفايل: {e}')
            return jsonify({'success': False, 'task_id': op_id, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
@require_api_token
def api_stats():
    return jsonify({'success': True, 'stats': db_stats()}), 200


@app.route('/api/logs', methods=['GET'])
@require_api_token
def api_logs():
    limit = int(request.args.get('limit', '100'))
    limit = max(1, min(500, limit))
    return jsonify({'success': True, 'logs': list_operations(limit=limit)}), 200


@app.route('/api/task/<int:task_id>', methods=['GET'])
@require_api_token
def api_task(task_id: int):
    op = get_operation(task_id)
    if not op:
        return jsonify({'success': False, 'error': 'not found'}), 404
    return jsonify({'success': True, 'task': op}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5789'))
    app.run(host='0.0.0.0', port=port, debug=True)
