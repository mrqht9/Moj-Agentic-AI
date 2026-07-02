"""
سكريبت مستقل لسحب التايم لاين الرئيسي (Home Timeline) للحساب نفسه
يعتمد على كوكيز الحساب - يحفظ جميع البيانات في ملف CSV يدعم العربية

الاستخدام:
    python twitter_scraper.py --count 100
    python twitter_scraper.py --count 50 --cookies coo.txt
"""

import json
import os
import sys
import random
import requests
import time
import csv
import argparse
from datetime import datetime

# اصلاح ترميز الكونسول في Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


# ========== تحميل الكوكيز ==========
def load_cookies(path="coo.txt"):
    """تحميل الكوكيز من ملف نصي (كل سطر: auth_token,ct0)"""
    if not os.path.exists(path):
        print(f"[X] ملف الكوكيز غير موجود: {path}")
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


# ========== إنشاء الهيدرز ==========
def make_headers(auth_token, ct0):
    """إنشاء الهيدرز المطلوبة لطلبات Twitter API"""
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "x-csrf-token": ct0,
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }


# ========== الحصول على معرف المستخدم ==========
def get_user_id(screen_name, headers):
    """الحصول على معرف المستخدم (user_id) من اسم المستخدم (screen_name)"""
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
        print(f"[X] خطأ في الحصول على معرف المستخدم: {e}")
        return None


