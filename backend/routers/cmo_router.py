"""
KiranaOS AI CMO Router mounted at /api/v1/cmo.
Implements Boli-Baki Multilingual Voice Udhaar Recovery with Soundbox payment webhook clearing,
Dead-Stock Break-Even Studio, 60-Second Dukaan Closing Ritual, and Handwritten Bahi-Khata
onboarding per PRD §5.4, §5.5, §7.4, §7.5, §7.6, FR-10, and Threat Models T-04-04 to T-04-SC.
"""

from datetime import datetime
import json
import logging
import math
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.bahi_khata_parser_service import (
    _normalize_phone,
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
from backend.services.sarvam_engine import synthesize_speech, translate_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cmo", tags=["AI CMO"])


# --------------------------------------------------------------------------
# Request Models
# --------------------------------------------------------------------------


class BoliBakiRequest(BaseModel):
    customer_id: int
    target_language: Optional[str] = None


class DeadStockCampaignRequest(BaseModel):
    item_id: int
    proposed_discount_rupees: float = Field(..., ge=0)
    usual_daily_sales: Optional[int] = Field(None, gt=0)


class SimulatePromoClickRequest(BaseModel):
    converted: Optional[bool] = None


class BahiKhataConfirmEntry(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    preferred_language: str = "hi-IN"
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None


class ConfirmBahiKhataRequest(BaseModel):
    batch_ref: Optional[str] = None
    entries: List[BahiKhataConfirmEntry] = Field(..., min_length=1)


# --------------------------------------------------------------------------
# Internal Helpers
# --------------------------------------------------------------------------


def _compute_days_since(timestamp_str: Optional[str]) -> int:
    """Safely computes elapsed integer days since an ISO/SQLite timestamp string."""
    if not timestamp_str:
        return 0
    cleaned = str(timestamp_str).replace("T", " ").split(".")[0].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return max(0, (datetime.now() - dt).days)
        except ValueError:
            continue
    return 0


def _format_amount_disp(amount: float) -> str:
    """Formats rupee amounts cleanly without trailing .00 for whole integers."""
    rounded = round(float(amount), 2)
    return f"{int(rounded)}" if rounded == int(rounded) else f"{rounded:.2f}"


def _format_localized_reminder(
    first_name: str, amt_disp: str, lang: str, source_msg: str, raw_translated: str
) -> str:
    """
    If offline translation returned an unmapped '[lang] ...' placeholder for dynamic
    names/amounts, build a clean localized reminder template without the bracket prefix.
    """
    if not raw_translated.startswith(f"[{lang}]"):
        return raw_translated

    if lang == "mr-IN":
        return (
            f"Namaskar {first_name} ji, tumche kirana dukanache {amt_disp} rupaye udhari baki aahe. "
            f"Krupaya dilelya Paytm link varun paise bhara."
        )
    if lang == "en-IN":
        return (
            f"Hello {first_name} ji, your grocery store balance of Rs {amt_disp} is due. "
            f"Please pay via the provided Paytm link."
        )
    return source_msg


def _strip_paytm_prefix(paytm_link_slug: str) -> str:
    """Extracts the short slug from 'paytm.me/<short_slug>'."""
    prefix = "paytm.me/"
    if paytm_link_slug.startswith(prefix):
        return paytm_link_slug[len(prefix):]
    return paytm_link_slug


def _derive_sku_slug_token(sku_name: str, item_id: int) -> str:
    """
    Extracts a concise lowercase slug token for promo links (e.g., 'bhujia' for
    'Haldiram Aloo Bhujia 400g').
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", sku_name or "")
    # Filter out trailing packaging size tokens such as 400g, 1L, 70g, 500ml, 1kg
    word_tokens = [
        t.lower()
        for t in tokens
        if not re.fullmatch(r"\d+(?:g|kg|ml|l|pcs|pkts?)?", t.lower())
    ]
    if word_tokens:
        return word_tokens[-1]
    return f"item-{item_id}"


def _format_attributed_link(row: Any) -> Dict[str, Any]:
    """Shapes a campaigns_and_links row into the PRD §7.5 attributed link object."""
    short_slug = _strip_paytm_prefix(row["paytm_link_slug"])
    conversions = int(row["conversions"] or 0)
    revenue = round(float(row["revenue_collected"] or 0.0), 2)
    return {
        "language": row["language_code"],
        "link": row["paytm_link_slug"],
        "slug": short_slug,
        "clicks": int(row["clicks"] or 0),
        "redemptions": conversions,
        "conversions": conversions,
        "revenue": revenue,
        "revenue_collected": revenue,
        "message_text": row["message_text"] or "",
        "simulate_click_endpoint": f"/api/v1/cmo/simulate-promo-click/{short_slug}",
    }


def _format_promo_offer_text(
    sku_name: str, discounted_price: float, discount_rupees: float, lang: str
) -> str:
    """Translates or formats a localized dead-stock promo offer message."""
    disc_disp = _format_amount_disp(discounted_price)
    save_disp = _format_amount_disp(discount_rupees)
    source_msg = (
        f"Special offer! {sku_name} ab sirf Rs {disc_disp} mein "
        f"(Rs {save_disp} ki bachat)."
    )
    trans_res = translate_text(
        text=source_msg,
        source_language_code="hi-IN",
        target_language_code=lang,
    )
    raw = trans_res.get("translated_text", source_msg)
    if raw.startswith(f"[{lang}]"):
        if lang == "mr-IN":
            return (
                f"Khas offer! {sku_name} aata fakt Rs {disc_disp} madhe "
                f"(Rs {save_disp} bachat)."
            )
        return source_msg
    return raw


# --------------------------------------------------------------------------
# 1. Boli-Baki Overdue Debtors & Voice Udhaar Recovery (PRD §7.4)
# --------------------------------------------------------------------------


@router.get("/overdue-debtors")
def get_overdue_debtors():
    """
    Surfaces customers with deterministic outstanding balance > Rs 0 and
    overdue_days > 10 days, attaching any existing UDHAAR_VOICE_LINK campaign.
    """
    conn = get_db_connection()
    try:
        customers = conn.execute(
            """
            SELECT id, name, phone, preferred_language, regular_cycle_days, last_visit_date
            FROM customers;
            """
        ).fetchall()

        debtors = []
        for cust in customers:
            balance = calculate_customer_balance(conn, cust["id"])
            outstanding = float(balance["net_outstanding_balance"])
            overdue_days = _compute_days_since(cust["last_visit_date"])

            if outstanding <= 0 or overdue_days <= 10:
                continue

            campaign_row = conn.execute(
                """
                SELECT id, campaign_title, language_code, paytm_link_slug, amount_expected,
                       message_text, clicks, conversions, revenue_collected, status, created_at
                FROM campaigns_and_links
                WHERE target_customer_id = ? AND campaign_type = 'UDHAAR_VOICE_LINK'
                ORDER BY id DESC LIMIT 1;
                """,
                (cust["id"],),
            ).fetchone()

            active_campaign: Optional[Dict[str, Any]] = None
            if campaign_row is not None:
                short_slug = _strip_paytm_prefix(campaign_row["paytm_link_slug"])
                active_campaign = {
                    "id": campaign_row["id"],
                    "campaign_title": campaign_row["campaign_title"],
                    "language_code": campaign_row["language_code"],
                    "paytm_link_slug": campaign_row["paytm_link_slug"],
                    "paytm_payment_link": f"https://{campaign_row['paytm_link_slug']}",
                    "link_slug": short_slug,
                    "amount_expected": float(campaign_row["amount_expected"] or outstanding),
                    "status": campaign_row["status"],
                    "clicks": int(campaign_row["clicks"] or 0),
                    "conversions": int(campaign_row["conversions"] or 0),
                    "revenue_collected": float(campaign_row["revenue_collected"] or 0.0),
                    "simulate_webhook_endpoint": f"/api/v1/cmo/simulate-link-paid/{short_slug}",
                }

            debtors.append(
                {
                    "customer_id": cust["id"],
                    "customer_name": cust["name"],
                    "phone": cust["phone"],
                    "preferred_language": cust["preferred_language"] or "hi-IN",
                    "overdue_days": overdue_days,
                    "outstanding_amount": outstanding,
                    "last_visit_date": cust["last_visit_date"],
                    "active_campaign": active_campaign,
                }
            )

        debtors.sort(key=lambda d: d["overdue_days"], reverse=True)
        return {
            "overdue_debtors": debtors,
            "count": len(debtors),
        }
    finally:
        close_db_connection(conn)


@router.post("/boli-baki-recovery")
def create_boli_baki_recovery(req: BoliBakiRequest):
    """
    Translates a polite udhaar reminder into the customer's preferred_language via
    Sarvam Translate, synthesizes a Bulbul v3 voice note, and persists/updates
    a tracked Paytm link in campaigns_and_links.
    """
    conn = get_db_connection()
    try:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?;", (req.customer_id,)
        ).fetchone()
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer #{req.customer_id} not found.",
            )

        balance = calculate_customer_balance(conn, req.customer_id)
        outstanding_amount = round(float(balance["net_outstanding_balance"]), 2)
        if outstanding_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer {customer['name']} has no outstanding udhaar balance.",
            )

        lang = req.target_language or customer["preferred_language"] or "hi-IN"
        overdue_days = _compute_days_since(customer["last_visit_date"])
        amt_disp = _format_amount_disp(outstanding_amount)
        first_name = (customer["name"] or "Customer").strip().split()[0]

        source_msg = (
            f"Namaste {first_name} ji, aapka kirana dukan ka {amt_disp} rupaye udhaar baki hai. "
            f"Kripya diye gaye Paytm link se bhugtan karein."
        )
        trans_res = translate_text(
            text=source_msg,
            source_language_code="hi-IN",
            target_language_code=lang,
        )
        translated_message = _format_localized_reminder(
            first_name=first_name,
            amt_disp=amt_disp,
            lang=lang,
            source_msg=source_msg,
            raw_translated=trans_res.get("translated_text", source_msg),
        )

        tts_res = synthesize_speech(
            text=translated_message,
            target_language_code=lang,
        )
        audio_b64 = tts_res.get("audio_base64", "")

        existing = conn.execute(
            """
            SELECT * FROM campaigns_and_links
            WHERE target_customer_id = ?
              AND campaign_type = 'UDHAAR_VOICE_LINK'
              AND status = 'SENT'
            ORDER BY id DESC LIMIT 1;
            """,
            (req.customer_id,),
        ).fetchone()

        if existing is not None:
            paytm_link_slug = existing["paytm_link_slug"]
            conn.execute(
                """
                UPDATE campaigns_and_links
                SET language_code = ?,
                    amount_expected = ?,
                    message_text = ?,
                    tts_audio_base64 = ?
                WHERE id = ?;
                """,
                (lang, outstanding_amount, translated_message, audio_b64, existing["id"]),
            )
            campaign_id = existing["id"]
        else:
            slug_name = re.sub(r"[^a-z0-9]+", "-", first_name.lower()).strip("-") or f"cust-{req.customer_id}"
            base_slug = f"paytm.me/munim-{slug_name}-{int(round(outstanding_amount))}"
            paytm_link_slug = base_slug
            while conn.execute(
                "SELECT id FROM campaigns_and_links WHERE paytm_link_slug = ?;",
                (paytm_link_slug,),
            ).fetchone():
                paytm_link_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

            cursor = conn.execute(
                """
                INSERT INTO campaigns_and_links (
                    campaign_title, campaign_type, target_customer_id, language_code,
                    paytm_link_slug, amount_expected, discount_per_unit, breakeven_extra_units,
                    message_text, tts_audio_base64, clicks, conversions, revenue_collected, status
                ) VALUES (?, 'UDHAAR_VOICE_LINK', ?, ?, ?, ?, 0.0, 0, ?, ?, 0, 0, 0.0, 'SENT');
                """,
                (
                    f"{customer['name']} Udhaar Recovery",
                    req.customer_id,
                    lang,
                    paytm_link_slug,
                    outstanding_amount,
                    translated_message,
                    audio_b64,
                ),
            )
            campaign_id = cursor.lastrowid

        short_slug = _strip_paytm_prefix(paytm_link_slug)
        log_business_event(
            conn=conn,
            event_category="CMO_GROWTH",
            summary_text=(
                f"Prepared Boli-Baki voice reminder ({lang}) for {customer['name']} "
                f"for Rs {amt_disp} ({paytm_link_slug})"
            ),
            evidence={
                "campaign_id": campaign_id,
                "customer_id": req.customer_id,
                "customer_name": customer["name"],
                "language_code": lang,
                "outstanding_amount": outstanding_amount,
                "overdue_days": overdue_days,
                "paytm_link_slug": paytm_link_slug,
                "fallback_used": bool(trans_res.get("fallback_used") or tts_res.get("fallback_used")),
            },
            actor="MERCHANT_APPROVED",
            commit=False,
        )
        conn.commit()

        return {
            "customer_id": req.customer_id,
            "customer_name": customer["name"],
            "preferred_language": lang,
            "overdue_days": overdue_days,
            "outstanding_amount": outstanding_amount,
            "paytm_payment_link": f"https://{paytm_link_slug}",
            "link_slug": short_slug,
            "translated_message": translated_message,
            "tts_audio_base64": audio_b64,
            "fallback_used": bool(trans_res.get("fallback_used") or tts_res.get("fallback_used")),
            "simulate_webhook_endpoint": f"/api/v1/cmo/simulate-link-paid/{short_slug}",
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to generate Boli-Baki recovery: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Boli-Baki voice recovery.",
        )
    finally:
        close_db_connection(conn)


@router.post("/simulate-link-paid/{slug}")
def simulate_link_paid(slug: str):
    """
    Simulates instant customer payment via tracked Paytm link:
      - Enforces idempotency on campaign status == 'PAID' and unique provider_ref.
      - Atomically appends REPAYMENT_JAMA (payment_mode='PAYTM_LINK'), updates campaign metrics,
        and logs CMO_GROWTH event in business_events.
      - Returns live Soundbox chime ("Paytm par {amount} rupaye prapt hue").
    """
    conn = get_db_connection()
    try:
        normalized_slug = _strip_paytm_prefix(slug.strip())
        campaign = conn.execute(
            """
            SELECT * FROM campaigns_and_links
            WHERE paytm_link_slug = ? OR paytm_link_slug = ?;
            """,
            (slug, f"paytm.me/{normalized_slug}"),
        ).fetchone()

        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment link '{slug}' not found.",
            )

        if campaign["status"] == "PAID":
            return {
                "status": "ALREADY_PAID",
                "slug": normalized_slug,
                "message": "Payment link already settled.",
            }

        target_customer_id = campaign["target_customer_id"]
        if not target_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment link has no target customer.",
            )

        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?;", (target_customer_id,)
        ).fetchone()
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer #{target_customer_id} not found.",
            )

        provider_ref = f"PAYTM-LINK-{campaign['id']}-{normalized_slug}"
        existing_repayment = conn.execute(
            "SELECT id FROM ledger_entries WHERE provider_ref = ?;",
            (provider_ref,),
        ).fetchone()
        if existing_repayment is not None:
            return {
                "status": "ALREADY_PAID",
                "slug": normalized_slug,
                "message": "Payment link already settled.",
            }

        current_balance = calculate_customer_balance(conn, target_customer_id)
        raw_amount = campaign["amount_expected"]
        if raw_amount is None or float(raw_amount) <= 0:
            raw_amount = current_balance["net_outstanding_balance"]
        amount_paid = round(float(raw_amount), 2)

        if amount_paid <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No positive amount due for settlement.",
            )

        conn.execute("BEGIN TRANSACTION;")
        repayment = add_repayment_entry(
            conn=conn,
            customer_id=target_customer_id,
            amount=amount_paid,
            payment_mode="PAYTM_LINK",
            provider_ref=provider_ref,
            source_utterance=f"Boli-Baki payment via {campaign['paytm_link_slug']}",
            actor="SYSTEM_AUTO",
            commit=False,
        )
        balance_after = float(repayment["balance"]["net_outstanding_balance"])

        conn.execute(
            """
            UPDATE campaigns_and_links
            SET status = 'PAID',
                clicks = clicks + 1,
                conversions = conversions + 1,
                revenue_collected = ROUND(revenue_collected + ?, 2)
            WHERE id = ?;
            """,
            (amount_paid, campaign["id"]),
        )

        amt_text = _format_amount_disp(amount_paid)
        biz_event_id = log_business_event(
            conn=conn,
            event_category="CMO_GROWTH",
            summary_text=(
                f"Boli-Baki link {campaign['paytm_link_slug']} paid by {customer['name']}: "
                f"Rs {amt_text} recovered (balance after: Rs {balance_after:.2f})"
            ),
            evidence={
                "campaign_id": campaign["id"],
                "slug": normalized_slug,
                "paytm_link_slug": campaign["paytm_link_slug"],
                "customer_id": target_customer_id,
                "customer_name": customer["name"],
                "amount_paid": amount_paid,
                "balance_after": balance_after,
                "provider_ref": provider_ref,
                "ledger_entry_id": repayment["entry_id"],
            },
            actor="SYSTEM_AUTO",
            commit=False,
        )
        conn.commit()

        soundbox_announcement = f"Paytm par {amt_text} rupaye prapt hue"
        soundbox_tts = synthesize_speech(
            text=soundbox_announcement,
            target_language_code="hi-IN",
        )

        return {
            "status": "PAID",
            "slug": normalized_slug,
            "customer_id": target_customer_id,
            "customer_name": customer["name"],
            "amount_paid": amount_paid,
            "balance_after": balance_after,
            "soundbox_announcement": soundbox_announcement,
            "soundbox_audio_base64": soundbox_tts.get("audio_base64", ""),
            "business_event_id": biz_event_id,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to simulate link payment: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process simulated link payment.",
        )
    finally:
        close_db_connection(conn)


# --------------------------------------------------------------------------
# 2. Dead-Stock Break-Even Studio & Per-Language Attribution (PRD §7.5)
# --------------------------------------------------------------------------


@router.get("/dead-stock")
def get_dead_stock():
    """
    Lists inventory items unsold > 15 days with current_stock > 0, including
    deterministic unit margin and any existing per-language DEAD_STOCK_BUNDLE links.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, sku_name, category, current_stock, unit, last_unit_cost,
                   selling_price, avg_daily_burn, supplier_name, last_sold_at
            FROM inventory_items
            WHERE current_stock > 0 AND last_sold_at IS NOT NULL;
            """
        ).fetchall()

        dead_stock_items: List[Dict[str, Any]] = []
        for item in rows:
            days_unsold = _compute_days_since(item["last_sold_at"])
            if days_unsold <= 15:
                continue

            unit_cost = round(float(item["last_unit_cost"]), 2)
            selling_price = round(float(item["selling_price"]), 2)
            current_margin = round(selling_price - unit_cost, 2)
            campaign_title = f"Dead-Stock Promo: {item['sku_name']}"

            link_rows = conn.execute(
                """
                SELECT * FROM campaigns_and_links
                WHERE campaign_type = 'DEAD_STOCK_BUNDLE' AND campaign_title = ?
                ORDER BY CASE WHEN language_code = 'mr-IN' THEN 0 ELSE 1 END, id ASC;
                """,
                (campaign_title,),
            ).fetchall()

            dead_stock_items.append(
                {
                    "item_id": item["id"],
                    "sku_name": item["sku_name"],
                    "category": item["category"],
                    "current_stock": int(item["current_stock"]),
                    "unit": item["unit"],
                    "unit_cost": unit_cost,
                    "selling_price": selling_price,
                    "current_margin_per_unit": current_margin,
                    "days_unsold": days_unsold,
                    "last_sold_at": item["last_sold_at"],
                    "supplier_name": item["supplier_name"],
                    "attributed_links": [_format_attributed_link(r) for r in link_rows],
                }
            )

        dead_stock_items.sort(key=lambda x: x["days_unsold"], reverse=True)
        return {
            "dead_stock_items": dead_stock_items,
            "count": len(dead_stock_items),
        }
    finally:
        close_db_connection(conn)


@router.post("/dead-stock-campaign")
def create_dead_stock_campaign(req: DeadStockCampaignRequest):
    """
    Validates proposed dead-stock discount against wholesale unit_cost via deterministic
    calculate_breakeven_offer. Blocks loss-making discounts with OFFER_BLOCKED_LOSS_MAKING,
    or creates/updates idempotent mr-IN and hi-IN promo links preserving click/conversion metrics.
    """
    if not math.isfinite(req.proposed_discount_rupees):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="proposed_discount_rupees must be finite.",
        )

    conn = get_db_connection()
    try:
        item = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?;", (req.item_id,)
        ).fetchone()
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item #{req.item_id} not found.",
            )

        unit_cost = round(float(item["last_unit_cost"]), 2)
        selling_price = round(float(item["selling_price"]), 2)
        days_unsold = _compute_days_since(item["last_sold_at"])

        if req.usual_daily_sales is not None:
            base_daily_sales = int(req.usual_daily_sales)
        elif float(item["avg_daily_burn"] or 0) >= 1:
            base_daily_sales = int(item["avg_daily_burn"])
        else:
            base_daily_sales = 4

        calc = calculate_breakeven_offer(
            unit_cost=unit_cost,
            selling_price=selling_price,
            usual_daily_volume=base_daily_sales,
            proposed_discount=req.proposed_discount_rupees,
            sku_name=item["sku_name"],
        )

        math_audit = {
            "old_margin_per_unit": calc["old_margin_per_unit"],
            "new_margin_per_unit": calc["new_margin_per_unit"],
            "usual_daily_sales": calc["usual_daily_sales"],
            "breakeven_daily_sales_needed": calc["breakeven_daily_sales_needed"],
            "extra_units_needed_per_day": calc["extra_units_needed_per_day"],
            "verdict": calc["verdict"],
        }

        if calc["status"] == "OFFER_BLOCKED_LOSS_MAKING":
            log_business_event(
                conn=conn,
                event_category="CMO_GROWTH",
                summary_text=(
                    f"Blocked loss-making promo on {item['sku_name']}: "
                    f"Rs {_format_amount_disp(req.proposed_discount_rupees)} discount violates wholesale cost Rs {unit_cost:g}"
                ),
                evidence={
                    "status": "OFFER_BLOCKED_LOSS_MAKING",
                    "item_id": item["id"],
                    "sku_name": item["sku_name"],
                    "unit_cost": unit_cost,
                    "selling_price": selling_price,
                    "proposed_discount": req.proposed_discount_rupees,
                    "math_audit": math_audit,
                    "reason": calc["reason"],
                },
                actor="SYSTEM_GUARD",
                commit=True,
            )
            return {
                "status": "OFFER_BLOCKED_LOSS_MAKING",
                "allowed": False,
                "item_id": item["id"],
                "sku_name": item["sku_name"],
                "days_unsold": days_unsold,
                "current_stock": int(item["current_stock"]),
                "unit_cost": unit_cost,
                "selling_price": selling_price,
                "proposed_discount": round(float(req.proposed_discount_rupees), 2),
                "reason": calc["reason"],
                "math_audit": math_audit,
                "attributed_links": [],
            }

        discounted_price = calc["discounted_price"]
        campaign_title = f"Dead-Stock Promo: {item['sku_name']}"
        sku_token = _derive_sku_slug_token(item["sku_name"], item["id"])

        conn.execute("BEGIN TRANSACTION;")
        target_langs = [("mr-IN", "mr"), ("hi-IN", "hi")]
        for lang_code, lang_short in target_langs:
            candidate_slug = f"paytm.me/promo-{lang_short}-{sku_token}"
            existing_row = conn.execute(
                "SELECT * FROM campaigns_and_links WHERE paytm_link_slug = ?;",
                (candidate_slug,),
            ).fetchone()

            if existing_row is not None and existing_row["campaign_title"] != campaign_title:
                candidate_slug = f"paytm.me/promo-{lang_short}-{sku_token}-{item['id']}"
                existing_row = conn.execute(
                    "SELECT * FROM campaigns_and_links WHERE paytm_link_slug = ?;",
                    (candidate_slug,),
                ).fetchone()

            localized_offer = _format_promo_offer_text(
                sku_name=item["sku_name"],
                discounted_price=discounted_price,
                discount_rupees=req.proposed_discount_rupees,
                lang=lang_code,
            )

            if existing_row is not None:
                # Preserve existing clicks, conversions, and revenue_collected across re-calls
                conn.execute(
                    """
                    UPDATE campaigns_and_links
                    SET amount_expected = ?,
                        discount_per_unit = ?,
                        breakeven_extra_units = ?,
                        message_text = ?
                    WHERE id = ?;
                    """,
                    (
                        discounted_price,
                        round(float(req.proposed_discount_rupees), 2),
                        int(calc["extra_units_needed_per_day"] or 0),
                        localized_offer,
                        existing_row["id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO campaigns_and_links (
                        campaign_title, campaign_type, target_customer_id, language_code,
                        paytm_link_slug, amount_expected, discount_per_unit, breakeven_extra_units,
                        message_text, tts_audio_base64, clicks, conversions, revenue_collected, status
                    ) VALUES (?, 'DEAD_STOCK_BUNDLE', NULL, ?, ?, ?, ?, ?, ?, NULL, 0, 0, 0.0, 'SENT');
                    """,
                    (
                        campaign_title,
                        lang_code,
                        candidate_slug,
                        discounted_price,
                        round(float(req.proposed_discount_rupees), 2),
                        int(calc["extra_units_needed_per_day"] or 0),
                        localized_offer,
                    ),
                )

        link_rows = conn.execute(
            """
            SELECT * FROM campaigns_and_links
            WHERE campaign_type = 'DEAD_STOCK_BUNDLE' AND campaign_title = ?
            ORDER BY CASE WHEN language_code = 'mr-IN' THEN 0 ELSE 1 END, id ASC;
            """,
            (campaign_title,),
        ).fetchall()
        attributed_links = [_format_attributed_link(r) for r in link_rows]

        log_business_event(
            conn=conn,
            event_category="CMO_GROWTH",
            summary_text=(
                f"Break-even verified for {item['sku_name']}: "
                f"Rs {_format_amount_disp(req.proposed_discount_rupees)} off requires "
                f"{calc['breakeven_daily_sales_needed']} units/day ({calc['verdict']})"
            ),
            evidence={
                "status": "CAMPAIGN_READY",
                "item_id": item["id"],
                "sku_name": item["sku_name"],
                "math_audit": math_audit,
                "links": [lnk["link"] for lnk in attributed_links],
            },
            actor="MERCHANT_APPROVED",
            commit=False,
        )
        conn.commit()

        return {
            "status": "CAMPAIGN_READY",
            "allowed": True,
            "item_id": item["id"],
            "sku_name": item["sku_name"],
            "days_unsold": days_unsold,
            "current_stock": int(item["current_stock"]),
            "unit_cost": unit_cost,
            "selling_price": selling_price,
            "proposed_discount": round(float(req.proposed_discount_rupees), 2),
            "discounted_price": discounted_price,
            "math_audit": math_audit,
            "attributed_links": attributed_links,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to create dead-stock campaign: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process dead-stock campaign.",
        )
    finally:
        close_db_connection(conn)


@router.post("/simulate-promo-click/{slug}")
def simulate_promo_click(
    slug: str,
    converted: bool = Query(True),
    payload: Optional[SimulatePromoClickRequest] = Body(None),
):
    """
    Increments clicks, and optionally conversions + revenue_collected, for a tracked
    promo link (mr-IN or hi-IN) and returns the updated per-language attribution breakdown.
    """
    is_converted = (
        payload.converted
        if payload is not None and payload.converted is not None
        else converted
    )
    conn = get_db_connection()
    try:
        normalized_slug = _strip_paytm_prefix(slug.strip())
        campaign = conn.execute(
            """
            SELECT * FROM campaigns_and_links
            WHERE paytm_link_slug = ? OR paytm_link_slug = ?;
            """,
            (slug, f"paytm.me/{normalized_slug}"),
        ).fetchone()

        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Promo link '{slug}' not found.",
            )

        unit_revenue = round(float(campaign["amount_expected"] or 0.0), 2) if is_converted else 0.0
        conv_delta = 1 if is_converted else 0

        conn.execute("BEGIN TRANSACTION;")
        conn.execute(
            """
            UPDATE campaigns_and_links
            SET clicks = clicks + 1,
                conversions = conversions + ?,
                revenue_collected = ROUND(revenue_collected + ?, 2)
            WHERE id = ?;
            """,
            (conv_delta, unit_revenue, campaign["id"]),
        )

        updated = conn.execute(
            "SELECT * FROM campaigns_and_links WHERE id = ?;", (campaign["id"],)
        ).fetchone()

        sibling_rows = conn.execute(
            """
            SELECT * FROM campaigns_and_links
            WHERE campaign_type = ? AND campaign_title = ?
            ORDER BY CASE WHEN language_code = 'mr-IN' THEN 0 ELSE 1 END, id ASC;
            """,
            (updated["campaign_type"], updated["campaign_title"]),
        ).fetchall()

        biz_event_id = log_business_event(
            conn=conn,
            event_category="CMO_GROWTH",
            summary_text=(
                f"Promo link {updated['paytm_link_slug']} ({updated['language_code']}) "
                f"recorded {'conversion' if is_converted else 'click'} "
                f"(clicks={updated['clicks']}, conversions={updated['conversions']}, "
                f"revenue=Rs {float(updated['revenue_collected']):.2f})"
            ),
            evidence={
                "campaign_id": updated["id"],
                "slug": normalized_slug,
                "language": updated["language_code"],
                "converted": is_converted,
                "clicks": int(updated["clicks"]),
                "conversions": int(updated["conversions"]),
                "revenue_collected": round(float(updated["revenue_collected"]), 2),
            },
            actor="SYSTEM_AUTO",
            commit=False,
        )
        conn.commit()

        return {
            "status": "RECORDED",
            "slug": normalized_slug,
            "link": updated["paytm_link_slug"],
            "language": updated["language_code"],
            "converted": is_converted,
            "clicks": int(updated["clicks"]),
            "conversions": int(updated["conversions"]),
            "redemptions": int(updated["conversions"]),
            "revenue_collected": round(float(updated["revenue_collected"]), 2),
            "business_event_id": biz_event_id,
            "language_breakdown": [_format_attributed_link(r) for r in sibling_rows],
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to simulate promo click: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record promo click attribution.",
        )
    finally:
        close_db_connection(conn)


