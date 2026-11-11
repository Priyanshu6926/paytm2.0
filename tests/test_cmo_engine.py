"""
Unit tests for KiranaOS AI CMO deterministic engines and Handwritten Bahi-Khata OCR service.
Validates PRD §5.4, §5.5, CMO-04, CMO-06, and ONBOARD-01.
"""

import httpx
import pytest

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.bahi_khata_parser_service import (
    MAX_IMAGE_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    parse_bahi_khata_page,
)
from backend.services.deterministic_engine import (
    add_credit_entry,
    add_repayment_entry,
    calculate_breakeven_offer,
    calculate_customer_balance,
    calculate_festive_restock_forecast,
    log_business_event,
)
from backend.services.seed_demo_data import seed_all


@pytest.fixture
def fresh_db(tmp_path):
    """Provides a cleanly initialized temporary SQLite database with seed data."""
    db_file = tmp_path / "cmo_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    seed_all(conn)
    try:
        yield conn
    finally:
        close_db_connection(conn)


# -----------------------------------------------------------------------------
# 1. Offer Break-Even Guardrail Engine Tests (PRD §5.4, CMO-04)
# -----------------------------------------------------------------------------


def test_breakeven_offer_benchmark():
    """
    Validates PRD §5.4 & §7.5 benchmark:
    Haldiram Aloo Bhujia 400g: cost=72.0, price=95.0, volume=4, discount=10.0
      -> old_margin=23.0, new_margin=13.0, breakeven=8, extra=4,
         allowed=True, status='SAFE', verdict='PROFITABLE_IF_VOLUME_DOUBLES'.
    """
    result = calculate_breakeven_offer(
        unit_cost=72.0,
        selling_price=95.0,
        usual_daily_volume=4,
        proposed_discount=10.0,
        sku_name="Haldiram Aloo Bhujia 400g",
    )

    assert result["sku_name"] == "Haldiram Aloo Bhujia 400g"
    assert result["unit_cost"] == 72.0
    assert result["selling_price"] == 95.0
    assert result["proposed_discount"] == 10.0
    assert result["discounted_price"] == 85.0
    assert result["old_margin_per_unit"] == 23.0
    assert result["new_margin_per_unit"] == 13.0
    assert result["usual_daily_sales"] == 4
    assert result["breakeven_daily_sales_needed"] == 8
    assert result["extra_units_needed_per_day"] == 4
    assert result["allowed"] is True
    assert result["status"] == "SAFE"
    assert result["verdict"] == "PROFITABLE_IF_VOLUME_DOUBLES"
    assert result["reason"] == ""


def test_breakeven_offer_zero_discount_preserves_margin():
    """Zero discount preserves margin and requires no extra daily units."""
    result = calculate_breakeven_offer(
        unit_cost=72.0,
        selling_price=95.0,
        usual_daily_volume=4,
        proposed_discount=0.0,
        sku_name="Haldiram Aloo Bhujia 400g",
    )

    assert result["allowed"] is True
    assert result["status"] == "SAFE"
    assert result["verdict"] == "MARGIN_PRESERVED"
    assert result["breakeven_daily_sales_needed"] == 4
    assert result["extra_units_needed_per_day"] == 0


def test_breakeven_offer_moderate_discount_verdict():
    """Small discount where breakeven < 2x usual volume uses PROFITABLE_IF_VOLUME_INCREASES."""
    result = calculate_breakeven_offer(
        unit_cost=72.0,
        selling_price=95.0,
        usual_daily_volume=4,
        proposed_discount=3.0,
        sku_name="Haldiram Aloo Bhujia 400g",
    )

    # old_margin=23, new_margin=20 -> ceil(4*23/20) = ceil(4.6) = 5 (< 8)
    assert result["allowed"] is True
    assert result["status"] == "SAFE"
    assert result["breakeven_daily_sales_needed"] == 5
    assert result["extra_units_needed_per_day"] == 1
    assert result["verdict"] == "PROFITABLE_IF_VOLUME_INCREASES"


