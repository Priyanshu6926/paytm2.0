"""
tests/test_voice_gateway.py

Unit and integration tests for KiranaOS Voice Gateway & Multimodal Input Layer.
Verifies dynamic SQL keyterm biasing, vernacular voice intent parser,
customer identity disambiguation guards, and Propose-Confirm-Commit API endpoints
mounted at /api/v1/voice/*.
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.seed_demo_data import seed_all
from backend.services.voice_intent_parser import (
    extract_keyterm_biasing_from_db,
    parse_voice_intent,
)


import os

@pytest.fixture(autouse=True)
def setup_database(tmp_path):
    """Provides a fresh isolated database for each test and seeds baseline demo data."""
    test_db_file = str(tmp_path / "test_voice.db")
    os.environ["KIRANAOS_DB_PATH"] = test_db_file
    init_db(test_db_file)
    conn = get_db_connection(test_db_file)
    try:
        seed_all(conn)
    finally:
        close_db_connection(conn)

    yield

    if "KIRANAOS_DB_PATH" in os.environ:
        del os.environ["KIRANAOS_DB_PATH"]


def test_keyterm_biasing_extraction():
    """
    Verifies that extract_keyterm_biasing_from_db dynamically pulls all customer
    and inventory names + aliases from active SQLite tables per D-03.
    """
    conn = get_db_connection()
    try:
        terms = extract_keyterm_biasing_from_db(conn)
    finally:
        close_db_connection(conn)

    assert isinstance(terms, list)
    assert len(terms) > 10

    # Verify customer names and aliases
    assert any("Ramesh Sharma" in t for t in terms)
    assert any("Ramesh Bhai" in t for t in terms)
    assert any("Suresh Patil" in t for t in terms)
    assert any("Suresh Tailor" in t for t in terms)
    assert any("Suresh Kadam" in t for t in terms)
    assert any("Suresh Kirana" in t for t in terms)
    assert any("Priya Deshmukh" in t for t in terms)

    # Verify inventory SKUs and local aliases
    assert any("Amul Pure Ghee" in t or "Amul Ghee" in t for t in terms)
    assert any("Fortune Oil" in t or "Fortune Sunlite Oil" in t for t in terms)
    assert any("Haldiram" in t or "Bhujia" in t for t in terms)

    # Verify deduplication
    lowered = [t.lower() for t in terms]
    assert len(lowered) == len(set(lowered))


def test_intent_parser_ambiguous_suresh_triggers_disambiguation():
    """
    Verifies D-04: 'Suresh ka 200 rupaye udhaar likh do' triggers NEEDS_DISAMBIGUATION
    guard without executing blind writes or unconfirmed mutations.
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Suresh ka 200 rupaye udhaar likh do", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "NEEDS_DISAMBIGUATION"
    assert res["intent"] == "CREDIT_UDHAAR"
    assert res["extracted_amount"] == 200.0
    assert "Suresh" in res["extracted_name"]
    assert len(res["candidates"]) == 2
    assert "2 customers matching" in res["ambiguity_reason"]
    assert "KiranaOS blocks blind writes" in res["why_am_i_seeing_this"]
    assert "Dukaan mein do Suresh hain" in res["spoken_prompt_hi"]
    assert "200" in res["spoken_prompt_hi"]


def test_intent_parser_resolved_ramesh_repayment_proposal():
    """
    Verifies D-04: 'Ramesh ne 300 rupaye jama kiye' accurately resolves Ramesh Sharma,
    extracts amount 300.0, and computes new balance (650 - 300 = 350).
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Ramesh ne 300 rupaye jama kiye", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "PROPOSAL"
    assert res["intent"] == "REPAYMENT_JAMA"
    assert res["extracted_amount"] == 300.0
    assert res["customer"]["name"] == "Ramesh Sharma"
    assert res["customer_name"] == "Ramesh Sharma"
    assert res["current_balance"] == 650.0
    assert res["new_balance"] == 350.0
    assert "Current balance ₹650.00 - repayment ₹300.00 = ₹350.00." in res["why_am_i_seeing_this"]
    assert "300 jama record karein?" in res["spoken_prompt_hi"]


def test_intent_parser_marathi_commands():
    """
    Verifies that Marathi vernacular phrases are properly parsed for credit and repayment.
    """
    conn = get_db_connection()
    try:
        # Marathi credit command
        credit_res = parse_voice_intent("Suresh che 200 rupaye udhari liha", language_hint="mr-IN", conn=conn)
        assert credit_res["status"] == "NEEDS_DISAMBIGUATION"
        assert credit_res["intent"] == "CREDIT_UDHAAR"
        assert credit_res["extracted_amount"] == 200.0

        # Marathi repayment command
        repay_res = parse_voice_intent("Ramesh ne 300 rupaye jama kele", language_hint="mr-IN", conn=conn)
        assert repay_res["status"] == "PROPOSAL"
        assert repay_res["intent"] == "REPAYMENT_JAMA"
        assert repay_res["extracted_amount"] == 300.0
        assert repay_res["new_balance"] == 350.0
    finally:
        close_db_connection(conn)


def test_intent_parser_inventory_stock_inward_and_stockout():
    """
    Verifies inventory intent parsing for stock inward and stockout triggers.
    """
    conn = get_db_connection()
    try:
        # Stock Inward
        inward_res = parse_voice_intent("Amul Ghee 5 packet aaya", language_hint="hi-IN", conn=conn)
        assert inward_res["status"] == "PROPOSAL"
        assert inward_res["intent"] == "STOCK_IN"
        assert inward_res["sku_name"] == "Amul Pure Ghee 1L"
        assert inward_res["quantity_delta"] == 5
        assert inward_res["new_stock"] == inward_res["current_stock"] + 5

        # Stockout Flag
        stockout_res = parse_voice_intent("Fortune Oil khatam ho gaya", language_hint="hi-IN", conn=conn)
        assert stockout_res["status"] == "PROPOSAL"
        assert stockout_res["intent"] == "STOCKOUT_FLAG"
        assert stockout_res["sku_name"] == "Fortune Sunlite Oil 1L"
        assert stockout_res["new_stock"] == 0
    finally:
        close_db_connection(conn)


def test_intent_parser_customer_not_found():
    """
    Verifies graceful fallback when speaking a customer name not in shop memory.
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Vikram ka 500 rupaye udhaar likho", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "CUSTOMER_NOT_FOUND"
    assert res["extracted_name"] == "Vikram"
    assert res["extracted_amount"] == 500.0


