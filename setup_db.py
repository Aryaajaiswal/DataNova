"""
setup_db.py
Initializes an empty SQLite database for user-uploaded data.
"""

import os
import sqlite3

DB_PATH = "datanova.db"

def create_database():
    """Create an empty database with a metadata table to track user-uploaded data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS _uploads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name  TEXT NOT NULL UNIQUE,
        file_name   TEXT NOT NULL,
        row_count   INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _query_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        query       TEXT NOT NULL,
        query_type  TEXT NOT NULL DEFAULT 'sql',
        user_message TEXT DEFAULT '',
        row_count   INTEGER DEFAULT 0,
        error       TEXT DEFAULT '',
        duration_ms INTEGER DEFAULT 0,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at '{DB_PATH}'.")

def _ensure_metadata_table():
    """Create the metadata tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS _uploads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name  TEXT NOT NULL UNIQUE,
        file_name   TEXT NOT NULL,
        row_count   INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _query_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        query       TEXT NOT NULL,
        query_type  TEXT NOT NULL DEFAULT "sql",
        user_message TEXT DEFAULT "",
        row_count   INTEGER DEFAULT 0,
        error       TEXT DEFAULT "",
        duration_ms INTEGER DEFAULT 0,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    conn.commit()
    conn.close()

def get_uploaded_tables():
    """Return list of user-uploaded table names (excluding internal metadata)."""
    _ensure_metadata_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM _uploads ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def register_upload(table_name: str, file_name: str, row_count: int):
    """Track an uploaded table in the metadata."""
    _ensure_metadata_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO _uploads (table_name, file_name, row_count) VALUES (?, ?, ?) "
        "ON CONFLICT(table_name) DO UPDATE SET file_name=excluded.file_name, row_count=excluded.row_count",
        (table_name, file_name, row_count)
    )
    conn.commit()
    conn.close()

def register_query_log(query: str, query_type: str = "sql", user_message: str = "", row_count: int = 0, error: str = "", duration_ms: int = 0):
    """Log a query execution to the audit log."""
    _ensure_metadata_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO _query_log (query, query_type, user_message, row_count, error, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (query, query_type, user_message, row_count, error, duration_ms)
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"register_query_log failed: {exc}")

def get_query_log(limit: int = 50) -> list:
    """Get the most recent query log entries."""
    _ensure_metadata_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, query, query_type, user_message, row_count, error, duration_ms, created_at FROM _query_log ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as exc:
        print(f"get_query_log failed: {exc}")
        return []

if __name__ == "__main__":
    create_database()
