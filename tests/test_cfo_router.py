"""
Integration tests for AI CFO FastAPI Router endpoints.
Validates PRD §5.2, §5.3, §7.2, §7.3, D-02, D-03, and Threat Models T-03-01 to T-03-06.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.main import app
from backend.services.seed_demo_data import seed_all


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Provides a TestClient connected to a clean, isolated SQLite test database with seed data."""
    db_file = tmp_path / "cfo_router_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    seed_all(conn)
    close_db_connection(conn)

    monkeypatch.setenv("KIRANAOS_DB_PATH", str(db_file))

    with TestClient(app) as test_client:
        yield test_client, str(db_file)


# -----------------------------------------------------------------------------
# 1. Settlement Waterfall Explainer Tests (PRD §5.3, §7.3, D-03)
# -----------------------------------------------------------------------------

def test_settlement_explainer(client_with_db):
    """
    Validates GET /api/v1/cfo/settlement-explainer:
      - HTTP 200
      - Exact arithmetic balance: 6450 - 635 == 5815.00 down to Rs 0.01
      - verification_status == 'DETERMINISTICALLY_BALANCED'
      - Spoken Hindi explanation present
      - High-fidelity Bulbul TTS audio base64 present
    """
    client, _ = client_with_db
    response = client.get("/api/v1/cfo/settlement-explainer")

    assert response.status_code == 200
    data = response.json()

    assert data["settlement_date"] == "2026-11-09"
    assert data["bank_account"] == "State Bank of India •••• 4921"
    assert data["gross_qr_collections"] == 6450.00
    assert data["total_deductions"] == 635.00
    assert data["net_settled_to_bank"] == 5815.00
    assert data["verification_status"] == "DETERMINISTICALLY_BALANCED"
    assert len(data["deductions"]) == 3

    # Exact arithmetic invariant assertion
    assert (data["gross_qr_collections"] - data["total_deductions"]) == data["net_settled_to_bank"]

    # Spoken Hindi explanation check
    assert "6,450" in data["spoken_explanation_hi"]
    assert "5,815" in data["spoken_explanation_hi"]
    assert "SBI bank" in data["spoken_explanation_hi"]

    # TTS audio check
    assert data["tts_audio_base64"]
    assert len(data["tts_audio_base64"]) > 50


# -----------------------------------------------------------------------------
# 2. Distributor Bill Scanning Proposal Tests (PRD §5.2, §7.2, D-02)
# -----------------------------------------------------------------------------

def test_scan_distributor_bill_demo_preset(client_with_db):
    """
    Validates POST /api/v1/cfo/scan-distributor-bill with JSON demo flag:
      - Status 'PROPOSAL'
      - Total Rs 4,920.00
      - Price creep alert on Fortune Sunlite Oil (+7.58%, Rs 10 erosion, Rs 160 MRP)
      - Dual action preview text
      - Audio attached
    """
    client, _ = client_with_db
    response = client.post("/api/v1/cfo/scan-distributor-bill", json={"use_demo_sample": True})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "PROPOSAL"
    assert data["supplier_name"] == "Gupta Wholesalers, APMC Vashi"
    assert data["invoice_number"] == "GW-2026-994"
    assert data["invoice_total"] == 4920.00
    assert len(data["line_items"]) == 3

    # Verify price creep alert
    assert len(data["price_creep_alerts"]) == 1
    alert = data["price_creep_alerts"][0]
    assert alert["sku_name"] == "Fortune Sunlite Oil 1L"
    assert alert["creep_percentage"] == 7.58
    assert alert["previous_unit_cost"] == 132.00
    assert alert["new_unit_cost"] == 142.00
    assert alert["recommended_new_mrp"] == 160.00
    assert "Savdhaan!" in alert["alert_hi"]

    # Dual action preview
    assert "+118 units to Inventory" in data["dual_action_preview"]
    assert "Rs 4,920 payable in Gupta Wholesalers Khata" in data["dual_action_preview"]
    assert data["tts_audio_base64"]


