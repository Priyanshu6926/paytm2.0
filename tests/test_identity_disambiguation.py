"""
Tests for KiranaOS Customer Identity Disambiguation Guard.
Verifies exact match resolution, alias lookup, candidate generation with live udhaar balances,
bilingual spoken prompts, and business_events audit logging per PRD §4 (FR-02), §7.1, and D-03.
"""

import json
import pytest

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.deterministic_engine import (
    record_ledger_entry,
    resolve_customer_identity,
)


@pytest.fixture
def test_db(tmp_path):
    """Fixture providing an initialized temporary SQLite database."""
    db_file = tmp_path / "disambig_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        yield conn
    finally:
        close_db_connection(conn)


@pytest.fixture
def populated_customers(test_db):
    """Seed sample customers matching Mumbai Kirana store dataset."""
    # 1. Ramesh Sharma (owes 650)
    c1 = test_db.execute(
        """
        INSERT INTO customers (name, aliases, phone, preferred_language, last_visit_date)
        VALUES ('Ramesh Sharma', '["Ramesh Bhai", "Ramesh Kirana"]', '9820011111', 'mr-IN', '2026-10-22 14:00:00');
        """
    ).lastrowid
    record_ledger_entry(test_db, c1, "CREDIT_UDHAAR", 650.0)

    # 2. Suresh Patil (Tailor) (owes 200, visited 5 days ago)
    c2 = test_db.execute(
        """
        INSERT INTO customers (name, aliases, phone, preferred_language, last_visit_date)
        VALUES ('Suresh Patil (Tailor)', '["Suresh Tailor"]', '9820022222', 'hi-IN', '5 days ago');
        """
    ).lastrowid
    record_ledger_entry(test_db, c2, "CREDIT_UDHAAR", 200.0)
    test_db.execute("UPDATE customers SET last_visit_date = '5 days ago' WHERE id = ?;", (c2,))

    # 3. Suresh Kadam (Kirana) (owes 450, visited 9 days ago)
    c3 = test_db.execute(
        """
        INSERT INTO customers (name, aliases, phone, preferred_language, last_visit_date)
        VALUES ('Suresh Kadam (Kirana)', '["Suresh Kirana"]', '9820033333', 'hi-IN', '9 days ago');
        """
    ).lastrowid
    record_ledger_entry(test_db, c3, "CREDIT_UDHAAR", 450.0)
    test_db.execute("UPDATE customers SET last_visit_date = '9 days ago' WHERE id = ?;", (c3,))

    # 4. Priya Deshmukh (owes 0)
    c4 = test_db.execute(
        """
        INSERT INTO customers (name, aliases, phone, preferred_language, last_visit_date)
        VALUES ('Priya Deshmukh', '[]', '9820044444', 'mr-IN', '2026-10-24 10:00:00');
        """
    ).lastrowid

    test_db.commit()
    return {"ramesh": c1, "suresh_patil": c2, "suresh_kadam": c3, "priya": c4}


def test_exact_name_match(test_db, populated_customers):
    """Exact full name query cleanly resolves to EXACT_MATCH with live balance."""
    res = resolve_customer_identity(test_db, "Ramesh Sharma")
    assert res["status"] == "EXACT_MATCH"
    assert res["customer"]["id"] == populated_customers["ramesh"]
    assert res["customer"]["name"] == "Ramesh Sharma"
    assert res["current_udhaar"] == 650.0


def test_alias_match(test_db, populated_customers):
    """Querying an alias cleanly resolves to the target customer."""
    res = resolve_customer_identity(test_db, "Ramesh Bhai")
    assert res["status"] == "EXACT_MATCH"
    assert res["customer"]["id"] == populated_customers["ramesh"]
    assert res["current_udhaar"] == 650.0


def test_unique_substring_match(test_db, populated_customers):
    """Unique partial substring query resolves to EXACT_MATCH."""
    res = resolve_customer_identity(test_db, "Priya")
    assert res["status"] == "EXACT_MATCH"
    assert res["customer"]["id"] == populated_customers["priya"]
    assert res["customer"]["name"] == "Priya Deshmukh"
    assert res["current_udhaar"] == 0.0


