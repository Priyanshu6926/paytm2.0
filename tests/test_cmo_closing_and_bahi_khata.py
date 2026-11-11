"""
Integration tests for AI CMO 60-Second Dukaan Closing Ritual & Handwritten Bahi-Khata
batch scanning / 1-tap atomic onboarding endpoints.
Validates PRD §5.5, §7.6, FR-10, CMO-06, ONBOARD-01, and Threat Models T-04-07 to T-04-SC.
"""

import base64
import io
import json

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.main import app
from backend.services.seed_demo_data import seed_all


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Provides a TestClient connected to a clean, isolated SQLite test database with seed data."""
    db_file = tmp_path / "cmo_closing_bahi_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    seed_all(conn)
    close_db_connection(conn)

    monkeypatch.setenv("KIRANAOS_DB_PATH", str(db_file))
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    with TestClient(app) as test_client:
        yield test_client, str(db_file)


# -----------------------------------------------------------------------------
# 1. 60-Second Dukaan Closing Ritual Tests (CMO-06, PRD §7.6)
# -----------------------------------------------------------------------------


def test_dukaan_closing_ritual_baseline(client_with_db):
    """
    Test 1 (Closing ritual baseline):
    GET /api/v1/cmo/dukaan-closing-ritual returns HTTP 200 with today_qr_sales >= 6450.0,
    unmatched_upi_count == 1, festive_restock_forecast for Amul Pure Ghee 1L
    (current_stock=4, normal_daily_burn=2, festive_surge_multiplier=3.5,
    projected_5day_demand=35, recommended_order_qty=31, supplier_name containing
    'Gupta Wholesalers', one_tap_order_draft mentioning 31), spoken_ritual_hi,
    and valid base64 tts_audio_base64.
    """
    client, _ = client_with_db
    response = client.get("/api/v1/cmo/dukaan-closing-ritual")

    assert response.status_code == 200
    data = response.json()

    assert data["today_qr_sales"] >= 6450.0
    assert data["today_udhaar_recovered"] == 0.0
    assert data["unmatched_upi_count"] == 1

    forecast = data["festive_restock_forecast"]
    assert forecast["sku_name"] == "Amul Pure Ghee 1L"
    assert forecast["current_stock"] == 4
    assert forecast["normal_daily_burn"] == 2.0
    assert forecast["festive_surge_multiplier"] == 3.5
    assert forecast["projected_5day_demand"] == 35
    assert forecast["recommended_order_qty"] == 31
    assert "Gupta Wholesalers" in forecast["supplier_name"]
    assert "31" in forecast["one_tap_order_draft"]

    assert "spoken_ritual_hi" in data
    assert "31" in data["spoken_ritual_hi"]
    assert "4" in data["spoken_ritual_hi"]

    assert data["tts_audio_base64"]
    audio_bytes = base64.b64decode(data["tts_audio_base64"])
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"


def test_dukaan_closing_ritual_reflects_live_udhaar_recovery(client_with_db):
    """
    Test 2 (Live udhaar recovery reflection):
    After Ramesh Sharma pays Rs 650 via /api/v1/cmo/simulate-link-paid/munim-ramesh-650,
    calling GET /api/v1/cmo/dukaan-closing-ritual reflects today_udhaar_recovered == 650.0
    in both JSON and spoken_ritual_hi.
    """
    client, _ = client_with_db

    pay_resp = client.post("/api/v1/cmo/simulate-link-paid/munim-ramesh-650")
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "PAID"

    ritual_resp = client.get("/api/v1/cmo/dukaan-closing-ritual")
    assert ritual_resp.status_code == 200
    data = ritual_resp.json()

    assert data["today_udhaar_recovered"] == 650.0
    assert "650" in data["spoken_ritual_hi"]
    assert data["festive_restock_forecast"]["recommended_order_qty"] == 31


# -----------------------------------------------------------------------------
# 2. Handwritten Bahi-Khata Scan & Atomic Onboarding Tests (ONBOARD-01)
# -----------------------------------------------------------------------------


def test_scan_bahi_khata_demo_sample(client_with_db):
    """
    Test 1 (Scan demo sample):
    POST /api/v1/cmo/scan-bahi-khata with JSON {"use_demo_sample": true} returns
    status='PROPOSAL', batch proposals list, and deterministic total_proposed_amount.
    """
    client, _ = client_with_db
    response = client.post("/api/v1/cmo/scan-bahi-khata", json={"use_demo_sample": True})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "PROPOSAL"
    assert data["proposal_count"] == 4
    assert len(data["proposals"]) == 4
    assert data["total_proposed_amount"] == 1290.0  # 340 + 520 + 280 + 150
    assert data["fallback_used"] is True

    statuses = {p["customer_name"]: p["match_status"] for p in data["proposals"]}
    assert statuses["Sunita Sawant"] == "NEW_CUSTOMER"
    assert statuses["Prakash Kulkarni"] == "NEW_CUSTOMER"
    assert statuses["Manoj Yadav"] == "NEW_CUSTOMER"
    assert statuses["Ramesh Sharma"] == "EXISTING_CUSTOMER"

    ramesh_prop = next(p for p in data["proposals"] if p["customer_name"] == "Ramesh Sharma")
    assert ramesh_prop["matched_customer_id"] is not None
    assert ramesh_prop["existing_balance"] == 650.0


def test_scan_bahi_khata_file_upload_with_timeout_fallback(client_with_db, monkeypatch):
    """
    Test 2 (Scan file upload):
    POST /api/v1/cmo/scan-bahi-khata with multipart image file upload falls back
    cleanly within 6.0s timeout and returns valid batch proposals.
    """
    client, _ = client_with_db
    fake_img = io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 512)

    response = client.post(
        "/api/v1/cmo/scan-bahi-khata",
        files={"file": ("bahi_page.jpg", fake_img, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSAL"
    assert data["proposal_count"] == 4
    assert data["total_proposed_amount"] == 1290.0
    assert data["fallback_used"] is True


def test_confirm_bahi_khata_atomic_onboarding(client_with_db):
    """
    Test 3 (Confirm batch onboarding):
    POST /api/v1/cmo/confirm-bahi-khata with edited proposals (mix of new customers
    and existing customer Ramesh Sharma) atomically creates new customer rows,
    appends CREDIT_UDHAAR rows into ledger_entries, updates balances deterministically,
    and logs a business_events audit record.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    ramesh = conn.execute(
        "SELECT id FROM customers WHERE name = 'Ramesh Sharma';"
    ).fetchone()
    before_cust_count = conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
    before_ledger_count = conn.execute("SELECT COUNT(*) FROM ledger_entries;").fetchone()[0]
    close_db_connection(conn)

    payload = {
        "batch_ref": "PAGE14-BATCH-01",
        "entries": [
            {
                "customer_id": None,
                "customer_name": "Sunita Sawant",
                "phone": "+919821112233",
                "preferred_language": "mr-IN",
                "amount": 350.0,
                "notes": "Atta 5kg + Dal (edited)",
            },
            {
                "customer_id": None,
                "customer_name": "Prakash Kulkarni",
                "phone": "+919821445566",
                "preferred_language": "mr-IN",
                "amount": 520.0,
                "notes": "Sabudana + Sugar + Tea",
            },
            {
                "customer_id": ramesh["id"],
                "customer_name": "Ramesh Sharma",
                "phone": "+919820111222",
                "preferred_language": "mr-IN",
                "amount": 150.0,
                "notes": "Milk + Bread khata",
            },
        ],
    }

    response = client.post("/api/v1/cmo/confirm-bahi-khata", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "CONFIRMED"
    assert data["batch_ref"] == "PAGE14-BATCH-01"
    assert data["entries_recorded"] == 3
    assert data["new_customers_created"] == 2
    assert data["total_onboarded_amount"] == 1020.0
    assert len(data["customer_results"]) == 3
    assert data["business_event_id"] is not None

    # Verify DB state atomically updated
    conn = get_db_connection(db_path)
    after_cust_count = conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
    after_ledger_count = conn.execute("SELECT COUNT(*) FROM ledger_entries;").fetchone()[0]
    assert after_cust_count == before_cust_count + 2
    assert after_ledger_count == before_ledger_count + 3

    # Verify Ramesh Sharma's balance increased from 650 to 800
    ramesh_res = next(r for r in data["customer_results"] if r["customer_id"] == ramesh["id"])
    assert ramesh_res["created_new_customer"] is False
    assert ramesh_res["balance_after"] == 800.0

    # Verify new customers received exact balances
    sunita_res = next(r for r in data["customer_results"] if r["customer_name"] == "Sunita Sawant")
    assert sunita_res["created_new_customer"] is True
    assert sunita_res["balance_after"] == 350.0

    # Verify business_events CMO_GROWTH audit row
    event = conn.execute(
        "SELECT * FROM business_events WHERE id = ?;", (data["business_event_id"],)
    ).fetchone()
    assert event is not None
    assert event["event_category"] == "CMO_GROWTH"
    evidence = json.loads(event["evidence_json"])
    assert evidence["batch_ref"] == "PAGE14-BATCH-01"
    assert evidence["total_onboarded_amount"] == 1020.0
    close_db_connection(conn)


def test_confirm_bahi_khata_idempotency_and_atomic_rollback(client_with_db):
    """
    Test 4 (Batch idempotency & rollback):
    - Re-submitting the same batch_ref returns ALREADY_CONFIRMED without duplicate credits.
    - Submitting an invalid entry inside a multi-entry batch rolls back the entire
      transaction so zero partial rows are committed.
    """
    client, db_path = client_with_db

    # Part A: Confirm batch once, then replay with same batch_ref
    batch_payload = {
        "batch_ref": "IDEMP-BATCH-99",
        "entries": [
            {
                "customer_name": "Kavita Joshi",
                "phone": "+919822001122",
                "preferred_language": "mr-IN",
                "amount": 240.0,
                "notes": "Tea & Sugar",
            }
        ],
    }
    first = client.post("/api/v1/cmo/confirm-bahi-khata", json=batch_payload)
    assert first.status_code == 200
    assert first.json()["status"] == "CONFIRMED"

    conn = get_db_connection(db_path)
    ledger_count_after_first = conn.execute("SELECT COUNT(*) FROM ledger_entries;").fetchone()[0]
    cust_count_after_first = conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
    close_db_connection(conn)

    replay = client.post("/api/v1/cmo/confirm-bahi-khata", json=batch_payload)
    assert replay.status_code == 200
    assert replay.json()["status"] == "ALREADY_CONFIRMED"
    assert replay.json()["batch_ref"] == "IDEMP-BATCH-99"

    conn = get_db_connection(db_path)
    assert conn.execute("SELECT COUNT(*) FROM ledger_entries;").fetchone()[0] == ledger_count_after_first
    assert conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0] == cust_count_after_first
    close_db_connection(conn)

    # Part B: Multi-entry batch where row 1 is a brand-new customer and row 2 references a non-existent customer_id
    # Must roll back row 1 cleanly so zero partial rows exist.
    bad_batch = {
        "batch_ref": "ROLLBACK-BATCH-01",
        "entries": [
            {
                "customer_name": "Should Not Persist User",
                "phone": "+919899000111",
                "preferred_language": "hi-IN",
                "amount": 199.0,
                "notes": "Row 1 valid",
            },
            {
                "customer_id": 999999,
                "customer_name": "Missing Customer",
                "amount": 500.0,
                "notes": "Row 2 invalid ID",
            },
        ],
    }
    err_resp = client.post("/api/v1/cmo/confirm-bahi-khata", json=bad_batch)
    assert err_resp.status_code in (400, 404)

    conn = get_db_connection(db_path)
    ghost = conn.execute(
        "SELECT id FROM customers WHERE name = 'Should Not Persist User';"
    ).fetchone()
    assert ghost is None
    assert conn.execute("SELECT COUNT(*) FROM ledger_entries;").fetchone()[0] == ledger_count_after_first
    assert conn.execute("SELECT COUNT(*) FROM customers;").fetchone()[0] == cust_count_after_first
    close_db_connection(conn)
