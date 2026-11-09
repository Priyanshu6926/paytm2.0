"""
Tests for KiranaOS Deterministic Memory & Calculation Engine.
Verifies pure Python SQL SUM arithmetic, reversal adjustments, zero-balance transitions,
and structured business_events audit logging per PRD §2, §5.1, D-02, and D-03.
"""

import json
import sqlite3
import pytest

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.deterministic_engine import (
    calculate_customer_balance,
    log_business_event,
    record_ledger_entry,
    reverse_ledger_entry,
)


@pytest.fixture
def test_db(tmp_path):
    """Fixture providing an initialized temporary SQLite database."""
    db_file = tmp_path / "engine_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        yield conn
    finally:
        close_db_connection(conn)


@pytest.fixture
def sample_customer(test_db):
    """Fixture creating a test customer."""
    cursor = test_db.execute(
        """
        INSERT INTO customers (name, aliases, phone, preferred_language)
        VALUES ('Ramesh Sharma', '["Ramesh Bhai", "Ramesh Kirana"]', '9820098200', 'mr-IN');
        """
    )
    test_db.commit()
    return cursor.lastrowid


def test_initial_zero_balance(test_db, sample_customer):
    """A customer with no ledger entries has exactly 0.0 balance and 0 confirmed entries."""
    balance = calculate_customer_balance(test_db, sample_customer)
    assert balance["customer_id"] == sample_customer
    assert balance["total_credit"] == 0.0
    assert balance["total_repayment"] == 0.0
    assert balance["total_adjustment"] == 0.0
    assert balance["net_outstanding_balance"] == 0.0
    assert balance["confirmed_entry_count"] == 0


def test_single_credit_and_repayment(test_db, sample_customer):
    """Single credit followed by partial repayment computes balance accurately."""
    # 1. Add credit of ₹650.00
    rec_res = record_ledger_entry(
        test_db,
        customer_id=sample_customer,
        entry_type="CREDIT_UDHAAR",
        amount=650.0,
        payment_mode="UDHAAR",
        provider_ref="TXN-CRED-001",
        source_utterance="Ramesh ko 650 ka udhaar do",
    )
    assert rec_res["balance"]["net_outstanding_balance"] == 650.0
    assert rec_res["balance"]["total_credit"] == 650.0
    assert rec_res["balance"]["confirmed_entry_count"] == 1

    # 2. Add repayment of ₹200.00
    rep_res = record_ledger_entry(
        test_db,
        customer_id=sample_customer,
        entry_type="REPAYMENT_JAMA",
        amount=200.0,
        payment_mode="PAYTM_QR",
        provider_ref="TXN-REP-001",
        source_utterance="Ramesh ne 200 QR se jama kiye",
    )
    assert rep_res["balance"]["net_outstanding_balance"] == 450.0
    assert rep_res["balance"]["total_credit"] == 650.0
    assert rep_res["balance"]["total_repayment"] == 200.0
    assert rep_res["balance"]["confirmed_entry_count"] == 2


def test_multi_transaction_balance_aggregation(test_db, sample_customer):
    """Multiple interleaved credits and repayments compute with 100% mathematical precision."""
    record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 100.50)
    record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 250.25)
    record_ledger_entry(test_db, sample_customer, "REPAYMENT_JAMA", 50.75, payment_mode="CASH")
    record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 14.25)
    record_ledger_entry(test_db, sample_customer, "REPAYMENT_JAMA", 100.00, payment_mode="PAYTM_QR")

    balance = calculate_customer_balance(test_db, sample_customer)
    # Expected: Total Credit = 100.50 + 250.25 + 14.25 = 365.00
    # Expected: Total Repayment = 50.75 + 100.00 = 150.75
    # Expected: Net = 365.00 - 150.75 = 214.25
    assert balance["total_credit"] == 365.00
    assert balance["total_repayment"] == 150.75
    assert balance["net_outstanding_balance"] == 214.25
    assert balance["confirmed_entry_count"] == 5


def test_reversal_of_credit_entry(test_db, sample_customer):
    """Reversing a credit entry creates compensating adjustment and reduces debt without UPDATE/DELETE."""
    # 1. Credit ₹500
    c1 = record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 500.0)
    assert c1["balance"]["net_outstanding_balance"] == 500.0

    # 2. Reversal of ₹500 credit
    rev_res = reverse_ledger_entry(
        test_db,
        entry_id=c1["entry_id"],
        reason="Wrong customer selected by mistake",
    )
    assert rev_res["entry_type"] == "REVERSAL_ADJUSTMENT"
    assert rev_res["amount"] == 500.0
    assert rev_res["balance"]["net_outstanding_balance"] == 0.0
    assert rev_res["balance"]["total_adjustment"] == -500.0
    assert rev_res["balance"]["confirmed_entry_count"] == 2

    # Verify target entry was untouched in database (PRD Law of Immutability)
    orig_entry = test_db.execute(
        "SELECT * FROM ledger_entries WHERE id = ?", (c1["entry_id"],)
    ).fetchone()
    assert orig_entry["amount"] == 500.0
    assert orig_entry["status"] == "CONFIRMED"


