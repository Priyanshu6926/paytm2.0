"""
Integration tests for AI CMO FastAPI Router endpoints.
Validates PRD §5.4, §7.4, §7.5, CMO-01 through CMO-05, and Threat Models T-04-04 to T-04-06.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.main import app
from backend.services.seed_demo_data import seed_all


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Provides a TestClient connected to a clean, isolated SQLite test database with seed data."""
    db_file = tmp_path / "cmo_router_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    seed_all(conn)
    close_db_connection(conn)

    monkeypatch.setenv("KIRANAOS_DB_PATH", str(db_file))
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    with TestClient(app) as test_client:
        yield test_client, str(db_file)


# -----------------------------------------------------------------------------
# 1. Boli-Baki Overdue Debtors & Voice Udhaar Recovery Tests (CMO-01, CMO-02, CMO-03)
# -----------------------------------------------------------------------------


def test_overdue_debtors(client_with_db):
    """
    Test 1 (Overdue debtors):
    GET /api/v1/cmo/overdue-debtors returns HTTP 200 containing Ramesh Sharma with
    outstanding_amount=650.0, overdue_days >= 18, preferred_language="mr-IN",
    and excludes customers with <= 10 overdue days or Rs 0 balance.
    """
    client, _ = client_with_db
    response = client.get("/api/v1/cmo/overdue-debtors")

    assert response.status_code == 200
    data = response.json()
    assert "overdue_debtors" in data
    assert data["count"] == len(data["overdue_debtors"])
    assert data["count"] == 1

    ramesh = data["overdue_debtors"][0]
    assert ramesh["customer_name"] == "Ramesh Sharma"
    assert ramesh["outstanding_amount"] == 650.0
    assert ramesh["overdue_days"] >= 18
    assert ramesh["preferred_language"] == "mr-IN"
    assert ramesh["active_campaign"] is not None
    assert ramesh["active_campaign"]["paytm_link_slug"] == "paytm.me/munim-ramesh-650"
    assert ramesh["active_campaign"]["status"] == "SENT"

    names = [d["customer_name"] for d in data["overdue_debtors"]]
    assert "Suresh Patil (Tailor)" not in names
    assert "Suresh Kadam (Kirana)" not in names
    assert "Priya Deshmukh" not in names


def test_boli_baki_recovery_generation(client_with_db):
    """
    Test 2 (Boli-Baki generation):
    POST /api/v1/cmo/boli-baki-recovery for Ramesh Sharma returns translated_message
    in mr-IN, valid base64 tts_audio_base64, tracked paytm_payment_link, and
    simulate_webhook_endpoint, persisting the campaign in campaigns_and_links.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    ramesh = conn.execute(
        "SELECT id FROM customers WHERE name = 'Ramesh Sharma';"
    ).fetchone()
    close_db_connection(conn)

    response = client.post(
        "/api/v1/cmo/boli-baki-recovery",
        json={"customer_id": ramesh["id"]},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["customer_id"] == ramesh["id"]
    assert data["customer_name"] == "Ramesh Sharma"
    assert data["preferred_language"] == "mr-IN"
    assert data["overdue_days"] >= 18
    assert data["outstanding_amount"] == 650.0
    assert data["paytm_payment_link"] == "https://paytm.me/munim-ramesh-650"
    assert data["link_slug"] == "munim-ramesh-650"
    assert (
        data["simulate_webhook_endpoint"]
        == "/api/v1/cmo/simulate-link-paid/munim-ramesh-650"
    )
    assert "650" in data["translated_message"]
    assert not data["translated_message"].startswith("[mr-IN]")

    # Verify valid playable WAV base64 audio
    audio_bytes = base64.b64decode(data["tts_audio_base64"])
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"

    # Verify persistence in campaigns_and_links and business_events
    conn = get_db_connection(db_path)
    campaign = conn.execute(
        "SELECT * FROM campaigns_and_links WHERE paytm_link_slug = 'paytm.me/munim-ramesh-650';"
    ).fetchone()
    assert campaign is not None
    assert campaign["status"] == "SENT"
    assert campaign["message_text"] == data["translated_message"]
    assert campaign["tts_audio_base64"] == data["tts_audio_base64"]

    event = conn.execute(
        """
        SELECT * FROM business_events
        WHERE event_category = 'CMO_GROWTH'
        ORDER BY id DESC LIMIT 1;
        """
    ).fetchone()
    assert event is not None
    assert event["actor"] == "MERCHANT_APPROVED"
    close_db_connection(conn)


def test_simulate_link_paid_and_soundbox_chime(client_with_db):
    """
    Test 3 (Simulate link paid + Soundbox chime):
    POST /api/v1/cmo/simulate-link-paid/munim-ramesh-650 returns status="PAID",
    clears Ramesh Sharma's balance to 0.0 via append-only REPAYMENT_JAMA (payment_mode="PAYTM_LINK"),
    marks campaign PAID, logs CMO_GROWTH in business_events, and returns
    soundbox_announcement="Paytm par 650 rupaye prapt hue" with playable soundbox_audio_base64.
    """
    client, db_path = client_with_db

    response = client.post("/api/v1/cmo/simulate-link-paid/munim-ramesh-650")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "PAID"
    assert data["slug"] == "munim-ramesh-650"
    assert data["customer_name"] == "Ramesh Sharma"
    assert data["amount_paid"] == 650.0
    assert data["balance_after"] == 0.0
    assert data["soundbox_announcement"] == "Paytm par 650 rupaye prapt hue"
    assert data["business_event_id"] is not None

    audio_bytes = base64.b64decode(data["soundbox_audio_base64"])
    assert audio_bytes[:4] == b"RIFF"

    conn = get_db_connection(db_path)
    campaign = conn.execute(
        "SELECT * FROM campaigns_and_links WHERE paytm_link_slug = 'paytm.me/munim-ramesh-650';"
    ).fetchone()
    assert campaign["status"] == "PAID"
    assert campaign["clicks"] == 1
    assert campaign["conversions"] == 1
    assert campaign["revenue_collected"] == 650.0

    repayment = conn.execute(
        """
        SELECT * FROM ledger_entries
        WHERE customer_id = ? AND entry_type = 'REPAYMENT_JAMA' AND payment_mode = 'PAYTM_LINK';
        """,
        (data["customer_id"],),
    ).fetchone()
    assert repayment is not None
    assert repayment["amount"] == 650.0

    cmo_event = conn.execute(
        "SELECT * FROM business_events WHERE id = ?;",
        (data["business_event_id"],),
    ).fetchone()
    assert cmo_event is not None
    assert cmo_event["event_category"] == "CMO_GROWTH"
    close_db_connection(conn)


def test_simulate_link_paid_idempotency(client_with_db):
    """
    Test 4 (Idempotency):
    Re-calling POST /api/v1/cmo/simulate-link-paid/munim-ramesh-650 returns
    status="ALREADY_PAID" without creating duplicate ledger repayments.
    """
    client, db_path = client_with_db

    first = client.post("/api/v1/cmo/simulate-link-paid/munim-ramesh-650")
    assert first.status_code == 200
    assert first.json()["status"] == "PAID"

    second = client.post("/api/v1/cmo/simulate-link-paid/munim-ramesh-650")
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["status"] == "ALREADY_PAID"

    conn = get_db_connection(db_path)
    repayments = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM ledger_entries
        WHERE entry_type = 'REPAYMENT_JAMA' AND payment_mode = 'PAYTM_LINK';
        """
    ).fetchone()
    assert repayments["cnt"] == 1
    close_db_connection(conn)
