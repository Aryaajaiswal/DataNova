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
        uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at '{DB_PATH}'.")

def _ensure_metadata_table():
    """Create the metadata table if it doesn't exist (robust initialization)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS _uploads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name  TEXT NOT NULL UNIQUE,
        file_name   TEXT NOT NULL,
        row_count   INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
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
        "INSERT OR REPLACE INTO _uploads (table_name, file_name, row_count) VALUES (?, ?, ?)",
        (table_name, file_name, row_count)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()