def test_reversal_of_repayment_entry(test_db, sample_customer):
    """Reversing a repayment entry (e.g., bounced cheque) increases debt back to original balance."""
    # 1. Credit ₹1000
    record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 1000.0)
    # 2. Repayment ₹400
    rep = record_ledger_entry(test_db, sample_customer, "REPAYMENT_JAMA", 400.0)
    assert calculate_customer_balance(test_db, sample_customer)["net_outstanding_balance"] == 600.0

    # 3. Reverse the ₹400 repayment
    rev = reverse_ledger_entry(test_db, rep["entry_id"], reason="Cheque bounced / payment failed")
    assert rev["balance"]["total_repayment"] == 400.0
    assert rev["balance"]["total_adjustment"] == 400.0
    assert rev["balance"]["net_outstanding_balance"] == 1000.0
    assert rev["balance"]["confirmed_entry_count"] == 3


def test_double_reversal_prevented(test_db, sample_customer):
    """Attempting to reverse an entry that was already reversed raises ValueError."""
    c = record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 300.0)
    reverse_ledger_entry(test_db, c["entry_id"], reason="First reversal")

    with pytest.raises(ValueError, match="already been reversed"):
        reverse_ledger_entry(test_db, c["entry_id"], reason="Second reversal attempt")


def test_reversing_a_reversal_prevented(test_db, sample_customer):
    """Attempting to reverse a REVERSAL_ADJUSTMENT entry itself raises ValueError."""
    c = record_ledger_entry(test_db, sample_customer, "CREDIT_UDHAAR", 300.0)
    rev = reverse_ledger_entry(test_db, c["entry_id"], reason="First reversal")

    with pytest.raises(ValueError, match="already a REVERSAL_ADJUSTMENT"):
        reverse_ledger_entry(test_db, rev["reversal_entry_id"], reason="Attempting to reverse reversal")


def test_business_events_audit_logging(test_db, sample_customer):
    """Every ledger mutation generates a structured audit event in business_events table."""
    rec = record_ledger_entry(
        test_db,
        customer_id=sample_customer,
        entry_type="CREDIT_UDHAAR",
        amount=450.0,
        payment_mode="UDHAAR",
        source_utterance="450 udhaar likho",
        actor="MERCHANT_APPROVED",
    )
    event_id = rec["business_event_id"]

    event_row = test_db.execute(
        "SELECT * FROM business_events WHERE id = ?", (event_id,)
    ).fetchone()
    assert event_row is not None
    assert event_row["event_category"] == "LEDGER"
    assert "₹450.00 credit" in event_row["summary_text"]
    assert event_row["actor"] == "MERCHANT_APPROVED"

    evidence = json.loads(event_row["evidence_json"])
    assert evidence["customer_id"] == sample_customer
    assert evidence["amount"] == 450.0
    assert evidence["source_utterance"] == "450 udhaar likho"
    assert evidence["balance_after"] == 450.0


def test_validation_rules(test_db, sample_customer):
    """Deterministic engine validates customer IDs, entry types, and positive amounts."""
    # Invalid customer ID
    with pytest.raises(ValueError, match="does not exist"):
        calculate_customer_balance(test_db, customer_id=99999)

    with pytest.raises(ValueError, match="does not exist"):
        record_ledger_entry(test_db, customer_id=99999, entry_type="CREDIT_UDHAAR", amount=100.0)

    # Invalid entry type
    with pytest.raises(ValueError, match="Invalid entry_type"):
        record_ledger_entry(test_db, sample_customer, entry_type="INVALID_TYPE", amount=100.0)

    # Non-positive amount
    with pytest.raises(ValueError, match="greater than zero"):
        record_ledger_entry(test_db, sample_customer, entry_type="CREDIT_UDHAAR", amount=0.0)

    with pytest.raises(ValueError, match="greater than zero"):
        record_ledger_entry(test_db, sample_customer, entry_type="CREDIT_UDHAAR", amount=-50.0)

    # Non-existent entry to reverse
    with pytest.raises(ValueError, match="does not exist"):
        reverse_ledger_entry(test_db, entry_id=99999, reason="Ghost entry")
