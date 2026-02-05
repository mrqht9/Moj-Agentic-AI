import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
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