def test_scan_distributor_bill_file_upload(client_with_db):
    """
    Validates POST /api/v1/cfo/scan-distributor-bill with multipart image file upload.
    """
    client, _ = client_with_db
    fake_img = io.BytesIO(b"\xff\xd8\xff\xe0" + b"0" * 500)
    response = client.post(
        "/api/v1/cfo/scan-distributor-bill",
        files={"file": ("invoice.jpg", fake_img, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSAL"
    assert data["invoice_number"] == "GW-2026-994"
    assert data["invoice_total"] == 4920.00


# -----------------------------------------------------------------------------
# 3. Confirm Distributor Bill Atomic Dual Write Tests (PRD §5.2, §7.2, D-02)
# -----------------------------------------------------------------------------

def test_confirm_distributor_bill_atomic_dual_write(client_with_db):
    """
    Validates POST /api/v1/cfo/confirm-distributor-bill:
      1. Increases inventory stock for all line items.
      2. Updates last_unit_cost and previous_unit_cost.
      3. Appends stock_events records.
      4. Appends supplier_ledger payable record.
      5. Appends business_events audit trail record.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)

    # Initial state checks
    oil_before = conn.execute("SELECT * FROM inventory_items WHERE sku_name = 'Fortune Sunlite Oil 1L'").fetchone()
    assert oil_before["current_stock"] == 12
    assert oil_before["last_unit_cost"] == 132.00
    assert oil_before["previous_unit_cost"] == 132.00
    assert oil_before["selling_price"] == 155.00

    maggi_before = conn.execute("SELECT * FROM inventory_items WHERE sku_name = 'Maggi Masala 70g'").fetchone()
    assert maggi_before["current_stock"] == 96

    close_db_connection(conn)

    payload = {
        "invoice_number": "GW-2026-994",
        "supplier_name": "Gupta Wholesalers, APMC Vashi",
        "line_items": [
            {
                "item_id": oil_before["id"],
                "sku_name": "Fortune Sunlite Oil 1L",
                "qty": 20,
                "unit": "liters",
                "unit_cost": 142.00,
                "line_total": 2840.00,
            },
            {
                "item_id": maggi_before["id"],
                "sku_name": "Maggi Masala 70g",
                "qty": 96,
                "unit": "packets",
                "unit_cost": 11.25,
                "line_total": 1080.00,
            },
            {
                "sku_name": "Amul Pure Ghee 1L",
                "qty": 2,
                "unit": "tins",
                "unit_cost": 500.00,
                "line_total": 1000.00,
            },
        ],
        "invoice_total": 4920.00,
        "price_creep_detected": True,
        "update_selling_prices": {
            "Fortune Sunlite Oil 1L": 160.00,
        },
    }

    response = client.post("/api/v1/cfo/confirm-distributor-bill", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["status"] == "CONFIRMED"
    assert res_data["invoice_number"] == "GW-2026-994"
    assert res_data["stock_events_created"] == 3
    assert res_data["supplier_ledger_id"] is not None
    assert res_data["business_event_id"] is not None

    # Verify Database State Mutations
    conn = get_db_connection(db_path)

    # 1. Inventory checks
    oil_after = conn.execute("SELECT * FROM inventory_items WHERE sku_name = 'Fortune Sunlite Oil 1L'").fetchone()
    assert oil_after["current_stock"] == 32  # 12 + 20
    assert oil_after["previous_unit_cost"] == 132.00
    assert oil_after["last_unit_cost"] == 142.00
    assert oil_after["selling_price"] == 160.00  # Updated selling price!

    maggi_after = conn.execute("SELECT * FROM inventory_items WHERE sku_name = 'Maggi Masala 70g'").fetchone()
    assert maggi_after["current_stock"] == 192  # 96 + 96

    # 2. Stock events checks
    stock_events = conn.execute(
        "SELECT * FROM stock_events WHERE invoice_number = 'GW-2026-994' ORDER BY id ASC"
    ).fetchall()
    assert len(stock_events) == 3
    assert stock_events[0]["event_type"] == "INWARD_INVOICE"
    assert stock_events[0]["quantity_delta"] == 20
    assert stock_events[0]["unit_cost"] == 142.00

    # 3. Supplier ledger check
    sup_ledger = conn.execute(
        "SELECT * FROM supplier_ledger WHERE invoice_number = 'GW-2026-994'"
    ).fetchone()
    assert sup_ledger is not None
    assert sup_ledger["supplier_name"] == "Gupta Wholesalers, APMC Vashi"
    assert sup_ledger["entry_type"] == "INVOICE_CREDIT"
    assert sup_ledger["amount"] == 4920.00
    assert sup_ledger["price_creep_flagged"] == 1

    # 4. Business events check
    bus_event = conn.execute(
        "SELECT * FROM business_events WHERE id = ?", (res_data["business_event_id"],)
    ).fetchone()
    assert bus_event is not None
    assert bus_event["event_category"] == "CFO_ALERT"
    assert "GW-2026-994" in bus_event["summary_text"]
    assert "+118 units added to stock" in bus_event["summary_text"]
    assert "Rs 4,920.00 recorded in supplier khata" in bus_event["summary_text"]

    close_db_connection(conn)


def test_confirm_distributor_bill_idempotency(client_with_db):
    """
    Validates idempotency guard (T-03-05):
    Submitting the same invoice_number twice must NOT duplicate inventory stock
    or create duplicate supplier_ledger entries.
    """
    client, db_path = client_with_db

    payload = {
        "invoice_number": "GW-DUP-101",
        "supplier_name": "Gupta Wholesalers, APMC Vashi",
        "line_items": [
            {
                "sku_name": "Amul Pure Ghee 1L",
                "qty": 5,
                "unit": "tins",
                "unit_cost": 500.00,
                "line_total": 2500.00,
            }
        ],
        "invoice_total": 2500.00,
        "price_creep_detected": False,
    }

    # First submission
    resp1 = client.post("/api/v1/cfo/confirm-distributor-bill", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "CONFIRMED"

    # Second submission with exact same invoice number
    resp2 = client.post("/api/v1/cfo/confirm-distributor-bill", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "ALREADY_CONFIRMED"
    assert data2["invoice_number"] == "GW-DUP-101"

    # Verify DB has only 1 entry in supplier_ledger
    conn = get_db_connection(db_path)
    entries = conn.execute(
        "SELECT * FROM supplier_ledger WHERE invoice_number = 'GW-DUP-101'"
    ).fetchall()
    assert len(entries) == 1

    # Verify stock only increased by 5 once (Amul Ghee initially 4 -> now 9, not 14)
    ghee = conn.execute("SELECT current_stock FROM inventory_items WHERE sku_name = 'Amul Pure Ghee 1L'").fetchone()
    assert ghee["current_stock"] == 9

    close_db_connection(conn)