# --------------------------------------------------------------------------
# API Router Integration Tests (FastAPI TestClient)
# --------------------------------------------------------------------------

from backend.main import app
from backend.services.sarvam_engine import generate_synthetic_wav_base64
import base64


def test_voice_health_endpoint():
    """Verifies GET /api/v1/voice/health returns healthy status and service info."""
    client = TestClient(app)
    response = client.get("/api/v1/voice/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["gateway"] == "voice"
    assert data["database"] == "connected"
    assert "Munim-AI" in data["service"]
    assert "hi-IN" in data["supported_languages"]


def test_voice_tts_endpoint():
    """Verifies POST /api/v1/voice/tts synthesizes speech with valid base64 audio."""
    client = TestClient(app)
    payload = {
        "text": "Namaste Ramesh ji, aapka kirana dukan ka 650 rupaye udhaar baki hai.",
        "target_language_code": "hi-IN",
    }
    response = client.post("/api/v1/voice/tts", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "audio_base64" in data
    assert len(data["audio_base64"]) > 50
    # Verify valid base64 payload
    decoded = base64.b64decode(data["audio_base64"])
    assert decoded[:4] == b"RIFF"


def test_voice_propose_ambiguous_suresh_returns_disambiguation_card():
    """
    Verifies PRD §7.1: POST /api/v1/voice/propose with 'Suresh ka 200 rupaye udhaar likh do'
    returns NEEDS_DISAMBIGUATION card with candidates list and synthesized spoken audio.
    """
    client = TestClient(app)
    payload = {
        "transcript_override": "Suresh ka 200 rupaye udhaar likh do",
        "language_hint": "hi-IN",
    }
    response = client.post("/api/v1/voice/propose", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "NEEDS_DISAMBIGUATION"
    assert data["intent"] == "CREDIT_UDHAAR"
    assert data["extracted_amount"] == 200.0
    assert len(data["candidates"]) == 2
    assert "Dukaan mein do Suresh hain" in data["spoken_prompt_hi"]
    assert "200" in data["spoken_prompt_hi"]
    assert "tts_audio_base64" in data
    assert len(data["tts_audio_base64"]) > 50


def test_voice_propose_ramesh_repayment_proposal():
    """
    Verifies PRD §7.1: POST /api/v1/voice/propose with 'Ramesh ne 300 rupaye jama kiye'
    returns typed PROPOSAL card with extracted details and spoken confirmation prompt.
    """
    client = TestClient(app)
    payload = {
        "transcript_override": "Ramesh ne 300 rupaye jama kiye",
        "language_hint": "hi-IN",
    }
    response = client.post("/api/v1/voice/propose", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "PROPOSAL"
    assert data["intent"] == "REPAYMENT_JAMA"
    assert data["extracted_amount"] == 300.0
    assert data["customer_name"] == "Ramesh Sharma"
    assert data["current_balance"] == 650.0
    assert data["new_balance"] == 350.0
    assert "tts_audio_base64" in data


def test_voice_confirm_ramesh_repayment_commits_to_ledger():
    """
    Verifies D-04: POST /api/v1/voice/confirm approves repayment proposal,
    commits deterministic write to ledger_entries, logs an audit event to business_events,
    and returns updated balance with synthesized audio.
    """
    client = TestClient(app)
    conn = get_db_connection()
    try:
        cust = conn.execute("SELECT id FROM customers WHERE name = 'Ramesh Sharma';").fetchone()
        cust_id = cust["id"]
    finally:
        close_db_connection(conn)

    confirm_payload = {
        "proposal_id": "PROP-TEST-RAMESH-01",
        "action": "APPROVE",
        "intent": "REPAYMENT_JAMA",
        "customer_id": cust_id,
        "amount": 300.0,
        "payment_mode": "CASH",
        "source_utterance": "Ramesh ne 300 rupaye jama kiye",
        "language_hint": "hi-IN",
    }

    response = client.post("/api/v1/voice/confirm", json=confirm_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "CONFIRMED"
    assert data["intent"] == "REPAYMENT_JAMA"
    assert data["new_balance"] == 350.0
    assert data["ledger_entry_id"] > 0
    assert data["business_event_id"] > 0
    assert "tts_audio_base64" in data
    assert len(data["tts_audio_base64"]) > 50

    # Verify that ledger_entries table has the new row with CONFIRMED status
    conn = get_db_connection()
    try:
        ledger_row = conn.execute(
            "SELECT * FROM ledger_entries WHERE id = ?;", (data["ledger_entry_id"],)
        ).fetchone()
        assert ledger_row is not None
        assert ledger_row["entry_type"] == "REPAYMENT_JAMA"
        assert float(ledger_row["amount"]) == 300.0
        assert ledger_row["status"] == "CONFIRMED"

        # Verify business_events audit row
        biz_row = conn.execute(
            "SELECT * FROM business_events WHERE id = ?;", (data["business_event_id"],)
        ).fetchone()
        assert biz_row is not None
        assert biz_row["event_category"] == "LEDGER"
        assert biz_row["actor"] == "MERCHANT_APPROVED"
    finally:
        close_db_connection(conn)


def test_voice_confirm_unapproved_action_rejected():
    """
    Verifies Threat Model T-02-05: confirmation endpoint strictly rejects any action
    other than 'APPROVE', preventing unconfirmed or accidental database mutations.
    """
    client = TestClient(app)
    unapproved_payload = {
        "proposal_id": "PROP-TEST-REJECT-01",
        "action": "CANCEL",
        "intent": "REPAYMENT_JAMA",
        "customer_id": 1,
        "amount": 300.0,
    }
    response = client.post("/api/v1/voice/confirm", json=unapproved_payload)
    assert response.status_code == 400
    assert "Explicit merchant approval" in response.json()["detail"]


def test_voice_confirm_credit_udhaar():
    """
    Verifies that confirming a CREDIT_UDHAAR proposal adds to the customer's balance.
    """
    client = TestClient(app)
    conn = get_db_connection()
    try:
        cust = conn.execute("SELECT id FROM customers WHERE name = 'Ramesh Sharma';").fetchone()
        cust_id = cust["id"]
    finally:
        close_db_connection(conn)

    payload = {
        "proposal_id": "PROP-TEST-CREDIT-01",
        "action": "APPROVE",
        "intent": "CREDIT_UDHAAR",
        "customer_id": cust_id,
        "amount": 100.0,
        "source_utterance": "Ramesh ka 100 udhaar likho",
    }
    response = client.post("/api/v1/voice/confirm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CONFIRMED"
    assert data["new_balance"] == 750.0  # 650 initial + 100 credit


def test_voice_confirm_stock_inward():
    """
    Verifies confirming a STOCK_IN proposal adjusts inventory_items.current_stock
    and records an immutable stock_events row.
    """
    client = TestClient(app)
    conn = get_db_connection()
    try:
        item = conn.execute("SELECT id, current_stock FROM inventory_items WHERE sku_name LIKE '%Ghee%';").fetchone()
        item_id = item["id"]
        initial_stock = int(item["current_stock"])
    finally:
        close_db_connection(conn)

    payload = {
        "proposal_id": "PROP-TEST-STOCK-01",
        "action": "APPROVE",
        "intent": "STOCK_IN",
        "item_id": item_id,
        "quantity_delta": 5,
        "source_utterance": "Amul Ghee 5 packet aaya",
    }
    response = client.post("/api/v1/voice/confirm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CONFIRMED"
    assert data["new_stock"] == initial_stock + 5
    assert data["stock_event_id"] > 0


def test_voice_propose_multipart_audio_upload():
    """
    Verifies POST /api/v1/voice/propose accepts multipart/form-data audio uploads
    and transcribes with dynamic keyterm biasing.
    """
    client = TestClient(app)
    # Generate realistic synthetic WAV bytes
    b64_audio = generate_synthetic_wav_base64("Suresh ka 200 rupaye udhaar likh do", "hi-IN")
    wav_bytes = base64.b64decode(b64_audio)

    response = client.post(
        "/api/v1/voice/propose",
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"language_hint": "hi-IN"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"NEEDS_DISAMBIGUATION", "PROPOSAL"}
    assert "tts_audio_base64" in data


def test_voice_propose_oversized_audio_rejected():
    """
    Verifies Threat Model T-02-04: Audio uploads exceeding 10MB are rejected
    with HTTP 413 Payload Too Large.
    """
    client = TestClient(app)
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 1024)

    response = client.post(
        "/api/v1/voice/propose",
        files={"file": ("large_audio.wav", oversized_bytes, "audio/wav")},
    )
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"].lower()

