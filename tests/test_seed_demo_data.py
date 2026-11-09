"""
Unit and Idempotency Tests for KiranaOS Pre-Seeded Dadar Mumbai Kirana Dataset.
Verifies PRD §9, §11, D-04, and Threat Model T-01-08.
"""

import json
import pytest

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.deterministic_engine import calculate_customer_balance
from backend.services.seed_demo_data import STORE_NAME, seed_all


@pytest.fixture
def fresh_db(tmp_path):
    """Provides a cleanly initialized temporary SQLite database."""
    db_file = tmp_path / "seed_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        yield conn
    finally:
        close_db_connection(conn)


def test_seed_demo_data_customers_and_balances(fresh_db):
    """Verify customer records and deterministic balances per D-04 and PRD §9."""
    result = seed_all(fresh_db)
    assert result["status"] == "SEEDED"
    assert result["store_name"] == STORE_NAME

    # 1. Ramesh Sharma (owes 650.00, regular_cycle=7, language=mr-IN)
    ramesh = fresh_db.execute("SELECT * FROM customers WHERE name = 'Ramesh Sharma'").fetchone()
    assert ramesh is not None
    assert ramesh["phone"] == "+919820111222"
    assert ramesh["preferred_language"] == "mr-IN"
    assert ramesh["regular_cycle_days"] == 7
    ramesh_bal = calculate_customer_balance(fresh_db, ramesh["id"])
    assert ramesh_bal["net_outstanding_balance"] == 650.00
    assert ramesh_bal["total_credit"] == 650.00
    assert ramesh_bal["total_repayment"] == 0.00

    # 2. Suresh Patil (Tailor) (owes 200.00, regular_cycle=4, language=mr-IN)
    suresh_patil = fresh_db.execute(
        "SELECT * FROM customers WHERE name = 'Suresh Patil (Tailor)'"
    ).fetchone()
    assert suresh_patil is not None
    assert suresh_patil["phone"] == "+919820333444"
    assert suresh_patil["preferred_language"] == "mr-IN"
    assert suresh_patil["regular_cycle_days"] == 4
    patil_bal = calculate_customer_balance(fresh_db, suresh_patil["id"])
    assert patil_bal["net_outstanding_balance"] == 200.00

    # 3. Suresh Kadam (Kirana) (owes 450.00, regular_cycle=3, language=mr-IN)
    suresh_kadam = fresh_db.execute(
        "SELECT * FROM customers WHERE name = 'Suresh Kadam (Kirana)'"
    ).fetchone()
    assert suresh_kadam is not None
    assert suresh_kadam["phone"] == "+919820555666"
    assert suresh_kadam["preferred_language"] == "mr-IN"
    assert suresh_kadam["regular_cycle_days"] == 3
    kadam_bal = calculate_customer_balance(fresh_db, suresh_kadam["id"])
    assert kadam_bal["net_outstanding_balance"] == 450.00

    # 4. Priya Deshmukh (owes 0.00, regular_cycle=3, language=mr-IN)
    priya = fresh_db.execute("SELECT * FROM customers WHERE name = 'Priya Deshmukh'").fetchone()
    assert priya is not None
    assert priya["phone"] == "+919820777888"
    assert priya["preferred_language"] == "mr-IN"
    assert priya["regular_cycle_days"] == 3
    priya_bal = calculate_customer_balance(fresh_db, priya["id"])
    assert priya_bal["net_outstanding_balance"] == 0.00