# ========== استخراج جميع بيانات التغريدة من الريسبونس ==========
def extract_all_tweet_data(tweet_obj, screen_name):
    """استخراج كل البيانات الموجودة في الريسبونس بدون استثناء"""
    try:
        legacy = tweet_obj.get("legacy", {})
        core = tweet_obj.get("core", {})
        user_results = core.get("user_results", {})
        user_result = user_results.get("result", {})
        user_legacy = user_result.get("legacy", {})
        user_core = user_result.get("core", {})  # تويتر نقل name/screen_name/created_at إلى هنا
        user_professional = user_result.get("professional", {})
        views_data = tweet_obj.get("views", {})
        edit_control = tweet_obj.get("edit_control", {})
        edit_control_initial = edit_control.get("edit_control_initial", edit_control)
        note_tweet = tweet_obj.get("note_tweet", {})
        note_result = note_tweet.get("note_tweet_results", {}).get("result", {})
        entities = legacy.get("entities", {})
        extended_entities = legacy.get("extended_entities", {})
        media_entities = entities.get("media", [])
        media_extended = extended_entities.get("media", [])
        media_data = media_extended if media_extended else media_entities
        card = tweet_obj.get("card", {})
        card_legacy = card.get("legacy", {})
        quoted_status = tweet_obj.get("quoted_status_result", {}).get("result", {})

        # استخراج روابط الفيديو إن وجدت
        video_urls = []
        for media in media_data:
            video_info = media.get("video_info", {})
            if video_info:
                variants = video_info.get("variants", [])
                # اختيار أعلى جودة mp4
                mp4_variants = [v for v in variants if v.get("content_type") == "video/mp4"]
                if mp4_variants:
                    best = max(mp4_variants, key=lambda v: v.get("bitrate", 0))
                    video_urls.append(best.get("url", ""))

        tweet_data = {
            # === بيانات التغريدة الأساسية ===
            "tweet_id": legacy.get("id_str", tweet_obj.get("rest_id", "")),
            "rest_id": tweet_obj.get("rest_id", ""),
            "full_text": legacy.get("full_text", ""),
            "note_text": note_result.get("text", ""),
            "created_at": legacy.get("created_at", ""),
            "lang": legacy.get("lang", ""),
            "source": tweet_obj.get("source", ""),
            "tweet_url": f"https://x.com/{screen_name}/status/{legacy.get('id_str', tweet_obj.get('rest_id', ''))}",

            # === التفاعل ===
            "favorite_count": legacy.get("favorite_count", 0),
            "reply_count": legacy.get("reply_count", 0),
            "retweet_count": legacy.get("retweet_count", 0),
            "quote_count": legacy.get("quote_count", 0),
            "bookmark_count": legacy.get("bookmark_count", 0),
            "views_count": views_data.get("count", "0"),
            "views_state": views_data.get("state", ""),
            "favorited": legacy.get("favorited", False),
            "retweeted": legacy.get("retweeted", False),
            "bookmarked": legacy.get("bookmarked", False),

            # === حالة التغريدة ===
            "is_quote_status": legacy.get("is_quote_status", False),
            "possibly_sensitive": legacy.get("possibly_sensitive", False),
            "possibly_sensitive_editable": legacy.get("possibly_sensitive_editable", False),
            "conversation_id": legacy.get("conversation_id_str", ""),
            "display_text_range": json.dumps(legacy.get("display_text_range", []), ensure_ascii=False),
            "is_translatable": tweet_obj.get("is_translatable", False),
            "unmention_data": json.dumps(tweet_obj.get("unmention_data", {}), ensure_ascii=False),

            # === التعديل ===
            "is_edit_eligible": edit_control_initial.get("is_edit_eligible", False),
            "edits_remaining": edit_control_initial.get("edits_remaining", ""),
            "editable_until_msecs": edit_control_initial.get("editable_until_msecs", ""),
            "edit_history_tweet_ids": json.dumps(edit_control_initial.get("edit_control_initial", {}).get("edit_tweet_ids", edit_control.get("edit_tweet_ids", [])), ensure_ascii=False),

            # === الرد على ===
            "in_reply_to_status_id": legacy.get("in_reply_to_status_id_str", ""),
            "in_reply_to_user_id": legacy.get("in_reply_to_user_id_str", ""),
            "in_reply_to_screen_name": legacy.get("in_reply_to_screen_name", ""),

            # === الاقتباس ===
            "quoted_tweet_id": quoted_status.get("rest_id", ""),
            "quoted_tweet_text": quoted_status.get("legacy", {}).get("full_text", ""),
            "quoted_tweet_user": quoted_status.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name", ""),

            # === الوسائط ===
            "has_media": len(media_data) > 0,
            "media_count": len(media_data),
            "media_types": json.dumps([m.get("type", "") for m in media_data], ensure_ascii=False),
            "media_urls": json.dumps([m.get("media_url_https", "") for m in media_data], ensure_ascii=False),
            "media_display_urls": json.dumps([m.get("display_url", "") for m in media_data], ensure_ascii=False),
            "media_expanded_urls": json.dumps([m.get("expanded_url", "") for m in media_data], ensure_ascii=False),
            "media_sizes": json.dumps([m.get("sizes", {}) for m in media_data], ensure_ascii=False),
            "media_alt_texts": json.dumps([m.get("ext_alt_text", "") for m in media_data], ensure_ascii=False),
            "video_urls": json.dumps(video_urls, ensure_ascii=False),
            "video_duration_ms": json.dumps([m.get("video_info", {}).get("duration_millis", 0) for m in media_data if m.get("video_info")], ensure_ascii=False),
            "video_aspect_ratio": json.dumps([m.get("video_info", {}).get("aspect_ratio", []) for m in media_data if m.get("video_info")], ensure_ascii=False),

            # === الكيانات (Entities) ===
            "hashtags": json.dumps([tag.get("text", "") for tag in entities.get("hashtags", [])], ensure_ascii=False),
            "user_mentions": json.dumps([
                {"id": m.get("id_str", ""), "screen_name": m.get("screen_name", ""), "name": m.get("name", "")}
                for m in entities.get("user_mentions", [])
            ], ensure_ascii=False),
            "urls": json.dumps([
                {"url": u.get("url", ""), "expanded_url": u.get("expanded_url", ""), "display_url": u.get("display_url", "")}
                for u in entities.get("urls", [])
            ], ensure_ascii=False),
            "symbols": json.dumps([s.get("text", "") for s in entities.get("symbols", [])], ensure_ascii=False),

            # === البطاقة (Card) ===
            "card_name": card_legacy.get("name", ""),
            "card_url": card_legacy.get("url", ""),
            "card_title": "",
            "card_description": "",

            # === بيانات المستخدم ===
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
            "user_default_profile": user_legacy.get("default_profile", False),
            "user_default_profile_image": user_legacy.get("default_profile_image", False),
            "user_pinned_tweet_ids": json.dumps(user_legacy.get("pinned_tweet_ids_str", []), ensure_ascii=False),
            "user_professional_type": user_professional.get("professional_type", ""),
            "user_professional_category": json.dumps(user_professional.get("category", []), ensure_ascii=False),
            "user_has_nft_avatar": user_result.get("has_nft_avatar", False),

            # === معلومات إضافية ===
            "typename": tweet_obj.get("__typename", ""),
            "extracted_at": datetime.now().isoformat()
        }

        # استخراج بيانات البطاقة إن وجدت
        card_binding_values = card_legacy.get("binding_values", [])
        for bv in card_binding_values:
            key = bv.get("key", "")
            val = bv.get("value", {})
            if key == "title":
                tweet_data["card_title"] = val.get("string_value", "")
            elif key == "description":
                tweet_data["card_description"] = val.get("string_value", "")

        return tweet_data

    except Exception as e:
        print(f"[X] خطأ في استخراج بيانات التغريدة: {e}")
        return None


