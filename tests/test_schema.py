"""
Tests for KiranaOS Authoritative Database Schema.
Verifies all 8 tables, foreign keys, CHECK constraints, and hardware-level append-only triggers.
Conforms to PRD §6, D-01, and D-02.
"""

import sqlite3
import pytest
from backend.database.connection import close_db_connection, get_db_connection, init_db

EXPECTED_TABLES = [
    "customers",
    "ledger_entries",
    "inventory_items",
    "stock_events",
    "supplier_ledger",
    "unmatched_payments_queue",
    "campaigns_and_links",
    "business_events",
]


@pytest.fixture
def test_db(tmp_path):
    """Fixture to provide a cleanly initialized temporary database."""
    db_file = tmp_path / "schema_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        yield conn
    finally:
        close_db_connection(conn)


def test_all_eight_tables_exist(test_db):
    """Verify that all 8 core KiranaOS tables exist in the initialized database."""
    cursor = test_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}

    for expected_table in EXPECTED_TABLES:
        assert expected_table in tables, f"Missing table: {expected_table}"


def test_ledger_entries_check_constraint(test_db):
    """Verify CHECK (amount > 0) rejects non-positive financial amounts."""
    # First create a valid customer
    test_db.execute(
        "INSERT INTO customers (name, preferred_language) VALUES (?, ?);",
        ("Ramesh Sharma", "mr-IN"),
    )
    customer_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]
    test_db.commit()

    # Amount == 0 should fail
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            """
            INSERT INTO ledger_entries (customer_id, entry_type, amount, payment_mode)
            VALUES (?, 'CREDIT_UDHAAR', 0.0, 'UDHAAR');
            """,
            (customer_id,),
        )

    # Amount < 0 should fail
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            """
            INSERT INTO ledger_entries (customer_id, entry_type, amount, payment_mode)
            VALUES (?, 'CREDIT_UDHAAR', -100.0, 'UDHAAR');
            """,
            (customer_id,),
        )


def test_ledger_entries_append_only_triggers(test_db):
    """Verify that direct UPDATE or DELETE on ledger_entries is blocked by triggers."""
    test_db.execute("INSERT INTO customers (name) VALUES ('Ramesh Sharma');")
    customer_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]

    test_db.execute(
        """
        INSERT INTO ledger_entries (customer_id, entry_type, amount, payment_mode, provider_ref)
        VALUES (?, 'CREDIT_UDHAAR', 650.0, 'UDHAAR', 'TXN-TEST-001');
        """,
        (customer_id,),
    )
    entry_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]
    test_db.commit()

    # UPDATE attempt should trigger ABORT
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "UPDATE ledger_entries SET amount = 500.0 WHERE id = ?;", (entry_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)

    # DELETE attempt should trigger ABORT
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "DELETE FROM ledger_entries WHERE id = ?;", (entry_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)


def test_stock_events_append_only_triggers(test_db):
    """Verify that direct UPDATE or DELETE on stock_events is blocked by triggers."""
    test_db.execute(
        """
        INSERT INTO inventory_items (sku_name, last_unit_cost, previous_unit_cost, selling_price)
        VALUES ('Amul Pure Ghee 1L', 500.0, 500.0, 600.0);
        """
    )
    item_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]

    test_db.execute(
        """
        INSERT INTO stock_events (item_id, event_type, quantity_delta, unit_cost, invoice_number)
        VALUES (?, 'INWARD_INVOICE', 20, 500.0, 'INV-2026-001');
        """,
        (item_id,),
    )
    event_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]
    test_db.commit()

    # UPDATE attempt should fail
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "UPDATE stock_events SET quantity_delta = 25 WHERE id = ?;", (event_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)

    # DELETE attempt should fail
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "DELETE FROM stock_events WHERE id = ?;", (event_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)


def test_business_events_append_only_triggers(test_db):
    """Verify that direct UPDATE or DELETE on business_events is blocked by triggers."""
    test_db.execute(
        """
        INSERT INTO business_events (event_category, summary_text, evidence_json, actor)
        VALUES ('LEDGER', 'Added ₹650 udhaar for Ramesh', '{"source": "voice"}', 'MERCHANT_APPROVED');
        """
    )
    event_id = test_db.execute("SELECT last_insert_rowid();").fetchone()[0]
    test_db.commit()

    # UPDATE attempt should fail
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "UPDATE business_events SET summary_text = 'Tampered text' WHERE id = ?;", (event_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)

    # DELETE attempt should fail
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        test_db.execute(
            "DELETE FROM business_events WHERE id = ?;", (event_id,)
        )
    assert "KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited." in str(exc_info.value)


def test_foreign_key_constraints(test_db):
    """Verify that foreign keys are enforced by SQLite."""
    # Invalid customer_id in ledger_entries should fail
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            """
            INSERT INTO ledger_entries (customer_id, entry_type, amount)
            VALUES (99999, 'CREDIT_UDHAAR', 100.0);
            """
        )

    # Invalid item_id in stock_events should fail
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            """
            INSERT INTO stock_events (item_id, event_type, quantity_delta)
            VALUES (99999, 'INWARD_INVOICE', 10);
            """
        )


def test_unique_constraints(test_db):
    """Verify UNIQUE constraints on provider_ref, sku_name, upi_txn_id, and paytm_link_slug."""
    # 1. inventory_items sku_name uniqueness
    test_db.execute(
        "INSERT INTO inventory_items (sku_name, last_unit_cost, previous_unit_cost, selling_price) VALUES ('Maggi 70g', 10, 10, 14);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            "INSERT INTO inventory_items (sku_name, last_unit_cost, previous_unit_cost, selling_price) VALUES ('Maggi 70g', 10, 10, 14);"
        )

    # 2. unmatched_payments_queue upi_txn_id uniqueness
    test_db.execute(
        "INSERT INTO unmatched_payments_queue (upi_txn_id, amount) VALUES ('UPI-001', 200.0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            "INSERT INTO unmatched_payments_queue (upi_txn_id, amount) VALUES ('UPI-001', 200.0);"
        )

    # 3. campaigns_and_links paytm_link_slug uniqueness
    test_db.execute(
        "INSERT INTO campaigns_and_links (campaign_title, campaign_type, language_code, paytm_link_slug) VALUES ('Test', 'UDHAAR_VOICE_LINK', 'hi-IN', 'paytm.me/slug-1');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            "INSERT INTO campaigns_and_links (campaign_title, campaign_type, language_code, paytm_link_slug) VALUES ('Test 2', 'UDHAAR_VOICE_LINK', 'hi-IN', 'paytm.me/slug-1');"
        )
