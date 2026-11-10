"""SQLite persistence: users (salted PBKDF2 password hashes) and quiz history."""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import config
from app.errors import AuthError

PBKDF2_ITERATIONS = 200_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD_LEN = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON quiz_attempts(user_id, id DESC);
"""


@contextmanager
def connect(path=None):
    path = Path(path or config.APP_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str, salt: bytes = None, iterations=PBKDF2_ITERATIONS) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


def create_user(username: str, password: str, path=None) -> int:
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3-32 characters: letters, numbers, . _ -")
    if len(password or "") < MIN_PASSWORD_LEN:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    with connect(path) as conn:
        try:
            cur = conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                               (username, hash_password(password)))
        except sqlite3.IntegrityError as exc:
            raise AuthError("That username is already taken.") from exc
        return cur.lastrowid


def authenticate(username: str, password: str, path=None):
    """Return {'id', 'username'} on success, else None."""
    username = (username or "").strip().lower()
    with connect(path) as conn:
        row = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?",
                           (username,)).fetchone()
    if row is None:
        hash_password(password or "")  # keep timing similar for unknown users
        return None
    if not verify_password(password or "", row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"]}


def save_quiz_attempt(user_id, topic, difficulty, score, total, details, path=None) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO quiz_attempts (user_id, topic, difficulty, score, total, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, topic, difficulty, score, total, json.dumps(details)),
        )
        return cur.lastrowid


def get_quiz_history(user_id, limit=50, path=None):
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, topic, difficulty, score, total, details, created_at "
            "FROM quiz_attempts WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{**dict(r), "details": json.loads(r["details"])} for r in rows]


def get_user_stats(user_id, path=None):
    with connect(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS attempts, COALESCE(SUM(score),0) AS score, "
            "COALESCE(SUM(total),0) AS total FROM quiz_attempts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    pct = round(100 * row["score"] / row["total"], 1) if row["total"] else 0.0
    return {"attempts": row["attempts"], "average_pct": pct}
