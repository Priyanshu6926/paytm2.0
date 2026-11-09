"""
Tests for KiranaOS SQLite Connection Manager.
Verifies WAL mode, foreign key enforcement, row factory, and lifecycle management.
"""

import sqlite3
import pytest
from backend.database.connection import (
    close_db_connection,
    get_db_connection,
    get_db_path,
    init_db,
)


def test_get_db_connection_in_memory():
    """Verify in-memory connection attributes and pragma settings."""
    conn = get_db_connection(":memory:")
    try:
        assert conn is not None
        assert conn.row_factory == sqlite3.Row

        # Check foreign keys enabled
        cursor = conn.cursor()
        fk_status = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1

        # Check busy timeout
        timeout = cursor.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert timeout == 5000
    finally:
        close_db_connection(conn)


def test_get_db_connection_file_wal_mode(tmp_path):
    """Verify file-based connection creates directory and enables WAL journal mode."""
    db_file = tmp_path / "nested" / "kiranaos_test.db"
    assert not db_file.parent.exists()

    conn = get_db_connection(str(db_file))
    try:
        assert db_file.parent.exists()
        cursor = conn.cursor()

        # Check WAL mode
        journal_mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal"

        # Check foreign keys enabled
        fk_status = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1
    finally:
        close_db_connection(conn)


def test_close_db_connection():
    """Verify safe closing of connections and handling of None."""
    # Closing None should not raise error
    close_db_connection(None)

    conn = get_db_connection(":memory:")
    close_db_connection(conn)

    # Attempting to query closed connection should raise ProgrammingError
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1;")


def test_row_factory_dictionary_access():
    """Verify dictionary-like row access via sqlite3.Row."""
    conn = get_db_connection(":memory:")
    try:
        conn.execute("CREATE TABLE test_sample (id INTEGER PRIMARY KEY, item_name TEXT);")
        conn.execute("INSERT INTO test_sample (id, item_name) VALUES (1, 'Amul Ghee');")
        row = conn.execute("SELECT * FROM test_sample WHERE id = 1;").fetchone()

        assert row is not None
        assert row["id"] == 1
        assert row["item_name"] == "Amul Ghee"
        assert tuple(row.keys()) == ("id", "item_name")
    finally:
        close_db_connection(conn)


def test_init_db_runs_safely(tmp_path):
    """Verify init_db initializes cleanly on a fresh path."""
    db_file = tmp_path / "init_test.db"
    init_db(str(db_file))
    assert db_file.exists()