# --------------------------------------------------------------------------
# 3. 60-Second Dukaan Closing Ritual (PRD §5.5, §7.6, CMO-06)
# --------------------------------------------------------------------------


@router.get("/dukaan-closing-ritual")
def get_dukaan_closing_ritual():
    """
    Aggregates today's live Paytm QR sales, today's recovered udhaar from ledger_entries,
    pending unmatched_payments_queue count, deterministic 3.5x Diwali restock forecast
    via calculate_festive_restock_forecast, and Bulbul v3 spoken Hindi closing briefing.
    """
    conn = get_db_connection()
    try:
        qr_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0.0) AS total
            FROM ledger_entries
            WHERE entry_type = 'REPAYMENT_JAMA'
              AND payment_mode = 'PAYTM_QR'
              AND status = 'CONFIRMED'
              AND date(created_at) = date('now');
            """
        ).fetchone()
        today_qr_repayments = float(qr_row["total"] or 0.0)
        today_qr_sales = round(6450.00 + today_qr_repayments, 2)

        recovered_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0.0) AS total
            FROM ledger_entries
            WHERE entry_type = 'REPAYMENT_JAMA'
              AND status = 'CONFIRMED'
              AND date(created_at) = date('now');
            """
        ).fetchone()
        today_udhaar_recovered = round(float(recovered_row["total"] or 0.0), 2)

        unmatched_row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM unmatched_payments_queue
            WHERE status = 'PENDING_REVIEW';
            """
        ).fetchone()
        unmatched_upi_count = int(unmatched_row["cnt"] or 0)

        top_item = conn.execute(
            """
            SELECT id, sku_name, current_stock, unit, avg_daily_burn,
                   festive_multiplier, supplier_name
            FROM inventory_items
            ORDER BY festive_multiplier DESC, current_stock ASC
            LIMIT 1;
            """
        ).fetchone()
        if top_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No inventory items available for festive restock forecast.",
            )

        forecast = calculate_festive_restock_forecast(
            daily_burn_rate=float(top_item["avg_daily_burn"] or 0.0),
            festive_multiplier=float(top_item["festive_multiplier"] or 1.0),
            current_stock=int(top_item["current_stock"] or 0),
            festival_window_days=5,
            sku_name=top_item["sku_name"],
            unit=top_item["unit"] or "tins",
            supplier_name=top_item["supplier_name"] or "Gupta Wholesalers",
            upcoming_event="Diwali Peak Week",
        )

        qr_disp = (
            f"{int(today_qr_sales):,}"
            if today_qr_sales == int(today_qr_sales)
            else f"{today_qr_sales:,.2f}"
        )
        rec_disp = _format_amount_disp(today_udhaar_recovered)
        supplier_short = (forecast["supplier_name"] or "Gupta Wholesalers").split(",")[0].strip()

        spoken_ritual_hi = (
            f"Dukaan band karne ka samay! Aaj Rs {qr_disp} ki Paytm QR bikri hui aur "
            f"Rs {rec_disp} udhaar wapas aaya. "
            f"{unmatched_upi_count} unmatched UPI payment review ke liye baki hai. "
            f"Zaroori sujhav: Diwali {forecast['days_away']} din door hai, "
            f"{forecast['sku_name']} ki maang {forecast['festive_surge_multiplier']:g} guna badhti hai "
            f"par sirf {forecast['current_stock']} {forecast['unit']} bache hain. "
            f"Kya {supplier_short} ko {forecast['recommended_order_qty']} {forecast['unit']} ka order bhej doon?"
        )

        tts_res = synthesize_speech(
            text=spoken_ritual_hi,
            target_language_code="hi-IN",
        )

        return {
            "today_qr_sales": today_qr_sales,
            "today_udhaar_recovered": today_udhaar_recovered,
            "unmatched_upi_count": unmatched_upi_count,
            "festive_restock_forecast": forecast,
            "spoken_ritual_hi": spoken_ritual_hi,
            "tts_audio_base64": tts_res.get("audio_base64", ""),
            "fallback_used": bool(tts_res.get("fallback_used", False)),
            "why_am_i_seeing_this": {
                "source": "Deterministic SQLite Aggregation & Diwali Surge Engine",
                "qr_baseline_amount": 6450.00,
                "live_qr_repayments_today": round(today_qr_repayments, 2),
                "today_udhaar_recovered": today_udhaar_recovered,
                "unmatched_upi_pending": unmatched_upi_count,
                "forecast_item_id": top_item["id"],
                "formula": "ceil(daily_burn_rate * festive_multiplier * 5) - current_stock",
            },
        }
    finally:
        close_db_connection(conn)


# --------------------------------------------------------------------------
# 4. Handwritten Bahi-Khata Scanner & 1-Tap Atomic Onboarding (ONBOARD-01)
# --------------------------------------------------------------------------


@router.post("/scan-bahi-khata")
async def scan_bahi_khata(
    request: Request,
    file: Optional[UploadFile] = File(None),
    use_demo_sample: Optional[bool] = Query(None),
):
    """
    Parses a physical bahi-khata notebook photo or demo sample into batch-editable
    customer credit proposals via bahi_khata_parser_service (10MB cap, 6.0s Sarvam
    Vision timeout with instant offline fallback).
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
        is_demo = True

    conn = get_db_connection()
    try:
        proposal = parse_bahi_khata_page(
            image_bytes=image_bytes,
            use_demo_sample=is_demo or (image_bytes is None),
            conn=conn,
        )
        return proposal
    finally:
        close_db_connection(conn)


