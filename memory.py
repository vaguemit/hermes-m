import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "agent.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,         -- 'reddit_post', 'email', 'linkedin_draft', 'monitor_report'
                title TEXT,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',      -- JSON: subreddit, recipients, etc.
                status TEXT DEFAULT 'pending',   -- pending | approved | rejected | posted | failed
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS posted_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                title TEXT,
                platform_id TEXT,               -- reddit post id, email message id, etc.
                posted_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS monitor_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,                    -- 'reddit', 'web'
                item_id TEXT UNIQUE,            -- reddit post/comment id
                content TEXT,
                sentiment TEXT,
                seen_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)


def enqueue(task_type: str, content: str, title: str = "", metadata: dict = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO queue (task_type, title, content, metadata) VALUES (?, ?, ?, ?)",
            (task_type, title, content, json.dumps(metadata or {}))
        )
        return cur.lastrowid


def get_pending() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM queue WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def update_status(item_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE queue SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, item_id)
        )


def log_posted(task_type: str, title: str, platform_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO posted_log (task_type, title, platform_id) VALUES (?, ?, ?)",
            (task_type, title, platform_id)
        )


def cache_monitor_item(source: str, item_id: str, content: str, sentiment: str = "neutral"):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO monitor_cache (source, item_id, content, sentiment) VALUES (?, ?, ?, ?)",
                (source, item_id, content, sentiment)
            )
            return True
        except sqlite3.IntegrityError:
            return False  # already seen


def add_chat_message(role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            (role, content)
        )


def get_chat_history(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


init_db()
