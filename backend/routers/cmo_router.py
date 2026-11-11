"""
KiranaOS AI CMO Router mounted at /api/v1/cmo.
Implements Boli-Baki Multilingual Voice Udhaar Recovery with Soundbox payment webhook clearing
and Dead-Stock Break-Even Studio per PRD §5.4, §7.4, §7.5, and Threat Models T-04-04 to T-04-SC.
"""

from datetime import datetime
import logging
import re
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import (
    add_repayment_entry,
    calculate_customer_balance,
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
