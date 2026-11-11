"""
Unit tests for KiranaOS AI CMO deterministic engines and Handwritten Bahi-Khata OCR service.
Validates PRD §5.4, §5.5, CMO-04, CMO-06, and ONBOARD-01.
"""

import pytest

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.deterministic_engine import (
    add_credit_entry,
    add_repayment_entry,
    calculate_breakeven_offer,
    calculate_customer_balance,
    calculate_festive_restock_forecast,
    log_business_event,
)
from backend.services.seed_demo_data import seed_all


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