# ========== الخصائص (Features) المطلوبة لطلب GraphQL ==========
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

# ========== إعدادات التايم لاين الرئيسي (Home Timeline) ==========
HOME_TIMELINE_QUERY_ID = "gKia-nBM9kwuDEfSDeWMfQ"
HOME_TIMELINE_URL = f"https://x.com/i/api/graphql/{HOME_TIMELINE_QUERY_ID}/HomeTimeline"


# ========== حفظ في CSV مع دعم كامل للعربية ==========
def save_to_csv(tweets, filename):
    """حفظ التغريدات كملف CSV يدعم العربية بالكامل"""
    if not tweets:
        print("[!] لا توجد تغريدات للحفظ")
        return

    # جمع جميع الأعمدة من كل التغريدات
    all_fields = []
    for tweet in tweets:
        for key in tweet.keys():
            if key not in all_fields:
                all_fields.append(key)

    # utf-8-sig يضيف BOM لضمان فتح العربية بشكل صحيح في Excel
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        for tweet in tweets:
            # تحويل أي قيم غير نصية
            row = {}
            for key in all_fields:
                val = tweet.get(key, "")
                if isinstance(val, (list, dict)):
                    row[key] = json.dumps(val, ensure_ascii=False)
                elif isinstance(val, bool):
                    row[key] = str(val)
                else:
                    row[key] = val
            writer.writerow(row)

    print(f"[SAVE] تم الحفظ: {filename} ({len(tweets)} تغريدة)")


