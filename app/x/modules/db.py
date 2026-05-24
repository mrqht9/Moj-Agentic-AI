import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    # Fix encoding for Arabic text
    con.execute("PRAGMA encoding = 'UTF-8'")
    return con


def init_db() -> None:
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cookies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                cookie_label TEXT,
                status TEXT NOT NULL,
                message TEXT,
                meta_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cookie_label TEXT NOT NULL,
                tweet_url TEXT NOT NULL,
                tweet_text TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                cookie_label TEXT NOT NULL,
                content TEXT NOT NULL,
                media_url TEXT,
                run_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SCHEDULED',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                tweet_url TEXT,
                error_message TEXT,
                callback_url TEXT,
                callback_payload TEXT,
                callback_status TEXT,
                published_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status_run "
            "ON scheduled_posts(status, run_at)"
        )


def now_iso() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def upsert_cookie(label: str, filename: str) -> int:
    with connect() as con:
        con.execute(
            "INSERT INTO cookies(label,filename,created_at) VALUES(?,?,?) "
            "ON CONFLICT(label) DO UPDATE SET filename=excluded.filename",
            (label, filename, now_iso()),
        )
        row = con.execute("SELECT id FROM cookies WHERE label=?", (label,)).fetchone()
        return int(row['id'])


def list_cookies() -> List[Dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT * FROM cookies ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_cookie_by_label(label: str) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM cookies WHERE label=?", (label,)).fetchone()
        return dict(r) if r else None


def get_cookie_by_id(cookie_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM cookies WHERE id=?", (cookie_id,)).fetchone()
        return dict(r) if r else None


def delete_cookie(cookie_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM cookies WHERE id=?", (cookie_id,)).fetchone()
        if not r:
            return None
        con.execute("DELETE FROM cookies WHERE id=?", (cookie_id,))
        return dict(r)


def log_operation(action: str, cookie_label: Optional[str], status: str, message: str, meta_json: str = "") -> int:
    import json
    # Fix encoding issue for Arabic text
    if meta_json and isinstance(meta_json, dict):
        meta_json = json.dumps(meta_json, ensure_ascii=False)
    with connect() as con:
        con.execute(
            "INSERT INTO operations(action,cookie_label,status,message,meta_json,created_at) VALUES(?,?,?,?,?,?)",
            (action, cookie_label, status, message, meta_json, now_iso()),
        )
        rid = con.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return int(rid)


def get_operation(op_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM operations WHERE id=?", (op_id,)).fetchone()
        return dict(r) if r else None


def list_operations(limit: int = 100) -> List[Dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def stats() -> Dict[str, int]:
    with connect() as con:
        cookies = con.execute("SELECT COUNT(*) c FROM cookies").fetchone()["c"]
        posts = con.execute("SELECT COUNT(*) c FROM operations WHERE action='post' AND status='success'").fetchone()["c"]
        profiles = con.execute("SELECT COUNT(*) c FROM operations WHERE action='profile' AND status='success'").fetchone()["c"]
        logins = con.execute("SELECT COUNT(*) c FROM operations WHERE action='login' AND status='success'").fetchone()["c"]
        tweets = con.execute("SELECT COUNT(*) c FROM tweets").fetchone()["c"]
    return {"cookies": int(cookies), "posts": int(posts), "profiles": int(profiles), "logins": int(logins), "tweets": int(tweets)}


def save_tweet(cookie_label: str, tweet_url: str, tweet_text: str = "") -> int:
    with connect() as con:
        con.execute(
            "INSERT INTO tweets(cookie_label, tweet_url, tweet_text, created_at) VALUES(?,?,?,?)",
            (cookie_label, tweet_url, tweet_text, now_iso()),
        )
        rid = con.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return int(rid)


def list_tweets(limit: int = 100, cookie_label: Optional[str] = None) -> List[Dict[str, Any]]:
    with connect() as con:
        if cookie_label:
            rows = con.execute(
                "SELECT * FROM tweets WHERE cookie_label=? ORDER BY id DESC LIMIT ?",
                (cookie_label, limit)
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM tweets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_tweet(tweet_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM tweets WHERE id=?", (tweet_id,)).fetchone()
        return dict(r) if r else None


def delete_tweet_from_db(tweet_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM tweets WHERE id=?", (tweet_id,)).fetchone()
        if not r:
            return None
        con.execute("DELETE FROM tweets WHERE id=?", (tweet_id,))
        return dict(r)


# ───────────────────────── Scheduled Posts ─────────────────────────
def insert_scheduled_post(
    event_id: str,
    cookie_label: str,
    content: str,
    run_at: str,
    media_url: Optional[str] = None,
    callback_url: Optional[str] = None,
    callback_payload: Optional[str] = None,
    max_attempts: int = 3,
) -> int:
    """يدرج تغريدة مجدولة جديدة. run_at بصيغة ISO UTC (YYYY-MM-DD HH:MM:SS)."""
    with connect() as con:
        con.execute(
            "INSERT INTO scheduled_posts("
            "event_id, cookie_label, content, media_url, run_at, status, attempts, max_attempts, "
            "callback_url, callback_payload, created_at, updated_at"
            ") VALUES(?,?,?,?,?,'SCHEDULED',0,?,?,?,?,?)",
            (event_id, cookie_label, content, media_url, run_at, max_attempts,
             callback_url, callback_payload, now_iso(), now_iso()),
        )
        rid = con.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return int(rid)


def get_scheduled_post(event_id: str) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM scheduled_posts WHERE event_id=?", (event_id,)).fetchone()
        return dict(r) if r else None


def list_scheduled_posts(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    with connect() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM scheduled_posts WHERE status=? ORDER BY run_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM scheduled_posts ORDER BY run_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_due_scheduled_posts(now_iso_str: str, batch_size: int = 10) -> List[Dict[str, Any]]:
    """يرجع التغريدات المُستحقة للنشر (SCHEDULED + run_at <= now)."""
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM scheduled_posts WHERE status='SCHEDULED' AND run_at <= ? "
            "ORDER BY run_at ASC LIMIT ?",
            (now_iso_str, batch_size)
        ).fetchall()
        return [dict(r) for r in rows]


def update_scheduled_post_status(
    event_id: str,
    status: str,
    tweet_url: Optional[str] = None,
    error_message: Optional[str] = None,
    increment_attempts: bool = False,
    mark_published: bool = False,
    callback_status: Optional[str] = None,
) -> bool:
    with connect() as con:
        sets = ["status=?", "updated_at=?"]
        params: list = [status, now_iso()]
        if tweet_url is not None:
            sets.append("tweet_url=?"); params.append(tweet_url)
        if error_message is not None:
            sets.append("error_message=?"); params.append(error_message)
        if increment_attempts:
            sets.append("attempts=attempts+1")
        if mark_published:
            sets.append("published_at=?"); params.append(now_iso())
        if callback_status is not None:
            sets.append("callback_status=?"); params.append(callback_status)
        params.append(event_id)
        cur = con.execute(
            f"UPDATE scheduled_posts SET {', '.join(sets)} WHERE event_id=?",
            params
        )
        return cur.rowcount > 0


def delete_scheduled_post(event_id: str) -> Optional[Dict[str, Any]]:
    with connect() as con:
        r = con.execute("SELECT * FROM scheduled_posts WHERE event_id=?", (event_id,)).fetchone()
        if not r:
            return None
        con.execute("DELETE FROM scheduled_posts WHERE event_id=?", (event_id,))
        return dict(r)
