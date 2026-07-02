"""
X Timeline Service — سحب التايم لاين الشخصي لحسابات X المسجّلة في موج،
وحفظه في قاعدة بيانات محلية، وعرضه لاحقاً.

يقرأ ملف الكوكيز بصيغة Playwright من app/x/cookies/{username}.json،
يستخرج auth_token و ct0، ويستخدمهما لطلب Home Timeline من X GraphQL API.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# ─── مسارات ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
COOKIES_DIR = BASE_DIR / "app" / "x" / "cookies"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "x_timeline.db"


# ─── إعدادات X GraphQL API (نفس اللي في twitter_scraper.py الأصلي) ─
HOME_TIMELINE_QUERY_ID = "gKia-nBM9kwuDEfSDeWMfQ"
HOME_TIMELINE_URL = f"https://x.com/i/api/graphql/{HOME_TIMELINE_QUERY_ID}/HomeTimeline"

# Bearer token عام لتويتر (نفس اللي يستخدمه المتصفح)
TWITTER_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

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
    "responsive_web_enhance_cards_enabled": False,
}


# ═══════════════════════════════════════════════════════════════════
#                        قاعدة البيانات
# ═══════════════════════════════════════════════════════════════════

def _connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_timeline_db() -> None:
    """ينشئ جدول التغريدات لو ما موجود."""
    with _connect_db() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS x_timeline_tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_username TEXT NOT NULL,
                user_id INTEGER,
                tweet_id TEXT NOT NULL,
                full_text TEXT,
                author_screen_name TEXT,
                author_name TEXT,
                created_at TEXT,
                favorite_count INTEGER DEFAULT 0,
                retweet_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                quote_count INTEGER DEFAULT 0,
                views_count TEXT,
                tweet_url TEXT,
                lang TEXT,
                is_retweet INTEGER DEFAULT 0,
                is_reply INTEGER DEFAULT 0,
                is_quote INTEGER DEFAULT 0,
                media_urls TEXT,
                raw_data TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(account_username, tweet_id)
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_timeline_account "
            "ON x_timeline_tweets(account_username, created_at DESC)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_timeline_user "
            "ON x_timeline_tweets(user_id, fetched_at DESC)"
        )


# ═══════════════════════════════════════════════════════════════════
#                        استخراج التوكنز من الكوكيز
# ═══════════════════════════════════════════════════════════════════

def extract_tokens_from_cookies(username: str) -> Tuple[Optional[str], Optional[str]]:
    """
    يقرأ ملف كوكيز الحساب من app/x/cookies/{username}.json (صيغة Playwright)
    ويستخرج auth_token و ct0.
    يرجع (auth_token, ct0) — أو (None, None) لو الملف مو موجود/غير صالح.
    """
    cookie_file = COOKIES_DIR / f"{username}.json"
    if not cookie_file.exists():
        return None, None

    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # الصيغة الجديدة: {"cookies": [...], "origins": []}
        # الصيغة القديمة (legacy): [...]
        if isinstance(data, dict) and "cookies" in data:
            cookies = data["cookies"]
        elif isinstance(data, list):
            cookies = data
        else:
            return None, None

        auth_token = None
        ct0 = None
        for c in cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            if name == "auth_token" and value:
                auth_token = value
            elif name == "ct0" and value:
                ct0 = value

        return auth_token, ct0
    except Exception as e:
        print(f"[x_timeline] فشل قراءة كوكيز {username}: {e}")
        return None, None


def _make_headers(auth_token: str, ct0: str) -> Dict[str, str]:
    """يبني الهيدرز المطلوبة لطلب X GraphQL API."""
    return {
        "authorization": f"Bearer {TWITTER_BEARER}",
        "x-csrf-token": ct0,
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "content-type": "application/json",
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "ar",
    }


# ═══════════════════════════════════════════════════════════════════
#                        استخراج بيانات التغريدة
# ═══════════════════════════════════════════════════════════════════

def _extract_tweet(tweet_obj: Dict) -> Optional[Dict]:
    """يستخرج البيانات المهمة من كائن تغريدة في response تويتر."""
    try:
        legacy = tweet_obj.get("legacy", {})
        core = tweet_obj.get("core", {})
        user_result = core.get("user_results", {}).get("result", {})
        user_legacy = user_result.get("legacy", {})
        user_core = user_result.get("core", {})

        tweet_id = legacy.get("id_str") or tweet_obj.get("rest_id", "")
        if not tweet_id:
            return None

        screen_name = user_core.get("screen_name") or user_legacy.get("screen_name", "")
        user_name = user_core.get("name") or user_legacy.get("name", "")

        # الميديا
        entities = legacy.get("entities", {})
        extended = legacy.get("extended_entities", {})
        media = extended.get("media") or entities.get("media") or []
        media_urls = []
        for m in media:
            url = m.get("media_url_https") or m.get("media_url")
            if url:
                media_urls.append(url)

        # نص كامل (لو note_tweet — تغريدة طويلة)
        note_text = (
            tweet_obj.get("note_tweet", {})
            .get("note_tweet_results", {})
            .get("result", {})
            .get("text", "")
        )
        full_text = note_text or legacy.get("full_text", "") or legacy.get("text", "")

        views = tweet_obj.get("views", {}) or {}

        return {
            "tweet_id": tweet_id,
            "full_text": full_text,
            "author_screen_name": screen_name,
            "author_name": user_name,
            "created_at": legacy.get("created_at", ""),
            "favorite_count": int(legacy.get("favorite_count", 0) or 0),
            "retweet_count": int(legacy.get("retweet_count", 0) or 0),
            "reply_count": int(legacy.get("reply_count", 0) or 0),
            "quote_count": int(legacy.get("quote_count", 0) or 0),
            "views_count": str(views.get("count", "0") or "0"),
            "tweet_url": f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name else "",
            "lang": legacy.get("lang", ""),
            "is_retweet": bool(legacy.get("retweeted_status_result")),
            "is_reply": bool(legacy.get("in_reply_to_status_id_str")),
            "is_quote": bool(legacy.get("is_quote_status")),
            "media_urls": media_urls,
        }
    except Exception as e:
        print(f"[x_timeline] فشل استخراج تغريدة: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
#                        سحب التايم لاين
# ═══════════════════════════════════════════════════════════════════

def fetch_and_save_timeline(
    account_username: str,
    count: int = 50,
    user_id: Optional[int] = None,
    include_rt: bool = True,
    include_replies: bool = True,
) -> Dict[str, Any]:
    """
    يسحب Home Timeline للحساب باستخدام كوكيزه ويحفظ التغريدات في DB.
    يرجع dict فيه: success, saved, total_fetched, message
    """
    init_timeline_db()

    auth_token, ct0 = extract_tokens_from_cookies(account_username)
    if not auth_token or not ct0:
        return {
            "success": False,
            "saved": 0,
            "total_fetched": 0,
            "message": (
                f"⚠️ ما لقيت auth_token/ct0 في كوكيز الحساب '{account_username}'. "
                f"تأكد أنه مسجل دخول في موج."
            ),
        }

    headers = _make_headers(auth_token, ct0)
    seen_ids = set()
    tweets_data: List[Dict] = []
    cursor: Optional[str] = None
    page = 1
    max_pages = 20  # حد أعلى لمنع الحلقات اللانهائية

    while len(tweets_data) < count and page <= max_pages:
        body = {
            "variables": {
                "count": min(20, count - len(tweets_data) + 5),
                "includePromotedContent": False,
                "latestControlAvailable": True,
                "requestContext": "launch",
                "withCommunity": True,
                "seenTweetIds": [],
            },
            "features": GRAPHQL_FEATURES,
            "queryId": HOME_TIMELINE_QUERY_ID,
        }
        if cursor:
            body["variables"]["cursor"] = cursor

        try:
            resp = requests.post(HOME_TIMELINE_URL, headers=headers, json=body, timeout=30)
        except requests.RequestException as e:
            return {
                "success": False,
                "saved": 0,
                "total_fetched": len(tweets_data),
                "message": f"❌ فشل الاتصال بـ X API: {e}",
            }

        if resp.status_code == 429:
            # Rate limit — انتظر بس مو طويل
            time.sleep(15)
            continue

        if resp.status_code == 401 or resp.status_code == 403:
            return {
                "success": False,
                "saved": 0,
                "total_fetched": len(tweets_data),
                "message": (
                    f"❌ الكوكيز منتهية أو غير صالحة (HTTP {resp.status_code}). "
                    f"سجّل دخول الحساب '{account_username}' من جديد."
                ),
            }

        if resp.status_code != 200:
            return {
                "success": False,
                "saved": 0,
                "total_fetched": len(tweets_data),
                "message": f"❌ خطأ HTTP {resp.status_code} من X API",
            }

        try:
            response_data = resp.json()
        except Exception:
            return {
                "success": False,
                "saved": 0,
                "total_fetched": len(tweets_data),
                "message": "❌ رد X API غير صالح (ليس JSON)",
            }

        instructions = (
            response_data.get("data", {})
            .get("home", {})
            .get("home_timeline_urt", {})
            .get("instructions", [])
        )

        next_cursor = None
        added_this_page = 0

        for instr in instructions:
            for entry in instr.get("entries", []):
                eid = entry.get("entryId", "")

                if eid.startswith("cursor-bottom-"):
                    next_cursor = entry.get("content", {}).get("value")
                    continue

                if not eid.startswith("tweet-"):
                    continue

                content = entry.get("content", {})
                item_content = content.get("itemContent", {})
                tweet_results = item_content.get("tweet_results", {})
                tweet_obj = tweet_results.get("result", {})

                # لو مغلَّف بـ TweetWithVisibilityResults
                if tweet_obj.get("__typename") == "TweetWithVisibilityResults":
                    tweet_obj = tweet_obj.get("tweet", {})

                if not tweet_obj:
                    continue

                extracted = _extract_tweet(tweet_obj)
                if not extracted:
                    continue

                if extracted["tweet_id"] in seen_ids:
                    continue

                # فلترة (اختيارية)
                if not include_rt and extracted["is_retweet"]:
                    continue
                if not include_replies and extracted["is_reply"]:
                    continue

                seen_ids.add(extracted["tweet_id"])
                tweets_data.append(extracted)
                added_this_page += 1

                if len(tweets_data) >= count:
                    break
            if len(tweets_data) >= count:
                break

        if added_this_page == 0 or not next_cursor:
            # ما جبنا جديد → نوقف
            break

        cursor = next_cursor
        page += 1
        time.sleep(1)  # مهلة بسيطة بين الصفحات

    # ─── حفظ في قاعدة البيانات ───
    saved_count = 0
    with _connect_db() as con:
        for t in tweets_data:
            try:
                con.execute(
                    """
                    INSERT INTO x_timeline_tweets (
                        account_username, user_id, tweet_id, full_text,
                        author_screen_name, author_name, created_at,
                        favorite_count, retweet_count, reply_count, quote_count,
                        views_count, tweet_url, lang,
                        is_retweet, is_reply, is_quote, media_urls, raw_data
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(account_username, tweet_id) DO UPDATE SET
                        favorite_count = excluded.favorite_count,
                        retweet_count  = excluded.retweet_count,
                        reply_count    = excluded.reply_count,
                        quote_count    = excluded.quote_count,
                        views_count    = excluded.views_count,
                        fetched_at     = CURRENT_TIMESTAMP
                    """,
                    (
                        account_username, user_id, t["tweet_id"], t["full_text"],
                        t["author_screen_name"], t["author_name"], t["created_at"],
                        t["favorite_count"], t["retweet_count"], t["reply_count"], t["quote_count"],
                        t["views_count"], t["tweet_url"], t["lang"],
                        int(t["is_retweet"]), int(t["is_reply"]), int(t["is_quote"]),
                        json.dumps(t["media_urls"], ensure_ascii=False),
                        json.dumps(t, ensure_ascii=False),
                    ),
                )
                saved_count += 1
            except Exception as e:
                print(f"[x_timeline] فشل حفظ تغريدة {t.get('tweet_id')}: {e}")

    return {
        "success": True,
        "saved": saved_count,
        "total_fetched": len(tweets_data),
        "message": f"✅ تم سحب {len(tweets_data)} تغريدة وحفظ {saved_count} في قاعدة البيانات.",
    }


# ═══════════════════════════════════════════════════════════════════
#                        عرض التغريدات المحفوظة
# ═══════════════════════════════════════════════════════════════════

def get_saved_tweets(
    account_username: str,
    limit: int = 10,
    offset: int = 0,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """
    يجيب التغريدات المحفوظة لحساب معين، مرتبة حسب created_at (الأحدث أولاً).
    """
    init_timeline_db()
    query = """
        SELECT tweet_id, full_text, author_screen_name, author_name, created_at,
               favorite_count, retweet_count, reply_count, quote_count, views_count,
               tweet_url, lang, is_retweet, is_reply, is_quote, media_urls, fetched_at
        FROM x_timeline_tweets
        WHERE account_username = ?
    """
    params: List[Any] = [account_username]
    if user_id is not None:
        query += " AND (user_id = ? OR user_id IS NULL)"
        params.append(user_id)
    # ترتيب: created_at ISO لو موجود، وإلا fetched_at
    query += " ORDER BY COALESCE(created_at, fetched_at) DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with _connect_db() as con:
        rows = con.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # decode media_urls
            try:
                d["media_urls"] = json.loads(d.get("media_urls") or "[]")
            except Exception:
                d["media_urls"] = []
            result.append(d)
        return result


def count_saved_tweets(account_username: str, user_id: Optional[int] = None) -> int:
    """يعد التغريدات المحفوظة لحساب."""
    init_timeline_db()
    query = "SELECT COUNT(*) AS c FROM x_timeline_tweets WHERE account_username = ?"
    params: List[Any] = [account_username]
    if user_id is not None:
        query += " AND (user_id = ? OR user_id IS NULL)"
        params.append(user_id)
    with _connect_db() as con:
        row = con.execute(query, params).fetchone()
        return int(row["c"]) if row else 0
