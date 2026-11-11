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


# -----------------------------------------------------------------------------
# 2. Dead-Stock Break-Even Studio & Per-Language Attribution Tests (CMO-04, CMO-05)
# -----------------------------------------------------------------------------


def test_dead_stock_query(client_with_db):
    """
    Test 1 (Dead stock query):
    GET /api/v1/cmo/dead-stock returns Haldiram Aloo Bhujia 400g (unsold 22 days > 15 days,
    stock 28, unit_cost 72.0, selling_price 95.0) and excludes recently sold items like
    Amul Pure Ghee 1L or Maggi Masala 70g.
    """
    client, _ = client_with_db
    response = client.get("/api/v1/cmo/dead-stock")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["dead_stock_items"]) == 1

    item = data["dead_stock_items"][0]
    assert item["sku_name"] == "Haldiram Aloo Bhujia 400g"
    assert item["days_unsold"] >= 22
    assert item["current_stock"] == 28
    assert item["unit_cost"] == 72.0
    assert item["selling_price"] == 95.0
    assert item["current_margin_per_unit"] == 23.0


@pytest.mark.parametrize("discount", [23.0, 25.0])
def test_dead_stock_campaign_loss_making_blocked(client_with_db, discount):
    """
    Test 2 (Loss-making offer blocked):
    POST /api/v1/cmo/dead-stock-campaign with item_id=3 and proposed_discount_rupees >= 23.0
    returns status="OFFER_BLOCKED_LOSS_MAKING", allowed=False, creates zero rows in
    campaigns_and_links, and logs a CMO_GROWTH guard event.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    bhujia = conn.execute(
        "SELECT id FROM inventory_items WHERE sku_name = 'Haldiram Aloo Bhujia 400g';"
    ).fetchone()
    before_campaigns = conn.execute(
        "SELECT COUNT(*) AS cnt FROM campaigns_and_links WHERE campaign_type = 'DEAD_STOCK_BUNDLE';"
    ).fetchone()["cnt"]
    close_db_connection(conn)

    response = client.post(
        "/api/v1/cmo/dead-stock-campaign",
        json={"item_id": bhujia["id"], "proposed_discount_rupees": discount},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OFFER_BLOCKED_LOSS_MAKING"
    assert data["allowed"] is False
    assert data["attributed_links"] == []
    assert "72" in data["reason"]

    conn = get_db_connection(db_path)
    after_campaigns = conn.execute(
        "SELECT COUNT(*) AS cnt FROM campaigns_and_links WHERE campaign_type = 'DEAD_STOCK_BUNDLE';"
    ).fetchone()["cnt"]
    assert after_campaigns == before_campaigns == 0

    guard_event = conn.execute(
        """
        SELECT * FROM business_events
        WHERE event_category = 'CMO_GROWTH' AND actor = 'SYSTEM_GUARD'
        ORDER BY id DESC LIMIT 1;
        """
    ).fetchone()
    assert guard_event is not None
    assert "OFFER_BLOCKED_LOSS_MAKING" in guard_event["evidence_json"]
    close_db_connection(conn)


def test_dead_stock_campaign_safe_breakeven_and_idempotency(client_with_db):
    """
    Test 3 (Safe break-even campaign + attribution links):
    POST /api/v1/cmo/dead-stock-campaign with item_id=3 and proposed_discount_rupees=10.0
    returns math_audit matching PRD §7.5 and two attributed_links (mr-IN and hi-IN).
    Re-calling the endpoint preserves existing click/conversion totals rather than resetting them.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    bhujia = conn.execute(
        "SELECT id FROM inventory_items WHERE sku_name = 'Haldiram Aloo Bhujia 400g';"
    ).fetchone()
    close_db_connection(conn)

    response = client.post(
        "/api/v1/cmo/dead-stock-campaign",
        json={"item_id": bhujia["id"], "proposed_discount_rupees": 10.0},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CAMPAIGN_READY"
    assert data["allowed"] is True
    assert data["sku_name"] == "Haldiram Aloo Bhujia 400g"
    assert data["days_unsold"] >= 22
    assert data["current_stock"] == 28
    assert data["unit_cost"] == 72.0
    assert data["selling_price"] == 95.0
    assert data["proposed_discount"] == 10.0
    assert data["discounted_price"] == 85.0

    audit = data["math_audit"]
    assert audit["old_margin_per_unit"] == 23.0
    assert audit["new_margin_per_unit"] == 13.0
    assert audit["usual_daily_sales"] == 4
    assert audit["breakeven_daily_sales_needed"] == 8
    assert audit["extra_units_needed_per_day"] == 4
    assert audit["verdict"] == "PROFITABLE_IF_VOLUME_DOUBLES"

    links = {lnk["language"]: lnk for lnk in data["attributed_links"]}
    assert set(links.keys()) == {"mr-IN", "hi-IN"}
    assert links["mr-IN"]["link"] == "paytm.me/promo-mr-bhujia"
    assert links["hi-IN"]["link"] == "paytm.me/promo-hi-bhujia"
    assert links["mr-IN"]["simulate_click_endpoint"] == "/api/v1/cmo/simulate-promo-click/promo-mr-bhujia"
    assert links["hi-IN"]["simulate_click_endpoint"] == "/api/v1/cmo/simulate-promo-click/promo-hi-bhujia"

    # Simulate 2 clicks/conversions on Marathi link
    client.post("/api/v1/cmo/simulate-promo-click/promo-mr-bhujia")
    client.post("/api/v1/cmo/simulate-promo-click/promo-mr-bhujia")

    # Re-calling dead-stock-campaign must preserve existing totals
    recalled = client.post(
        "/api/v1/cmo/dead-stock-campaign",
        json={"item_id": bhujia["id"], "proposed_discount_rupees": 10.0},
    )
    assert recalled.status_code == 200
    recalled_links = {lnk["language"]: lnk for lnk in recalled.json()["attributed_links"]}
    assert recalled_links["mr-IN"]["clicks"] == 2
    assert recalled_links["mr-IN"]["redemptions"] == 2
    assert recalled_links["mr-IN"]["revenue"] == 170.0
    assert recalled_links["hi-IN"]["clicks"] == 0


def test_simulate_promo_click_per_language_attribution(client_with_db):
    """
    Test 4 (Per-language click & conversion attribution):
    POST /api/v1/cmo/simulate-promo-click/{slug} increments clicks, conversions, and
    revenue_collected for the targeted language link (mr-IN vs hi-IN) independently
    and persists across reloads.
    """
    client, db_path = client_with_db
    conn = get_db_connection(db_path)
    bhujia = conn.execute(
        "SELECT id FROM inventory_items WHERE sku_name = 'Haldiram Aloo Bhujia 400g';"
    ).fetchone()
    close_db_connection(conn)

    init_resp = client.post(
        "/api/v1/cmo/dead-stock-campaign",
        json={"item_id": bhujia["id"], "proposed_discount_rupees": 10.0},
    )
    assert init_resp.status_code == 200

    # 3 converted clicks on mr-IN + 1 non-converted click on hi-IN + 1 converted click on hi-IN
    for _ in range(3):
        r_mr = client.post("/api/v1/cmo/simulate-promo-click/promo-mr-bhujia")
        assert r_mr.status_code == 200

    r_hi_click_only = client.post(
        "/api/v1/cmo/simulate-promo-click/promo-hi-bhujia",
        json={"converted": False},
    )
    assert r_hi_click_only.status_code == 200
    r_hi_conv = client.post("/api/v1/cmo/simulate-promo-click/promo-hi-bhujia")
    assert r_hi_conv.status_code == 200

    last_data = r_hi_conv.json()
    assert last_data["slug"] == "promo-hi-bhujia"
    assert last_data["language"] == "hi-IN"
    assert last_data["clicks"] == 2
    assert last_data["conversions"] == 1
    assert last_data["revenue_collected"] == 85.0

    breakdown = {item["language"]: item for item in last_data["language_breakdown"]}
    assert breakdown["mr-IN"]["clicks"] == 3
    assert breakdown["mr-IN"]["conversions"] == 3
    assert breakdown["mr-IN"]["revenue"] == 255.0
    assert breakdown["hi-IN"]["clicks"] == 2
    assert breakdown["hi-IN"]["conversions"] == 1
    assert breakdown["hi-IN"]["revenue"] == 85.0

    # Verify reload persistence via GET /api/v1/cmo/dead-stock
    reload_resp = client.get("/api/v1/cmo/dead-stock")
    assert reload_resp.status_code == 200
    reloaded_links = {
        lnk["language"]: lnk for lnk in reload_resp.json()["dead_stock_items"][0]["attributed_links"]
    }
    assert reloaded_links["mr-IN"]["clicks"] == 3
    assert reloaded_links["mr-IN"]["redemptions"] == 3
    assert reloaded_links["mr-IN"]["revenue"] == 255.0
    assert reloaded_links["hi-IN"]["clicks"] == 2
    assert reloaded_links["hi-IN"]["redemptions"] == 1
    assert reloaded_links["hi-IN"]["revenue"] == 85.0


def test_cmo_validation_and_error_guards(client_with_db):
    """
    Validates T-04-05 and T-04-06 input validation & 404/400/422 guards:
      - Negative proposed_discount_rupees rejected with HTTP 422.
      - Unknown customer_id, item_id, and slug return HTTP 404 without SQL leaks.
      - Zero-balance customer (Priya Deshmukh) rejected with HTTP 400.
    """
    client, db_path = client_with_db

    # Negative discount -> 422
    neg_resp = client.post(
        "/api/v1/cmo/dead-stock-campaign",
        json={"item_id": 3, "proposed_discount_rupees": -5.0},
    )
    assert neg_resp.status_code == 422

    # Unknown IDs/slugs -> 404
    assert (
        client.post("/api/v1/cmo/boli-baki-recovery", json={"customer_id": 9999}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/cmo/dead-stock-campaign",
            json={"item_id": 9999, "proposed_discount_rupees": 5.0},
        ).status_code
        == 404
    )
    assert client.post("/api/v1/cmo/simulate-link-paid/nonexistent-slug").status_code == 404
    assert client.post("/api/v1/cmo/simulate-promo-click/nonexistent-slug").status_code == 404

    # Zero-balance customer -> 400
    conn = get_db_connection(db_path)
    priya = conn.execute(
        "SELECT id FROM customers WHERE name = 'Priya Deshmukh';"
    ).fetchone()
    close_db_connection(conn)
    zero_resp = client.post(
        "/api/v1/cmo/boli-baki-recovery",
        json={"customer_id": priya["id"]},
    )
    assert zero_resp.status_code == 400


