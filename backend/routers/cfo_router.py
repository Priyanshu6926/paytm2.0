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
    add_repayment_entry,
    calculate_customer_balance,
    calculate_settlement_reconciliation,
    log_business_event,
    resolve_customer_identity,
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


class ResolvePaymentRequest(BaseModel):
    queue_id: int = Field(..., description="ID of the item in unmatched_payments_queue")
    resolved_customer_id: int = Field(..., description="Chosen customer ID to credit payment to")
    merchant_notes: Optional[str] = Field(None, description="Optional merchant notes or memo")


class QRWebhookPayload(BaseModel):
    upi_txn_id: str = Field(..., description="Paytm/UPI Transaction Reference ID")
    amount: float = Field(..., gt=0, description="Amount received via QR in Rs")
    payer_name: str = Field(..., description="Customer name from bank/UPI handle")
    payer_vpa: Optional[str] = Field(None, description="Payer VPA / UPI ID")


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


# --------------------------------------------------------------------------
# 4. Ambiguous UPI Payment Queue (PRD §5.4, §7.4, D-04)
# --------------------------------------------------------------------------

@router.get("/unmatched-payments")
def get_unmatched_payments():
    """
    Retrieves all pending ambiguous payments from unmatched_payments_queue
    for merchant review per PRD §5.4 & §7.4.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, upi_txn_id, amount, payer_name, payer_vpa,
                   candidate_customers_json, ambiguity_reason, status,
                   resolved_customer_id, created_at
            FROM unmatched_payments_queue
            WHERE status = 'PENDING_REVIEW'
            ORDER BY created_at DESC;
            """
        ).fetchall()

        results = []
        for r in rows:
            try:
                candidates = json.loads(r["candidate_customers_json"] or "[]")
            except Exception:
                candidates = []

            results.append({
                "id": r["id"],
                "upi_txn_id": r["upi_txn_id"],
                "amount": float(r["amount"]),
                "payer_name": r["payer_name"],
                "payer_vpa": r["payer_vpa"],
                "candidate_customers": candidates,
                "ambiguity_reason": r["ambiguity_reason"],
                "status": r["status"],
                "resolved_customer_id": r["resolved_customer_id"],
                "created_at": r["created_at"],
            })

        return results
    finally:
        close_db_connection(conn)


@router.post("/resolve-unmatched-payment")
def resolve_unmatched_payment(req: ResolvePaymentRequest):
    """
    Resolves an ambiguous payment from unmatched_payments_queue with 1-tap:
    links transaction to the selected customer, records append-only REPAYMENT_JAMA,
    and updates customer balance deterministically per PRD §5.4, §7.4 & D-04.
    """
    conn = get_db_connection()
    try:
        # 1. Fetch target queue item
        queue_item = conn.execute(
            "SELECT * FROM unmatched_payments_queue WHERE id = ?;", (req.queue_id,)
        ).fetchone()

        if queue_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unmatched payment queue item #{req.queue_id} not found.",
            )

        if queue_item["status"] != "PENDING_REVIEW":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Queue item #{req.queue_id} is already resolved (status: {queue_item['status']}).",
            )

        # 2. Verify target customer exists
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?;", (req.resolved_customer_id,)
        ).fetchone()

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer #{req.resolved_customer_id} does not exist.",
            )

        # 3. Update queue item status to LINKED
        conn.execute(
            """
            UPDATE unmatched_payments_queue
            SET status = 'LINKED', resolved_customer_id = ?
            WHERE id = ?;
            """,
            (req.resolved_customer_id, req.queue_id),
        )

        # 4. Insert append-only repayment into ledger_entries
        repay_res = add_repayment_entry(
            conn=conn,
            customer_id=req.resolved_customer_id,
            amount=float(queue_item["amount"]),
            payment_mode="PAYTM_QR",
            provider_ref=queue_item["upi_txn_id"],
            source_utterance=f"Manual reconciliation of unmatched payment {queue_item['upi_txn_id']} by merchant",
            actor="MERCHANT_APPROVED",
        )

        # 5. Log audit trail in business_events
        summary = (
            f"Reconciled unmatched QR payment {queue_item['upi_txn_id']} "
            f"(Rs {queue_item['amount']:,.2f}) to customer #{req.resolved_customer_id} ({customer['name']})"
        )
        evidence = {
            "queue_id": req.queue_id,
            "upi_txn_id": queue_item["upi_txn_id"],
            "amount": float(queue_item["amount"]),
            "payer_name": queue_item["payer_name"],
            "payer_vpa": queue_item["payer_vpa"],
            "resolved_customer_id": req.resolved_customer_id,
            "resolved_customer_name": customer["name"],
            "merchant_notes": req.merchant_notes,
            "balance_after": repay_res["balance"]["net_outstanding_balance"],
        }

        biz_event_id = log_business_event(
            conn=conn,
            event_category="SETTLEMENT",
            summary_text=summary,
            evidence=evidence,
            actor="MERCHANT_APPROVED",
        )

        conn.commit()

        return {
            "status": "LINKED",
            "queue_id": req.queue_id,
            "resolved_customer_id": req.resolved_customer_id,
            "customer_name": customer["name"],
            "amount": float(queue_item["amount"]),
            "customer_balance_after": repay_res["balance"]["net_outstanding_balance"],
            "business_event_id": biz_event_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to resolve unmatched payment: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve unmatched payment: {exc}",
        )
    finally:
        close_db_connection(conn)


