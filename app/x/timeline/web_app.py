"""
تطبيق Flask لسحب تغريدات تويتر مع واجهة احترافية
"""
import json
import os
import sys
import random
import re
import secrets
import hashlib
import requests
import time
import csv
import io
import sqlite3
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, jsonify, redirect,
                   url_for, flash, session, send_file, abort)

# اصلاح ترميز الكونسول في Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

app = Flask(__name__)

# [FIX-1] Secret key عشوائي يتغير مع كل تشغيل (او يُحفظ في ملف)
SECRET_KEY_FILE = 'secret.key'
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(app.secret_key)

# [FIX-6] تأمين Session Cookies
app.config['JSON_AS_ASCII'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=6)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request

@app.template_filter('from_json')
def from_json_filter(s):
    try:
        if s and s != '[]' and s != '{}':
            return json.loads(s)
        return []
    except Exception:
        return []

@app.template_global()
def now():
    return datetime.now()

# [FIX-2] كلمة المرور مشفرة بـ SHA-256 + Salt
# غيّر كلمة المرور من هنا:
ADMIN_USER = "admin"
ADMIN_SALT = "x9k2m_scraper_salt_2025"
def _hash_pass(password):
    return hashlib.sha256(f"{ADMIN_SALT}{password}".encode()).hexdigest()
ADMIN_PASS_HASH = _hash_pass("Mm112233@@")  # غيّر admin123 لكلمة مرور اقوى

# [FIX-4] حماية Brute Force
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# حالة السحب الجارية
scrape_status = {}
scrape_lock = threading.Lock()

# [FIX-9] CSRF Token
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def validate_csrf_token():
    token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token', '')
    if not token or token != session.get('_csrf_token'):
        abort(403)

app.jinja_env.globals['csrf_token'] = generate_csrf_token

# [FIX-7] Security Headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

# ======================= قاعدة البيانات =======================
# [FIX-11] Context manager لمنع تسريب الاتصالات
from contextlib import contextmanager

