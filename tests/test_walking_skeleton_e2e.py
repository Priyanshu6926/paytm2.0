"""
End-to-End Walking Skeleton Verification Test Harness.
Verifies PRD §2, §4, §6, §9, §11, and D-01, D-02, D-03, D-04, D-05.
Uses FastAPI TestClient to test the complete booted stack:
SQLite schema -> Idempotent Seeder -> Deterministic Engine -> FastAPI Memory Routers.
"""

import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.seed_demo_data import STORE_NAME


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """
    Spawns TestClient with a fresh temporary SQLite database path.
    Triggers FastAPI lifespan (init_db + seed_all) automatically.
    """
    temp_dir = tmp_path_factory.mktemp("e2e_db")
    test_db_file = str(temp_dir / "e2e_walking_skeleton.db")
    os.environ["KIRANAOS_DB_PATH"] = test_db_file

    with TestClient(app) as test_client:
        yield test_client

    if "KIRANAOS_DB_PATH" in os.environ:
        del os.environ["KIRANAOS_DB_PATH"]


def test_root_endpoint(client):
    """Root endpoint responds with store name and status."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["store"] == STORE_NAME


def test_memory_health_all_eight_tables_populated(client):
    """Health check confirms database connection and population of all 8 authoritative tables."""
    resp = client.get("/api/v1/memory/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["store_name"] == STORE_NAME
    assert data["database"] == "connected"
    assert data["all_tables_populated"] is True

    expected_tables = [
        "customers",
        "ledger_entries",
        "inventory_items",
        "stock_events",
        "supplier_ledger",
        "unmatched_payments_queue",
        "campaigns_and_links",
        "business_events",
    ]
    for table_name in expected_tables:
        assert table_name in data["tables"], f"Table {table_name} missing from health response"
        assert data["tables"][table_name] > 0, f"Table {table_name} must have at least 1 record"


def test_customers_list_and_ramesh_balance(client):
    """Verify customer list endpoint and exact 650.00 deterministic balance for Ramesh Sharma."""
    resp = client.get("/api/v1/memory/customers")
    assert resp.status_code == 200
    customers = resp.json()
    assert isinstance(customers, list)
    assert len(customers) == 4

    ramesh = next((c for c in customers if c["name"] == "Ramesh Sharma"), None)
    assert ramesh is not None
    assert ramesh["outstanding_balance"] == 650.00
    assert ramesh["total_credit"] == 650.00
    assert ramesh["total_repayment"] == 0.00
    assert ramesh["phone"] == "+919820111222"
    assert ramesh["preferred_language"] == "mr-IN"
    assert ramesh["days_overdue"] == 18

    priya = next((c for c in customers if c["name"] == "Priya Deshmukh"), None)
    assert priya is not None
    assert priya["outstanding_balance"] == 0.00


def test_customer_identity_disambiguation_suresh_query(client):
    """
    Searching for 'Suresh' must trigger identity disambiguation guard with 2 candidates
    (Suresh Patil vs Suresh Kadam) preventing blind writes per PRD §4 (FR-02) and D-03.
    """
    # 1. Via GET /api/v1/memory/customers?query=Suresh
    resp = client.get("/api/v1/memory/customers?query=Suresh")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NEEDS_DISAMBIGUATION"
    assert "candidates" in data
    assert len(data["candidates"]) == 2

    candidate_names = [c["name"] for c in data["candidates"]]
    assert "Suresh Patil (Tailor)" in candidate_names
    assert "Suresh Kadam (Kirana)" in candidate_names

    # Check live udhaar balances on candidates
    patil = next(c for c in data["candidates"] if "Tailor" in c["name"])
    assert patil["current_udhaar"] == 200.00
    kadam = next(c for c in data["candidates"] if "Kirana" in c["name"])
    assert kadam["current_udhaar"] == 450.00

    # Spoken Hindi prompt for voice UX
    assert "spoken_prompt_hi" in data
    assert "Suresh" in data["spoken_prompt_hi"]

    # 2. Via explicit GET /api/v1/memory/customers/resolve?query=Suresh
    resolve_resp = client.get("/api/v1/memory/customers/resolve?query=Suresh")
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "NEEDS_DISAMBIGUATION"


def test_customer_ledger_timeline(client):
    """Verify customer ledger endpoint returns append-only transaction history."""
    # Find Ramesh's ID
    cust_resp = client.get("/api/v1/memory/customers")
    ramesh_id = next(c["id"] for c in cust_resp.json() if c["name"] == "Ramesh Sharma")

    resp = client.get(f"/api/v1/memory/customers/{ramesh_id}/ledger")
    assert resp.status_code == 200
    ledger_data = resp.json()
    assert ledger_data["customer"]["name"] == "Ramesh Sharma"
    assert ledger_data["net_outstanding_balance"] == 650.00
    assert len(ledger_data["ledger_entries"]) >= 1

    entry = ledger_data["ledger_entries"][0]
    assert entry["entry_type"] == "CREDIT_UDHAAR"
    assert entry["amount"] == 650.00
    assert entry["payment_mode"] == "UDHAAR"
    assert entry["status"] == "CONFIRMED"


def test_customer_ledger_404_for_unknown_id(client):
    """Non-existent customer ID returns HTTP 404."""
    resp = client.get("/api/v1/memory/customers/99999/ledger")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_inventory_list(client):
    """Verify inventory endpoint returns all 3 demo SKUs with stock, burn rate, and multipliers."""
    resp = client.get("/api/v1/memory/inventory")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) == 4

    skus = {item["sku_name"]: item for item in items}
    assert "Amul Pure Ghee 1L" in skus
    assert "Fortune Sunlite Oil 1L" in skus
    assert "Haldiram Aloo Bhujia 400g" in skus
    assert "Maggi Masala 70g" in skus

    ghee = skus["Amul Pure Ghee 1L"]
    assert ghee["current_stock"] == 4
    assert ghee["unit"] == "tins"
    assert ghee["festive_multiplier"] == 3.5
    assert ghee["avg_daily_burn"] == 2.0
    assert ghee["selling_price"] == 650.0

    oil = skus["Fortune Sunlite Oil 1L"]
    assert oil["current_stock"] == 12
    assert oil["last_unit_cost"] == 132.0
    assert oil["selling_price"] == 155.0

    bhujia = skus["Haldiram Aloo Bhujia 400g"]
    assert bhujia["current_stock"] == 28
    assert bhujia["avg_daily_burn"] == 0.0


def test_business_events_feed(client):
    """Verify business events feed returns chronological audit entries with structured evidence."""
    resp = client.get("/api/v1/memory/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    assert len(events) >= 1

    # Check that system startup event is present
    startup_event = next((e for e in events if e["event_category"] == "SYSTEM_STARTUP"), None)
    assert startup_event is not None
    assert startup_event["actor"] == "SYSTEM_SEEDER"
    assert "evidence" in startup_event
    assert startup_event["evidence"]["store_name"] == STORE_NAME