# ========== سحب التايم لاين الرئيسي (Home Timeline) ==========
def fetch_home_timeline(count=100, cookies_path="coo.txt", include_rt=True, include_replies=True):
    """
    سحب التايم لاين الخاص بالحساب نفسه (الصفحة الرئيسية Home Timeline)
    باستخدام كوكيز الحساب - يتوقف عند الوصول للعدد المطلوب بالضبط

    المعاملات:
        count: عدد التغريدات المطلوب حفظها - يتوقف عند الوصول لهذا الرقم
        cookies_path: مسار ملف الكوكيز
        include_rt: تضمين إعادات التغريد (افتراضي: نعم)
        include_replies: تضمين الردود (افتراضي: نعم)
    """
    cookies = load_cookies(cookies_path)
    if not cookies:
        print("[X] لا يوجد كوكيز صالحة")
        return []

    print(f"[>>] الهدف: {count} تغريدة من التايم لاين الرئيسي للحساب")
    print()

    all_tweets = []
    seen_ids = set()
    cursor = None
    page = 1
    skipped_rt = 0
    skipped_reply = 0

    while len(all_tweets) < count:
        print(f"[P{page}] محفوظ: {len(all_tweets)}/{count} | تخطي RT: {skipped_rt} | تخطي ردود: {skipped_reply}")

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
                print("[WAIT] Rate limit - انتظار 60 ثانية...")
                time.sleep(60)
                continue

            resp.raise_for_status()
            response_data = resp.json()

        except requests.exceptions.RequestException as e:
            print(f"[X] خطأ في الطلب: {e}")
            break

        instructions = (
            response_data.get("data", {})
                .get("home", {})
                .get("home_timeline_urt", {})
                .get("instructions", [])
        )

        found_in_page = 0
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
                    tweet_result = entry["content"]["itemContent"]["tweet_results"]["result"]

                    if tweet_result.get("__typename") == "TweetWithVisibilityResults":
                        tweet_result = tweet_result.get("tweet", tweet_result)

                    if tweet_result.get("__typename") != "Tweet":
                        continue

                    legacy = tweet_result.get("legacy", {})
                    full_text = legacy.get("full_text", "")
                    tid = legacy.get("id_str", tweet_result.get("rest_id", ""))

                    # تجاهل المكرر
                    if tid in seen_ids:
                        continue
                    seen_ids.add(tid)

                    # تجاهل الريتويت (اختياري)
                    if full_text.startswith("RT @") and not include_rt:
                        skipped_rt += 1
                        continue

                    # تجاهل الردود (اختياري)
                    if legacy.get("in_reply_to_status_id_str") and not include_replies:
                        skipped_reply += 1
                        continue

                    # استخراج اسم صاحب التغريدة (كل تغريدة من حساب مختلف في التايم لاين)
                    # ملاحظة: نقل تويتر screen_name إلى core بدلا من legacy
                    _user_result = (tweet_result.get("core", {})
                                    .get("user_results", {}).get("result", {}))
                    screen_name = (_user_result.get("core", {}).get("screen_name", "")
                                   or _user_result.get("legacy", {}).get("screen_name", ""))

                    # استخراج جميع البيانات
                    tweet_data = extract_all_tweet_data(tweet_result, screen_name)

                    if tweet_data:
                        all_tweets.append(tweet_data)
                        found_in_page += 1
                        print(f"   [+] [{len(all_tweets)}/{count}] @{screen_name}: {full_text[:50]}...")

                    # التوقف عند الوصول للعدد المطلوب
                    if len(all_tweets) >= count:
                        break

                except (KeyError, TypeError):
                    continue

            if len(all_tweets) >= count:
                break

        # التوقف عند الوصول للعدد المطلوب
        if len(all_tweets) >= count:
            print(f"\n[DONE] تم الوصول للعدد المطلوب: {count} تغريدة")
            break

        # الانتقال للصفحة التالية
        if next_cursor and entries_in_page > 0:
            cursor = next_cursor
            page += 1
            delay = random.uniform(2.0, 4.0)
            print(f"[WAIT] انتظار {delay:.1f} ثانية...")
            time.sleep(delay)
        else:
            print(f"\n[END] انتهت تغريدات التايم لاين المتاحة ({len(all_tweets)} تغريدة)")
            break

    # قص القائمة للعدد المطلوب بالضبط
    all_tweets = all_tweets[:count]

    print(f"\n{'=' * 50}")
    print(f"[OK] النتيجة النهائية: {len(all_tweets)} تغريدة من التايم لاين")
    print(f"   تخطي ريتويت: {skipped_rt}")
    print(f"   تخطي ردود: {skipped_reply}")
    print(f"{'=' * 50}")

    return all_tweets


# ========== الإعدادات - عدّل هنا ==========
TWEET_COUNT = 500             # ← عدد التغريدات المطلوبة من التايم لاين
COOKIES_FILE = "coo.txt"      # ← مسار ملف الكوكيز
INCLUDE_RT = True             # ← تضمين إعادات التغريد
INCLUDE_REPLIES = True        # ← تضمين الردود

# ========== نقطة الدخول ==========
if __name__ == "__main__":
    print(f"[START] بدء سحب التايم لاين الرئيسي للحساب")
    print(f"[>>] العدد المطلوب: {TWEET_COUNT} تغريدة")
    print()

    tweets = fetch_home_timeline(
        count=TWEET_COUNT,
        cookies_path=COOKIES_FILE,
        include_rt=INCLUDE_RT,
        include_replies=INCLUDE_REPLIES
    )

    if not tweets:
        print("[X] لم يتم سحب اي تغريدات")
        exit(1)

    # حفظ تلقائي في CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"home_timeline_{len(tweets)}_{timestamp}.csv"
    save_to_csv(tweets, filename)

    print(f"\n[DONE] انتهى! الملف: {filename}")
