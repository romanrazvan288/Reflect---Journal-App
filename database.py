import os
import json
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "journal.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite database, creating entries and settings tables, with schema migrations."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_pinned INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()

        # Schema migration: safely ensure 'is_pinned' column exists in existing tables
        cursor = conn.execute("PRAGMA table_info(entries)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "is_pinned" not in columns:
            conn.execute("ALTER TABLE entries ADD COLUMN is_pinned INTEGER DEFAULT 0")
            conn.commit()


# ------------------------------------------------------------------------------
# PIN & Security Helpers (PBKDF2 HMAC SHA-256)
# ------------------------------------------------------------------------------
def hash_pin(pin: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Hash PIN using PBKDF2 HMAC SHA-256 with 100,000 iterations."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100000)
    return key.hex(), salt.hex()


def verify_pin(pin: str) -> bool:
    """Verify if entered PIN matches the stored salt and hash."""
    stored_hash = get_setting("pin_hash")
    stored_salt = get_setting("pin_salt")
    if not stored_hash or not stored_salt:
        return False
    try:
        salt_bytes = bytes.fromhex(stored_salt)
        computed_hash, _ = hash_pin(pin, salt=salt_bytes)
        return computed_hash == stored_hash
    except Exception:
        return False


def set_user_pin(pin: str) -> None:
    """Hash and store the user's PIN in the settings table."""
    hashed, salt_hex = hash_pin(pin)
    set_setting("pin_hash", hashed)
    set_setting("pin_salt", salt_hex)


def is_pin_configured() -> bool:
    """Check if a security PIN is currently configured."""
    return get_setting("pin_hash") is not None and get_setting("pin_salt") is not None


def get_setting(key: str) -> Optional[str]:
    """Retrieve a value from the settings table."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    """Insert or update a setting value."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()


# ------------------------------------------------------------------------------
# Draft Auto-Save Persistence
# ------------------------------------------------------------------------------
def save_draft(title: str, mood: str, content: str) -> None:
    """Persist unsaved new entry draft into the settings table."""
    payload = json.dumps({"title": title, "mood": mood, "content": content})
    set_setting("new_entry_draft", payload)


def load_draft() -> Optional[Dict[str, str]]:
    """Retrieve saved draft if one exists."""
    raw = get_setting("new_entry_draft")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def clear_draft() -> None:
    """Clear any saved draft from settings."""
    with get_connection() as conn:
        conn.execute("DELETE FROM settings WHERE key = 'new_entry_draft'")
        conn.commit()


# ------------------------------------------------------------------------------
# Journal Entries Storage
# ------------------------------------------------------------------------------
def add_entry(title: str, content: str, mood: str) -> int:
    """Insert a new journal entry and return its newly created row ID."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO entries (title, content, mood, created_at, is_pinned)
            VALUES (?, ?, ?, ?, 0)
            """,
            (title.strip(), content.strip(), mood, created_at),
        )
        conn.commit()
        return cursor.lastrowid


def update_entry(entry_id: int, title: str, content: str, mood: str) -> None:
    """Update an existing journal entry by its ID."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE entries
            SET title = ?, content = ?, mood = ?
            WHERE id = ?
            """,
            (title.strip(), content.strip(), mood, entry_id),
        )
        conn.commit()


def toggle_pin_entry(entry_id: int) -> int:
    """Toggle the is_pinned status of an entry and return the new state (0 or 1)."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT is_pinned FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        new_val = 0 if (row and row["is_pinned"]) else 1
        conn.execute("UPDATE entries SET is_pinned = ? WHERE id = ?", (new_val, entry_id))
        conn.commit()
        return new_val


def get_all_entries() -> List[Dict[str, Any]]:
    """Retrieve all journal entries ordered with pinned first, then newest to oldest."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, content, mood, created_at, COALESCE(is_pinned, 0) as is_pinned
            FROM entries
            ORDER BY is_pinned DESC, id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_entry(entry_id: int) -> None:
    """Delete a journal entry by its ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
