"""
KiranaOS Pre-Seeded Dadar Mumbai Kirana Store Dataset Generator
Conforms to PRD §9, §11, D-04, and Threat Model T-01-08.
Populates authoritative baseline data for "Ganesh Provision & General Store (Dadar, Mumbai)".
Guarantees strict idempotence: repeated runs do not duplicate records or corrupt balances.
"""

from datetime import datetime, timedelta
import json
import sqlite3
from typing import Any, Dict, Optional

from backend.database.connection import get_db_connection


STORE_NAME = "Ganesh Provision & General Store (Dadar, Mumbai)"


def seed_all(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Idempotently seeds baseline customers, ledger entries, inventory items,
    stock events, supplier ledger, ambiguous payment queue, and business events
    for Ganesh Provision & General Store (Dadar, Mumbai).

    If conn is None, creates a connection to the configured database.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        now = datetime.now()

        # ----------------------------------------------------------------------
        # 1. Customers
        # ----------------------------------------------------------------------
        customers_spec = [
            {
                "name": "Ramesh Sharma",
                "aliases": ["Ramesh Bhai", "Rameshji"],
                "phone": "+919820111222",
                "preferred_language": "mr-IN",
                "regular_cycle_days": 7,
                "days_ago": 18,
                "udhaar_amount": 650.00,
                "provider_ref": "SEED-UDHAAR-RAMESH-001",
                "utterance": "Ramesh Sharma udhaar 650",
            },
            {
                "name": "Suresh Patil (Tailor)",
                "aliases": ["Suresh Tailor", "Suresh"],
                "phone": "+919820333444",
                "preferred_language": "mr-IN",
                "regular_cycle_days": 4,
                "days_ago": 5,
                "udhaar_amount": 200.00,
                "provider_ref": "SEED-UDHAAR-SURESH-PATIL-001",
                "utterance": "Suresh Patil Tailor udhaar 200",
            },
            {
                "name": "Suresh Kadam (Kirana)",
                "aliases": ["Suresh Kirana", "Suresh"],
                "phone": "+919820555666",
                "preferred_language": "mr-IN",
                "regular_cycle_days": 3,
                "days_ago": 9,
                "udhaar_amount": 450.00,
                "provider_ref": "SEED-UDHAAR-SURESH-KADAM-001",
                "utterance": "Suresh Kadam Kirana udhaar 450",
            },
            {
                "name": "Priya Deshmukh",
                "aliases": ["Priyatai"],
                "phone": "+919820777888",
                "preferred_language": "mr-IN",
                "regular_cycle_days": 3,
                "days_ago": 16,
                "udhaar_amount": 0.00,
                "provider_ref": None,
                "utterance": None,
            },
        ]

        customer_id_map: Dict[str, int] = {}

        for c in customers_spec:
            last_visit_dt = (now - timedelta(days=c["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
            aliases_json = json.dumps(c["aliases"], ensure_ascii=False)

            existing_cust = conn.execute(
                "SELECT id FROM customers WHERE phone = ? OR name = ?;",
                (c["phone"], c["name"]),
            ).fetchone()

            if existing_cust:
                cust_id = existing_cust["id"]
                conn.execute(
                    """
                    UPDATE customers
                    SET name = ?, aliases = ?, phone = ?, preferred_language = ?, regular_cycle_days = ?, last_visit_date = ?
                    WHERE id = ?;
                    """,
                    (
                        c["name"],
                        aliases_json,
                        c["phone"],
                        c["preferred_language"],
                        c["regular_cycle_days"],
                        last_visit_dt,
                        cust_id,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO customers (
                        name, aliases, phone, preferred_language, regular_cycle_days, last_visit_date
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        c["name"],
                        aliases_json,
                        c["phone"],
                        c["preferred_language"],
                        c["regular_cycle_days"],
                        last_visit_dt,
                    ),
                )
                cust_id = cursor.lastrowid

            customer_id_map[c["name"]] = cust_id

            # ------------------------------------------------------------------
            # 2. Append-Only Ledger Entry (Initial Udhaar)
            # ------------------------------------------------------------------
            if c["udhaar_amount"] > 0 and c["provider_ref"]:
                existing_entry = conn.execute(
                    "SELECT id FROM ledger_entries WHERE provider_ref = ?;",
                    (c["provider_ref"],),
                ).fetchone()

                if not existing_entry:
                    entry_created_at = (now - timedelta(days=c["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        """
                        INSERT INTO ledger_entries (
                            customer_id, entry_type, amount, payment_mode, provider_ref,
                            source_utterance, confidence_score, status, created_at
                        ) VALUES (?, 'CREDIT_UDHAAR', ?, 'UDHAAR', ?, ?, 1.0, 'CONFIRMED', ?);
                        """,
                        (
                            cust_id,
                            c["udhaar_amount"],
                            c["provider_ref"],
                            c["utterance"],
                            entry_created_at,
                        ),
                    )

        # ----------------------------------------------------------------------
        # 3. Inventory Items
        # ----------------------------------------------------------------------
        inventory_spec = [
            {
                "sku_name": "Amul Pure Ghee 1L",
                "local_aliases": ["Amul Ghee", "Ghee 1L", "Asli Ghee"],
                "category": "Dairy & Staples",
                "current_stock": 4,
                "unit": "tins",
                "last_unit_cost": 580.0,
                "previous_unit_cost": 580.0,
                "selling_price": 650.0,
                "avg_daily_burn": 2.0,
                "festive_multiplier": 3.5,
                "reorder_threshold": 10,
                "supplier_name": "Gupta Wholesalers, APMC Vashi",
                "supplier_phone": "+919820999000",
                "days_restocked": 10,
                "days_sold": 1,
                "invoice_num": "GW-INV-2026-101",
            },
            {
                "sku_name": "Fortune Sunlite Oil 1L",
                "local_aliases": ["Fortune Oil", "Sunlite Oil", "Tel 1L"],
                "category": "Edible Oils",
                "current_stock": 12,
                "unit": "pouches",
                "last_unit_cost": 132.0,
                "previous_unit_cost": 132.0,
                "selling_price": 155.0,
                "avg_daily_burn": 3.0,
                "festive_multiplier": 1.5,
                "reorder_threshold": 8,
                "supplier_name": "Gupta Wholesalers, APMC Vashi",
                "supplier_phone": "+919820999000",
                "days_restocked": 7,
                "days_sold": 1,
                "invoice_num": "GW-INV-2026-102",
            },
            {
                "sku_name": "Haldiram Aloo Bhujia 400g",
                "local_aliases": ["Haldiram Bhujia", "Aloo Bhujia", "Bhujia 400g"],
                "category": "Snacks",
                "current_stock": 28,
                "unit": "packets",
                "last_unit_cost": 72.0,
                "previous_unit_cost": 72.0,
                "selling_price": 95.0,
                "avg_daily_burn": 0.0,
                "festive_multiplier": 1.0,
                "reorder_threshold": 5,
                "supplier_name": "Gupta Wholesalers, APMC Vashi",
                "supplier_phone": "+919820999000",
                "days_restocked": 30,
                "days_sold": 22,
                "invoice_num": "GW-INV-2026-089",
            },
            {
                "sku_name": "Maggi Masala 70g",
                "local_aliases": ["Maggi Masala", "Maggi 70g", "Masala Noodles"],
                "category": "Packaged Foods & Noodles",
                "current_stock": 96,
                "unit": "packets",
                "last_unit_cost": 11.25,
                "previous_unit_cost": 11.25,
                "selling_price": 14.0,
                "avg_daily_burn": 12.0,
                "festive_multiplier": 1.2,
                "reorder_threshold": 24,
                "supplier_name": "Gupta Wholesalers, APMC Vashi",
                "supplier_phone": "+919820999000",
                "days_restocked": 5,
                "days_sold": 1,
                "invoice_num": "GW-INV-2026-103",
            },
        ]

        item_id_map: Dict[str, int] = {}

        for item in inventory_spec:
            aliases_json = json.dumps(item["local_aliases"], ensure_ascii=False)
            last_restocked = (now - timedelta(days=item["days_restocked"])).strftime("%Y-%m-%d %H:%M:%S")
            last_sold = (now - timedelta(days=item["days_sold"])).strftime("%Y-%m-%d %H:%M:%S")

            existing_item = conn.execute(
                "SELECT id FROM inventory_items WHERE sku_name = ?;",
                (item["sku_name"],),
            ).fetchone()

            if existing_item:
                item_id = existing_item["id"]
                conn.execute(
                    """
                    UPDATE inventory_items
                    SET local_aliases = ?, category = ?, current_stock = ?, unit = ?,
                        last_unit_cost = ?, previous_unit_cost = ?, selling_price = ?,
                        avg_daily_burn = ?, festive_multiplier = ?, reorder_threshold = ?,
                        supplier_name = ?, supplier_phone = ?, last_restocked_at = ?, last_sold_at = ?
                    WHERE id = ?;
                    """,
                    (
                        aliases_json,
                        item["category"],
                        item["current_stock"],
                        item["unit"],
                        item["last_unit_cost"],
                        item["previous_unit_cost"],
                        item["selling_price"],
                        item["avg_daily_burn"],
                        item["festive_multiplier"],
                        item["reorder_threshold"],
                        item["supplier_name"],
                        item["supplier_phone"],
                        last_restocked,
                        last_sold,
                        item_id,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO inventory_items (
                        sku_name, local_aliases, category, current_stock, unit,
                        last_unit_cost, previous_unit_cost, selling_price,
                        avg_daily_burn, festive_multiplier, reorder_threshold,
                        supplier_name, supplier_phone, last_restocked_at, last_sold_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item["sku_name"],
                        aliases_json,
                        item["category"],
                        item["current_stock"],
                        item["unit"],
                        item["last_unit_cost"],
                        item["previous_unit_cost"],
                        item["selling_price"],
                        item["avg_daily_burn"],
                        item["festive_multiplier"],
                        item["reorder_threshold"],
                        item["supplier_name"],
                        item["supplier_phone"],
                        last_restocked,
                        last_sold,
                    ),
                )
                item_id = cursor.lastrowid

            item_id_map[item["sku_name"]] = item_id

            # ------------------------------------------------------------------
            # 4. Stock Events (Initial Inward Baseline)
            # ------------------------------------------------------------------
            existing_stock = conn.execute(
                "SELECT id FROM stock_events WHERE invoice_number = ? AND item_id = ?;",
                (item["invoice_num"], item_id),
            ).fetchone()

            if not existing_stock:
                stock_created_at = (now - timedelta(days=item["days_restocked"])).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    """
                    INSERT INTO stock_events (
                        item_id, event_type, quantity_delta, unit_cost, invoice_number, raw_transcript, created_at
                    ) VALUES (?, 'INWARD_INVOICE', ?, ?, ?, ?, ?);
                    """,
                    (
                        item_id,
                        item["current_stock"],
                        item["last_unit_cost"],
                        item["invoice_num"],
                        f"Initial inward inventory baseline: {item['current_stock']} {item['unit']}",
                        stock_created_at,
                    ),
                )

        # ----------------------------------------------------------------------
        # 5. Supplier Ledger (Baseline Balance for Gupta Wholesalers)
        # ----------------------------------------------------------------------
        supplier_name = "Gupta Wholesalers, APMC Vashi"
        supplier_inv = "GW-INV-2026-BASE"
        existing_supp = conn.execute(
            "SELECT id FROM supplier_ledger WHERE invoice_number = ? AND supplier_name = ?;",
            (supplier_inv, supplier_name),
        ).fetchone()

        if not existing_supp:
            # Baseline payable = (4 * 580) + (12 * 132) + (28 * 72) = 2320 + 1584 + 2016 = 5920.0
            supplier_created_at = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO supplier_ledger (
                    supplier_name, entry_type, amount, invoice_number, price_creep_flagged, created_at
                ) VALUES (?, 'INVOICE_CREDIT', 5920.0, ?, 0, ?);
                """,
                (supplier_name, supplier_inv, supplier_created_at),
            )

        # ----------------------------------------------------------------------
        # 6. Ambiguous Payments Queue (₹200 from 'Suresh')
        # ----------------------------------------------------------------------
        upi_txn = "UPI-DEMO-SURESH-200"
        existing_unmatched = conn.execute(
            "SELECT id FROM unmatched_payments_queue WHERE upi_txn_id = ?;",
            (upi_txn,),
        ).fetchone()

        suresh_patil_id = customer_id_map.get("Suresh Patil (Tailor)")
        suresh_kadam_id = customer_id_map.get("Suresh Kadam (Kirana)")

        candidates_data = [
            {
                "customer_id": suresh_patil_id,
                "name": "Suresh Patil (Tailor)",
                "phone": "+919820333444",
                "current_udhaar": 200.0,
                "last_visit": "5 days ago",
            },
            {
                "customer_id": suresh_kadam_id,
                "name": "Suresh Kadam (Kirana)",
                "phone": "+919820555666",
                "current_udhaar": 450.0,
                "last_visit": "9 days ago",
            },
        ]
        candidates_json = json.dumps(candidates_data, ensure_ascii=False)

        if not existing_unmatched:
            unmatched_created_at = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO unmatched_payments_queue (
                    upi_txn_id, amount, payer_name, payer_vpa, candidate_customers_json,
                    ambiguity_reason, status, resolved_customer_id, created_at
                ) VALUES (?, 200.0, 'Suresh', 'suresh@paytm', ?, ?, 'PENDING_REVIEW', NULL, ?);
                """,
                (
                    upi_txn,
                    candidates_json,
                    "Multiple customers named Suresh match ₹200 UPI payment",
                    unmatched_created_at,
                ),
            )

        # ----------------------------------------------------------------------
        # 7. Campaigns & Links (Boli-Baki Voice Link for Ramesh Sharma)
        # ----------------------------------------------------------------------
        campaign_slug = "paytm.me/munim-ramesh-650"
        existing_campaign = conn.execute(
            "SELECT id FROM campaigns_and_links WHERE paytm_link_slug = ?;",
            (campaign_slug,),
        ).fetchone()

        ramesh_id = customer_id_map.get("Ramesh Sharma")
        if not existing_campaign and ramesh_id:
            campaign_created_at = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO campaigns_and_links (
                    campaign_title, campaign_type, target_customer_id, language_code,
                    paytm_link_slug, amount_expected, discount_per_unit, breakeven_extra_units,
                    message_text, tts_audio_base64, clicks, conversions, revenue_collected,
                    status, created_at
                ) VALUES (?, 'UDHAAR_VOICE_LINK', ?, 'mr-IN', ?, 650.0, 0.0, 0, ?, NULL, 0, 0, 0.0, 'SENT', ?);
                """,
                (
                    "Ramesh Sharma Udhaar Recovery",
                    ramesh_id,
                    campaign_slug,
                    "Namaskar Rameshji, Ganesh Provision Store kadun 650 rupaye udhaar baki ahe.",
                    campaign_created_at,
                ),
            )

        # ----------------------------------------------------------------------
        # 8. Business Events (System Startup Event)
        # ----------------------------------------------------------------------
        existing_event = conn.execute(
            """
            SELECT id FROM business_events
            WHERE event_category = 'SYSTEM_STARTUP' AND actor = 'SYSTEM_SEEDER';
            """
        ).fetchone()

        if not existing_event:
            startup_evidence = {
                "store_name": STORE_NAME,
                "customers_seeded": len(customers_spec),
                "inventory_items_seeded": len(inventory_spec),
                "unmatched_payments_seeded": 1,
                "supplier": supplier_name,
            }
            conn.execute(
                """
                INSERT INTO business_events (
                    event_category, summary_text, evidence_json, actor, created_at
                ) VALUES ('SYSTEM_STARTUP', ?, ?, 'SYSTEM_SEEDER', ?);
                """,
                (
                    f"{STORE_NAME} demo dataset seeded successfully",
                    json.dumps(startup_evidence, ensure_ascii=False),
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

        conn.commit()

        return {
            "status": "SEEDED",
            "store_name": STORE_NAME,
            "customers_count": len(customers_spec),
            "inventory_count": len(inventory_spec),
            "customer_ids": customer_id_map,
            "inventory_ids": item_id_map,
        }

    finally:
        if should_close:
            conn.close()
