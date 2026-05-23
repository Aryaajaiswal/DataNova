"""Tests for database module."""

import os, tempfile
import pytest
import pandas as pd


@pytest.fixture
def db():
    from database import DatabaseConnector
    tmp = os.path.join(tempfile.gettempdir(), f"test_datanova_{os.urandom(4).hex()}.db")
    engine_str = f"sqlite:///{tmp}"
    dc = DatabaseConnector(engine_str)
    df = pd.DataFrame({"name": ["A", "B", "C"], "value": [10, 20, 30]})
    dc.upload_dataframe(df, "test_table")
    yield dc
    dc.engine.dispose()
    for _ in range(3):
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
            break
        except PermissionError:
            import time; time.sleep(0.1)


class TestDatabaseConnector:
    def test_connection(self, db):
        assert db.test_connection()

    def test_get_tables(self, db):
        tables = db.get_tables()
        assert "test_table" in tables

    def test_get_table_schema(self, db):
        schema = db.get_table_schema("test_table")
        assert "test_table" in schema
        assert "name" in schema

    def test_execute_query(self, db):
        df = db.execute_query("SELECT * FROM test_table")
        assert len(df) == 3

    def test_execute_query_limit(self, db):
        df = db.execute_query("SELECT * FROM test_table LIMIT 2")
        assert len(df) == 2

    def test_security_blocked(self, db):
        with pytest.raises(ValueError, match="Only SELECT"):
            db.execute_query("DROP TABLE test_table")

    def test_security_insert_blocked(self, db):
        with pytest.raises(ValueError, match="Only SELECT"):
            db.execute_query("INSERT INTO test_table VALUES (1,2)")

    def test_pagination(self, db):
        df = db.execute_query_paginated("SELECT * FROM test_table", page=1, page_size=2)
        assert len(df) == 2

    def test_upload_dataframe(self, db):
        df2 = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        db.upload_dataframe(df2, "new_table")
        tables = db.get_tables()
        assert "new_table" in tables

    def test_auto_limit(self, db):
        df = db.execute_query("SELECT * FROM test_table")
        assert len(df) <= 500
