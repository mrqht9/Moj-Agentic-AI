from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import sqlite3
import csv
import io
import json
import random
import requests
import time
from datetime import datetime
import os
import threading
import atexit

# إنشاء تطبيق Flask مع دعم UTF-8
app = Flask(__name__)
app.secret_key = 'twitter_scraper_secret_key_2025_secure'

# إعداد Flask للتعامل مع UTF-8 والنصوص العربية
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'

# بيانات تسجيل الدخول الثابتة
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'twitter2025'

# 🆕 إعدادات الويب هوك
WEBHOOK_URL = "https://n8n.srv968786.hstgr.cloud/webhook/xpost"
WEBHOOK_ENABLED = True  # تفعيل/إلغاء تفعيل الويب هوك

# إعداد المجدولة للمهام الخلفية - الحل المُصحح
scheduler = None

def create_scheduler():
    """إنشاء وإعداد المجدولة بشكل صحيح"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
        print("✅ تم إنشاء المجدولة")
    return scheduler

def init_scheduler():
    """تشغيل المجدولة بشكل آمن"""
    global scheduler
    try:
        if scheduler is None:
            scheduler = create_scheduler()
        
        if not scheduler.running:
            scheduler.start()
            print("🚀 تم تشغيل المجدولة بنجاح")
            
            # تسجيل إيقاف المجدولة عند إغلاق التطبيق
            atexit.register(lambda: scheduler.shutdown() if scheduler and scheduler.running else None)
            
    except Exception as e:
        print(f"❌ خطأ في تشغيل المجدولة: {e}")

# ========== نموذج المستخدم ==========
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User('admin')
    return None

# 🆕 دوال الويب هوك
def get_user_webhook_config(username: str):
    """جلب إعدادات الويب هوك للمستخدم"""
    try:
        conn = sqlite3.connect('twitter_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT webhook_url, webhook_enabled
            FROM webhook_settings
            WHERE username = ?
        """, (username,))
        row = cursor.fetchone()
        conn.close()

        if row and row["webhook_url"]:
            return row["webhook_url"], bool(row["webhook_enabled"])

        return None, None
    except Exception as e:
        print(f"❌ Webhook config error @{username}: {e}")
        return None, None


def send_webhook(webhook_url: str, tweet_data: dict):
    """إرسال Webhook متوافق مع n8n"""
    try:
        payload = {
            "event": "tweet.new",
            "source": "twitter-monitor",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "tweet_id": tweet_data.get("tweet_id"),
                "text": tweet_data.get("full_text"),
                "lang": tweet_data.get("lang"),
                "created_at": tweet_data.get("created_at"),
                "url": f"https://twitter.com/{tweet_data.get('screen_name')}/status/{tweet_data.get('tweet_id')}",

                "metrics": {
                    "likes": tweet_data.get("favorite_count", 0),
                    "retweets": tweet_data.get("retweet_count", 0),
                    "replies": tweet_data.get("reply_count", 0),
                    "views": int(tweet_data.get("views_count", "0") or 0)
                },

                "media": {
                    "has_media": tweet_data.get("has_media", False),
                    "media_count": tweet_data.get("media_count", 0),
                    "media_types": json.loads(tweet_data.get("media_types", "[]") or "[]"),
                    "media_urls": json.loads(tweet_data.get("media_urls", "[]") or "[]")
                },

                "user": {
                    "username": tweet_data.get("screen_name"),
                    "display_name": tweet_data.get("user_name"),
                    "verified": bool(tweet_data.get("user_verified")),
                    "followers": tweet_data.get("user_followers_count", 0),
                    "following": tweet_data.get("user_following_count", 0)
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Twitter-Monitor/2.0"
        }

        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )

        success = 200 <= response.status_code < 300
        message = (response.text or "").strip()
        if len(message) > 500:
            message = message[:500] + "..."

        return success, message, response.status_code

    except requests.exceptions.Timeout:
        return False, "Timeout", None
    except requests.exceptions.ConnectionError:
        return False, "Connection error", None
    except Exception as e:
        return False, str(e), None


def send_webhook_with_logging(webhook_url, tweet_data, username):
    """إرسال Webhook + تسجيل كامل"""
    success, message, status_code = send_webhook(webhook_url, tweet_data)

    try:
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO webhook_logs
            (username, tweet_id, webhook_url, status, response_code, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            tweet_data.get("tweet_id"),
            webhook_url,
            "success" if success else "error",
            status_code,
            message
        ))

        if success:
            cursor.execute("""
                INSERT INTO webhook_settings
                (username, webhook_url, webhook_enabled, last_sent_tweet_id, total_sent, updated_timestamp)
                VALUES (?, ?, 1, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(username) DO UPDATE SET
                    last_sent_tweet_id=excluded.last_sent_tweet_id,
                    total_sent=webhook_settings.total_sent + 1,
                    updated_timestamp=CURRENT_TIMESTAMP
            """, (
                username,
                webhook_url,
                tweet_data.get("tweet_id")
            ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"❌ Webhook logging error: {e}")

    return success, message


# ========== إضافة الفلاتر المخصصة المُصححة ==========
@app.template_filter('from_json')
def from_json_filter(json_str):
    """فلتر لتحويل النص JSON إلى كائن Python"""
    try:
        if json_str and json_str != '[]' and json_str != '{}':
            return json.loads(json_str)
        return []
    except (json.JSONDecodeError, TypeError):
        return []

@app.template_filter('safe_json')
def safe_json_filter(data):
    """فلتر آمن لتحويل البيانات إلى JSON"""
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return '{}'

@app.template_filter('format_number')
def format_number_filter(number):
    """فلتر لتنسيق الأرقام"""
    try:
        if isinstance(number, str) and number.isdigit():
            number = int(number)
        elif isinstance(number, str):
            return number
        
        if number >= 1000000:
            return f"{number/1000000:.1f}م"
        elif number >= 1000:
            return f"{number/1000:.1f}ك"
        return str(number)
    except (ValueError, TypeError):
        return str(number)

@app.template_filter('format_number')
def format_number_filter(number):
    """فلتر لتنسيق الأرقام"""
    try:
        if isinstance(number, str) and number.isdigit():
            number = int(number)
        elif isinstance(number, str):
            return number
        
        if number >= 1000000:
            return f"{number/1000000:.1f}م"
        elif number >= 1000:
            return f"{number/1000:.1f}ك"
        return str(number)
    except (ValueError, TypeError):
        return str(number)

# 🔧 أضف أو عدل هذا الفلتر هنا
@app.template_filter('truncate_text')
def truncate_text_filter(text, length=100):
    """فلتر لاقتصار النص"""
    if not text:
        return ""
    if len(text) <= length:
        return text
    return text[:length] + "..."

@app.template_filter('format_date')
def format_date_filter(date_str):
    """فلتر لتنسيق التاريخ"""
    try:
        if not date_str:
            return ""
        if 'GMT' in date_str or '+0000' in date_str:
            dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
            return dt.strftime("%Y-%m-%d %H:%M")
        elif 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        return date_str
    except (ValueError, TypeError):
        return date_str

@app.template_filter('truncate_text')
def truncate_text_filter(text, length=100):
    """فلتر لاقتصار النص"""
    if not text:
        return ""
    if len(text) <= length:
        return text
    return text[:length] + "..."

@app.template_filter('format_date')
def format_date_filter(date_str):
    """فلتر لتنسيق التاريخ"""
    try:
        if not date_str:
            return ""
        if 'GMT' in date_str or '+0000' in date_str:
            dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
            return dt.strftime("%Y-%m-%d %H:%M")
        elif 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        return date_str
    except (ValueError, TypeError):
        return date_str

@app.template_filter('unique')
def unique_filter(items):
    """فلتر للحصول على العناصر الفريدة"""
    try:
        if isinstance(items, list):
            return list(set(items))
        return items
    except:
        return items

@app.template_filter('selectattr')
def selectattr_filter(items, attr):
    """فلتر لتحديد العناصر التي لها خاصية معينة"""
    try:
        result = []
        for item in items:
            if isinstance(item, dict) and item.get(attr):
                result.append(item)
            elif hasattr(item, attr) and getattr(item, attr):
                result.append(item)
        return result
    except:
        return []

@app.template_filter('map')
def map_filter(items, attribute=None):
    """فلتر لاستخراج خاصية معينة من قائمة العناصر - مُصحح"""
    try:
        if not items:
            return []
        
        result = []
        for item in items:
            if attribute:
                if isinstance(item, dict) and attribute in item:
                    result.append(item[attribute])
                elif hasattr(item, attribute):
                    result.append(getattr(item, attribute))
                else:
                    try:
                        result.append(item[attribute])
                    except (KeyError, IndexError):
                        pass
            else:
                result.append(item)
        
        return result
    except Exception as e:
        print(f"خطأ في فلتر map: {e}")
        return []

@app.template_filter('extract')
def extract_filter(items, key):
    """فلتر لاستخراج قيم معينة من قائمة العناصر"""
    try:
        result = []
        for item in items:
            if isinstance(item, dict) and key in item:
                result.append(item[key])
            elif hasattr(item, key):
                result.append(getattr(item, key))
            else:
                try:
                    result.append(item[key])
                except:
                    pass
        return result
    except:
        return []

@app.template_filter('pluck')
def pluck_filter(items, attribute):
    """فلتر لاستخراج خاصية معينة (بديل map|attribute)"""
    try:
        if not items:
            return []
            
        result = []
        for item in items:
            try:
                if isinstance(item, dict):
                    if attribute in item:
                        result.append(item[attribute])
                elif hasattr(item, attribute):
                    result.append(getattr(item, attribute))
                else:
                    value = item[attribute]
                    result.append(value)
            except (KeyError, AttributeError, IndexError, TypeError):
                continue
                
        return result
    except Exception as e:
        print(f"خطأ في فلتر pluck: {e}")
        return []

# دوال التاريخ والوقت - مُصححة بالكامل
@app.template_global()
def current_datetime():
    """الحصول على الوقت الحالي"""
    return datetime.now().isoformat()

@app.template_global()
def utc_datetime():
    """الحصول على الوقت العالمي"""
    return datetime.utcnow().isoformat()

@app.template_global()
def now():
    """الحصول على الوقت الحالي - مبسط"""
    return datetime.now().isoformat()

@app.template_global()
def datetime_now():
    """إرجاع كائن datetime حالي"""
    return datetime.now()

@app.template_global()
def moment(date_input=None):
    """دعم moment.js مبسط - بدون عمليات حسابية معقدة"""
    if date_input is None:
        return datetime.now()
    elif isinstance(date_input, str):
        try:
            return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
        except:
            return datetime.now()
    return date_input

@app.template_filter('now_iso')
def now_iso_filter():
    """فلتر الوقت الحالي ISO"""
    return datetime.now().isoformat()

@app.template_filter('to_datetime')
def to_datetime_filter(date_str):
    """تحويل نص التاريخ إلى datetime"""
    try:
        if isinstance(date_str, str):
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_str
    except:
        return datetime.now()

@app.template_filter('time_since')
def time_since_filter(date_str):
    """حساب الوقت المنقضي منذ تاريخ معين"""
    try:
        if isinstance(date_str, str):
            past_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            past_date = date_str
            
        now = datetime.now()
        diff = now - past_date
        
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "الآن"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}د"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}ساعة"
        else:
            days = seconds // 86400
            return f"{days} يوم"
    except:
        return "غير معروف"