@contextmanager
def get_db_ctx():
    conn = sqlite3.connect('scraper.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_db():
    conn = sqlite3.connect('scraper.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            tweet_id TEXT UNIQUE,
            rest_id TEXT,
            full_text TEXT,
            note_text TEXT,
            created_at TEXT,
            lang TEXT,
            source TEXT,
            tweet_url TEXT,
            favorite_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            retweet_count INTEGER DEFAULT 0,
            quote_count INTEGER DEFAULT 0,
            bookmark_count INTEGER DEFAULT 0,
            views_count TEXT DEFAULT '0',
            views_state TEXT,
            favorited INTEGER DEFAULT 0,
            retweeted INTEGER DEFAULT 0,
            bookmarked INTEGER DEFAULT 0,
            is_quote_status INTEGER DEFAULT 0,
            possibly_sensitive INTEGER DEFAULT 0,
            conversation_id TEXT,
            display_text_range TEXT,
            is_translatable INTEGER DEFAULT 0,
            is_edit_eligible INTEGER DEFAULT 0,
            edits_remaining TEXT,
            editable_until_msecs TEXT,
            in_reply_to_status_id TEXT,
            in_reply_to_user_id TEXT,
            in_reply_to_screen_name TEXT,
            quoted_tweet_id TEXT,
            quoted_tweet_text TEXT,
            quoted_tweet_user TEXT,
            has_media INTEGER DEFAULT 0,
            media_count INTEGER DEFAULT 0,
            media_types TEXT DEFAULT '[]',
            media_urls TEXT DEFAULT '[]',
            video_urls TEXT DEFAULT '[]',
            hashtags TEXT DEFAULT '[]',
            user_mentions TEXT DEFAULT '[]',
            urls TEXT DEFAULT '[]',
            symbols TEXT DEFAULT '[]',
            card_name TEXT,
            card_url TEXT,
            card_title TEXT,
            card_description TEXT,
            user_id TEXT,
            screen_name TEXT,
            user_name TEXT,
            user_verified INTEGER DEFAULT 0,
            user_is_blue_verified INTEGER DEFAULT 0,
            user_followers_count INTEGER DEFAULT 0,
            user_following_count INTEGER DEFAULT 0,
            user_statuses_count INTEGER DEFAULT 0,
            user_favourites_count INTEGER DEFAULT 0,
            user_listed_count INTEGER DEFAULT 0,
            user_media_count INTEGER DEFAULT 0,
            user_location TEXT,
            user_description TEXT,
            user_profile_image_url TEXT,
            user_profile_banner_url TEXT,
            user_created_at TEXT,
            user_url TEXT,
            user_protected INTEGER DEFAULT 0,
            is_retweet INTEGER DEFAULT 0,
            is_reply INTEGER DEFAULT 0,
            extracted_at TEXT,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scrape_jobs (
            id TEXT PRIMARY KEY,
            username TEXT,
            requested_count INTEGER,
            actual_count INTEGER DEFAULT 0,
            include_retweets INTEGER DEFAULT 0,
            include_replies INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            message TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME
        );

        CREATE INDEX IF NOT EXISTS idx_tweets_screen_name ON tweets(screen_name);
        CREATE INDEX IF NOT EXISTS idx_tweets_job_id ON tweets(job_id);
    ''')
    conn.commit()
    conn.close()

# ======================= Twitter API =======================
def load_cookies(path="coo.txt"):
    if not os.path.exists(path):
        return []
    cookies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                t1, t2 = parts
                if len(t1) > len(t2):
                    ct0, auth_token = t1, t2
                else:
                    auth_token, ct0 = t1, t2
                cookies.append((auth_token, ct0))
    return cookies

def make_headers(auth_token, ct0):
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-csrf-token": ct0,
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

def get_user_id(screen_name, headers):
    url = "https://x.com/i/api/graphql/-0XdHI-mrHWBQd8-oLo1aA/ProfileSpotlightsQuery"
    params = {"variables": json.dumps({"screen_name": screen_name})}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("data", {})
                .get("user_result_by_screen_name", {})
                .get("result", {})
                .get("rest_id"))
    except Exception:
        return None

GRAPHQL_FEATURES = {
    "rweb_video_screen_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": False,
    "responsive_web_grok_share_attachment_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_enhance_cards_enabled": False
}

# إعدادات التايم لاين الرئيسي (Home Timeline)
HOME_TIMELINE_QUERY_ID = "gKia-nBM9kwuDEfSDeWMfQ"
HOME_TIMELINE_URL = f"https://x.com/i/api/graphql/{HOME_TIMELINE_QUERY_ID}/HomeTimeline"

def extract_all_tweet_data(tweet_obj, screen_name):
    try:
        legacy = tweet_obj.get("legacy", {})
        core = tweet_obj.get("core", {})
        user_result = core.get("user_results", {}).get("result", {})
        user_legacy = user_result.get("legacy", {})
        user_core = user_result.get("core", {})  # تويتر نقل name/screen_name/created_at إلى هنا
        user_professional = user_result.get("professional", {}) or {}
        views_data = tweet_obj.get("views", {})
        edit_control = tweet_obj.get("edit_control", {})
        edit_initial = edit_control.get("edit_control_initial", edit_control)
        note_tweet = tweet_obj.get("note_tweet", {})
        note_result = note_tweet.get("note_tweet_results", {}).get("result", {})
        entities = legacy.get("entities", {})
        extended_entities = legacy.get("extended_entities", {})
        media_ext = extended_entities.get("media", [])
        media_ent = entities.get("media", [])
        media_data = media_ext if media_ext else media_ent
        card = tweet_obj.get("card", {})
        card_legacy = card.get("legacy", {})
        quoted = tweet_obj.get("quoted_status_result", {}).get("result", {})

        video_urls = []
        for m in media_data:
            vi = m.get("video_info", {})
            if vi:
                mp4s = [v for v in vi.get("variants", []) if v.get("content_type") == "video/mp4"]
                if mp4s:
                    best = max(mp4s, key=lambda v: v.get("bitrate", 0))
                    video_urls.append(best.get("url", ""))

        full_text = legacy.get("full_text", "")
        is_rt = 1 if full_text.startswith("RT @") else 0
        is_reply = 1 if legacy.get("in_reply_to_status_id_str") else 0

        card_title = ""
        card_desc = ""
        for bv in card_legacy.get("binding_values", []):
            k = bv.get("key", "")
            v = bv.get("value", {})
            if k == "title":
                card_title = v.get("string_value", "")
            elif k == "description":
                card_desc = v.get("string_value", "")

        return {
            "tweet_id": legacy.get("id_str", tweet_obj.get("rest_id", "")),
            "rest_id": tweet_obj.get("rest_id", ""),
            "full_text": full_text,
            "note_text": note_result.get("text", ""),
            "created_at": legacy.get("created_at", ""),
            "lang": legacy.get("lang", ""),
            "source": tweet_obj.get("source", ""),
            "tweet_url": f"https://x.com/{screen_name}/status/{legacy.get('id_str', tweet_obj.get('rest_id', ''))}",
            "favorite_count": legacy.get("favorite_count", 0),
            "reply_count": legacy.get("reply_count", 0),
            "retweet_count": legacy.get("retweet_count", 0),
            "quote_count": legacy.get("quote_count", 0),
            "bookmark_count": legacy.get("bookmark_count", 0),
            "views_count": str(views_data.get("count", "0")),
            "views_state": views_data.get("state", ""),
            "favorited": legacy.get("favorited", False),
            "retweeted": legacy.get("retweeted", False),
            "bookmarked": legacy.get("bookmarked", False),
            "is_quote_status": legacy.get("is_quote_status", False),
            "possibly_sensitive": legacy.get("possibly_sensitive", False),
            "conversation_id": legacy.get("conversation_id_str", ""),
            "display_text_range": json.dumps(legacy.get("display_text_range", []), ensure_ascii=False),
            "is_translatable": tweet_obj.get("is_translatable", False),
            "is_edit_eligible": edit_initial.get("is_edit_eligible", False),
            "edits_remaining": str(edit_initial.get("edits_remaining", "")),
            "editable_until_msecs": str(edit_initial.get("editable_until_msecs", "")),
            "in_reply_to_status_id": legacy.get("in_reply_to_status_id_str", ""),
            "in_reply_to_user_id": legacy.get("in_reply_to_user_id_str", ""),
            "in_reply_to_screen_name": legacy.get("in_reply_to_screen_name", ""),
            "quoted_tweet_id": quoted.get("rest_id", ""),
            "quoted_tweet_text": quoted.get("legacy", {}).get("full_text", ""),
            "quoted_tweet_user": quoted.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name", ""),
            "has_media": len(media_data) > 0,
            "media_count": len(media_data),
            "media_types": json.dumps([m.get("type", "") for m in media_data], ensure_ascii=False),
            "media_urls": json.dumps([m.get("media_url_https", "") for m in media_data], ensure_ascii=False),
            "video_urls": json.dumps(video_urls, ensure_ascii=False),
            "hashtags": json.dumps([t.get("text", "") for t in entities.get("hashtags", [])], ensure_ascii=False),
            "user_mentions": json.dumps([{"id": m.get("id_str", ""), "screen_name": m.get("screen_name", ""), "name": m.get("name", "")} for m in entities.get("user_mentions", [])], ensure_ascii=False),
            "urls": json.dumps([{"url": u.get("url", ""), "expanded_url": u.get("expanded_url", ""), "display_url": u.get("display_url", "")} for u in entities.get("urls", [])], ensure_ascii=False),
            "symbols": json.dumps([s.get("text", "") for s in entities.get("symbols", [])], ensure_ascii=False),
            "card_name": card_legacy.get("name", ""),
            "card_url": card_legacy.get("url", ""),
            "card_title": card_title,
            "card_description": card_desc,
            "user_id": user_result.get("rest_id", ""),
            "screen_name": screen_name or user_core.get("screen_name", ""),
            "user_name": user_core.get("name", "") or user_legacy.get("name", ""),
            "user_verified": user_legacy.get("verified", False),
            "user_is_blue_verified": user_result.get("is_blue_verified", False),
            "user_followers_count": user_legacy.get("followers_count", 0),
            "user_following_count": user_legacy.get("friends_count", 0),
            "user_statuses_count": user_legacy.get("statuses_count", 0),
            "user_favourites_count": user_legacy.get("favourites_count", 0),
            "user_listed_count": user_legacy.get("listed_count", 0),
            "user_media_count": user_legacy.get("media_count", 0),
            "user_location": user_legacy.get("location", ""),
            "user_description": user_legacy.get("description", ""),
            "user_profile_image_url": user_legacy.get("profile_image_url_https", ""),
            "user_profile_banner_url": user_legacy.get("profile_banner_url", ""),
            "user_created_at": user_core.get("created_at", "") or user_legacy.get("created_at", ""),
            "user_url": user_legacy.get("url", ""),
            "user_protected": user_legacy.get("protected", False),
            "is_retweet": is_rt,
            "is_reply": is_reply,
            "extracted_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"[X] extract error: {e}")
        return None

# [FIX-5] قائمة بيضاء للأعمدة المسموحة - يمنع SQL Injection عبر أسماء الأعمدة
ALLOWED_COLUMNS = {
    "job_id", "tweet_id", "rest_id", "full_text", "note_text", "created_at",
    "lang", "source", "tweet_url", "favorite_count", "reply_count",
    "retweet_count", "quote_count", "bookmark_count", "views_count",
    "views_state", "favorited", "retweeted", "bookmarked", "is_quote_status",
    "possibly_sensitive", "conversation_id", "display_text_range",
    "is_translatable", "is_edit_eligible", "edits_remaining",
    "editable_until_msecs", "in_reply_to_status_id", "in_reply_to_user_id",
    "in_reply_to_screen_name", "quoted_tweet_id", "quoted_tweet_text",
    "quoted_tweet_user", "has_media", "media_count", "media_types",
    "media_urls", "video_urls", "hashtags", "user_mentions", "urls",
    "symbols", "card_name", "card_url", "card_title", "card_description",
    "user_id", "screen_name", "user_name", "user_verified",
    "user_is_blue_verified", "user_followers_count", "user_following_count",
    "user_statuses_count", "user_favourites_count", "user_listed_count",
    "user_media_count", "user_location", "user_description",
    "user_profile_image_url", "user_profile_banner_url", "user_created_at",
    "user_url", "user_protected", "is_retweet", "is_reply", "extracted_at"
}

def save_tweet_to_db(tweet_data, job_id):
    try:
        tweet_data["job_id"] = job_id
        # فقط الأعمدة المسموحة
        safe_data = {k: v for k, v in tweet_data.items() if k in ALLOWED_COLUMNS}
        cols = list(safe_data.keys())
        placeholders = ", ".join(["?" for _ in cols])
        vals = []
        for c in cols:
            v = safe_data[c]
            if isinstance(v, bool):
                vals.append(int(v))
            else:
                vals.append(v)
        with get_db_ctx() as conn:
            conn.execute(
                f"INSERT OR IGNORE INTO tweets ({', '.join(cols)}) VALUES ({placeholders})",
                vals
            )
        return True
    except Exception as e:
        print(f"[X] DB save error: {e}")
        return False

# ======================= عملية السحب =======================
def run_scrape(job_id, username, count, include_rt, include_replies):
    global scrape_status
    with scrape_lock:
        scrape_status[job_id] = {
            "saved": 0, "skipped_rt": 0, "skipped_reply": 0,
            "page": 0, "status": "running", "message": "جاري البدء..."
        }

    try:
        cookies = load_cookies("coo.txt")
        if not cookies:
            with scrape_lock:
                scrape_status[job_id]["status"] = "error"
                scrape_status[job_id]["message"] = "ملف الكوكيز غير موجود او فارغ"
            _finish_job(job_id, 0, "error", scrape_status[job_id]["message"])
            return

        with scrape_lock:
            scrape_status[job_id]["message"] = "جاري سحب التايم لاين الرئيسي..."

        saved = 0
        seen_ids = set()
        cursor = None
        page = 1
        sk_rt = 0
        sk_reply = 0

        while saved < count:
            with scrape_lock:
                scrape_status[job_id]["page"] = page
                scrape_status[job_id]["message"] = f"صفحة {page} - محفوظ {saved}/{count}"

            body = {
                "variables": {
                    "count": 20,
                    "includePromotedContent": False,
                    "latestControlAvailable": True,
                    "requestContext": "launch",
                    "withCommunity": True,
                    "seenTweetIds": []
                },
                "features": GRAPHQL_FEATURES,
                "queryId": HOME_TIMELINE_QUERY_ID
            }
            if cursor:
                body["variables"]["cursor"] = cursor

            try:
                auth_token, ct0 = random.choice(cookies)
                headers = make_headers(auth_token, ct0)
                resp = requests.post(HOME_TIMELINE_URL, headers=headers, json=body, timeout=30)
                if resp.status_code == 429:
                    with scrape_lock:
                        scrape_status[job_id]["message"] = "Rate limit - انتظار 60 ثانية..."
                    time.sleep(60)
                    continue
                resp.raise_for_status()
                response_data = resp.json()
            except Exception as e:
                with scrape_lock:
                    scrape_status[job_id]["message"] = f"خطا في الطلب: {str(e)[:80]}"
                break

            instructions = (response_data.get("data", {})
                .get("home", {}).get("home_timeline_urt", {})
                .get("instructions", []))

            entries_in_page = 0
            next_cursor = None

            for instr in instructions:
                for entry in instr.get("entries", []):
                    eid = entry.get("entryId", "")
                    if eid.startswith("cursor-bottom-"):
                        next_cursor = entry.get("content", {}).get("value")
                        continue
                    if not eid.startswith("tweet-"):
                        continue
                    entries_in_page += 1
                    try:
                        tr = entry["content"]["itemContent"]["tweet_results"]["result"]
                        if tr.get("__typename") == "TweetWithVisibilityResults":
                            tr = tr.get("tweet", tr)
                        if tr.get("__typename") != "Tweet":
                            continue
                        leg = tr.get("legacy", {})
                        ft = leg.get("full_text", "")
                        tid = leg.get("id_str", tr.get("rest_id", ""))
                        if tid in seen_ids:
                            continue
                        seen_ids.add(tid)

                        if ft.startswith("RT @") and not include_rt:
                            sk_rt += 1
                            with scrape_lock:
                                scrape_status[job_id]["skipped_rt"] = sk_rt
                            continue
                        if leg.get("in_reply_to_status_id_str") and not include_replies:
                            sk_reply += 1
                            with scrape_lock:
                                scrape_status[job_id]["skipped_reply"] = sk_reply
                            continue

                        # اسم صاحب التغريدة (كل تغريدة من حساب مختلف في التايم لاين)
                        _ur = tr.get("core", {}).get("user_results", {}).get("result", {})
                        sn = (_ur.get("core", {}).get("screen_name", "")
                              or _ur.get("legacy", {}).get("screen_name", ""))
                        td = extract_all_tweet_data(tr, sn)
                        if td and save_tweet_to_db(td, job_id):
                            saved += 1
                            with scrape_lock:
                                scrape_status[job_id]["saved"] = saved
                                scrape_status[job_id]["message"] = f"[{saved}/{count}] {ft[:50]}..."

                        if saved >= count:
                            break
                    except (KeyError, TypeError):
                        continue
                if saved >= count:
                    break

            if saved >= count:
                break

            if next_cursor and entries_in_page > 0:
                cursor = next_cursor
                page += 1
                time.sleep(random.uniform(2.0, 4.0))
            else:
                break

        msg = f"تم حفظ {saved} تغريدة | تخطي RT: {sk_rt} | تخطي ردود: {sk_reply}"
        with scrape_lock:
            scrape_status[job_id]["status"] = "done"
            scrape_status[job_id]["saved"] = saved
            scrape_status[job_id]["message"] = msg
        _finish_job(job_id, saved, "done", msg)

    except Exception as e:
        with scrape_lock:
            scrape_status[job_id]["status"] = "error"
            scrape_status[job_id]["message"] = str(e)
        _finish_job(job_id, 0, "error", str(e))

    # [FIX-10] تنظيف الذاكرة بعد 60 ثانية من انتهاء العملية
    def cleanup():
        time.sleep(60)
        with scrape_lock:
            scrape_status.pop(job_id, None)
    threading.Thread(target=cleanup, daemon=True).start()

def _finish_job(job_id, actual_count, status, message):
    try:
        conn = get_db()
        conn.execute(
            "UPDATE scrape_jobs SET actual_count=?, status=?, message=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
            (actual_count, status, message, job_id)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ======================= المسارات =======================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# [FIX-8] التحقق من صحة اسم المستخدم
def sanitize_username(username):
    username = username.strip().lstrip("@")
    if not re.match(r'^[a-zA-Z0-9_]{1,50}$', username):
        return None
    return username

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # [FIX-4] فحص Brute Force
        ip = request.remote_addr
        now_time = datetime.now()
        if ip in login_attempts:
            attempts, lockout_until = login_attempts[ip]
            if lockout_until and now_time < lockout_until:
                remaining = int((lockout_until - now_time).total_seconds() / 60) + 1
                flash(f"تم قفل الحساب مؤقتا. حاول بعد {remaining} دقيقة", "error")
                return render_template("login_new.html")

        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")

        # [FIX-2] مقارنة بالهاش وليس النص الصريح
        if u == ADMIN_USER and _hash_pass(p) == ADMIN_PASS_HASH:
            session["logged_in"] = True
            session.permanent = True
            login_attempts.pop(ip, None)
            return redirect(url_for("index"))

        # تسجيل المحاولة الفاشلة
        attempts, _ = login_attempts.get(ip, (0, None))
        attempts += 1
        if attempts >= MAX_LOGIN_ATTEMPTS:
            login_attempts[ip] = (attempts, now_time + timedelta(minutes=LOCKOUT_MINUTES))
            flash(f"تم قفل الحساب لمدة {LOCKOUT_MINUTES} دقيقة بسبب كثرة المحاولات", "error")
        else:
            login_attempts[ip] = (attempts, None)
            flash(f"بيانات خاطئة. المحاولات المتبقية: {MAX_LOGIN_ATTEMPTS - attempts}", "error")

    return render_template("login_new.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    conn = get_db()
    total_tweets = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(DISTINCT screen_name) FROM tweets").fetchone()[0]
    total_jobs = conn.execute("SELECT COUNT(*) FROM scrape_jobs").fetchone()[0]
    recent_jobs = conn.execute("SELECT * FROM scrape_jobs ORDER BY started_at DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("index_new.html",
        total_tweets=total_tweets, total_users=total_users,
        total_jobs=total_jobs, recent_jobs=recent_jobs)

@app.route("/scrape", methods=["GET", "POST"])
@login_required
def scrape():
    if request.method == "POST":
        # [FIX-9] CSRF
        validate_csrf_token()

        # سحب التايم لاين الرئيسي للحساب نفسه - لا حاجة لاسم مستخدم
        username = "home_timeline"

        try:
            count = int(request.form.get("count", 100))
        except (ValueError, TypeError):
            count = 100

        include_rt = request.form.get("include_rt") == "on"
        include_replies = request.form.get("include_replies") == "on"

        count = max(1, min(count, 5000))

        job_id = f"{username}_{secrets.token_hex(4)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        conn = get_db()
        conn.execute(
            "INSERT INTO scrape_jobs (id, username, requested_count, include_retweets, include_replies) VALUES (?,?,?,?,?)",
            (job_id, username, count, int(include_rt), int(include_replies))
        )
        conn.commit()
        conn.close()

        t = threading.Thread(target=run_scrape, args=(job_id, username, count, include_rt, include_replies), daemon=True)
        t.start()

        return redirect(url_for("job_progress", job_id=job_id))

    return render_template("scrape_new.html")

@app.route("/progress/<job_id>")
@login_required
def job_progress(job_id):
    return render_template("progress_new.html", job_id=job_id)

@app.route("/api/status/<job_id>")
@login_required
def api_status(job_id):
    with scrape_lock:
        st = scrape_status.get(job_id, {})
    if not st:
        conn = get_db()
        job = conn.execute("SELECT * FROM scrape_jobs WHERE id=?", (job_id,)).fetchone()
        conn.close()
        if job:
            return jsonify({"status": job["status"], "saved": job["actual_count"],
                "message": job["message"] or "", "page": 0, "skipped_rt": 0, "skipped_reply": 0})
    return jsonify(st)

@app.route("/tweets")
@login_required
def tweets_list():
    username = request.args.get("username", "").strip()
    job_id = request.args.get("job_id", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 50

    conn = get_db()
    where = []
    params = []
    if username:
        where.append("LOWER(screen_name) = LOWER(?)")
        params.append(username)
    if job_id:
        where.append("job_id = ?")
        params.append(job_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = conn.execute(f"SELECT COUNT(*) FROM tweets {where_sql}", params).fetchone()[0]
    offset = (page - 1) * per_page
    tweets = conn.execute(
        f"SELECT * FROM tweets {where_sql} ORDER BY saved_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    users = conn.execute("SELECT DISTINCT screen_name FROM tweets ORDER BY screen_name").fetchall()
    jobs = conn.execute("SELECT id, username, actual_count, started_at FROM scrape_jobs ORDER BY started_at DESC LIMIT 50").fetchall()
    conn.close()

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template("tweets_new.html",
        tweets=tweets, total=total, page=page, total_pages=total_pages,
        username=username, job_id=job_id, users=users, jobs=jobs)

@app.route("/export/csv")
@login_required
def export_csv():
    username = request.args.get("username", "").strip()
    job_id = request.args.get("job_id", "").strip()

    conn = get_db()
    where = []
    params = []
    if username:
        where.append("LOWER(screen_name) = LOWER(?)")
        params.append(username)
    if job_id:
        where.append("job_id = ?")
        params.append(job_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"SELECT * FROM tweets {where_sql} ORDER BY saved_at DESC", params).fetchall()
    conn.close()

    if not rows:
        flash("لا توجد تغريدات للتصدير", "error")
        return redirect(url_for("tweets_list"))

    output = io.StringIO()
    fieldnames = rows[0].keys()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))

    data = output.getvalue().encode("utf-8-sig")
    output.close()

    fname = f"tweets_{username or 'all'}_{len(rows)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(io.BytesIO(data), mimetype="text/csv; charset=utf-8",
                     as_attachment=True, download_name=fname)

@app.route("/tweet/<tweet_id>")
@login_required
def tweet_detail(tweet_id):
    conn = get_db()
    tweet = conn.execute("SELECT * FROM tweets WHERE tweet_id=?", (tweet_id,)).fetchone()
    conn.close()
    if not tweet:
        flash("التغريدة غير موجودة", "error")
        return redirect(url_for("tweets_list"))
    return render_template("tweet_detail_new.html", tweet=dict(tweet))

@app.route("/api/delete_job/<job_id>", methods=["POST"])
@login_required
def delete_job(job_id):
    # [FIX-12] CSRF validation
    token = request.headers.get('X-CSRF-Token', '') or request.form.get('_csrf_token', '')
    if not token or token != session.get('_csrf_token'):
        abort(403)
    # [FIX-8] Validate job_id format
    if not re.match(r'^[a-zA-Z0-9_]{1,100}$', job_id):
        abort(400)
    with get_db_ctx() as conn:
        conn.execute("DELETE FROM tweets WHERE job_id=?", (job_id,))
        conn.execute("DELETE FROM scrape_jobs WHERE id=?", (job_id,))
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()
    print("[OK] تم تشغيل التطبيق")
    print("[>>] http://0.0.0.0:5637")
    print(f"[>>] المستخدم: {ADMIN_USER}")
    app.run(debug=False, host="0.0.0.0", port=5637)
