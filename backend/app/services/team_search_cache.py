"""SQLite-backed team search cache with stale fallback and retry cooldown."""
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "team_sections_cache.sqlite3"
SEARCH_TTL_SECONDS = 3600
RETRY_SECONDS = 180


def _connect():
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.execute("""CREATE TABLE IF NOT EXISTS team_search_cache (
        query TEXT PRIMARY KEY, payload TEXT NOT NULL, saved_at REAL NOT NULL,
        retry_after REAL NOT NULL DEFAULT 0)""")
    return db


def normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def read_search(query: str):
    try:
        with _connect() as db:
            row = db.execute("SELECT payload, saved_at, retry_after FROM team_search_cache WHERE query=?",
                             (normalize_query(query),)).fetchone()
        if row:
            return {"results": json.loads(row[0]), "saved_at": row[1], "retry_after": row[2]}
    except (sqlite3.Error, ValueError, TypeError):
        pass
    return None


def save_search(query: str, results):
    try:
        with _connect() as db:
            db.execute("""INSERT INTO team_search_cache(query,payload,saved_at,retry_after)
                VALUES(?,?,?,0) ON CONFLICT(query) DO UPDATE SET
                payload=excluded.payload,saved_at=excluded.saved_at,retry_after=0""",
                (normalize_query(query), json.dumps(results), time.time()))
    except (sqlite3.Error, ValueError, TypeError):
        pass


def postpone_search(query: str):
    try:
        with _connect() as db:
            db.execute("UPDATE team_search_cache SET retry_after=? WHERE query=?",
                       (time.time() + RETRY_SECONDS, normalize_query(query)))
    except sqlite3.Error:
        pass
