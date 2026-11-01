import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).parent / "journal.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite database and create the entries table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_entry(title: str, content: str, mood: str) -> int:
    """Insert a new journal entry and return its newly created row ID."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO entries (title, content, mood, created_at)
            VALUES (?, ?, ?, ?)
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


def get_all_entries() -> List[Dict[str, Any]]:
    """Retrieve all journal entries ordered from newest to oldest."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, content, mood, created_at
            FROM entries
            ORDER BY id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_entry(entry_id: int) -> None:
    """Delete a journal entry by its ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