# ========== دوال قاعدة البيانات مع دعم الويب هوك ==========
def create_database():
    """إنشاء قاعدة البيانات والجداول المطلوبة - مع إضافة جداول الويب هوك"""
    conn = sqlite3.connect('twitter_data.db')
    cursor = conn.cursor()
    
    # جدول التغريدات الرئيسي
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tweet_id TEXT UNIQUE NOT NULL,
        user_id TEXT,
        screen_name TEXT,
        user_name TEXT,
        full_text TEXT,
        created_at TEXT,
        favorite_count INTEGER DEFAULT 0,
        reply_count INTEGER DEFAULT 0,
        retweet_count INTEGER DEFAULT 0,
        quote_count INTEGER DEFAULT 0,
        bookmark_count INTEGER DEFAULT 0,
        views_count TEXT DEFAULT '0',
        lang TEXT,
        source TEXT,
        is_quote_status BOOLEAN DEFAULT 0,
        possibly_sensitive BOOLEAN DEFAULT 0,
        conversation_id TEXT,
        display_text_range TEXT,
        user_verified BOOLEAN DEFAULT 0,
        user_followers_count INTEGER DEFAULT 0,
        user_following_count INTEGER DEFAULT 0,
        user_statuses_count INTEGER DEFAULT 0,
        user_location TEXT,
        user_description TEXT,
        user_profile_image_url TEXT,
        user_created_at TEXT,
        user_url TEXT,
        user_protected BOOLEAN DEFAULT 0,
        is_edit_eligible BOOLEAN DEFAULT 0,
        edits_remaining TEXT DEFAULT '0',
        editable_until_msecs TEXT DEFAULT '0',
        edit_history_tweet_ids TEXT DEFAULT '[]',
        has_media BOOLEAN DEFAULT 0,
        media_count INTEGER DEFAULT 0,
        media_types TEXT DEFAULT '[]',
        media_urls TEXT DEFAULT '[]',
        hashtags TEXT DEFAULT '[]',
        user_mentions TEXT DEFAULT '[]',
        urls TEXT DEFAULT '[]',
        symbols TEXT DEFAULT '[]',
        in_reply_to_status_id TEXT,
        in_reply_to_user_id TEXT,
        in_reply_to_screen_name TEXT,
        extracted_at TEXT,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # جدول المراقبة التلقائية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monitoring_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        interval_seconds INTEGER DEFAULT 60,
        is_active BOOLEAN DEFAULT 1,
        last_tweet_id TEXT,
        last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_fetched INTEGER DEFAULT 0
    )
    ''')
    
    # جدول سجل المراقبة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monitoring_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        status TEXT,
        message TEXT,
        tweet_id TEXT,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # جدول تفاصيل الوسائط
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tweet_id TEXT,
        media_id TEXT,
        media_key TEXT,
        media_type TEXT,
        media_url TEXT,
        display_url TEXT,
        expanded_url TEXT,
        width INTEGER,
        height INTEGER,
        duration_millis INTEGER,
        alt_text TEXT,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tweet_id) REFERENCES tweets (tweet_id)
    )
    ''')
    
    # 🆕 جدول إعدادات الويب هوك
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS webhook_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        webhook_url TEXT,
        webhook_enabled BOOLEAN DEFAULT 1,
        last_sent_tweet_id TEXT,
        total_sent INTEGER DEFAULT 0,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 🆕 جدول سجل الويب هوك
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS webhook_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        tweet_id TEXT,
        webhook_url TEXT,
        status TEXT,
        response_code INTEGER,
        message TEXT,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # جدول الاستجابات الخام
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        response_data TEXT,
        response_type TEXT DEFAULT 'latest_tweet',
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def get_tweets_from_database(username=None, limit=None, search_text=None, lang=None):
    """استخراج التغريدات من قاعدة البيانات مع فلاتر"""
    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        where = []
        params = []

        if username:
            where.append("LOWER(screen_name) = LOWER(?)")
            params.append(username.strip())

        if search_text:
            where.append("full_text LIKE ?")
            params.append(f"%{search_text}%")

        if lang:
            where.append("lang = ?")
            params.append(lang)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        lim = int(limit or 50)

        query = f"""
            SELECT * FROM tweets
            {where_sql}
            ORDER BY created_timestamp DESC
            LIMIT ?
        """
        params.append(lim)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        # نُحوّلها إلى dict لتكون القوالب أكثر ثباتاً
        return [dict(r) for r in rows]

    except sqlite3.Error as e:
        print(f"خطأ في الاستعلام: {e}")
        return []
    finally:
        conn.close()

def get_database_stats():
    """إحصائيات قاعدة البيانات"""
    conn = sqlite3.connect('twitter_data.db')
    cursor = conn.cursor()
    
    stats = {}
    
    try:
        # عدد التغريدات
        cursor.execute('SELECT COUNT(*) FROM tweets')
        stats['tweets_count'] = cursor.fetchone()[0]
        
        # عدد المستخدمين
        cursor.execute('SELECT COUNT(DISTINCT screen_name) FROM tweets')
        stats['users_count'] = cursor.fetchone()[0]
        
        # عدد الوسائط
        cursor.execute('SELECT COUNT(*) FROM media_details')
        stats['media_count'] = cursor.fetchone()[0]
        
        # عدد مهام المراقبة النشطة
        cursor.execute('SELECT COUNT(*) FROM monitoring_jobs WHERE is_active = 1')
        stats['active_jobs'] = cursor.fetchone()[0]
        
        return stats
        
    except sqlite3.Error as e:
        print(f"خطأ في جلب الإحصائيات: {e}")
        return {'tweets_count': 0, 'users_count': 0, 'media_count': 0, 'active_jobs': 0}
    finally:
        conn.close()