def test_seed_demo_data_inventory_and_supplier(fresh_db):
    """Verify inventory items, stock movements, and supplier khata per D-04 and PRD §9."""
    seed_all(fresh_db)

    # 1. Amul Pure Ghee 1L (stock: 4, burn: 2.0, multiplier: 3.5, selling: 650.0)
    ghee = fresh_db.execute("SELECT * FROM inventory_items WHERE sku_name = 'Amul Pure Ghee 1L'").fetchone()
    assert ghee is not None
    assert ghee["current_stock"] == 4
    assert ghee["unit"] == "tins"
    assert ghee["last_unit_cost"] == 580.0
    assert ghee["previous_unit_cost"] == 580.0
    assert ghee["selling_price"] == 650.0
    assert ghee["avg_daily_burn"] == 2.0
    assert ghee["festive_multiplier"] == 3.5
    assert ghee["reorder_threshold"] == 10
    assert "Gupta Wholesalers" in ghee["supplier_name"]

    # 2. Fortune Sunlite Oil 1L (stock: 12, cost: 132.0, selling: 155.0, burn: 3.0, multiplier: 1.5)
    oil = fresh_db.execute("SELECT * FROM inventory_items WHERE sku_name = 'Fortune Sunlite Oil 1L'").fetchone()
    assert oil is not None
    assert oil["current_stock"] == 12
    assert oil["unit"] == "pouches"
    assert oil["last_unit_cost"] == 132.0
    assert oil["previous_unit_cost"] == 132.0
    assert oil["selling_price"] == 155.0
    assert oil["avg_daily_burn"] == 3.0
    assert oil["festive_multiplier"] == 1.5
    assert oil["reorder_threshold"] == 8

    # 3. Haldiram Aloo Bhujia 400g (stock: 28, cost: 72.0, selling: 95.0, burn: 0.0, multiplier: 1.0)
    bhujia = fresh_db.execute("SELECT * FROM inventory_items WHERE sku_name = 'Haldiram Aloo Bhujia 400g'").fetchone()
    assert bhujia is not None
    assert bhujia["current_stock"] == 28
    assert bhujia["unit"] == "packets"
    assert bhujia["last_unit_cost"] == 72.0
    assert bhujia["selling_price"] == 95.0
    assert bhujia["avg_daily_burn"] == 0.0
    assert bhujia["festive_multiplier"] == 1.0
    assert bhujia["reorder_threshold"] == 5

    # 4. Stock Events: inward movements for all three items
    stock_events = fresh_db.execute("SELECT * FROM stock_events").fetchall()
    assert len(stock_events) == 3
    for se in stock_events:
        assert se["event_type"] == "INWARD_INVOICE"
        assert se["quantity_delta"] > 0

    # 5. Supplier Ledger
    supp_entries = fresh_db.execute("SELECT * FROM supplier_ledger").fetchall()
    assert len(supp_entries) >= 1
    assert supp_entries[0]["supplier_name"] == "Gupta Wholesalers, APMC Vashi"
    assert supp_entries[0]["entry_type"] == "INVOICE_CREDIT"
    assert supp_entries[0]["amount"] == 5920.0


def test_seed_demo_data_unmatched_payments_and_business_events(fresh_db):
    """Verify ambiguous payments queue and system startup business event."""
    seed_all(fresh_db)

    # 1. Unmatched payments queue
    unmatched = fresh_db.execute("SELECT * FROM unmatched_payments_queue").fetchall()
    assert len(unmatched) == 1
    queue_item = unmatched[0]
    assert queue_item["upi_txn_id"] == "UPI-DEMO-SURESH-200"
    assert queue_item["amount"] == 200.0
    assert queue_item["payer_name"] == "Suresh"
    assert queue_item["status"] == "PENDING_REVIEW"
    candidates = json.loads(queue_item["candidate_customers_json"])
    assert len(candidates) == 2
    candidate_names = [c["name"] for c in candidates]
    assert "Suresh Patil (Tailor)" in candidate_names
    assert "Suresh Kadam (Kirana)" in candidate_names

    # 2. Business Events
    startup_events = fresh_db.execute(
        "SELECT * FROM business_events WHERE event_category = 'SYSTEM_STARTUP' AND actor = 'SYSTEM_SEEDER'"
    ).fetchall()
    assert len(startup_events) == 1
    evidence = json.loads(startup_events[0]["evidence_json"])
    assert evidence["store_name"] == STORE_NAME
    assert evidence["customers_seeded"] == 4
    assert evidence["inventory_items_seeded"] == 3


def test_seed_all_strict_idempotence(fresh_db):
    """
    Verify that calling seed_all multiple times is strictly idempotent:
    - Table counts do not increase on second call.
    - Balances remain 100% identical.
    - No duplicate ledger entries or stock movements.
    """
    # First seed
    seed_all(fresh_db)

    # Record counts
    tables = [
        "customers",
        "ledger_entries",
        "inventory_items",
        "stock_events",
        "supplier_ledger",
        "unmatched_payments_queue",
        "campaigns_and_links",
        "business_events",
    ]
    initial_counts = {}
    for t in tables:
        initial_counts[t] = fresh_db.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()["c"]

    # Verify initial non-zero counts for all 8 tables
    for t in tables:
        assert initial_counts[t] > 0, f"Table {t} should have at least 1 record"

    # Second seed
    seed_all(fresh_db)

    # Verify counts did not change
    for t in tables:
        new_count = fresh_db.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()["c"]
        assert new_count == initial_counts[t], f"Table {t} count changed from {initial_counts[t]} to {new_count}"

    # Verify balances remained identical
    ramesh = fresh_db.execute("SELECT id FROM customers WHERE name = 'Ramesh Sharma'").fetchone()
    assert calculate_customer_balance(fresh_db, ramesh["id"])["net_outstanding_balance"] == 650.00

    suresh_patil = fresh_db.execute("SELECT id FROM customers WHERE name = 'Suresh Patil (Tailor)'").fetchone()
    assert calculate_customer_balance(fresh_db, suresh_patil["id"])["net_outstanding_balance"] == 200.00
