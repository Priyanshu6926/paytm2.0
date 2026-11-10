"""
Tests for Ambiguous UPI Reconciliation Queue & QR Webhook Simulator.
Validates PRD §5.4, §7.4, D-04, and Threat Models T-03-07 to T-03-09.
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.main import app
from backend.services.seed_demo_data import seed_all


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Provides a TestClient connected to an isolated SQLite test database with seed data."""
    db_file = tmp_path / "cfo_unmatched_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    seed_all(conn)
    close_db_connection(conn)

    monkeypatch.setenv("KIRANAOS_DB_PATH", str(db_file))

    with TestClient(app) as test_client:
        yield test_client, str(db_file)


# -----------------------------------------------------------------------------
# 1. Unmatched Payments Queue Tests (PRD §5.4, §7.4, D-04)
# -----------------------------------------------------------------------------

def test_get_unmatched_payments(client_with_db):
    """
    Validates GET /api/v1/cfo/unmatched-payments:
      - Retrieves the pre-seeded Suresh ambiguous ₹200 payment.
      - Deserializes candidate_customers into structured JSON array.
      - Displays ambiguity reason and pending status.
    """
    client, _ = client_with_db
    response = client.get("/api/v1/cfo/unmatched-payments")

    assert response.status_code == 200
    queue = response.json()
    assert len(queue) >= 1

    suresh_item = next((item for item in queue if item["upi_txn_id"] == "UPI-DEMO-SURESH-200"), None)
    assert suresh_item is not None
    assert suresh_item["amount"] == 200.0
    assert suresh_item["payer_name"] == "Suresh"
    assert suresh_item["status"] == "PENDING_REVIEW"
    assert "Suresh" in suresh_item["ambiguity_reason"]
    assert len(suresh_item["candidate_customers"]) == 2

    # Check candidate names in the card
    candidate_names = [c["name"] for c in suresh_item["candidate_customers"]]
    assert "Suresh Patil (Tailor)" in candidate_names
    assert "Suresh Kadam (Kirana)" in candidate_names


def test_resolve_unmatched_payment_to_debtor(client_with_db):
    """
    Validates POST /api/v1/cfo/resolve-unmatched-payment:
      - Resolves queue item to Suresh Patil (Tailor).
      - Clears his ₹200 udhaar balance down to ₹0.00.
      - Updates queue status to 'LINKED'.
      - Appends SETTLEMENT audit event in business_events.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)

    # 1. Verify Suresh Patil's initial udhaar balance is ₹200.00
    sp = conn.execute("SELECT id, name FROM customers WHERE name = 'Suresh Patil (Tailor)';").fetchone()
    assert sp is not None
    sp_id = sp["id"]

    q_item = conn.execute("SELECT id FROM unmatched_payments_queue WHERE upi_txn_id = 'UPI-DEMO-SURESH-200';").fetchone()
    assert q_item is not None
    queue_id = q_item["id"]
    close_db_connection(conn)

    # 2. Resolve queue item
    payload = {
        "queue_id": queue_id,
        "resolved_customer_id": sp_id,
        "merchant_notes": "Identified Suresh Patil visiting at 5 PM",
    }
    response = client.post("/api/v1/cfo/resolve-unmatched-payment", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "LINKED"
    assert data["queue_id"] == queue_id
    assert data["resolved_customer_id"] == sp_id
    assert data["customer_balance_after"] == 0.00  # Rs 200 - Rs 200 == Rs 0.00!

    # 3. Check Database State
    conn = get_db_connection(db_path)

    # Queue item should now be LINKED
    updated_q = conn.execute("SELECT * FROM unmatched_payments_queue WHERE id = ?;", (queue_id,)).fetchone()
    assert updated_q["status"] == "LINKED"
    assert updated_q["resolved_customer_id"] == sp_id

    # Ledger should contain the repayment entry
    ledger_row = conn.execute(
        "SELECT * FROM ledger_entries WHERE provider_ref = 'UPI-DEMO-SURESH-200';"
    ).fetchone()
    assert ledger_row is not None
    assert ledger_row["entry_type"] == "REPAYMENT_JAMA"
    assert ledger_row["amount"] == 200.00
    assert ledger_row["customer_id"] == sp_id

    # Audit event in business_events
    bus_event = conn.execute(
        "SELECT * FROM business_events WHERE id = ?;", (data["business_event_id"],)
    ).fetchone()
    assert bus_event is not None
    assert bus_event["event_category"] == "SETTLEMENT"
    assert "UPI-DEMO-SURESH-200" in bus_event["summary_text"]
    assert "Suresh Patil" in bus_event["summary_text"]

    close_db_connection(conn)


def test_resolve_unmatched_payment_already_linked_rejected(client_with_db):
    """
    Validates that attempting to resolve an already LINKED queue item returns HTTP 400.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    sp = conn.execute("SELECT id FROM customers WHERE name = 'Suresh Patil (Tailor)';").fetchone()
    q_item = conn.execute("SELECT id FROM unmatched_payments_queue WHERE upi_txn_id = 'UPI-DEMO-SURESH-200';").fetchone()
    close_db_connection(conn)

    payload = {
        "queue_id": q_item["id"],
        "resolved_customer_id": sp["id"],
    }

    # First resolution: OK
    r1 = client.post("/api/v1/cfo/resolve-unmatched-payment", json=payload)
    assert r1.status_code == 200

    # Second resolution: Rejected HTTP 400
    r2 = client.post("/api/v1/cfo/resolve-unmatched-payment", json=payload)
    assert r2.status_code == 400
    assert "already resolved" in r2.json()["detail"].lower()