@router.post("/confirm-bahi-khata")
def confirm_bahi_khata(req: ConfirmBahiKhataRequest):
    """
    Atomically onboards a batch of edited Bahi-Khata customer credit entries:
      - Enforces batch_ref idempotency guard against ledger_entries.provider_ref.
      - Validates all amounts (> 0, finite) and customer matches inside a single SQLite transaction.
      - Creates new customers or links verified existing customers (rejecting ambiguous names).
      - Records append-only CREDIT_UDHAAR entries via deterministic_engine.add_credit_entry
        and logs a consolidated CMO_GROWTH audit event in business_events.
    """
    for idx, entry in enumerate(req.entries, start=1):
        if not math.isfinite(entry.amount) or round(float(entry.amount), 2) <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Row {idx} amount must be a positive finite number.",
            )
        if not entry.customer_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Row {idx} customer_name cannot be blank.",
            )

    supplied_ref = (req.batch_ref or "").strip()
    batch_id = supplied_ref or uuid.uuid4().hex[:12]

    conn = get_db_connection()
    try:
        if supplied_ref:
            existing_batch = conn.execute(
                "SELECT id FROM ledger_entries WHERE provider_ref LIKE ? LIMIT 1;",
                (f"BAHI-{supplied_ref}-%",),
            ).fetchone()
            if existing_batch is not None:
                return {
                    "status": "ALREADY_CONFIRMED",
                    "batch_ref": supplied_ref,
                    "message": "Bahi-khata batch already onboarded.",
                }

        conn.execute("BEGIN TRANSACTION;")
        new_customers_created = 0
        customer_results: List[Dict[str, Any]] = []

        for idx, entry in enumerate(req.entries, start=1):
            clean_name = entry.customer_name.strip()
            amount_val = round(float(entry.amount), 2)

            if entry.customer_id is not None:
                cust = conn.execute(
                    "SELECT id, name FROM customers WHERE id = ?;",
                    (entry.customer_id,),
                ).fetchone()
                if cust is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Customer #{entry.customer_id} not found (row {idx}).",
                    )
                resolved_id = int(cust["id"])
                resolved_name = str(cust["name"])
                created_new = False
            else:
                lower_name = clean_name.lower()
                norm_phone = _normalize_phone(entry.phone)
                all_custs = conn.execute(
                    "SELECT id, name, phone FROM customers;"
                ).fetchall()

                matched = []
                for c in all_custs:
                    db_name = (c["name"] or "").strip().lower()
                    db_phone = _normalize_phone(c["phone"])
                    if db_name == lower_name or (norm_phone and db_phone and norm_phone == db_phone):
                        matched.append(c)

                if len(matched) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Ambiguous customer match for '{clean_name}' (row {idx}). "
                            "Please provide an explicit customer_id."
                        ),
                    )
                if len(matched) == 1:
                    resolved_id = int(matched[0]["id"])
                    resolved_name = str(matched[0]["name"])
                    created_new = False
                else:
                    clean_phone = (entry.phone or "").strip() or None
                    pref_lang = (entry.preferred_language or "hi-IN").strip() or "hi-IN"
                    cur = conn.execute(
                        """
                        INSERT INTO customers (name, aliases, phone, preferred_language, last_visit_date)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
                        """,
                        (clean_name, json.dumps([], ensure_ascii=False), clean_phone, pref_lang),
                    )
                    resolved_id = int(cur.lastrowid)
                    resolved_name = clean_name
                    created_new = True
                    new_customers_created += 1

            provider_ref = f"BAHI-{batch_id}-{idx}"
            utterance = f"Bahi-Khata OCR onboarding: {entry.notes or clean_name}"
            credit_res = add_credit_entry(
                conn=conn,
                customer_id=resolved_id,
                amount=amount_val,
                source_utterance=utterance,
                provider_ref=provider_ref,
                actor="MERCHANT_APPROVED",
                commit=False,
            )

            customer_results.append(
                {
                    "row_index": idx,
                    "customer_id": resolved_id,
                    "customer_name": resolved_name,
                    "created_new_customer": created_new,
                    "amount_credited": credit_res["amount"],
                    "ledger_entry_id": credit_res["entry_id"],
                    "provider_ref": provider_ref,
                    "balance_after": credit_res["balance"]["net_outstanding_balance"],
                }
            )

        total_onboarded_amount = round(
            sum(round(float(e.amount), 2) for e in req.entries), 2
        )

        biz_event_id = log_business_event(
            conn=conn,
            event_category="CMO_GROWTH",
            summary_text=(
                f"Onboarded {len(req.entries)} Bahi-Khata entries "
                f"({new_customers_created} new customers) totaling Rs {_format_amount_disp(total_onboarded_amount)}"
            ),
            evidence={
                "batch_ref": batch_id,
                "entries_recorded": len(req.entries),
                "new_customers_created": new_customers_created,
                "total_onboarded_amount": total_onboarded_amount,
                "customer_results": customer_results,
            },
            actor="MERCHANT_APPROVED",
            commit=False,
        )
        conn.commit()

        return {
            "status": "CONFIRMED",
            "batch_ref": batch_id,
            "entries_recorded": len(req.entries),
            "new_customers_created": new_customers_created,
            "total_onboarded_amount": total_onboarded_amount,
            "customer_results": customer_results,
            "business_event_id": biz_event_id,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to confirm bahi-khata batch: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm bahi-khata onboarding batch.",
        )
    finally:
        close_db_connection(conn)
