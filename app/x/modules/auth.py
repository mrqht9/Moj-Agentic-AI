import os
from functools import wraps
from flask import request, jsonify, session, redirect, url_for


def get_tokens():
    raw = os.getenv('XSUITE_API_TOKENS', 'your-secure-token-here')
    tokens = [t.strip() for t in raw.split(',') if t.strip()]
    return set(tokens)


def require_api_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.lower().startswith('bearer '):
            return jsonify({'success': False, 'error': 'Missing Bearer token'}), 401
        token = auth.split(' ', 1)[1].strip()
        if token not in get_tokens():
            return jsonify({'success': False, 'error': 'Invalid token'}), 403
        return fn(*args, **kwargs)
    return wrapper


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('system_login'))
        return fn(*args, **kwargs)
    return wrapper