def get_monitoring_jobs():
    """الحصول على قائمة مهام المراقبة"""
    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT * FROM monitoring_jobs 
        ORDER BY created_timestamp DESC
        ''')
        
        jobs = cursor.fetchall()
        return [dict(job) for job in jobs]
    except sqlite3.Error as e:
        print(f"خطأ في جلب مهام المراقبة: {e}")
        return []
    finally:
        conn.close()

def get_monitoring_logs(limit=50):
    """الحصول على سجلات المراقبة"""
    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT * FROM monitoring_logs 
        ORDER BY created_timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        logs = cursor.fetchall()
        return [dict(log) for log in logs]
    except sqlite3.Error as e:
        print(f"خطأ في جلب سجلات المراقبة: {e}")
        return []
    finally:
        conn.close()

def log_monitoring_action(username, action, status, message, tweet_id=None):
    """تسجيل إجراء المراقبة مع دعم الويب هوك"""
    try:
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO monitoring_logs (username, action, status, message, tweet_id)
        VALUES (?, ?, ?, ?, ?)
        ''', (username, action, status, message, tweet_id))
        
        conn.commit()
        conn.close()
        
        # طباعة السجل مع رموز تعبيرية
        status_icon = "✅" if status == "نجح" else "❌" if status == "خطأ" else "ℹ️"
        webhook_icon = "🎯" if action == "ويب هوك" else ""
        
        print(f"{status_icon}{webhook_icon} @{username} - {action} - {status} - {message}")
        
    except Exception as e:
        print(f"❌ خطأ في تسجيل الإجراء: {e}")

# ========== دوال Twitter API ==========
def load_cookies(path="coo.txt"):
    """تحميل الكوكيز من ملف نصي"""
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
    """إنشاء الهيدرز المطلوبة للطلبات"""
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-csrf-token": ct0,
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

def get_user_id(screen_name, headers):
    """الحصول على معرف المستخدم من اسم المستخدم"""
    url = "https://x.com/i/api/graphql/-0XdHI-mrHWBQd8-oLo1aA/ProfileSpotlightsQuery"
    params = {"variables": json.dumps({"screen_name": screen_name})}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        response_data = resp.json()
        
        user_id = (
            response_data.get("data", {})
                .get("user_result_by_screen_name", {})
                .get("result", {})
                .get("rest_id")
        )
        
        return user_id
    except Exception as e:
        print(f"خطأ في الحصول على معرف المستخدم: {e}")
        return None

def extract_comprehensive_tweet_data(tweet_obj, screen_name):
    """استخراج جميع بيانات التغريدة بشكل شامل"""
    try:
        legacy = tweet_obj.get("legacy", {})
        user_results = tweet_obj.get("core", {}).get("user_results", {})
        user_data = user_results.get("result", {}).get("legacy", {})
        user_core = user_results.get("result", {}).get("core", {})  # name/screen_name/created_at الجديدة
        views_data = tweet_obj.get("views", {})
        edit_control = tweet_obj.get("edit_control", {})
        entities = legacy.get("entities", {})
        extended_entities = legacy.get("extended_entities", {})
        media_data = entities.get("media", []) or extended_entities.get("media", [])
        
        tweet_data = {
            "tweet_id": legacy.get("id_str", tweet_obj.get("rest_id")),
            "user_id": tweet_obj.get("core", {}).get("user_results", {}).get("result", {}).get("rest_id"),
            "screen_name": screen_name or user_core.get("screen_name", ""),
            "user_name": user_core.get("name", "") or user_data.get("name", ""),
            "full_text": legacy.get("full_text", ""),
            "created_at": legacy.get("created_at", ""),
            "favorite_count": legacy.get("favorite_count", 0),
            "reply_count": legacy.get("reply_count", 0),
            "retweet_count": legacy.get("retweet_count", 0),
            "quote_count": legacy.get("quote_count", 0),
            "bookmark_count": legacy.get("bookmark_count", 0),
            "views_count": str(views_data.get("count", "0")) if views_data.get("count") != "–" else "0",
            "lang": legacy.get("lang", ""),
            "source": tweet_obj.get("source", ""),
            "is_quote_status": legacy.get("is_quote_status", False),
            "possibly_sensitive": legacy.get("possibly_sensitive", False),
            "conversation_id": legacy.get("conversation_id_str", ""),
            "display_text_range": json.dumps(legacy.get("display_text_range", []), ensure_ascii=False),
            "user_verified": user_data.get("verified", False),
            "user_followers_count": user_data.get("followers_count", 0),
            "user_following_count": user_data.get("friends_count", 0),
            "user_statuses_count": user_data.get("statuses_count", 0),
            "user_location": user_data.get("location", ""),
            "user_description": user_data.get("description", ""),
            "user_profile_image_url": user_data.get("profile_image_url_https", ""),
            "user_created_at": user_core.get("created_at", "") or user_data.get("created_at", ""),
            "user_url": user_data.get("url", ""),
            "user_protected": user_data.get("protected", False),
            "is_edit_eligible": edit_control.get("is_edit_eligible", False),
            "edits_remaining": str(edit_control.get("edits_remaining", "0")),
            "editable_until_msecs": str(edit_control.get("editable_until_msecs", "0")),
            "edit_history_tweet_ids": json.dumps(edit_control.get("edit_history_tweet_ids", []), ensure_ascii=False),
            "has_media": len(media_data) > 0,
            "media_count": len(media_data),
            "media_types": json.dumps([media.get("type") for media in media_data], ensure_ascii=False),
            "media_urls": json.dumps([media.get("media_url_https") for media in media_data], ensure_ascii=False),
            "hashtags": json.dumps([tag.get("text") for tag in entities.get("hashtags", [])], ensure_ascii=False),
            "user_mentions": json.dumps([{"screen_name": mention.get("screen_name"), "name": mention.get("name")} for mention in entities.get("user_mentions", [])], ensure_ascii=False),
            "urls": json.dumps([{"url": url.get("url"), "expanded_url": url.get("expanded_url")} for url in entities.get("urls", [])], ensure_ascii=False),
            "symbols": json.dumps([symbol.get("text") for symbol in entities.get("symbols", [])], ensure_ascii=False),
            "in_reply_to_status_id": legacy.get("in_reply_to_status_id_str", ""),
            "in_reply_to_user_id": legacy.get("in_reply_to_user_id_str", ""),
            "in_reply_to_screen_name": legacy.get("in_reply_to_screen_name", ""),
            "extracted_at": datetime.now().isoformat()
        }
        
        return tweet_data, media_data
        
    except Exception as e:
        print(f"خطأ في استخراج بيانات التغريدة: {e}")
        return None, []

