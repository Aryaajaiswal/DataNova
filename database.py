"""
database.py
Provides a DatabaseConnector abstraction with security filters and timeout support.
"""

import re
import pandas as pd
from sqlalchemy import create_engine, inspect, text as sa_text

BLOCKED_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bATTACH\b',
    r'\bDETACH\b', r'\bREPLACE\b', r'\bVACUUM\b', r'\bREINDEX\b',
    r'\bEXEC\b', r'\bEXECUTE\b', r'\bGRANT\b', r'\bLOAD\b',
    r'\bPRAGMA\b',
]

class DatabaseConnector:
    def __init__(self, db_url: str, timeout: int = 30):
        self.db_url = db_url
        connect_args = {"timeout": timeout} if db_url.startswith("sqlite") else {}
        self.engine = create_engine(self.db_url, connect_args=connect_args, pool_pre_ping=True)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_tables(self) -> list[str]:
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception:
            return []

    def get_table_schema(self, table_name: str) -> str:
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            col_defs = ", ".join(f"{c['name']} {c['type']}" for c in columns)
            return f"{table_name}({col_defs})"
        except Exception:
            return ""

    def _is_query_safe(self, sql: str) -> bool:
        """Check if SQL is read-only. Uses regex word boundaries to avoid false positives."""
        upper_sql = sql.upper()
        for pattern in BLOCKED_KEYWORDS:
            if re.search(pattern, upper_sql):
                return False
        return True

    def execute_query(self, sql: str) -> pd.DataFrame:
        """Executes a read-only SQL query with security checks."""
        if not self._is_query_safe(sql):
            raise ValueError("Only SELECT queries are allowed for security reasons.")
        return pd.read_sql(sql, self.engine)

    def upload_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        df.to_sql(table_name, self.engine, if_exists="replace", index=False)

    def upload_csv(self, file_path: str, table_name: str, encoding: str = "utf-8") -> int:
        df = pd.read_csv(file_path, encoding=encoding)
        self.upload_dataframe(df, table_name)
        return len(df)

    def upload_excel(self, file_path: str, table_name: str, sheet_name: str = 0) -> int:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        self.upload_dataframe(df, table_name)
        return len(df)