@pytest.mark.parametrize("discount", [23.0, 30.0])
def test_breakeven_offer_loss_making_hard_stop(discount):
    """
    Hard stop guardrail: discounts where (selling_price - proposed_discount) <= unit_cost
    must block the offer with OFFER_BLOCKED_LOSS_MAKING.
    """
    result = calculate_breakeven_offer(
        unit_cost=72.0,
        selling_price=95.0,
        usual_daily_volume=4,
        proposed_discount=discount,
        sku_name="Haldiram Aloo Bhujia 400g",
    )

    assert result["allowed"] is False
    assert result["status"] == "OFFER_BLOCKED_LOSS_MAKING"
    assert result["verdict"] == "OFFER_BLOCKED_LOSS_MAKING"
    assert result["breakeven_daily_sales_needed"] is None
    assert result["extra_units_needed_per_day"] is None
    assert "72" in result["reason"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"unit_cost": 72.0, "selling_price": 0.0, "usual_daily_volume": 4, "proposed_discount": 5.0},
        {"unit_cost": 72.0, "selling_price": -10.0, "usual_daily_volume": 4, "proposed_discount": 5.0},
        {"unit_cost": -5.0, "selling_price": 95.0, "usual_daily_volume": 4, "proposed_discount": 5.0},
        {"unit_cost": 72.0, "selling_price": 95.0, "usual_daily_volume": 4, "proposed_discount": -1.0},
        {"unit_cost": 72.0, "selling_price": 95.0, "usual_daily_volume": 0, "proposed_discount": 5.0},
        {"unit_cost": 72.0, "selling_price": 95.0, "usual_daily_volume": -2, "proposed_discount": 5.0},
    ],
)
def test_breakeven_offer_invalid_inputs_raise_value_error(kwargs):
    """Zero/negative guards raise ValueError rather than dividing by zero or miscalculating."""
    with pytest.raises(ValueError):
        calculate_breakeven_offer(**kwargs)


# -----------------------------------------------------------------------------
# 2. Proactive Festive Restock Forecast Engine Tests (PRD §5.5, CMO-06)
# -----------------------------------------------------------------------------


def test_festive_restock_benchmark():
    """
    Validates PRD §5.5 & §7.6 Diwali benchmark:
    Amul Pure Ghee 1L: daily_burn=2.0, multiplier=3.5, stock=4, window=5
      -> projected_5day_demand=35, recommended_order_qty=31,
         one_tap_order_draft referencing 31 tins and Gupta Wholesalers.
    """
    result = calculate_festive_restock_forecast(
        daily_burn_rate=2.0,
        festive_multiplier=3.5,
        current_stock=4,
        festival_window_days=5,
        sku_name="Amul Pure Ghee 1L",
        unit="tins",
        supplier_name="Gupta Wholesalers",
    )

    assert result["upcoming_event"] == "Diwali Peak Week"
    assert result["days_away"] == 5
    assert result["sku_name"] == "Amul Pure Ghee 1L"
    assert result["unit"] == "tins"
    assert result["current_stock"] == 4
    assert result["normal_daily_burn"] == 2.0
    assert result["festive_surge_multiplier"] == 3.5
    assert result["projected_5day_demand"] == 35
    assert result["recommended_order_qty"] == 31
    assert result["supplier_name"] == "Gupta Wholesalers"
    assert "31 tins" in result["one_tap_order_draft"]
    assert "Gupta Wholesalers" in result["one_tap_order_draft"]


def test_festive_restock_surplus_clamps_to_zero():
    """When current_stock >= projected_5day_demand, recommended_order_qty is clamped to 0."""
    result = calculate_festive_restock_forecast(
        daily_burn_rate=2.0,
        festive_multiplier=3.5,
        current_stock=50,
        festival_window_days=5,
        sku_name="Amul Pure Ghee 1L",
    )

    assert result["projected_5day_demand"] == 35
    assert result["recommended_order_qty"] == 0
    assert result["one_tap_order_draft"] == "Stock sufficient for festive window."


def test_festive_restock_invalid_inputs_raise_value_error():
    """Negative burn rate, non-positive multiplier/window, or negative stock raise ValueError."""
    with pytest.raises(ValueError):
        calculate_festive_restock_forecast(-1.0, 3.5, 4, 5)
    with pytest.raises(ValueError):
        calculate_festive_restock_forecast(2.0, 0.0, 4, 5)
    with pytest.raises(ValueError):
        calculate_festive_restock_forecast(2.0, 3.5, 4, 0)
    with pytest.raises(ValueError):
        calculate_festive_restock_forecast(2.0, 3.5, -1, 5)