def save_tweet_to_database(tweet_data, media_data, username):
    """حفظ التغريدة وبياناتها في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        # التحقق من وجود التغريدة
        cursor.execute('SELECT id FROM tweets WHERE tweet_id = ?', (tweet_data['tweet_id'],))
        existing = cursor.fetchone()
        
        if existing:
            # تحديث التغريدة الموجودة
            update_query = '''
            UPDATE tweets SET 
                favorite_count = ?, reply_count = ?, retweet_count = ?, 
                quote_count = ?, bookmark_count = ?, views_count = ?,
                extracted_at = ?, updated_timestamp = CURRENT_TIMESTAMP
            WHERE tweet_id = ?
            '''
            cursor.execute(update_query, (
                tweet_data['favorite_count'], tweet_data['reply_count'], 
                tweet_data['retweet_count'], tweet_data['quote_count'],
                tweet_data['bookmark_count'], tweet_data['views_count'],
                tweet_data['extracted_at'], tweet_data['tweet_id']
            ))
            action = "تحديث"
        else:
            # إدراج تغريدة جديدة
            columns = list(tweet_data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = list(tweet_data.values())
            
            insert_query = f'''
            INSERT INTO tweets ({", ".join(columns)})
            VALUES ({placeholders})
            '''
            
            cursor.execute(insert_query, values)
            action = "إضافة"
        
        # حفظ تفاصيل الوسائط
        if media_data:
            cursor.execute('DELETE FROM media_details WHERE tweet_id = ?', (tweet_data['tweet_id'],))
            
            for media in media_data:
                media_insert = '''
                INSERT INTO media_details (
                    tweet_id, media_id, media_key, media_type, media_url,
                    display_url, expanded_url, width, height, duration_millis, alt_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                cursor.execute(media_insert, (
                    tweet_data['tweet_id'], media.get("id_str", ""), media.get("media_key", ""),
                    media.get("type", ""), media.get("media_url_https", ""), media.get("display_url", ""),
                    media.get("expanded_url", ""), 
                    media.get("original_info", {}).get("width", 0),
                    media.get("original_info", {}).get("height", 0),
                    media.get("video_info", {}).get("duration_millis", 0),
                    media.get("alt_text", "")
                ))
        
        conn.commit()
        conn.close()
        
        return True, action
        
    except Exception as e:
        print(f"خطأ في حفظ التغريدة: {e}")
        return False, "خطأ"

# إعدادات التايم لاين الرئيسي (Home Timeline)
HOME_TIMELINE_QUERY_ID = "gKia-nBM9kwuDEfSDeWMfQ"
HOME_TIMELINE_URL = f"https://x.com/i/api/graphql/{HOME_TIMELINE_QUERY_ID}/HomeTimeline"


def fetch_latest_tweet_for_monitoring(username):
    """سحب آخر تغريدة أصلية من التايم لاين الرئيسي للحساب (يتجاهل إعادة التغريد)

    ملاحظة: تم تحويل المراقبة لتعتمد على التايم لاين الرئيسي (Home Timeline)
    الخاص بالحساب المرتبط بالكوكيز، بدلا من تغريدات حساب محدد.
    المعامل username يُستخدم للتسجيل/التتبع فقط.
    """
    try:
        cookies = load_cookies("coo.txt")
        if not cookies:
            log_monitoring_action(username, "فحص", "خطأ", "ملف الكوكيز غير موجود")
            return None, "ملف الكوكيز غير موجود"

        auth_token, ct0 = random.choice(cookies)
        headers = make_headers(auth_token, ct0)

        # سحب التايم لاين الرئيسي (Home Timeline) - لا يحتاج معرف مستخدم
        features = {
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

        body = {
            "variables": {
                "count": 20,
                "includePromotedContent": False,
                "latestControlAvailable": True,
                "requestContext": "launch",
                "withCommunity": True,
                "seenTweetIds": []
            },
            "features": features,
            "queryId": HOME_TIMELINE_QUERY_ID
        }

        resp = requests.post(HOME_TIMELINE_URL, headers=headers, json=body, timeout=30)

        if resp.status_code == 429:
            log_monitoring_action(username, "فحص", "تحذير", "تم الوصول إلى الحد الأقصى للطلبات")
            return None, "تم الوصول إلى الحد الأقصى للطلبات"

        resp.raise_for_status()
        response_data = resp.json()

        # استخراج تغريدات التايم لاين والبحث عن أول تغريدة أصلية
        instructions = (
            response_data.get("data", {})
                .get("home", {})
                .get("home_timeline_urt", {})
                .get("instructions", [])
        )

        for instr in instructions:
            for entry in instr.get("entries", []):
                eid = entry.get("entryId", "")

                if eid.startswith("tweet-"):
                    try:
                        tweet_obj = entry["content"]["itemContent"]["tweet_results"]["result"]

                        if tweet_obj.get("__typename") == "TweetWithVisibilityResults":
                            tweet_obj = tweet_obj.get("tweet", tweet_obj)

                        if tweet_obj.get("__typename") == "Tweet":
                            # 🎯 التحقق من أن التغريدة ليست إعادة تغريد
                            legacy = tweet_obj.get("legacy", {})
                            full_text = legacy.get("full_text", "")
                            
                            # ✅ تجاهل إعادة التغريد
                            if full_text.startswith("RT @"):
                                print(f"🔄 تجاهل إعادة تغريد: {full_text[:50]}...")
                                continue
                                
                            # ✅ تجاهل التغريدات المقتبسة إذا كانت مجرد اقتباس بدون إضافة
                            if legacy.get("is_quote_status", False):
                                # إذا كان النص فقط رابط لتغريدة أخرى، تجاهلها
                                if len(full_text.strip()) < 30 and "https://t.co/" in full_text:
                                    print(f"📋 تجاهل اقتباس بسيط: {full_text[:50]}...")
                                    continue
                            
                            # ✅ تجاهل الردود إذا كنت لا تريدها (اختياري)
                            if legacy.get("in_reply_to_status_id_str"):
                                print(f"💬 تجاهل رد: {full_text[:50]}...")
                                continue
                            
                            # ✅ هذه تغريدة أصلية - استخراج اسم صاحبها الفعلي من التايم لاين
                            _ur = tweet_obj.get("core", {}).get("user_results", {}).get("result", {})
                            sn = (_ur.get("core", {}).get("screen_name", "")
                                  or _ur.get("legacy", {}).get("screen_name", "") or username)
                            tweet_data, media_data = extract_comprehensive_tweet_data(tweet_obj, sn)
                            
                            if tweet_data:
                                print(f"✅ تم العثور على تغريدة أصلية: {tweet_data['tweet_id']}")
                                return tweet_data, None
                        
                    except Exception as e:
                        print(f"خطأ في معالجة التغريدة: {e}")
                        continue

        log_monitoring_action(username, "فحص", "تحذير", "لا توجد تغريدات أصلية")
        return None, "لا توجد تغريدات أصلية"
        
    except Exception as e:
        log_monitoring_action(username, "فحص", "خطأ", f"خطأ في الطلب: {str(e)}")
        return None, f"خطأ في الطلب: {str(e)}"

# 🆕 دوال المراقبة التلقائية مع الويب هوك
def monitor_user_tweets(username):
    """مراقبة تغريدات المستخدم وسحب الجديد منها - مع إرسال ويب هوك"""
    try:
        print(f"🔍 فحص التغريدات الجديدة للمستخدم: @{username}")
        
        # الحصول على آخر تغريدة محفوظة
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT last_tweet_id FROM monitoring_jobs WHERE username = ? AND is_active = 1',
            (username,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            print(f"⚠️ المهمة غير نشطة أو غير موجودة: @{username}")
            return
            
        last_tweet_id = result[0]
        conn.close()
        
        # سحب آخر تغريدة من تويتر
        tweet_data, error = fetch_latest_tweet_for_monitoring(username)
        
        if not tweet_data:
            log_monitoring_action(username, "مراقبة", "خطأ", error or "فشل في سحب التغريدة")
            return
        
        current_tweet_id = tweet_data.get("tweet_id")
        
        # التحقق إذا كانت التغريدة جديدة
        if last_tweet_id == current_tweet_id:
            log_monitoring_action(username, "مراقبة", "عادي", "لا توجد تغريدات جديدة")
            conn = sqlite3.connect('twitter_data.db')
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE monitoring_jobs
                SET last_checked = CURRENT_TIMESTAMP
                WHERE username = ?
            """, (username,))
            conn.commit()
            conn.close()
            return
        
        # حفظ التغريدة الجديدة
        success, action = save_tweet_to_database(tweet_data, [], username)
        
        if not success:
            log_monitoring_action(username, "مراقبة", "خطأ", "فشل في حفظ التغريدة")
            return
        
        # تحديث بيانات المراقبة
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE monitoring_jobs
            SET last_tweet_id = ?,
                last_checked = CURRENT_TIMESTAMP,
                total_fetched = total_fetched + 1
            WHERE username = ?
        """, (current_tweet_id, username))
        conn.commit()
        conn.close()

        # =====================================================
        # 🚨 Webhook (المعدل ✔)
        # =====================================================
        user_webhook_url, user_enabled = get_user_webhook_config(username)

        effective_webhook_url = user_webhook_url or WEBHOOK_URL
        effective_enabled = (
            user_enabled if user_enabled is not None else WEBHOOK_ENABLED
        )

        if effective_enabled and effective_webhook_url:
            try:
                webhook_success, webhook_message = send_webhook_with_logging(
                    effective_webhook_url,
                    tweet_data,
                    username
                )

                if webhook_success:
                    log_monitoring_action(
                        username,
                        "ويب هوك",
                        "نجح",
                        "تم إرسال التغريدة إلى n8n",
                        current_tweet_id
                    )
                    print(f"🎯 Webhook OK → @{username} ({current_tweet_id})")
                else:
                    log_monitoring_action(
                        username,
                        "ويب هوك",
                        "خطأ",
                        webhook_message,
                        current_tweet_id
                    )
                    print(f"⚠️ Webhook FAIL → @{username}: {webhook_message}")

            except Exception as webhook_error:
                log_monitoring_action(
                    username,
                    "ويب هوك",
                    "خطأ",
                    str(webhook_error),
                    current_tweet_id
                )
                print(f"❌ Webhook Exception: {webhook_error}")

        # =====================================================

        log_monitoring_action(
            username,
            "مراقبة",
            "نجح",
            f"تم {action} تغريدة جديدة",
            current_tweet_id
        )

        print(f"✅ تغريدة جديدة محفوظة @{username}: {current_tweet_id}")

    except Exception as e:
        log_monitoring_action(username, "مراقبة", "خطأ", f"خطأ عام: {str(e)}")
        print(f"❌ خطأ في مراقبة @{username}: {e}")


def start_monitoring_job(username, interval_seconds):
    """بدء مهمة مراقبة جديدة مع معالجة محسنة للأخطاء"""
    global scheduler
    
    try:
        print(f"🚀 محاولة بدء مراقبة @{username} كل {interval_seconds} ثانية")
        
        # التحقق من صحة المدخلات
        if interval_seconds < 10:
            print(f"❌ الحد الأدنى 10 ثواني، تم تعديل {interval_seconds} إلى 10")
            interval_seconds = 10
        
        if interval_seconds > 3600:
            print(f"⚠️ الحد الأقصى ساعة واحدة، تم تعديل {interval_seconds} إلى 3600")
            interval_seconds = 3600
        
        # التحقق من ملف الكوكيز أولاً
        if not os.path.exists("coo.txt"):
            log_monitoring_action(username, "بدء", "خطأ", "ملف coo.txt غير موجود")
            return False
        
        cookies = load_cookies("coo.txt")
        if not cookies:
            log_monitoring_action(username, "بدء", "خطأ", "ملف الكوكيز فارغ أو غير صالح")
            return False
        
        # التأكد من تشغيل المجدولة
        if scheduler is None:
            init_scheduler()
        
        if not scheduler.running:
            scheduler.start()
            print("🔄 تم تشغيل المجدولة")
        
        # إضافة المهمة إلى قاعدة البيانات
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        # التحقق من وجود المهمة
        cursor.execute('SELECT id, is_active FROM monitoring_jobs WHERE username = ?', (username,))
        existing = cursor.fetchone()
        
        if existing:
            # تحديث المهمة الموجودة
            cursor.execute('''
            UPDATE monitoring_jobs 
            SET interval_seconds = ?, is_active = 1, last_checked = CURRENT_TIMESTAMP
            WHERE username = ?
            ''', (interval_seconds, username))
            print(f"📝 تحديث مهمة موجودة للمستخدم @{username}")
        else:
            # إضافة مهمة جديدة
            cursor.execute('''
            INSERT INTO monitoring_jobs (username, interval_seconds, is_active)
            VALUES (?, ?, 1)
            ''', (username, interval_seconds))
            print(f"➕ إضافة مهمة جديدة للمستخدم @{username}")
        
        conn.commit()
        conn.close()
        
        # إضافة المهمة إلى المجدولة
        job_id = f"monitor_{username}"
        
        # إزالة المهمة إذا كانت موجودة
        try:
            scheduler.remove_job(job_id)
            print(f"🗑️ تم حذف المهمة السابقة {job_id}")
        except Exception as e:
            print(f"ℹ️ لا توجد مهمة سابقة للحذف")
        
        # إضافة مهمة جديدة
        scheduler.add_job(
            func=monitor_user_tweets,
            args=[username],
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            name=f"Monitor @{username}",
            replace_existing=True,
            misfire_grace_time=30,  # إعطاء مهلة 30 ثانية للمهام المتأخرة
            coalesce=True,  # دمج المهام المتراكمة
            max_instances=1  # مثيل واحد فقط من المهمة
        )
        
        print(f"✅ تم جدولة المهمة {job_id} بنجاح")
        
        # طباعة المهام المجدولة
        jobs = scheduler.get_jobs()
        print(f"📅 إجمالي المهام المجدولة: {len(jobs)}")
        for job in jobs:
            print(f"   - {job.id}: التشغيل التالي في {job.next_run_time}")
        
        # اختبار فوري للمهمة
        try:
            print(f"🧪 اختبار فوري للمراقبة...")
            monitor_user_tweets(username)
            print(f"✅ الاختبار الفوري نجح")
        except Exception as e:
            print(f"⚠️ الاختبار الفوري فشل: {e}")
        
        log_monitoring_action(username, "بدء", "نجح", f"تم بدء المراقبة كل {interval_seconds} ثانية")
        print(f"🎉 تم بدء مراقبة @{username} كل {interval_seconds} ثانية بنجاح")
        
        return True
        
    except Exception as e:
        log_monitoring_action(username, "بدء", "خطأ", f"فشل في بدء المراقبة: {str(e)}")
        print(f"❌ خطأ في بدء مراقبة @{username}: {e}")
        import traceback
        traceback.print_exc()
        return False

def stop_monitoring_job(username):
    """إيقاف مهمة المراقبة"""
    global scheduler
    
    try:
        # إيقاف المهمة في قاعدة البيانات
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE monitoring_jobs 
        SET is_active = 0 
        WHERE username = ?
        ''', (username,))
        
        conn.commit()
        conn.close()
        
        # إزالة المهمة من المجدولة
        if scheduler and scheduler.running:
            job_id = f"monitor_{username}"
            try:
                scheduler.remove_job(job_id)
                print(f"🗑️ تم حذف المهمة {job_id} من المجدولة")
            except Exception as e:
                print(f"ℹ️ المهمة غير موجودة في المجدولة: {e}")
        
        log_monitoring_action(username, "إيقاف", "نجح", "تم إيقاف المراقبة")
        print(f"⏸️ تم إيقاف مراقبة @{username}")
        
        return True
        
    except Exception as e:
        log_monitoring_action(username, "إيقاف", "خطأ", f"فشل في إيقاف المراقبة: {str(e)}")
        print(f"❌ خطأ في إيقاف مراقبة @{username}: {e}")
        return False

def restore_monitoring_jobs():
    """استعادة مهام المراقبة النشطة عند بدء التطبيق مع معالجة محسنة"""
    global scheduler
    
    try:
        print("🔄 استعادة مهام المراقبة النشطة...")
        
        # التأكد من تشغيل المجدولة
        if scheduler is None:
            init_scheduler()
        
        if not scheduler.running:
            scheduler.start()
        
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, interval_seconds FROM monitoring_jobs WHERE is_active = 1')
        active_jobs = cursor.fetchall()
        
        conn.close()
        
        if not active_jobs:
            print("ℹ️ لا توجد مهام نشطة للاستعادة")
            return
        
        restored_count = 0
        for username, interval_seconds in active_jobs:
            try:
                job_id = f"monitor_{username}"
                
                # إزالة المهمة إذا كانت موجودة
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
                
                # إضافة المهمة
                scheduler.add_job(
                    func=monitor_user_tweets,
                    args=[username],
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=job_id,
                    name=f"Monitor @{username}",
                    replace_existing=True,
                    misfire_grace_time=30,
                    coalesce=True,
                    max_instances=1
                )
                
                print(f"🔄 تم استعادة مراقبة @{username} (كل {interval_seconds} ثانية)")
                restored_count += 1
                
            except Exception as e:
                print(f"❌ خطأ في استعادة @{username}: {e}")
        
        print(f"✅ تم استعادة {restored_count} من أصل {len(active_jobs)} مهمة مراقبة")
        
        # عرض حالة المجدولة
        jobs = scheduler.get_jobs()
        print(f"📅 إجمالي المهام المجدولة: {len(jobs)}")
        
    except Exception as e:
        print(f"❌ خطأ في استعادة مهام المراقبة: {e}")
        import traceback
        traceback.print_exc()

def get_media_details(tweet_id):
    """الحصول على تفاصيل الوسائط لتغريدة معينة"""
    try:
        conn = sqlite3.connect('twitter_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM media_details 
        WHERE tweet_id = ? 
        ORDER BY created_timestamp
        ''', (tweet_id,))
        
        media_items = cursor.fetchall()
        conn.close()
        
        media_list = []
        for item in media_items:
            media_data = {
                'media_id': item['media_id'],
                'media_key': item['media_key'],
                'type': item['media_type'],
                'url': item['media_url'],
                'display_url': item['display_url'],
                'expanded_url': item['expanded_url'],
                'dimensions': {
                    'width': item['width'],
                    'height': item['height']
                },
                'alt_text': item['alt_text'],
                'duration_millis': item['duration_millis'] if item['media_type'] == 'video' else None,
                'created_at': item['created_timestamp']
            }
            media_list.append(media_data)
        
        return media_list
        
    except Exception as e:
        print(f"خطأ في الحصول على تفاصيل الوسائط: {e}")
        return []

# 🆕 API Endpoints للويب هوك
@app.route('/api/webhook/configure', methods=['POST'])
@login_required
def configure_webhook():
    """تكوين الويب هوك لمستخدم معين"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        webhook_url = data.get('webhook_url', '').strip()
        enabled = data.get('enabled', True)
        
        if not username or not webhook_url:
            return jsonify({'status': 'error', 'message': 'البيانات المطلوبة مفقودة'}), 400
        
        # التحقق من صحة الرابط
        if not webhook_url.startswith(('http://', 'https://')):
            return jsonify({'status': 'error', 'message': 'رابط الويب هوك غير صحيح'}), 400
        
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        # التحقق من وجود المستخدم في مهام المراقبة
        cursor.execute('SELECT id FROM monitoring_jobs WHERE username = ?', (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': f'المستخدم @{username} غير موجود في قائمة المراقبة'}), 400
        
        # إدراج أو تحديث إعدادات الويب هوك
        cursor.execute('''
        INSERT OR REPLACE INTO webhook_settings (username, webhook_url, webhook_enabled, updated_timestamp)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (username, webhook_url, enabled))
        
        conn.commit()
        conn.close()
        
        # تسجيل العملية
        log_monitoring_action(username, "إعداد ويب هوك", "نجح", f"تم تكوين الويب هوك: {webhook_url}")
        
        return jsonify({
            'status': 'success', 
            'message': f'تم تكوين الويب هوك للمستخدم @{username}',
            'data': {
                'username': username,
                'webhook_url': webhook_url,
                'enabled': enabled
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/status')
@login_required
def webhook_status():
    """حالة الويب هوك العامة والمستخدمين"""
    try:
        conn = sqlite3.connect('twitter_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # إعدادات الويب هوك لكل مستخدم
        cursor.execute('''
        SELECT ws.*, mj.is_active as monitoring_active, mj.last_checked, mj.total_fetched
        FROM webhook_settings ws
        LEFT JOIN monitoring_jobs mj ON ws.username = mj.username
        ORDER BY ws.updated_timestamp DESC
        ''')
        settings = [dict(row) for row in cursor.fetchall()]
        
        # آخر سجلات الويب هوك
        cursor.execute('''
        SELECT * FROM webhook_logs 
        ORDER BY created_timestamp DESC 
        LIMIT 50
        ''')
        logs = [dict(row) for row in cursor.fetchall()]
        
        # إحصائيات الويب هوك
        cursor.execute('SELECT COUNT(*) as total_sent FROM webhook_logs WHERE status = "success"')
        total_sent = cursor.fetchone()['total_sent']
        
        cursor.execute('SELECT COUNT(*) as total_failed FROM webhook_logs WHERE status = "error"')
        total_failed = cursor.fetchone()['total_failed']
        
        # إحصائيات لكل مستخدم
        cursor.execute('''
        SELECT username, 
               COUNT(*) as total_attempts,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
               SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed,
               MAX(created_timestamp) as last_attempt
        FROM webhook_logs 
        GROUP BY username
        ORDER BY total_attempts DESC
        ''')
        user_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # حساب معدل النجاح العام
        success_rate = 0
        if (total_sent + total_failed) > 0:
            success_rate = round((total_sent / (total_sent + total_failed)) * 100, 2)
        
        return jsonify({
            'status': 'success',
            'data': {
                'global_config': {
                    'webhook_url': WEBHOOK_URL,
                    'webhook_enabled': WEBHOOK_ENABLED
                },
                'user_settings': settings,
                'recent_logs': logs,
                'statistics': {
                    'total_sent': total_sent,
                    'total_failed': total_failed,
                    'success_rate': success_rate,
                    'user_stats': user_stats
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/test', methods=['POST'])
@login_required
def test_webhook():
    """اختبار الويب هوك"""
    try:
        data = request.json
        webhook_url = data.get('webhook_url', WEBHOOK_URL).strip()
        username = data.get('username', 'test_user').strip()
        
        if not webhook_url:
            return jsonify({'status': 'error', 'message': 'رابط الويب هوك مطلوب'}), 400
        
        # إنشاء تغريدة وهمية للاختبار
        test_tweet = {
            'tweet_id': f'test_{int(time.time())}',
            'screen_name': username,
            'user_name': 'مستخدم تجريبي للاختبار',
            'full_text': f'🧪 هذه تغريدة تجريبية لاختبار الويب هوك - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'created_at': datetime.now().isoformat(),
            'favorite_count': random.randint(1, 100),
            'retweet_count': random.randint(1, 50),
            'reply_count': random.randint(0, 20),
            'views_count': str(random.randint(100, 10000)),
            'media_count': 0,
            'has_media': False,
            'lang': 'ar',
            'extracted_at': datetime.now().isoformat()
        }
        
        # إرسال الاختبار
        start_time = time.time()
        success, message = send_webhook(webhook_url, test_tweet)
        response_time = round((time.time() - start_time) * 1000, 2)  # بالميلي ثانية
        
        # تسجيل اختبار الويب هوك
        log_monitoring_action(username, "اختبار ويب هوك", "نجح" if success else "خطأ", 
                            f"وقت الاستجابة: {response_time}ms - {message}")
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message,
            'data': {
                'webhook_url': webhook_url,
                'response_time_ms': response_time,
                'test_tweet': test_tweet,
                'success': success
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/logs')
@login_required
def webhook_logs():
    """سجلات الويب هوك مع فلترة"""
    try:
        limit = request.args.get('limit', 100, type=int)
        username = request.args.get('username', '').strip()
        status = request.args.get('status', '').strip()  # success, error
        
        # التحقق من الحدود
        if limit > 1000:
            limit = 1000
        
        conn = sqlite3.connect('twitter_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # بناء الاستعلام حسب المعايير
        query_parts = ['SELECT * FROM webhook_logs WHERE 1=1']
        params = []
        
        if username:
            query_parts.append('AND username = ?')
            params.append(username)
        
        if status:
            query_parts.append('AND status = ?')
            params.append(status)
        
        query_parts.append('ORDER BY created_timestamp DESC LIMIT ?')
        params.append(limit)
        
        final_query = ' '.join(query_parts)
        cursor.execute(final_query, params)
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': logs,
            'filters': {
                'username': username if username else None,
                'status': status if status else None,
                'limit': limit
            },
            'count': len(logs),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/settings/<username>', methods=['GET'])
@login_required
def get_webhook_settings(username):
    """الحصول على إعدادات الويب هوك لمستخدم معين"""
    try:
        username = username.strip()
        
        conn = sqlite3.connect('twitter_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # جلب إعدادات الويب هوك
        cursor.execute('''
        SELECT ws.*, 
               mj.is_active as monitoring_active,
               mj.interval_seconds,
               mj.last_checked,
               mj.total_fetched
        FROM webhook_settings ws
        LEFT JOIN monitoring_jobs mj ON ws.username = mj.username
        WHERE ws.username = ?
        ''', (username,))
        
        settings = cursor.fetchone()
        
        if not settings:
            conn.close()
            return jsonify({
                'status': 'success',
                'data': None,
                'message': f'لا توجد إعدادات ويب هوك للمستخدم @{username}'
            })
        
        settings = dict(settings)
        
        # جلب آخر 10 سجلات للمستخدم
        cursor.execute('''
        SELECT * FROM webhook_logs 
        WHERE username = ? 
        ORDER BY created_timestamp DESC 
        LIMIT 10
        ''', (username,))
        
        recent_logs = [dict(row) for row in cursor.fetchall()]
        
        # إحصائيات المستخدم
        cursor.execute('''
        SELECT 
            COUNT(*) as total_attempts,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed
        FROM webhook_logs 
        WHERE username = ?
        ''', (username,))
        
        stats = dict(cursor.fetchone())
        conn.close()
        
        # حساب معدل النجاح
        success_rate = 0
        if stats['total_attempts'] > 0:
            success_rate = round((stats['successful'] / stats['total_attempts']) * 100, 2)
        
        stats['success_rate'] = success_rate
        
        return jsonify({
            'status': 'success',
            'data': {
                'settings': settings,
                'recent_logs': recent_logs,
                'statistics': stats
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/settings/<username>', methods=['DELETE'])
@login_required
def delete_webhook_settings(username):
    """حذف إعدادات الويب هوك لمستخدم معين"""
    try:
        username = username.strip()
        
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        # التحقق من وجود الإعدادات
        cursor.execute('SELECT id FROM webhook_settings WHERE username = ?', (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error', 
                'message': f'لا توجد إعدادات ويب هوك للمستخدم @{username}'
            }), 404
        
        # حذف الإعدادات
        cursor.execute('DELETE FROM webhook_settings WHERE username = ?', (username,))
        
        conn.commit()
        conn.close()
        
        # تسجيل العملية
        log_monitoring_action(username, "حذف ويب هوك", "نجح", "تم حذف إعدادات الويب هوك")
        
        return jsonify({
            'status': 'success',
            'message': f'تم حذف إعدادات الويب هوك للمستخدم @{username}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/webhook/global/toggle', methods=['POST'])
@login_required
def toggle_global_webhook():
    """تفعيل/إلغاء تفعيل الويب هوك العام"""
    try:
        global WEBHOOK_ENABLED
        
        data = request.json
        enabled = data.get('enabled', not WEBHOOK_ENABLED)
        
        WEBHOOK_ENABLED = bool(enabled)
        
        status_text = "مُفعّل" if WEBHOOK_ENABLED else "مُعطّل"
        
        # تسجيل التغيير
        log_monitoring_action("النظام", "تغيير حالة ويب هوك", "نجح", f"الويب هوك العام {status_text}")
        
        return jsonify({
            'status': 'success',
            'message': f'تم {status_text} الويب هوك العام',
            'data': {
                'webhook_enabled': WEBHOOK_ENABLED,
                'webhook_url': WEBHOOK_URL
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ========== معالج الأخطاء ==========
@app.errorhandler(500)
def internal_error(error):
    print(f"خطأ 500: {error}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="خطأ داخلي في الخادم"), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="الصفحة غير موجودة"), 404

# ========== المسارات (Routes) ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User('admin')
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """تسجيل الخروج"""
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية"""
    try:
        stats = get_database_stats()
        recent_tweets = get_tweets_from_database(limit=5)
        monitoring_jobs = get_monitoring_jobs()
        return render_template('index.html', stats=stats, recent_tweets=recent_tweets, monitoring_jobs=monitoring_jobs)
    except Exception as e:
        print(f"خطأ في الصفحة الرئيسية: {e}")
        return render_template('error.html', error_code=500, error_message=str(e)), 500

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """صفحة البحث"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if username:
            return redirect(url_for('user_tweets', username=username))
        else:
            flash('الرجاء إدخال اسم المستخدم', 'error')
    
    return render_template('search.html')

@app.route('/user/<username>')
@login_required
def user_tweets(username):
    """عرض تغريدات مستخدم معين"""
    try:
        tweets = get_tweets_from_database(username=username, limit=50)
        return render_template('user_tweets.html', username=username, tweets=tweets)
    except Exception as e:
        print(f"خطأ في عرض تغريدات المستخدم: {e}")
        flash(f'خطأ في تحميل تغريدات @{username}', 'error')
        return redirect(url_for('search'))

@app.route('/all_tweets')
@login_required
def all_tweets():
    """عرض جميع التغريدات مع فلاتر متقدمة"""
    try:
        search_text = request.args.get('search', '')
        lang = request.args.get('lang', '')
        tweets = get_tweets_from_database(search_text=search_text, lang=lang, limit=100)
        return render_template('all_tweets.html', tweets=tweets)
    except Exception as e:
        print(f"خطأ في عرض جميع التغريدات: {e}")
        return render_template('error.html', error_code=500, error_message=str(e)), 500

@app.route('/monitoring')
@login_required
def monitoring():
    """صفحة إدارة المراقبة"""
    try:
        jobs = get_monitoring_jobs()
        logs = get_monitoring_logs(50)  # آخر 50 سجل
        return render_template('monitoring.html', jobs=jobs, logs=logs)
    except Exception as e:
        print(f"خطأ في صفحة المراقبة: {e}")
        return render_template('error.html', error_code=500, error_message=str(e)), 500

@app.route('/start_monitoring', methods=['POST'])
@login_required
def start_monitoring():
    """بدء مراقبة مستخدم"""
    try:
        username = request.form.get('username', '').strip()
        interval = int(request.form.get('interval', 60))
        
        if not username:
            flash('الرجاء إدخال اسم المستخدم', 'error')
            return redirect(url_for('monitoring'))
        
        # تعديل الحد الأدنى إلى 10 ثواني والحد الأقصى إلى ساعة
        if interval < 10:
            flash('الحد الأدنى للفاصل الزمني هو 10 ثواني', 'error')
            return redirect(url_for('monitoring'))
        
        if interval > 3600:
            flash('الحد الأقصى للفاصل الزمني هو ساعة واحدة (3600 ثانية)', 'error')
            return redirect(url_for('monitoring'))
        
        if start_monitoring_job(username, interval):
            flash(f'تم بدء مراقبة @{username} كل {interval} ثانية', 'success')
        else:
            flash(f'فشل في بدء مراقبة @{username}', 'error')
        
        return redirect(url_for('monitoring'))
    except Exception as e:
        print(f"خطأ في بدء المراقبة: {e}")
        flash('خطأ في بدء المراقبة', 'error')
        return redirect(url_for('monitoring'))

@app.route('/stop_monitoring/<username>')
@login_required
def stop_monitoring_route(username):
    """إيقاف مراقبة مستخدم"""
    try:
        if stop_monitoring_job(username):
            flash(f'تم إيقاف مراقبة @{username}', 'success')
        else:
            flash(f'فشل في إيقاف مراقبة @{username}', 'error')
        
        return redirect(url_for('monitoring'))
    except Exception as e:
        print(f"خطأ في إيقاف المراقبة: {e}")
        flash('خطأ في إيقاف المراقبة', 'error')
        return redirect(url_for('monitoring'))

@app.route('/api/monitoring_status')
@login_required
def monitoring_status():
    """حالة المراقبة (JSON API)"""
    try:
        jobs = get_monitoring_jobs()
        logs = get_monitoring_logs(20)
        stats = get_database_stats()
        
        return jsonify({
            'status': 'success',
            'jobs': jobs,
            'recent_logs': logs,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api_docs')
@login_required
def api_docs():
    """صفحة توثيق API"""
    return render_template('api_docs.html')

@app.route('/api/diagnose')
@login_required
def api_diagnose():
    """API لتشخيص مشاكل المراقبة"""
    try:
        return jsonify({
            'status': 'success',
            'message': 'تم تشغيل التشخيص - راجع الكونسول',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ========== API Endpoints ==========
@app.route('/api/tweets/latest', methods=['GET'])
def api_latest_tweets():
    """API: الحصول على آخر التغريدات المحفوظة"""
    try:
        limit = request.args.get('limit', 10, type=int)
        username = request.args.get('username', None)
        
        # التحقق من صحة البارامترات
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
            
        tweets = get_tweets_from_database(username=username, limit=limit)
        
        # تحويل البيانات إلى صيغة API - مُصحح للعمل مع sqlite3.Row
        api_tweets = []
        for tweet in tweets:
            try:
                # تحويل sqlite3.Row إلى قاموس أولاً
                tweet_dict = dict(tweet)
                
                # تحويل البيانات JSON المحفوظة بشكل آمن
                hashtags = []
                user_mentions = []
                urls = []
                media_types = []
                media_urls = []
                
                try:
                    hashtags = json.loads(tweet_dict.get('hashtags', '[]')) if tweet_dict.get('hashtags') else []
                except:
                    hashtags = []
                
                try:
                    user_mentions = json.loads(tweet_dict.get('user_mentions', '[]')) if tweet_dict.get('user_mentions') else []
                except:
                    user_mentions = []
                
                try:
                    urls = json.loads(tweet_dict.get('urls', '[]')) if tweet_dict.get('urls') else []
                except:
                    urls = []
                
                try:
                    media_types = json.loads(tweet_dict.get('media_types', '[]')) if tweet_dict.get('media_types') else []
                except:
                    media_types = []
                
                try:
                    media_urls = json.loads(tweet_dict.get('media_urls', '[]')) if tweet_dict.get('media_urls') else []
                except:
                    media_urls = []
                
                # الحصول على تفاصيل الوسائط من قاعدة البيانات
                media_details = get_media_details(tweet_dict.get('tweet_id', ''))
                
                # تنسيق views_count بشكل آمن
                views_count = 0
                try:
                    views_str = str(tweet_dict.get('views_count', '0'))
                    views_count = int(views_str) if views_str.isdigit() else 0
                except:
                    views_count = 0
                
                tweet_data = {
                    'id': tweet_dict.get('tweet_id', ''),
                    'user': {
                        'id': tweet_dict.get('user_id', ''),
                        'username': tweet_dict.get('screen_name', ''),
                        'display_name': tweet_dict.get('user_name', ''),
                        'verified': bool(tweet_dict.get('user_verified', False)),
                        'followers_count': tweet_dict.get('user_followers_count', 0),
                        'following_count': tweet_dict.get('user_following_count', 0),
                        'profile_image_url': tweet_dict.get('user_profile_image_url', ''),
                        'location': tweet_dict.get('user_location', ''),
                        'description': tweet_dict.get('user_description', ''),
                        'created_at': tweet_dict.get('user_created_at', '')
                    },
                    'content': {
                        'text': tweet_dict.get('full_text', ''),
                        'language': tweet_dict.get('lang', ''),
                        'created_at': tweet_dict.get('created_at', ''),
                        'source': tweet_dict.get('source', ''),
                        'is_quote': bool(tweet_dict.get('is_quote_status', False)),
                        'possibly_sensitive': bool(tweet_dict.get('possibly_sensitive', False))
                    },
                    'engagement': {
                        'views_count': views_count,
                        'likes_count': tweet_dict.get('favorite_count', 0),
                        'retweets_count': tweet_dict.get('retweet_count', 0),
                        'replies_count': tweet_dict.get('reply_count', 0),
                        'quotes_count': tweet_dict.get('quote_count', 0),
                        'bookmarks_count': tweet_dict.get('bookmark_count', 0)
                    },
                    'entities': {
                        'hashtags': hashtags,
                        'user_mentions': user_mentions,
                        'urls': urls
                    },
                    'media': {
                        'has_media': bool(tweet_dict.get('has_media', False)),
                        'media_count': tweet_dict.get('media_count', 0),
                        'media_types': media_types,
                        'media_urls': media_urls,
                        'media_details': media_details
                    },
                    'conversation': {
                        'conversation_id': tweet_dict.get('conversation_id', ''),
                        'in_reply_to_tweet_id': tweet_dict.get('in_reply_to_status_id', ''),
                        'in_reply_to_user_id': tweet_dict.get('in_reply_to_user_id', ''),
                        'in_reply_to_username': tweet_dict.get('in_reply_to_screen_name', '')
                    },
                    'meta': {
                        'extracted_at': tweet_dict.get('extracted_at', ''),
                        'created_timestamp': tweet_dict.get('created_timestamp', ''),
                        'updated_timestamp': tweet_dict.get('updated_timestamp', '')
                    }
                }
                
                api_tweets.append(tweet_data)
                
            except Exception as e:
                print(f"خطأ في معالجة التغريدة: {e}")
                continue
        
        return jsonify({
            'status': 'success',
            'data': {
                'tweets': api_tweets,
                'count': len(api_tweets),
                'limit': limit,
                'username_filter': username
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"خطأ في API latest tweets: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/stats', methods=['GET'])
def api_database_stats():
    """API: إحصائيات قاعدة البيانات مع تفاصيل إضافية"""
    try:
        stats = get_database_stats()
        
        # إحصائيات إضافية
        conn = sqlite3.connect('twitter_data.db')
        cursor = conn.cursor()
        
        # أكثر المستخدمين نشاطاً
        cursor.execute('''
        SELECT screen_name, COUNT(*) as tweet_count 
        FROM tweets 
        GROUP BY screen_name 
        ORDER BY tweet_count DESC 
        LIMIT 10
        ''')
        top_users = [{'username': row[0], 'tweet_count': row[1]} for row in cursor.fetchall()]
        
        # اللغات الأكثر استخداماً
        cursor.execute('''
        SELECT lang, COUNT(*) as count 
        FROM tweets 
        WHERE lang IS NOT NULL AND lang != '' 
        GROUP BY lang 
        ORDER BY count DESC 
        LIMIT 5
        ''')
        top_languages = [{'language': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'overview': stats,
                'analytics': {
                    'top_users': top_users,
                    'top_languages': top_languages
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        })

 
# ===================== إضافات: API للتغريدة + حذف + تصدير CSV + حذف من المراقبة =====================

def _get_tweet_with_media(tweet_id: str):
    """جلب تغريدة واحدة مع الوسائط من قاعدة البيانات"""
    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM tweets WHERE tweet_id = ?", (tweet_id,))
        row = cur.fetchone()
        if not row:
            return None
        tweet = dict(row)

        cur.execute("SELECT * FROM media_details WHERE tweet_id = ?", (tweet_id,))
        media = [dict(r) for r in cur.fetchall()]
        tweet["media_details"] = media

        # فك حقول JSON المخزنة كنص (إن وجدت)
        for k in ["hashtags", "mentions", "urls", "media_urls", "media_types", "entities", "extended_entities"]:
            if k in tweet and isinstance(tweet[k], str) and tweet[k]:
                try:
                    tweet[k] = json.loads(tweet[k])
                except Exception:
                    pass

        return tweet
    finally:
        conn.close()


@app.route('/api/tweet/<tweet_id>', methods=['GET'])
@login_required
def api_tweet(tweet_id):
    """عرض تغريدة واحدة كـ JSON"""
    tweet = _get_tweet_with_media(tweet_id)
    if not tweet:
        return jsonify({"status": "error", "message": "Tweet not found", "tweet_id": tweet_id}), 404
    return jsonify({"status": "success", "data": tweet})


@app.route('/api/user/<username>/tweets', methods=['GET'])
@login_required
def api_user_tweets(username):
    """عرض تغريدات حساب من قاعدة البيانات عبر API"""
    try:
        limit = int(request.args.get("limit", 50))
    except Exception:
        limit = 50
    tweets = get_tweets_from_database(username=username, limit=limit)
    return jsonify({"status": "success", "username": username, "count": len(tweets), "data": tweets})


@app.route('/api/tweet/<tweet_id>/delete', methods=['POST'])
@login_required
def api_delete_tweet(tweet_id):
    """حذف تغريدة واحدة"""
    conn = sqlite3.connect('twitter_data.db')
    cur = conn.cursor()
    try:
        # حذف الوسائط أولاً
        cur.execute("DELETE FROM media_details WHERE tweet_id = ?", (tweet_id,))
        cur.execute("DELETE FROM tweets WHERE tweet_id = ?", (tweet_id,))
        conn.commit()
        return jsonify({"status": "success", "deleted_tweet_id": tweet_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/tweets/delete', methods=['POST'])
@login_required
def api_delete_tweets_bulk():
    """حذف عدة تغريدات (tweet_ids)"""
    payload = request.get_json(silent=True) or {}
    tweet_ids = payload.get("tweet_ids") or []
    if isinstance(tweet_ids, str):
        tweet_ids = [tweet_ids]
    tweet_ids = [t for t in tweet_ids if t]

    if not tweet_ids:
        return jsonify({"status": "error", "message": "tweet_ids is required"}), 400

    conn = sqlite3.connect('twitter_data.db')
    cur = conn.cursor()
    try:
        for tid in tweet_ids:
            cur.execute("DELETE FROM media_details WHERE tweet_id = ?", (tid,))
            cur.execute("DELETE FROM tweets WHERE tweet_id = ?", (tid,))
        conn.commit()
        return jsonify({"status": "success", "deleted_count": len(tweet_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()


@app.route('/export/csv', methods=['POST'])
@login_required
def export_csv():
    """تصدير تغريدات CSV: إما لحساب/حسابات أو لتغريدات محددة"""
    # يدعم: form-data أو JSON
    payload = request.get_json(silent=True)
    if payload:
        usernames = payload.get("usernames") or []
        tweet_ids = payload.get("tweet_ids") or []
    else:
        usernames = request.form.getlist("usernames")
        tweet_ids = request.form.getlist("tweet_ids")

        # دعم حقول مخفية على شكل نص مفصول بفواصل
        if not usernames and request.form.get("usernames_csv"):
            usernames = [u.strip() for u in request.form.get("usernames_csv", "").split(",") if u.strip()]
        if not tweet_ids and request.form.get("tweet_ids_csv"):
            tweet_ids = [t.strip() for t in request.form.get("tweet_ids_csv", "").split(",") if t.strip()]

    if isinstance(usernames, str): usernames = [usernames]
    if isinstance(tweet_ids, str): tweet_ids = [tweet_ids]

    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        rows = []
        if tweet_ids:
            qmarks = ",".join(["?"] * len(tweet_ids))
            cur.execute(f"SELECT * FROM tweets WHERE tweet_id IN ({qmarks}) ORDER BY created_timestamp DESC", tuple(tweet_ids))
            rows = [dict(r) for r in cur.fetchall()]
        elif usernames:
            # عدة حسابات
            qmarks = ",".join(["?"] * len(usernames))
            cur.execute(f"SELECT * FROM tweets WHERE LOWER(screen_name) IN ({qmarks}) ORDER BY created_timestamp DESC",
                        tuple([u.lower() for u in usernames]))
            rows = [dict(r) for r in cur.fetchall()]
        else:
            return jsonify({"status": "error", "message": "usernames or tweet_ids required"}), 400

        output = io.StringIO()
        if rows:
            # ترتيب أعمدة ثابت قدر الإمكان
            fieldnames = list(rows[0].keys())
        else:
            fieldnames = ["tweet_id", "screen_name", "full_text", "created_at"]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

        data = output.getvalue().encode("utf-8-sig")
        output.close()

        filename = f"tweets_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return send_file(
            io.BytesIO(data),
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=filename
        )
    finally:
        conn.close()


@app.route('/delete_monitoring/<username>', methods=['POST'])
@login_required
def delete_monitoring(username):
    """حذف حساب من قائمة المراقبة (قاعدة البيانات + إيقاف Job إن وجد)"""
    uname = (username or "").strip()
    if not uname:
        return jsonify({"status": "error", "message": "username required"}), 400

    # إيقاف job من المجدولة إذا موجود
    try:
        init_scheduler()
        job_id = f"monitor_{uname}"
        if scheduler and scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
    except Exception as e:
        print(f"⚠️ تعذر إزالة Job من المجدولة @{uname}: {e}")

    conn = sqlite3.connect('twitter_data.db')
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM monitoring_jobs WHERE LOWER(username) = LOWER(?)", (uname,))
        cur.execute("DELETE FROM monitoring_logs WHERE LOWER(username) = LOWER(?)", (uname,))
        # إعدادات الويب هوك الخاصة بالحساب (اختياري)
        try:
            cur.execute("DELETE FROM webhook_settings WHERE LOWER(username) = LOWER(?)", (uname,))
        except Exception:
            pass
        conn.commit()
        flash(f"تم حذف @{uname} من قائمة المراقبة", "success")
        return redirect(url_for('monitoring'))
    except Exception as e:
        conn.rollback()
        flash(f"خطأ أثناء حذف @{uname} من المراقبة: {e}", "error")
        return redirect(url_for('monitoring'))
    finally:
        conn.close()



# تشغيل التطبيق
if __name__ == '__main__':
    try:
        # إنشاء قاعدة البيانات
        create_database()
        print("✅ تم إنشاء قاعدة البيانات")
        
        # تشغيل المجدولة
        init_scheduler()
        
        # استعادة مهام المراقبة النشطة
        restore_monitoring_jobs()
        
        print("🚀 تم بدء تطبيق مراقبة تويتر مع الويب هوك")
        print(f"👤 اسم المستخدم: {ADMIN_USERNAME}")
        print(f"🔐 كلمة المرور: {ADMIN_PASSWORD}")
        print(f"🎯 الويب هوك: {WEBHOOK_URL}")
        print("🌐 الرابط: http://localhost:5000")
        
        # تشغيل التطبيق بدون debug لتجنب مشاكل APScheduler
        app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5070)
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل التطبيق: {e}")
        import traceback
        traceback.print_exc()
