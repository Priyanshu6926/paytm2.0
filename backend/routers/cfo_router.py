"""
KiranaOS AI CFO Router mounted at /api/v1/cfo.
Implements Margin Defense & Settlement Reconciliation per PRD §5.2, §5.3, §7.2, §7.3,
D-01, D-02, D-03, and Threat Models T-03-01 to T-03-06.
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.bill_parser_service import parse_distributor_bill
from backend.services.deterministic_engine import (
    calculate_settlement_reconciliation,
    log_business_event,
)
from backend.services.sarvam_engine import synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cfo", tags=["AI CFO"])


# --------------------------------------------------------------------------
# Request & Response Pydantic Models
# --------------------------------------------------------------------------

class BillLineItem(BaseModel):
    item_id: Optional[int] = Field(None, description="Existing inventory item ID if matched")
    sku_name: str = Field(..., description="Product SKU name")
    qty: int = Field(..., description="Quantity delivered", gt=0)
    unit: Optional[str] = Field("units", description="Unit of measurement")
    unit_cost: float = Field(..., description="Wholesale unit cost in Rs", gt=0)
    line_total: float = Field(..., description="Total line cost in Rs")


class ConfirmBillRequest(BaseModel):
    invoice_number: str = Field(..., description="Wholesale invoice or bill number")
    supplier_name: str = Field(..., description="Distributor or wholesaler name")
    line_items: List[BillLineItem] = Field(..., min_length=1, description="List of invoiced items")
    invoice_total: float = Field(..., description="Total invoice amount in Rs", gt=0)
    price_creep_detected: bool = Field(False, description="Flag indicating if price hike was detected")
    update_selling_prices: Optional[Dict[str, float]] = Field(
        None, description="Optional map of SKU name or item_id to updated selling price"
    )


# --------------------------------------------------------------------------
# 1. Paytm Settlement Waterfall Explainer Endpoint (PRD §5.3, §7.3, D-03)
# --------------------------------------------------------------------------

@router.get("/settlement-explainer")
def get_settlement_explainer():
    """
    Returns deterministically reconciled daily Paytm settlement waterfall
    with synthesized Bulbul TTS Hindi audio explanation per PRD §5.3 & §7.3.
    """
    deductions = [
        {
            "type": "PAYTM_MERCHANT_LOAN_EDI",
            "label": "Paytm Business Loan Daily Installment (Loan #PTM-882)",
            "amount": 450.00,
        },
        {
            "type": "SOUNDBOX_RENTAL",
            "label": "Paytm AI Soundbox Monthly Subscription",
            "amount": 125.00,
        },
        {
            "type": "CUSTOMER_REFUND",
            "label": "Instant Refund (Txn #99102)",
            "amount": 60.00,
        },
    ]

    # Deterministic reconciliation assertion (Gross QR Rs 6,450 - Deductions Rs 635 == Net Payout Rs 5,815)
    recon = calculate_settlement_reconciliation(
        gross_qr_collections=6450.00,
        deductions=deductions,
        bank_account="State Bank of India •••• 4921",
        settlement_date="2026-11-09",
    )

    # Synthesize Bulbul v3 TTS spoken explanation in Hindi
    tts_result = synthesize_speech(
        text=recon["spoken_explanation_hi"],
        target_language_code="hi-IN",
        mock_fallback=False,
    )

    return {
        "settlement_date": recon["settlement_date"],
        "bank_account": recon["bank_account"],
        "gross_qr_collections": recon["gross_qr_collections"],
        "deductions": recon["deductions"],
        "total_deductions": recon["total_deductions"],
        "net_settled_to_bank": recon["net_settled_to_bank"],
        "verification_status": recon["verification_status"],
        "spoken_explanation_hi": recon["spoken_explanation_hi"],
        "tts_audio_base64": tts_result.get("audio_base64", ""),
    }


# --------------------------------------------------------------------------
# 2. Distributor Bill Scanning & Price Creep Proposal (PRD §5.2, §7.2, D-02)
# --------------------------------------------------------------------------

@router.post("/scan-distributor-bill")
async def scan_distributor_bill(
    request: Request,
    file: Optional[UploadFile] = File(None),
    use_demo_sample: Optional[bool] = Query(None),
):
    """
    Processes a distributor invoice either from uploaded image bytes or preset demo invoice.
    Cross-references database inventory to surface price-creep alerts (>= 2.0%) and
    outputs a proposal card with dual action preview and spoken Hindi audio.
    """
    content_type = request.headers.get("content-type", "")
    is_demo = use_demo_sample if use_demo_sample is not None else False
    image_bytes: Optional[bytes] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict) and "use_demo_sample" in body:
                is_demo = bool(body["use_demo_sample"])
        except Exception:
            pass

    if file is not None:
        image_bytes = await file.read()
    elif not is_demo and "multipart/form-data" not in content_type:
        # Default to demo sample if neither file nor flag explicitly provided
        is_demo = True

    conn = get_db_connection()
    try:
        proposal = parse_distributor_bill(
            image_bytes=image_bytes,
            use_demo_sample=is_demo or (image_bytes is None),
            conn=conn,
        )
        return proposal
    finally:
        close_db_connection(conn)


# --------------------------------------------------------------------------
# 3. Confirm Distributor Bill (Atomic Dual Write) (PRD §5.2, §7.2, D-02)
# --------------------------------------------------------------------------

@router.post("/confirm-distributor-bill")
def confirm_distributor_bill(req: ConfirmBillRequest):
    """
    Atomically updates both inventory stock and supplier payable ledger in a single
    SQLite transaction, logging a structured CFO_ALERT business event per PRD §7.2 & D-02.
    Guarded by invoice_number idempotency check to prevent duplicate credits.
    """
    conn = get_db_connection()
    try:
        # 1. Idempotency Check on invoice_number
        existing_invoice = conn.execute(
            """
            SELECT id, supplier_name, amount, created_at
            FROM supplier_ledger
            WHERE invoice_number = ? AND entry_type = 'INVOICE_CREDIT';
            """,
            (req.invoice_number,),
        ).fetchone()

        if existing_invoice is not None:
            logger.info("Invoice %s was already confirmed.", req.invoice_number)
            return {
                "status": "ALREADY_CONFIRMED",
                "invoice_number": req.invoice_number,
                "supplier_ledger_id": existing_invoice["id"],
                "message": f"Invoice {req.invoice_number} has already been confirmed and processed.",
            }

        # 2. Atomic Dual Write Transaction
        conn.execute("BEGIN TRANSACTION;")

        total_units_added = 0
        stock_event_ids: List[int] = []

        # (a) Update inventory_items & append stock_events
        for item in req.line_items:
            total_units_added += item.qty

            # Match inventory item by item_id or sku_name
            db_item = None
            if item.item_id:
                db_item = conn.execute(
                    "SELECT * FROM inventory_items WHERE id = ?;", (item.item_id,)
                ).fetchone()

            if db_item is None:
                db_item = conn.execute(
                    "SELECT * FROM inventory_items WHERE sku_name = ?;", (item.sku_name,)
                ).fetchone()

            if db_item is not None:
                target_item_id = db_item["id"]
                current_stock = int(db_item["current_stock"])
                last_cost = float(db_item["last_unit_cost"])
                selling_price = float(db_item["selling_price"])

                # Determine if selling price is updated
                new_selling_price = selling_price
                if req.update_selling_prices:
                    if str(target_item_id) in req.update_selling_prices:
                        new_selling_price = float(req.update_selling_prices[str(target_item_id)])
                    elif item.sku_name in req.update_selling_prices:
                        new_selling_price = float(req.update_selling_prices[item.sku_name])

                conn.execute(
                    """
                    UPDATE inventory_items
                    SET current_stock = ?,
                        previous_unit_cost = ?,
                        last_unit_cost = ?,
                        selling_price = ?,
                        last_restocked_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (
                        current_stock + item.qty,
                        last_cost,
                        item.unit_cost,
                        new_selling_price,
                        target_item_id,
                    ),
                )
            else:
                # Insert newly encountered SKU
                cursor = conn.execute(
                    """
                    INSERT INTO inventory_items (
                        sku_name, current_stock, unit, last_unit_cost, previous_unit_cost, selling_price, supplier_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item.sku_name,
                        item.qty,
                        item.unit or "units",
                        item.unit_cost,
                        item.unit_cost,
                        round(item.unit_cost * 1.15, 2),  # Default 15% markup if unknown
                        req.supplier_name,
                    ),
                )
                target_item_id = cursor.lastrowid

            # Append stock_events row (append-only)
            cursor_se = conn.execute(
                """
                INSERT INTO stock_events (
                    item_id, event_type, quantity_delta, unit_cost, invoice_number, raw_transcript
                ) VALUES (?, 'INWARD_INVOICE', ?, ?, ?, ?);
                """,
                (
                    target_item_id,
                    item.qty,
                    item.unit_cost,
                    req.invoice_number,
                    f"Distributor bill confirmation: {req.invoice_number}",
                ),
            )
            stock_event_ids.append(cursor_se.lastrowid)

        # (b) Record supplier_ledger entry (append-only)
        cursor_sl = conn.execute(
            """
            INSERT INTO supplier_ledger (
                supplier_name, entry_type, amount, invoice_number, price_creep_flagged
            ) VALUES (?, 'INVOICE_CREDIT', ?, ?, ?);
            """,
            (
                req.supplier_name,
                req.invoice_total,
                req.invoice_number,
                1 if req.price_creep_detected else 0,
            ),
        )
        supplier_ledger_id = cursor_sl.lastrowid

        # (c) Append business_events audit trail (append-only)
        summary_text = (
            f"Confirmed distributor bill {req.invoice_number} from {req.supplier_name}: "
            f"+{total_units_added} units added to stock, "
            f"Rs {req.invoice_total:,.2f} recorded in supplier khata"
        )
        evidence = {
            "invoice_number": req.invoice_number,
            "supplier_name": req.supplier_name,
            "invoice_total": req.invoice_total,
            "total_units_added": total_units_added,
            "line_items": [i.model_dump() for i in req.line_items],
            "price_creep_detected": req.price_creep_detected,
            "supplier_ledger_id": supplier_ledger_id,
            "stock_event_ids": stock_event_ids,
        }

        business_event_id = log_business_event(
            conn=conn,
            event_category="CFO_ALERT",
            summary_text=summary_text,
            evidence=evidence,
            actor="MERCHANT_APPROVED",
        )

        conn.commit()

        return {
            "status": "CONFIRMED",
            "invoice_number": req.invoice_number,
            "stock_events_created": len(stock_event_ids),
            "supplier_ledger_id": supplier_ledger_id,
            "business_event_id": business_event_id,
            "message": "Stock and supplier khata updated atomically.",
        }

    except Exception as exc:
        conn.rollback()
        logger.error("Transaction failed during bill confirmation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm distributor bill: {exc}",
        )
    finally:
        close_db_connection(conn)
