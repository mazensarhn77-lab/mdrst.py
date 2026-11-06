"""Small database adapter: local SQLite or hosted Supabase PostgreSQL."""
from __future__ import annotations
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

class Connection:
    """Translate the app's qmark SQL parameters for psycopg while preserving SQLite locally."""
    def __init__(self, raw, postgres=False):
        self.raw = raw
        self.postgres = postgres
    def execute(self, sql, params=()):
        if self.postgres:
            sql = sql.replace("?", "%s")
        return self.raw.execute(sql, params)
    def __enter__(self):
        self.raw.__enter__()
        return self
    def __exit__(self, exc_type, exc, tb):
        return self.raw.__exit__(exc_type, exc, tb)


def connect(sqlite_path, timeout=15):
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        # Transaction pooling (recommended for serverless) does not support prepared statements.
        raw = psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
        return Connection(raw, postgres=True)
    raw = sqlite3.connect(sqlite_path, timeout=timeout)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys=ON")
    return Connection(raw)


def is_unique_error(exc):
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    if USE_POSTGRES:
        import psycopg
        return isinstance(exc, psycopg.errors.UniqueViolation)
    return False