def test_ambiguous_name_triggers_disambiguation_guard(test_db, populated_customers):
    """
    When query matches multiple customers (e.g. 'Suresh'), system halts auto-write
    and returns NEEDS_DISAMBIGUATION with candidate cards and spoken prompt.
    """
    res = resolve_customer_identity(test_db, "Suresh")
    assert res["status"] == "NEEDS_DISAMBIGUATION"
    assert res["query_name"] == "Suresh"
    assert "Found 2 customers matching 'Suresh'" in res["ambiguity_reason"]
    assert res["why_am_i_seeing_this"] == "KiranaOS blocks blind writes when customer names overlap."
    assert len(res["candidates"]) == 2

    # Check candidates have live calculated udhaar
    candidate_map = {c["customer_id"]: c for c in res["candidates"]}
    assert populated_customers["suresh_patil"] in candidate_map
    assert populated_customers["suresh_kadam"] in candidate_map

    c_patil = candidate_map[populated_customers["suresh_patil"]]
    assert c_patil["name"] == "Suresh Patil (Tailor)"
    assert c_patil["current_udhaar"] == 200.0
    assert "5 days ago" in c_patil["last_visit"]

    c_kadam = candidate_map[populated_customers["suresh_kadam"]]
    assert c_kadam["name"] == "Suresh Kadam (Kirana)"
    assert c_kadam["current_udhaar"] == 450.0
    assert "9 days ago" in c_kadam["last_visit"]

    # Spoken Hindi prompt per PRD §7.1
    assert "Dukaan mein do Suresh hain" in res["spoken_prompt_hi"]
    assert "Suresh Patil (Tailor)" in res["spoken_prompt_hi"]
    assert "Suresh Kadam (Kirana)" in res["spoken_prompt_hi"]


def test_disambiguation_logs_audit_event(test_db, populated_customers):
    """Disambiguation guard trigger creates an immutable audit event in business_events per D-03."""
    initial_event_count = test_db.execute("SELECT COUNT(*) FROM business_events;").fetchone()[0]

    resolve_customer_identity(test_db, "Suresh")

    events = test_db.execute(
        "SELECT * FROM business_events WHERE event_category = 'LEDGER' AND actor = 'SYSTEM_GUARD' ORDER BY id DESC;"
    ).fetchall()
    assert len(events) >= 1
    latest_event = events[0]
    assert "Identity disambiguation triggered for 'Suresh'" in latest_event["summary_text"]

    evidence = json.loads(latest_event["evidence_json"])
    assert evidence["query_name"] == "Suresh"
    assert evidence["candidate_count"] == 2


def test_customer_not_found(test_db, populated_customers):
    """Non-existent customer query returns NOT_FOUND status."""
    res = resolve_customer_identity(test_db, "Amitabh Bachchan")
    assert res["status"] == "NOT_FOUND"
    assert res["query_name"] == "Amitabh Bachchan"

    # Empty string or whitespace
    res_empty = resolve_customer_identity(test_db, "   ")
    assert res_empty["status"] == "NOT_FOUND"


def test_last_visit_timestamp_formatting(test_db):
    """Test format_last_visit with ISO timestamp and SQLite datetime strings."""
    from datetime import datetime, timedelta
    from backend.services.deterministic_engine import format_last_visit

    # None
    assert format_last_visit(None) == "No prior visit"
    assert format_last_visit("") == "No prior visit"

    # String with 'days ago'
    assert format_last_visit("5 days ago") == "5 days ago"

    # Datetime from today
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    assert format_last_visit(now_str) == "Today"

    # Datetime from 1 day ago
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert format_last_visit(yesterday_str) == "1 day ago"

    # Datetime from 7 days ago
    past_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    assert format_last_visit(past_str) == "7 days ago"