# --------------------------------------------------------------------------
# 5. Simulated Paytm QR Payment Webhook (PRD §5.4, §7.4, D-04)
# --------------------------------------------------------------------------

@router.post("/simulate-qr-webhook")
def simulate_qr_webhook(payload: QRWebhookPayload):
    """
    Ingests an incoming Paytm Soundbox / QR payment webhook.
    Applies identity resolution:
      - If unique customer match: auto-reconciles payment into ledger_entries.
      - If ambiguous match or collision: enqueues to unmatched_payments_queue for 1-tap review.
      - If unknown customer: enqueues to unmatched_payments_queue for manual merchant assignment.
    Guarded against duplicate upi_txn_id submissions per T-03-07.
    """
    conn = get_db_connection()
    try:
        # 1. Idempotency Guards (T-03-07)
        existing_ledger = conn.execute(
            "SELECT id FROM ledger_entries WHERE provider_ref = ?;", (payload.upi_txn_id,)
        ).fetchone()
        if existing_ledger is not None:
            return {
                "status": "ALREADY_PROCESSED",
                "upi_txn_id": payload.upi_txn_id,
                "message": "Transaction already processed in customer ledger.",
            }

        existing_queue = conn.execute(
            "SELECT id FROM unmatched_payments_queue WHERE upi_txn_id = ?;", (payload.upi_txn_id,)
        ).fetchone()
        if existing_queue is not None:
            return {
                "status": "ALREADY_QUEUED",
                "upi_txn_id": payload.upi_txn_id,
                "message": "Transaction is already pending review in unmatched payments queue.",
            }

        # 2. Identity Resolution
        resolution = resolve_customer_identity(conn, payload.payer_name)
        status_res = resolution.get("status")

        # 3. Handle Single Clean Match -> Auto-Reconcile
        if status_res == "EXACT_MATCH":
            cust = resolution["customer"]
            repay_res = add_repayment_entry(
                conn=conn,
                customer_id=cust["id"],
                amount=payload.amount,
                payment_mode="PAYTM_QR",
                provider_ref=payload.upi_txn_id,
                source_utterance=f"Paytm QR webhook auto-reconcile: {payload.payer_name} ({payload.upi_txn_id})",
                actor="SYSTEM_AUTO",
            )

            biz_id = log_business_event(
                conn=conn,
                event_category="SETTLEMENT",
                summary_text=f"Auto-reconciled Paytm QR payment {payload.upi_txn_id} (Rs {payload.amount:,.2f}) for {cust['name']}",
                evidence={
                    "upi_txn_id": payload.upi_txn_id,
                    "amount": payload.amount,
                    "customer_id": cust["id"],
                    "customer_name": cust["name"],
                    "balance_after": repay_res["balance"]["net_outstanding_balance"],
                },
                actor="SYSTEM_AUTO",
            )
            conn.commit()

            return {
                "status": "AUTO_RECONCILED",
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "amount": payload.amount,
                "balance_after": repay_res["balance"]["net_outstanding_balance"],
                "business_event_id": biz_id,
            }

        # 4. Handle Ambiguous Match -> Queue for Merchant Review
        elif status_res == "NEEDS_DISAMBIGUATION":
            candidates = resolution.get("candidates", [])
            ambiguity_reason = resolution.get(
                "ambiguity_reason",
                f"Multiple customers matching '{payload.payer_name}' found in shop memory",
            )
            candidates_json = json.dumps(candidates, ensure_ascii=False)

            cursor = conn.execute(
                """
                INSERT INTO unmatched_payments_queue (
                    upi_txn_id, amount, payer_name, payer_vpa, candidate_customers_json,
                    ambiguity_reason, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW');
                """,
                (
                    payload.upi_txn_id,
                    payload.amount,
                    payload.payer_name,
                    payload.payer_vpa or f"{payload.payer_name.lower().replace(' ', '')}@paytm",
                    candidates_json,
                    ambiguity_reason,
                ),
            )
            queue_id = cursor.lastrowid

            biz_id = log_business_event(
                conn=conn,
                event_category="CFO_ALERT",
                summary_text=f"Ambiguous QR payment {payload.upi_txn_id} (Rs {payload.amount:,.2f}) queued for review: {ambiguity_reason}",
                evidence={
                    "queue_id": queue_id,
                    "upi_txn_id": payload.upi_txn_id,
                    "amount": payload.amount,
                    "payer_name": payload.payer_name,
                    "candidates": candidates,
                    "ambiguity_reason": ambiguity_reason,
                },
                actor="SYSTEM_GUARD",
            )
            conn.commit()

            return {
                "status": "QUEUED_FOR_REVIEW",
                "queue_id": queue_id,
                "ambiguity_reason": ambiguity_reason,
                "candidate_count": len(candidates),
            }

        # 5. Handle Unknown Customer Match -> Queue for Manual Assignment
        else:
            ambiguity_reason = f"Payer name '{payload.payer_name}' not found in shop customer records"
            cursor = conn.execute(
                """
                INSERT INTO unmatched_payments_queue (
                    upi_txn_id, amount, payer_name, payer_vpa, candidate_customers_json,
                    ambiguity_reason, status
                ) VALUES (?, ?, ?, ?, '[]', ?, 'PENDING_REVIEW');
                """,
                (
                    payload.upi_txn_id,
                    payload.amount,
                    payload.payer_name,
                    payload.payer_vpa or f"{payload.payer_name.lower().replace(' ', '')}@paytm",
                    ambiguity_reason,
                ),
            )
            queue_id = cursor.lastrowid

            biz_id = log_business_event(
                conn=conn,
                event_category="CFO_ALERT",
                summary_text=f"Unknown payer QR payment {payload.upi_txn_id} (Rs {payload.amount:,.2f}) queued for review",
                evidence={
                    "queue_id": queue_id,
                    "upi_txn_id": payload.upi_txn_id,
                    "amount": payload.amount,
                    "payer_name": payload.payer_name,
                    "ambiguity_reason": ambiguity_reason,
                },
                actor="SYSTEM_GUARD",
            )
            conn.commit()

            return {
                "status": "QUEUED_FOR_REVIEW",
                "queue_id": queue_id,
                "ambiguity_reason": ambiguity_reason,
                "candidate_count": 0,
            }

    except Exception as exc:
        conn.rollback()
        logger.error("Failed to process simulated QR webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process QR webhook: {exc}",
        )
    finally:
        close_db_connection(conn)
