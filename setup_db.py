"""
setup_db.py
Initializes an empty SQLite database for user-uploaded data.
"""

import hashlib
import secrets
import sqlite3

DB_PATH = "datanova.db"

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _ensure_all_tables():
    """Create all tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS _uploads (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL DEFAULT 'anonymous',
        table_name  TEXT NOT NULL,
        file_name   TEXT NOT NULL,
        row_count   INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, table_name)
    );
    CREATE TABLE IF NOT EXISTS _query_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL DEFAULT 'anonymous',
        query       TEXT NOT NULL,
        query_type  TEXT NOT NULL DEFAULT 'sql',
        user_message TEXT DEFAULT '',
        row_count   INTEGER DEFAULT 0,
        error       TEXT DEFAULT '',
        duration_ms INTEGER DEFAULT 0,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT NOT NULL UNIQUE,
        password    TEXT NOT NULL,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _alerts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        name        TEXT NOT NULL,
        table_name  TEXT NOT NULL DEFAULT '',
        dashboard_name TEXT NOT NULL DEFAULT '',
        condition_type TEXT NOT NULL DEFAULT 'threshold',
        column_name TEXT DEFAULT '',
        operator    TEXT DEFAULT '>',
        threshold   REAL DEFAULT 0,
        slack_webhook TEXT DEFAULT '',
        email_to    TEXT DEFAULT '',
        enabled     INTEGER NOT NULL DEFAULT 1,
        last_triggered TEXT DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _workspaces (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        owner_id    TEXT NOT NULL,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS _workspace_members (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        username    TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'member',
        FOREIGN KEY(workspace_id) REFERENCES _workspaces(id),
        UNIQUE(workspace_id, username)
    );
    CREATE TABLE IF NOT EXISTS _workspace_dashboards (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        dashboard_json TEXT NOT NULL,
        name        TEXT NOT NULL,
        created_by  TEXT NOT NULL,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(workspace_id) REFERENCES _workspaces(id)
    );
    CREATE TABLE IF NOT EXISTS _saved_dashboards (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        name        TEXT NOT NULL,
        table_name  TEXT NOT NULL DEFAULT '',
        dashboard_json TEXT NOT NULL,
        share_token TEXT NOT NULL UNIQUE,
        created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    _migrate_schema(conn, cursor)
    conn.close()

def _migrate_schema(conn, cursor):
    """Migrate old schema to new schema."""
    try:
        # Check _uploads for user_id column
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(_uploads)").fetchall()]
        if "user_id" not in cols:
            # Recreate _uploads with new schema, preserving existing data
            cursor.executescript("""
            CREATE TABLE _uploads_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL DEFAULT 'anonymous',
                table_name  TEXT NOT NULL,
                file_name   TEXT NOT NULL,
                row_count   INTEGER NOT NULL DEFAULT 0,
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, table_name)
            );
            INSERT INTO _uploads_new (id, user_id, table_name, file_name, row_count, uploaded_at)
                SELECT id, 'anonymous', table_name, file_name, row_count, uploaded_at FROM _uploads;
            DROP TABLE _uploads;
            ALTER TABLE _uploads_new RENAME TO _uploads;
            """)
        # Check _query_log for user_id column
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(_query_log)").fetchall()]
        if "user_id" not in cols:
            cursor.executescript("""
            CREATE TABLE _query_log_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL DEFAULT 'anonymous',
                query       TEXT NOT NULL,
                query_type  TEXT NOT NULL DEFAULT 'sql',
                user_message TEXT DEFAULT '',
                row_count   INTEGER DEFAULT 0,
                error       TEXT DEFAULT '',
                duration_ms INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO _query_log_new (id, user_id, query, query_type, user_message, row_count, error, duration_ms, created_at)
                SELECT id, 'anonymous', query, query_type, user_message, row_count, error, duration_ms, created_at FROM _query_log;
            DROP TABLE _query_log;
            ALTER TABLE _query_log_new RENAME TO _query_log;
            """)
        conn.commit()
    except Exception as exc:
        print(f"Migration note: {exc}")

def create_database():
    _ensure_all_tables()
    print(f"Database initialized at '{DB_PATH}'.")

# ── Auth ──

def register_user(username: str, password: str) -> tuple[bool, str]:
    _ensure_all_tables()
    if len(username) < 2:
        return False, "Username must be at least 2 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO _users (username, password) VALUES (?, ?)",
                       (username, _hash_password(password)))
        conn.commit()
        return True, "Registered successfully."
    except sqlite3.IntegrityError:
        return False, "Username already taken."
    finally:
        conn.close()

def login_user(username: str, password: str) -> tuple[bool, str]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM _users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == _hash_password(password):
        return True, "Login successful."
    return False, "Invalid username or password."

def user_exists(username: str) -> bool:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM _users WHERE username = ?", (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# ── Saved Dashboards ──

def save_dashboard(user_id: str, name: str, table_name: str, dashboard_dict: dict) -> tuple[bool, str, str]:
    _ensure_all_tables()
    import json
    share_token = secrets.token_hex(8)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO _saved_dashboards (user_id, name, table_name, dashboard_json, share_token) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, table_name, json.dumps(dashboard_dict), share_token)
        )
        conn.commit()
        return True, "Dashboard saved.", share_token
    except Exception as e:
        return False, f"Save failed: {e}", ""
    finally:
        conn.close()

def load_user_dashboards(user_id: str) -> list[dict]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, table_name, dashboard_json, share_token, created_at, updated_at FROM _saved_dashboards WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    import json
    result = []
    for r in rows:
        result.append({
            "id": r[0], "name": r[1], "table_name": r[2],
            "dashboard": json.loads(r[3]), "share_token": r[4],
            "created_at": r[5], "updated_at": r[6]
        })
    return result

def delete_dashboard(dashboard_id: int, user_id: str) -> bool:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM _saved_dashboards WHERE id = ? AND user_id = ?", (dashboard_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_dashboard_by_token(share_token: str) -> dict | None:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, table_name, dashboard_json, user_id FROM _saved_dashboards WHERE share_token = ?",
        (share_token,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return {"id": row[0], "name": row[1], "table_name": row[2], "dashboard": json.loads(row[3]), "user_id": row[4]}
    return None

# ── Uploads (now user-scoped) ──

def get_uploaded_tables(user_id: str = "anonymous"):
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM _uploads WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def register_upload(table_name: str, file_name: str, row_count: int, user_id: str = "anonymous"):
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO _uploads (user_id, table_name, file_name, row_count) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, table_name) DO UPDATE SET file_name=excluded.file_name, row_count=excluded.row_count",
        (user_id, table_name, file_name, row_count)
    )
    conn.commit()
    conn.close()

# ── Query Log (now user-scoped) ──

def register_query_log(query: str, query_type: str = "sql", user_message: str = "", row_count: int = 0, error: str = "", duration_ms: int = 0, user_id: str = "anonymous"):
    _ensure_all_tables()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO _query_log (user_id, query, query_type, user_message, row_count, error, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, query, query_type, user_message, row_count, error, duration_ms)
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"register_query_log failed: {exc}")

def get_query_log(limit: int = 50, user_id: str = "anonymous") -> list:
    _ensure_all_tables()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, query, query_type, user_message, row_count, error, duration_ms, created_at FROM _query_log WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as exc:
        print(f"get_query_log failed: {exc}")
        return []

# ── Alerts ──

def create_alert(user_id: str, name: str, table_name: str, dashboard_name: str,
                 condition_type: str = "threshold", column_name: str = "", operator: str = ">",
                 threshold: float = 0, slack_webhook: str = "", email_to: str = "") -> tuple[bool, str]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO _alerts (user_id, name, table_name, dashboard_name, condition_type, column_name, operator, threshold, slack_webhook, email_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, table_name, dashboard_name, condition_type, column_name, operator, threshold, slack_webhook, email_to)
        )
        conn.commit()
        return True, "Alert created."
    except Exception as e:
        return False, f"Failed: {e}"
    finally:
        conn.close()

def get_user_alerts(user_id: str) -> list[dict]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, table_name, dashboard_name, condition_type, column_name, operator, threshold, slack_webhook, email_to, enabled, last_triggered, created_at FROM _alerts WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r[0], "name": r[1], "table_name": r[2], "dashboard_name": r[3],
            "condition_type": r[4], "column_name": r[5], "operator": r[6],
            "threshold": r[7], "slack_webhook": r[8], "email_to": r[9],
            "enabled": bool(r[10]), "last_triggered": r[11], "created_at": r[12]
        })
    return result

def delete_alert(alert_id: int, user_id: str) -> bool:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM _alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def update_alert_trigger(alert_id: int):
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE _alerts SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

# ── Workspaces ──

def create_workspace(name: str, owner_id: str) -> tuple[bool, str]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO _workspaces (name, owner_id) VALUES (?, ?)", (name, owner_id))
        ws_id = cursor.lastrowid
        cursor.execute("INSERT INTO _workspace_members (workspace_id, username, role) VALUES (?, ?, 'owner')", (ws_id, owner_id))
        conn.commit()
        return True, "Workspace created."
    except sqlite3.IntegrityError:
        return False, "Workspace name already taken."
    except Exception as e:
        return False, f"Failed: {e}"
    finally:
        conn.close()

def get_user_workspaces(username: str) -> list[dict]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.id, w.name, w.owner_id, wm.role, w.created_at
        FROM _workspaces w
        JOIN _workspace_members wm ON w.id = wm.workspace_id
        WHERE wm.username = ?
        ORDER BY w.created_at DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "owner_id": r[2], "role": r[3], "created_at": r[4]} for r in rows]

def get_workspace_members(workspace_id: int) -> list[dict]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM _workspace_members WHERE workspace_id = ?", (workspace_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"username": r[0], "role": r[1]} for r in rows]

def add_workspace_member(workspace_id: int, username: str, role: str = "member") -> tuple[bool, str]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO _workspace_members (workspace_id, username, role) VALUES (?, ?, ?)", (workspace_id, username, role))
        conn.commit()
        return True, f"Added {username}."
    except sqlite3.IntegrityError:
        return False, f"{username} is already a member."
    except Exception as e:
        return False, f"Failed: {e}"
    finally:
        conn.close()

def save_workspace_dashboard(workspace_id: int, name: str, created_by: str, dashboard_dict: dict) -> tuple[bool, str]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        import json
        cursor.execute(
            "INSERT INTO _workspace_dashboards (workspace_id, dashboard_json, name, created_by) VALUES (?, ?, ?, ?)",
            (workspace_id, json.dumps(dashboard_dict), name, created_by)
        )
        conn.commit()
        return True, "Dashboard saved to workspace."
    except Exception as e:
        return False, f"Failed: {e}"
    finally:
        conn.close()

def get_workspace_dashboards(workspace_id: int) -> list[dict]:
    _ensure_all_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, dashboard_json, created_by, created_at FROM _workspace_dashboards WHERE workspace_id = ? ORDER BY created_at DESC", (workspace_id,))
    rows = cursor.fetchall()
    conn.close()
    import json
    result = []
    for r in rows:
        result.append({"id": r[0], "name": r[1], "dashboard": json.loads(r[2]), "created_by": r[3], "created_at": r[4]})
    return result

def check_alert_condition(alert: dict, dbc) -> tuple[bool, str]:
    """Check if an alert condition is met. Returns (triggered, message)."""
    try:
        table = alert["table_name"]
        col = alert["column_name"]
        op = alert["operator"]
        threshold = alert["threshold"]
        if not table:
            return False, ""
        if not col:
            df = dbc.execute_query(f"SELECT COUNT(*) as cnt FROM [{table}]")
            val = float(df.iloc[0, 0])
            label = "row count"
        else:
            df = dbc.execute_query(f"SELECT AVG(CAST([{col}] AS REAL)) as val FROM [{table}]")
            val = float(df.iloc[0, 0])
            label = f"avg({col})"
        triggered = {
            ">": val > threshold, "<": val < threshold,
            ">=": val >= threshold, "<=": val <= threshold,
            "==": abs(val - threshold) < 0.001
        }.get(op, False)
        if triggered:
            return True, f"⚠ Alert '{alert['name']}': {label} = {val:.2f} {op} {threshold}"
        return False, ""
    except Exception as e:
        return False, f"Check error: {e}"

if __name__ == "__main__":
    create_database()
