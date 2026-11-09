"""
KiranaOS Database Connection Manager
Provides thread-safe access to SQLite database with WAL mode and foreign key enforcement.
Conforms to PRD §6, D-01, D-05, and Threat Model T-01-03.
"""

import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kiranaos.db"
)
SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "schema.sql"
)


def get_db_path(db_path: Optional[str] = None) -> str:
    """Resolve database path, defaulting to DEFAULT_DB_PATH or KIRANAOS_DB_PATH env var."""
    if db_path is not None:
        return db_path
    return os.environ.get("KIRANAOS_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Open and configure a SQLite connection.
    Enforces:
    - Row factory = sqlite3.Row for dictionary-like column access
    - PRAGMA foreign_keys = ON
    - PRAGMA journal_mode = WAL (for persistent file databases)
    - PRAGMA busy_timeout = 5000 (5s timeout to prevent lock contention per T-01-03)
    """
    resolved_path = get_db_path(db_path)
    if resolved_path != ":memory:":
        parent_dir = os.path.dirname(os.path.abspath(resolved_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(resolved_path, timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Execute essential PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON;")
    if resolved_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")

    return conn


def close_db_connection(conn: Optional[sqlite3.Connection]) -> None:
    """Safely close an open database connection."""
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize the database using backend/database/schema.sql.
    Creates parent directories and executes authoritative DDL statements.
    """
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Authoritative schema file not found at {SCHEMA_PATH}")

    conn = get_db_connection(db_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        close_db_connection(conn)
