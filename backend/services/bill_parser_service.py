"""
Distributor Bill OCR & Price-Creep Detection Service.
Adheres to the Law of Demo-Day Survivability (PRD §2, §7.2, D-02) and Threat Model T-03-01.
Integrates Sarvam Vision OCR with a 6.0-second timeout, falling back gracefully to
high-fidelity offline invoices (Gupta Wholesalers GW-2026-994).
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

import httpx

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import calculate_price_creep
from backend.services.sarvam_engine import synthesize_speech

logger = logging.getLogger(__name__)

# Constants
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_OCR_URL = os.getenv("SARVAM_OCR_URL", "https://api.sarvam.ai/document/ocr")
REQUEST_TIMEOUT_SECONDS = 6.0
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB limit per threat model T-03-01

# Authoritative Demo Preset Invoice (Gupta Wholesalers, APMC Vashi) per PRD §7.2
DEMO_PRESET_INVOICE = {
    "supplier_name": "Gupta Wholesalers, APMC Vashi",
    "invoice_number": "GW-2026-994",
    "invoice_date": "2026-11-10",
    "line_items": [
        {
            "sku_name": "Fortune Sunlite Oil 1L",
            "qty": 20,
            "unit": "liters",
            "unit_cost": 142.00,
            "line_total": 2840.00,
        },
        {
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
}


def _match_inventory_item(sku_name: str, db_items: List[sqlite3.Row]) -> Optional[sqlite3.Row]:
    """Finds matching inventory item by SKU name or local aliases."""
    clean_sku = sku_name.lower().strip()

    # 1. Exact or substring match on sku_name
    for item in db_items:
        db_name = (item["sku_name"] or "").lower().strip()
        if clean_sku == db_name or clean_sku in db_name or db_name in clean_sku:
            return item

    # 2. Local aliases match
    for item in db_items:
        aliases_raw = item["local_aliases"]
        if not aliases_raw:
            continue
        try:
            aliases = json.loads(aliases_raw)
        except Exception:
            aliases = []
        for alias in aliases:
            a_lower = str(alias).lower().strip()
            if clean_sku == a_lower or clean_sku in a_lower or a_lower in clean_sku:
                return item

    return None


def parse_distributor_bill(
    image_bytes: Optional[bytes] = None,
    use_demo_sample: bool = False,
    conn: Optional[sqlite3.Connection] = None,
    mock_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Parses a distributor invoice from raw image bytes or preset sample per PRD §7.2 & D-02.
    Queries SQLite inventory to identify price creep and outputs a structured proposal card.
    """
    fallback_used = False
    raw_invoice_data = None

    # Handle file size safety guardrail (T-03-01)
    if image_bytes is not None and len(image_bytes) > MAX_IMAGE_BYTES:
        logger.warning("Uploaded invoice image exceeds 10MB (%d bytes). Using fallback.", len(image_bytes))
        fallback_used = True

    # 1. OCR Processing: attempt external Sarvam Vision OCR if image provided and not mock_fallback
    if image_bytes and not mock_fallback and not fallback_used:
        api_key = os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)
        if api_key:
            try:
                headers = {"api-subscription-key": api_key}
                files = {"file": ("invoice.jpg", image_bytes, "image/jpeg")}
                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = client.post(SARVAM_OCR_URL, headers=headers, files=files)
                    if response.status_code == 200:
                        ocr_json = response.json()
                        # If external OCR yields valid structured items, parse them
                        if "line_items" in ocr_json and ocr_json["line_items"]:
                            raw_invoice_data = ocr_json
                        else:
                            fallback_used = True
                    else:
                        fallback_used = True
            except Exception as exc:
                logger.warning("Sarvam OCR call failed or timed out: %s. Using offline fallback.", exc)
                fallback_used = True
        else:
            fallback_used = True
    else:
        fallback_used = True

    # 2. Offline Fallback / Demo Preset Selection
    if raw_invoice_data is None:
        raw_invoice_data = DEMO_PRESET_INVOICE
        fallback_used = True

    supplier_name = raw_invoice_data.get("supplier_name", "Gupta Wholesalers, APMC Vashi")
    invoice_number = raw_invoice_data.get("invoice_number", "GW-2026-994")
    invoice_date = raw_invoice_data.get("invoice_date", "2026-11-10")
    raw_line_items = raw_invoice_data.get("line_items", [])

    # 3. Query SQLite inventory to match items and compute price creep
    should_close_conn = False
    if conn is None:
        conn = get_db_connection()
        should_close_conn = True

    try:
        db_items = conn.execute(
            """
            SELECT id, sku_name, local_aliases, last_unit_cost, previous_unit_cost, selling_price
            FROM inventory_items;
            """
        ).fetchall()

        enriched_line_items: List[Dict[str, Any]] = []
        price_creep_alerts: List[Dict[str, Any]] = []
        computed_invoice_total = 0.0
        total_units = 0

        for line in raw_line_items:
            sku_name = line.get("sku_name", "")
            qty = int(line.get("qty", 0))
            unit = line.get("unit", "units")
            new_unit_cost = round(float(line.get("unit_cost", 0.0)), 2)
            line_total = round(float(line.get("line_total", qty * new_unit_cost)), 2)
            computed_invoice_total += line_total
            total_units += qty

            matched_item = _match_inventory_item(sku_name, db_items)
            item_id = matched_item["id"] if matched_item else None

            if matched_item:
                last_cost = round(float(matched_item["last_unit_cost"]), 2)
                selling_price = round(float(matched_item["selling_price"]), 2)

                creep_calc = calculate_price_creep(
                    previous_unit_cost=last_cost,
                    new_unit_cost=new_unit_cost,
                    selling_price=selling_price,
                    sku_name=matched_item["sku_name"],
                    supplier_name=supplier_name,
                )

                if creep_calc["price_creep_flagged"]:
                    price_creep_alerts.append({
                        "sku_name": matched_item["sku_name"],
                        "previous_unit_cost": last_cost,
                        "new_unit_cost": new_unit_cost,
                        "creep_percentage": creep_calc["creep_percentage"],
                        "margin_erosion_per_unit": creep_calc["margin_erosion_per_unit"],
                        "recommended_new_mrp": creep_calc["recommended_new_mrp"],
                        "alert_hi": creep_calc["alert_hi"],
                    })

            enriched_line_items.append({
                "item_id": item_id,
                "sku_name": sku_name,
                "qty": qty,
                "unit": unit,
                "unit_cost": new_unit_cost,
                "line_total": line_total,
            })

        invoice_total = round(
            float(raw_invoice_data.get("invoice_total", computed_invoice_total)), 2
        )

        # 4. Construct dual action preview message per PRD §7.2
        supplier_short = supplier_name.split(",")[0].strip()
        dual_action_preview = (
            f"Confirming adds +{total_units} units to Inventory AND "
            f"records Rs {invoice_total:,.0f} payable in {supplier_short} Khata."
        )

        # 5. Synthesize speech alert for the primary price creep warning
        if price_creep_alerts:
            alert_text = price_creep_alerts[0]["alert_hi"]
        else:
            alert_text = f"Bill scan safal raha. Kul rashi Rs {invoice_total:,.0f} hai."

        tts_result = synthesize_speech(
            text=alert_text,
            target_language_code="hi-IN",
            mock_fallback=mock_fallback or fallback_used,
        )
        tts_audio_base64 = tts_result.get("audio_base64", "")

        return {
            "status": "PROPOSAL",
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "invoice_total": invoice_total,
            "price_creep_alerts": price_creep_alerts,
            "line_items": enriched_line_items,
            "dual_action_preview": dual_action_preview,
            "tts_audio_base64": tts_audio_base64,
            "fallback_used": fallback_used,
        }

    finally:
        if should_close_conn:
            close_db_connection(conn)
