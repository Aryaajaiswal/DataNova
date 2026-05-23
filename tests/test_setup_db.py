"""Tests for database module."""

import os, sqlite3, tempfile
import pytest
import pandas as pd

# Use a temp DB for tests
TEST_DB = os.path.join(tempfile.gettempdir(), "test_datanova.db")

@pytest.fixture(autouse=True)
def setup_teardown():
    # Point setup_db to test DB
    import setup_db
    old_path = setup_db.DB_PATH
    setup_db.DB_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    setup_db.create_database()
    yield
    setup_db.DB_PATH = old_path
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestAuth:
    def test_register_login(self):
        from setup_db import register_user, login_user
        ok, msg = register_user("testuser", "testpass")
        assert ok
        ok, msg = login_user("testuser", "testpass")
        assert ok

    def test_duplicate_user(self):
        from setup_db import register_user
        register_user("dup", "pass123")
        ok, msg = register_user("dup", "otherpass")
        assert not ok
        assert "already taken" in msg.lower()

    def test_wrong_password(self):
        from setup_db import register_user, login_user
        register_user("user1", "correct")
        ok, msg = login_user("user1", "wrong")
        assert not ok

    def test_short_username(self):
        from setup_db import register_user
        ok, msg = register_user("a", "pass123")
        assert not ok


class TestUploads:
    def test_register_upload(self):
        from setup_db import register_upload, get_uploaded_tables
        register_upload("my_table", "file.csv", 100, user_id="alice")
        tables = get_uploaded_tables("alice")
        assert "my_table" in tables

    def test_upload_isolation(self):
        from setup_db import register_upload, get_uploaded_tables
        register_upload("alice_tbl", "a.csv", 50, user_id="alice")
        register_upload("bob_tbl", "b.csv", 30, user_id="bob")
        alice_tables = get_uploaded_tables("alice")
        bob_tables = get_uploaded_tables("bob")
        assert "alice_tbl" in alice_tables
        assert "bob_tbl" not in alice_tables
        assert "bob_tbl" in bob_tables


class TestQueryLog:
    def test_log_query(self):
        from setup_db import register_query_log, get_query_log
        register_query_log("SELECT 1", "sql", "test", 1, "", 100, user_id="alice")
        logs = get_query_log(10, user_id="alice")
        assert len(logs) == 1
        assert logs[0][1] == "SELECT 1"

    def test_log_isolation(self):
        from setup_db import register_query_log, get_query_log
        register_query_log("alice query", user_id="alice")
        register_query_log("bob query", user_id="bob")
        assert len(get_query_log(10, user_id="alice")) == 1
        assert len(get_query_log(10, user_id="bob")) == 1


class TestSavedDashboards:
    def test_save_load(self):
        from setup_db import save_dashboard, load_user_dashboards
        dash = {"title": "Test", "kpis": [], "charts": []}
        ok, msg, token = save_dashboard("alice", "My Dash", "my_table", dash)
        assert ok
        assert token
        saved = load_user_dashboards("alice")
        assert len(saved) == 1
        assert saved[0]["name"] == "My Dash"

    def test_delete(self):
        from setup_db import save_dashboard, load_user_dashboards, delete_dashboard
        ok, _, token = save_dashboard("alice", "Del Me", "t", {"title": "x"})
        assert ok
        saved = load_user_dashboards("alice")
        dash_id = saved[0]["id"]
        assert delete_dashboard(dash_id, "alice")
        assert len(load_user_dashboards("alice")) == 0

    def test_share(self):
        from setup_db import save_dashboard, get_dashboard_by_token
        ok, _, token = save_dashboard("alice", "Share Me", "t", {"title": "Shared Dash"})
        assert ok
        loaded = get_dashboard_by_token(token)
        assert loaded is not None
        assert loaded["name"] == "Share Me"
        assert loaded["dashboard"]["title"] == "Shared Dash"
