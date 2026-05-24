"""
Scheduled Posts Publisher — Background worker لنشر التغريدات المجدولة
يعمل داخل سيرفر app/x. يقرأ من جدول scheduled_posts، ينشر التغريدات
المُستحقة عبر Playwright، ثم يستدعي webhook الـ callback لإشعار main app.
"""
import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from modules.db import (
    get_due_scheduled_posts,
    update_scheduled_post_status,
    get_cookie_by_label,
    save_tweet,
    log_operation,
)
from modules.utils import download_to_temp, is_url
from modules.x_post import post_to_x


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIES_DIR = BASE_DIR / 'cookies'

# الفاصل بين الـ ticks (ثوانٍ)
TICK_INTERVAL = 15
# مهلة retry بين المحاولات (ثوانٍ): 60, 300, 900 (1min, 5min, 15min)
RETRY_DELAYS = [60, 300, 900]
# مهلة استدعاء الـ webhook (ثوانٍ)
WEBHOOK_TIMEOUT = 10

_worker_thread: Optional[threading.Thread] = None
_stop_flag = threading.Event()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def _publish_one(post: dict) -> dict:
    """
    ينشر تغريدة مجدولة. يرجع dict {success, tweet_url, error}.
    لا يحدّث DB هنا — المتصل مسؤول عن ذلك.
    """
    event_id = post['event_id']
    cookie_label = post['cookie_label']
    content = post['content']
    media_url = post.get('media_url')

    cookie = get_cookie_by_label(cookie_label)
    if not cookie:
        return {"success": False, "tweet_url": None,
                "error": f"الحساب '{cookie_label}' غير مسجّل"}

    storage_state_path = str(COOKIES_DIR / cookie['filename'])
    if not os.path.exists(storage_state_path):
        return {"success": False, "tweet_url": None,
                "error": f"ملف كوكيز '{cookie_label}' غير موجود"}

    media_path = None
    tmp_dir = None
    try:
        if media_url and is_url(media_url):
            tmp_dir = tempfile.mkdtemp(prefix='sched_media_')
            try:
                media_path = download_to_temp(media_url, tmp_dir)
            except Exception as e:
                logger.warning(f"[Scheduler] {event_id} media download failed: {e}")
                media_path = None

        tweet_url = post_to_x(
            storage_state_path=storage_state_path,
            text=content,
            media_path=media_path,
            headless=True,
        )

        if tweet_url:
            try:
                save_tweet(cookie_label, tweet_url, content)
            except Exception:
                pass
            return {"success": True, "tweet_url": tweet_url, "error": None}

        return {"success": False, "tweet_url": None,
                "error": "النشر لم يُرجع رابط تغريدة"}

    except Exception as e:
        return {"success": False, "tweet_url": None, "error": str(e)[:500]}
    finally:
        if tmp_dir:
            try:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass


def _fire_callback(post: dict, success: bool, tweet_url: Optional[str], error: Optional[str]):
    """يستدعي callback_url لإشعار main app بالنتيجة."""
    callback_url = post.get('callback_url')
    if not callback_url:
        return None

    payload_raw = post.get('callback_payload') or '{}'
    try:
        callback_payload = json.loads(payload_raw)
    except Exception:
        callback_payload = {}

    payload = {
        "event_id": post['event_id'],
        "cookie_label": post['cookie_label'],
        "content": post['content'],
        "success": success,
        "tweet_url": tweet_url,
        "error": error,
        "callback_payload": callback_payload,
        "fired_at": _utc_now_iso(),
    }

    try:
        resp = requests.post(
            callback_url, json=payload, timeout=WEBHOOK_TIMEOUT
        )
        cb_status = "ok" if resp.status_code < 400 else f"http_{resp.status_code}"
    except Exception as e:
        cb_status = f"error:{str(e)[:100]}"

    logger.info(f"[Scheduler] {post['event_id']} callback → {cb_status}")
    return cb_status


def _process_due_posts():
    """يعالج جميع التغريدات المُستحقة في الدورة الحالية."""
    now_iso = _utc_now_iso()
    due = get_due_scheduled_posts(now_iso, batch_size=5)
    if not due:
        return

    logger.info(f"[Scheduler] processing {len(due)} due post(s)")
    for post in due:
        event_id = post['event_id']
        attempts = post.get('attempts', 0)
        max_attempts = post.get('max_attempts', 3)

        # علّمها كـ PUBLISHING لمنع المعالجة المتكررة
        update_scheduled_post_status(event_id, "PUBLISHING", increment_attempts=True)

        result = _publish_one(post)
        success = result['success']
        tweet_url = result['tweet_url']
        error = result['error']

        if success:
            update_scheduled_post_status(
                event_id, "PUBLISHED",
                tweet_url=tweet_url, mark_published=True
            )
            try:
                log_operation('schedule_publish', post['cookie_label'], 'success',
                              f"تم نشر التغريدة المجدولة ✅",
                              meta_json=json.dumps({"event_id": event_id, "tweet_url": tweet_url},
                                                   ensure_ascii=False))
            except Exception:
                pass

            cb_status = _fire_callback(post, True, tweet_url, None)
            if cb_status:
                update_scheduled_post_status(event_id, "PUBLISHED", callback_status=cb_status)

        else:
            new_attempts = attempts + 1
            if new_attempts < max_attempts:
                # سيتم إعادة المحاولة في الـ tick التالي بعد فترة retry
                from datetime import timedelta
                delay = RETRY_DELAYS[min(new_attempts - 1, len(RETRY_DELAYS) - 1)]
                next_run = (datetime.now(timezone.utc) + timedelta(seconds=delay)
                            ).strftime('%Y-%m-%d %H:%M:%S')
                # نُعيد الحالة إلى SCHEDULED مع تأجيل run_at
                from modules.db import connect as _conn
                with _conn() as con:
                    con.execute(
                        "UPDATE scheduled_posts SET status='SCHEDULED', run_at=?, "
                        "error_message=?, updated_at=? WHERE event_id=?",
                        (next_run, error, _utc_now_iso(), event_id)
                    )
                logger.warning(f"[Scheduler] {event_id} attempt {new_attempts}/{max_attempts} "
                               f"failed: {error[:100]} — retrying at {next_run}")
            else:
                # استنفذت المحاولات
                update_scheduled_post_status(
                    event_id, "FAILED", error_message=error
                )
                try:
                    log_operation('schedule_publish', post['cookie_label'], 'error',
                                  f"فشل نشر التغريدة المجدولة بعد {max_attempts} محاولة",
                                  meta_json=json.dumps({"event_id": event_id, "error": error},
                                                       ensure_ascii=False))
                except Exception:
                    pass

                cb_status = _fire_callback(post, False, None, error)
                if cb_status:
                    update_scheduled_post_status(event_id, "FAILED", callback_status=cb_status)


def _worker_loop():
    logger.info(f"[Scheduler] worker started — tick every {TICK_INTERVAL}s")
    while not _stop_flag.is_set():
        try:
            _process_due_posts()
        except Exception as e:
            logger.error(f"[Scheduler] worker error: {e}", exc_info=True)
        _stop_flag.wait(TICK_INTERVAL)
    logger.info("[Scheduler] worker stopped")


def start_worker():
    """يبدأ الـ background worker (idempotent)."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return False
    _stop_flag.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="ScheduledPublisher")
    _worker_thread.start()
    return True


def stop_worker():
    """يوقف الـ worker."""
    _stop_flag.set()