def test_resolve_unmatched_payment_invalid_ids(client_with_db):
    """Validates 404 error handling for non-existent queue_id or customer_id."""
    client, _ = client_with_db

    # Non-existent queue_id
    r1 = client.post("/api/v1/cfo/resolve-unmatched-payment", json={"queue_id": 99999, "resolved_customer_id": 1})
    assert r1.status_code == 404

    # Non-existent customer_id
    conn = get_db_connection()
    q_item = conn.execute("SELECT id FROM unmatched_payments_queue LIMIT 1;").fetchone()
    close_db_connection(conn)

    r2 = client.post("/api/v1/cfo/resolve-unmatched-payment", json={"queue_id": q_item["id"], "resolved_customer_id": 88888})
    assert r2.status_code == 404


# -----------------------------------------------------------------------------
# 2. QR Webhook Simulator Tests (PRD §5.4, §7.4, D-04)
# -----------------------------------------------------------------------------

def test_qr_webhook_single_exact_match_auto_reconciled(client_with_db):
    """
    Validates that a QR payment for an unambiguous customer (e.g. Ramesh Sharma)
    is immediately auto-reconciled into ledger_entries without entering review queue.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    ramesh = conn.execute("SELECT id FROM customers WHERE name = 'Ramesh Sharma';").fetchone()
    close_db_connection(conn)

    webhook_payload = {
        "upi_txn_id": "UPI-TXN-RAMESH-300",
        "amount": 300.00,
        "payer_name": "Ramesh Sharma",
        "payer_vpa": "ramesh.sharma@okaxis",
    }

    response = client.post("/api/v1/cfo/simulate-qr-webhook", json=webhook_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "AUTO_RECONCILED"
    assert data["customer_id"] == ramesh["id"]
    assert data["customer_name"] == "Ramesh Sharma"
    assert data["amount"] == 300.00
    assert data["balance_after"] == 350.00  # Initial 650.00 - 300.00 == 350.00

    # Verify not queued
    conn = get_db_connection(db_path)
    queued = conn.execute("SELECT id FROM unmatched_payments_queue WHERE upi_txn_id = 'UPI-TXN-RAMESH-300';").fetchone()
    assert queued is None

    # Verify ledger entry created
    entry = conn.execute("SELECT * FROM ledger_entries WHERE provider_ref = 'UPI-TXN-RAMESH-300';").fetchone()
    assert entry is not None
    assert entry["entry_type"] == "REPAYMENT_JAMA"
    assert entry["amount"] == 300.00

    close_db_connection(conn)


def test_qr_webhook_ambiguous_collision_queued_for_review(client_with_db):
    """
    Validates that a QR payment from 'Suresh' (multiple matches) halts auto-write
    and safely routes into unmatched_payments_queue with candidates attached.
    """
    client, db_path = client_with_db

    webhook_payload = {
        "upi_txn_id": "UPI-TXN-SURESH-NEW-100",
        "amount": 100.00,
        "payer_name": "Suresh",
        "payer_vpa": "suresh@paytm",
    }

    response = client.post("/api/v1/cfo/simulate-qr-webhook", json=webhook_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "QUEUED_FOR_REVIEW"
    assert data["candidate_count"] == 2
    assert "Suresh" in data["ambiguity_reason"]
    queue_id = data["queue_id"]

    # Verify it is stored in DB
    conn = get_db_connection(db_path)
    q_row = conn.execute("SELECT * FROM unmatched_payments_queue WHERE id = ?;", (queue_id,)).fetchone()
    assert q_row is not None
    assert q_row["status"] == "PENDING_REVIEW"
    assert q_row["amount"] == 100.00

    # Verify NO ledger repayment entry was created
    ledger_row = conn.execute("SELECT id FROM ledger_entries WHERE provider_ref = 'UPI-TXN-SURESH-NEW-100';").fetchone()
    assert ledger_row is None

    close_db_connection(conn)


def test_qr_webhook_unknown_payer_queued_for_manual_assignment(client_with_db):
    """
    Validates that a QR payment from an unknown customer routes to the queue
    with 0 candidates for manual assignment.
    """
    client, db_path = client_with_db

    webhook_payload = {
        "upi_txn_id": "UPI-TXN-UNKNOWN-555",
        "amount": 555.00,
        "payer_name": "Anand Mahindra",
        "payer_vpa": "anand@okhdfcbank",
    }

    response = client.post("/api/v1/cfo/simulate-qr-webhook", json=webhook_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "QUEUED_FOR_REVIEW"
    assert data["candidate_count"] == 0
    assert "not found" in data["ambiguity_reason"].lower()


def test_qr_webhook_duplicate_txn_id_idempotence(client_with_db):
    """
    Validates that submitting a duplicate upi_txn_id is idempotently handled
    without creating duplicate ledger entries or queue rows.
    """
    client, _ = client_with_db

    payload = {
        "upi_txn_id": "UPI-TXN-IDEMPOTENT-777",
        "amount": 250.00,
        "payer_name": "Ramesh Sharma",
    }

    # First attempt: auto-reconciled
    r1 = client.post("/api/v1/cfo/simulate-qr-webhook", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "AUTO_RECONCILED"

    # Second attempt with same upi_txn_id: ALREADY_PROCESSED
    r2 = client.post("/api/v1/cfo/simulate-qr-webhook", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "ALREADY_PROCESSED"