def test_ledger_commit_false_supports_atomic_rollback(tmp_path):
    """
    Validates optional commit=False parameter on log_business_event, add_credit_entry,
    and add_repayment_entry so multi-entry batches can roll back atomically.
    """
    db_file = tmp_path / "cmo_tx_test.db"
    init_db(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        seed_all(conn)
        ramesh = conn.execute(
            "SELECT id FROM customers WHERE name = 'Ramesh Sharma';"
        ).fetchone()
        ramesh_id = ramesh["id"]
        initial_balance = calculate_customer_balance(conn, ramesh_id)["net_outstanding_balance"]

        add_credit_entry(conn, ramesh_id, 100.0, source_utterance="tx-test", commit=False)
        add_repayment_entry(conn, ramesh_id, 25.0, source_utterance="tx-test", commit=False)
        log_business_event(conn, "CMO_GROWTH", "Batch test", {"ok": True}, commit=False)

        # Visible inside open transaction before rollback
        assert calculate_customer_balance(conn, ramesh_id)["net_outstanding_balance"] == initial_balance + 75.0

        # Rollback restores prior state cleanly
        conn.rollback()
        assert calculate_customer_balance(conn, ramesh_id)["net_outstanding_balance"] == initial_balance
    finally:
        close_db_connection(conn)


# -----------------------------------------------------------------------------
# 3. Handwritten Bahi-Khata OCR Parser Service Tests (ONBOARD-01)
# -----------------------------------------------------------------------------


def test_bahi_khata_demo_preset_parsing(fresh_db):
    """
    Validates demo preset parsing:
      - status == 'PROPOSAL', fallback_used == True
      - non-empty batch-editable proposals with positive amounts
      - deterministic total_proposed_amount equals exact sum of row amounts
      - read-only classification against SQLite customers (zero business_events mutation)
    """
    events_before = fresh_db.execute("SELECT COUNT(*) AS cnt FROM business_events;").fetchone()["cnt"]
    ledger_before = fresh_db.execute("SELECT COUNT(*) AS cnt FROM ledger_entries;").fetchone()["cnt"]

    result = parse_bahi_khata_page(use_demo_sample=True, conn=fresh_db)

    assert result["status"] == "PROPOSAL"
    assert result["fallback_used"] is True
    assert result["detected_language"] == "mr-IN"
    assert result["proposal_count"] == len(result["proposals"])
    assert result["proposal_count"] == 4

    expected_sum = round(sum(row["amount"] for row in result["proposals"]), 2)
    assert result["total_proposed_amount"] == expected_sum
    assert expected_sum == 1290.00  # 340 + 520 + 280 + 150

    for row in result["proposals"]:
        assert row["amount"] > 0
        assert row["match_status"] in {"EXISTING_CUSTOMER", "NEW_CUSTOMER", "AMBIGUOUS"}

    # Confirm read-only preview did not mutate financial or audit tables
    events_after = fresh_db.execute("SELECT COUNT(*) AS cnt FROM business_events;").fetchone()["cnt"]
    ledger_after = fresh_db.execute("SELECT COUNT(*) AS cnt FROM ledger_entries;").fetchone()["cnt"]
    assert events_after == events_before
    assert ledger_after == ledger_before


def test_bahi_khata_upload_fallback_and_10mb_guardrail(fresh_db, monkeypatch):
    """
    Passing mock JPEG bytes without SARVAM_API_KEY or >10MB bytes returns clean
    offline fallback proposal without raising exceptions or calling network.
    """
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    # 1. Mock JPEG bytes without API key -> clean fallback
    res_no_key = parse_bahi_khata_page(image_bytes=b"\xff\xd8\xffmock-jpeg", conn=fresh_db)
    assert res_no_key["status"] == "PROPOSAL"
    assert res_no_key["fallback_used"] is True
    assert res_no_key["proposal_count"] == 4

    # 2. >10MB payload even with API key set -> blocked before HTTP call, uses fallback
    monkeypatch.setenv("SARVAM_API_KEY", "secret-test-key-should-not-leak")
    called = {"count": 0}

    def fail_if_called(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("HTTP client should not be called for >10MB uploads")

    monkeypatch.setattr(httpx.Client, "post", fail_if_called)

    oversized = b"x" * (MAX_IMAGE_BYTES + 1)
    res_oversized = parse_bahi_khata_page(image_bytes=oversized, conn=fresh_db)
    assert called["count"] == 0
    assert res_oversized["status"] == "PROPOSAL"
    assert res_oversized["fallback_used"] is True
    assert "secret-test-key-should-not-leak" not in str(res_oversized)


def test_bahi_khata_timeout_survivability_6s(fresh_db, monkeypatch):
    """
    Mocking httpx.Client.post to raise httpx.TimeoutException degrades cleanly
    under the 6.0s timeout policy to DEMO_BAHI_KHATA_PAGE with fallback_used=True.
    """
    monkeypatch.setenv("SARVAM_API_KEY", "secret-test-key-should-not-leak")
    observed_timeouts = []

    original_init = httpx.Client.__init__

    def spy_init(self, *args, **kwargs):
        observed_timeouts.append(kwargs.get("timeout"))
        return original_init(self, *args, **kwargs)

    def raise_timeout(self, *args, **kwargs):
        raise httpx.TimeoutException("Sarvam Vision OCR timed out")

    monkeypatch.setattr(httpx.Client, "__init__", spy_init)
    monkeypatch.setattr(httpx.Client, "post", raise_timeout)

    result = parse_bahi_khata_page(image_bytes=b"\xff\xd8\xffmock-jpeg", conn=fresh_db)

    assert REQUEST_TIMEOUT_SECONDS == 6.0
    assert observed_timeouts == [6.0]
    assert result["status"] == "PROPOSAL"
    assert result["fallback_used"] is True
    assert result["proposal_count"] == 4
    assert result["total_proposed_amount"] == 1290.00
    assert "secret-test-key-should-not-leak" not in str(result)


def test_bahi_khata_customer_match_classification(fresh_db, monkeypatch):
    """
    Validates EXISTING_CUSTOMER, NEW_CUSTOMER, and AMBIGUOUS classification:
      - 'Ramesh Sharma' -> EXISTING_CUSTOMER with matched_customer_id and existing_balance
      - 'Sunita Sawant' -> NEW_CUSTOMER with matched_customer_id=None
      - 'Suresh' -> AMBIGUOUS with candidate_customers and matched_customer_id=None
    Does not log SYSTEM_GUARD events during read-only OCR preview.
    """
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "page_title": "Uploaded Khata Page",
                "detected_language": "mr-IN",
                "entries": [
                    {
                        "customer_name": "Ramesh Sharma",
                        "phone": "+919820111222",
                        "preferred_language": "mr-IN",
                        "amount": 150.0,
                        "notes": "Milk + Bread",
                        "confidence": 0.96,
                    },
                    {
                        "customer_name": "Sunita Sawant",
                        "phone": "+919821112233",
                        "preferred_language": "mr-IN",
                        "amount": 340.0,
                        "notes": "Atta 5kg",
                        "confidence": 0.94,
                    },
                    {
                        "customer_name": "Suresh",
                        "phone": "",
                        "preferred_language": "mr-IN",
                        "amount": 225.0,
                        "notes": "Sugar 2kg",
                        "confidence": 0.87,
                    },
                ],
            }

    monkeypatch.setattr(httpx.Client, "post", lambda self, *args, **kwargs: FakeResponse())

    events_before = fresh_db.execute("SELECT COUNT(*) AS cnt FROM business_events;").fetchone()["cnt"]
    result = parse_bahi_khata_page(image_bytes=b"\xff\xd8\xffmock-jpeg", conn=fresh_db)
    events_after = fresh_db.execute("SELECT COUNT(*) AS cnt FROM business_events;").fetchone()["cnt"]

    assert events_after == events_before
    assert result["fallback_used"] is False
    assert result["proposal_count"] == 3
    assert result["total_proposed_amount"] == 715.00

    by_name = {row["customer_name"]: row for row in result["proposals"]}

    ramesh_row = by_name["Ramesh Sharma"]
    assert ramesh_row["match_status"] == "EXISTING_CUSTOMER"
    assert ramesh_row["matched_customer_id"] is not None
    assert ramesh_row["existing_balance"] == 650.00

    sunita_row = by_name["Sunita Sawant"]
    assert sunita_row["match_status"] == "NEW_CUSTOMER"
    assert sunita_row["matched_customer_id"] is None

    suresh_row = by_name["Suresh"]
    assert suresh_row["match_status"] == "AMBIGUOUS"
    assert suresh_row["matched_customer_id"] is None
    assert len(suresh_row["candidate_customers"]) == 2
    cand_names = {c["name"] for c in suresh_row["candidate_customers"]}
    assert "Suresh Patil (Tailor)" in cand_names
    assert "Suresh Kadam (Kirana)" in cand_names


