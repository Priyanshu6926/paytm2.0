"""
backend/routers/voice_router.py

KiranaOS Voice Gateway Router mounted at /api/v1/voice.
Implements the Propose-Confirm-Commit Multimodal API for Kirana shop counters
per PRD §2, §7.1, D-04, D-05, and Threat Model T-02-04 & T-02-05.
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import (
    add_credit_entry,
    add_repayment_entry,
    calculate_customer_balance,
    record_stock_event,
)
from backend.services.sarvam_engine import (
    MAX_AUDIO_BYTES,
    get_sarvam_health_status,
    synthesize_speech,
    transcribe_audio,
)
from backend.services.voice_intent_parser import (
    extract_keyterm_biasing_from_db,
    parse_voice_intent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Gateway"])


def get_connection() -> sqlite3.Connection:
    """Helper to acquire database connection."""
    return get_db_connection()


# --------------------------------------------------------------------------
# Request & Response Models
# --------------------------------------------------------------------------

class VoiceProposeRequest(BaseModel):
    transcript_override: Optional[str] = Field(
        None, description="Direct text transcript for voice intent parsing"
    )
    language_hint: str = Field(
        "hi-IN", description="Language code for STT/TTS (hi-IN, mr-IN, en-IN)"
    )


class ProposalConfirmRequest(BaseModel):
    proposal_id: Optional[str] = Field(None, description="Unique proposal identifier")
    action: str = Field(
        ...,
        description="Explicit approval action. Must be 'APPROVE' to commit writes (Threat Model T-02-05).",
    )
    intent: str = Field(
        ...,
        description="Intent type: CREDIT_UDHAAR, REPAYMENT_JAMA, STOCK_IN, STOCKOUT_FLAG",
    )
    customer_id: Optional[int] = Field(None, description="Customer ID for ledger writes")
    amount: Optional[float] = Field(None, description="Monetary transaction amount in INR")
    payment_mode: Optional[str] = Field("UDHAAR", description="Payment mode (UDHAAR, CASH, UPI)")
    item_id: Optional[int] = Field(None, description="Inventory Item ID for stock events")
    quantity_delta: Optional[int] = Field(None, description="Quantity change for inventory")
    source_utterance: Optional[str] = Field(None, description="Original shop voice transcript")
    language_hint: Optional[str] = Field("hi-IN", description="Target language for spoken confirmation")


class TextToSpeechRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize into vernacular speech")
    target_language_code: str = Field(
        "hi-IN", description="Target Indian language code (hi-IN, mr-IN, en-IN)"
    )
    speaker: Optional[str] = Field("meera", description="Sarvam Bulbul voice speaker")


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/health")
def get_voice_health() -> Dict[str, Any]:
    """
    Returns Voice Gateway health, database connectivity, and Sarvam engine status.
    Adheres to PRD §3 and D-05.
    """
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM customers;").fetchone()
        cust_count = int(row["count"]) if row else 0
        db_status = "connected" if cust_count >= 0 else "error"
    except Exception as exc:
        db_status = f"error: {str(exc)}"
    finally:
        close_db_connection(conn)

    sarvam_health = get_sarvam_health_status()

    return {
        "status": "healthy",
        "gateway": "voice",
        "database": db_status,
        "sarvam_api_key_configured": sarvam_health.get("api_key_configured", False),
        "sarvam_fallback_mode": not sarvam_health.get("api_key_configured", False),
        "service": "Munim-AI KiranaOS Voice Gateway",
        "supported_languages": ["hi-IN", "mr-IN", "en-IN"],
    }


@router.post("/tts")
def generate_tts(request: TextToSpeechRequest) -> Dict[str, Any]:
    """
    Direct endpoint for vernacular speech synthesis using Sarvam Bulbul v3 TTS.
    Falls back gracefully to high-fidelity synthetic WAV audio if unauthenticated or offline.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text payload cannot be empty.",
        )

    res = synthesize_speech(
        text=request.text,
        target_language_code=request.target_language_code,
        speaker=request.speaker or "meera",
    )
    return res


@router.post("/propose")
async def propose_voice_action(
    request: Request,
) -> Dict[str, Any]:
    """
    Generates an unconfirmed typed Proposal Card or Disambiguation Card from voice or text.
    Accepts application/json OR multipart/form-data with audio file uploads.
    Performs dynamic SQL keyterm biasing and vernacular intent parsing per D-03 & D-04.
    """
    content_type = request.headers.get("content-type", "").lower()
    transcript: Optional[str] = None
    language_hint: str = "hi-IN"

    conn = get_connection()
    try:
        # Case A: JSON Payload
        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload.",
                )
            transcript = body.get("transcript_override")
            language_hint = body.get("language_hint") or "hi-IN"

        # Case B: Multipart Form Data
        elif "multipart/form-data" in content_type:
            form = await request.form()
            transcript = form.get("transcript_override")
            language_hint = str(form.get("language_hint") or "hi-IN")

            uploaded_file = form.get("file") or form.get("audio")
            if uploaded_file and hasattr(uploaded_file, "read"):
                audio_bytes = await uploaded_file.read()
                # Enforce file size limit (Threat Model T-02-04)
                if len(audio_bytes) > MAX_AUDIO_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio payload exceeds {MAX_AUDIO_BYTES} bytes (10MB) limit.",
                    )

                # Transcribe audio if no explicit override was provided
                if not transcript and len(audio_bytes) > 0:
                    biasing_terms = extract_keyterm_biasing_from_db(conn)
                    stt_result = transcribe_audio(
                        audio_bytes=audio_bytes,
                        prompt_terms=biasing_terms,
                        language_code=language_hint,
                    )
                    transcript = stt_result.get("transcript", "")
        else:
            # Fallback check for query params or simple text
            transcript = request.query_params.get("transcript_override")

        if not transcript or not str(transcript).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either transcript_override or a valid audio file upload must be provided.",
            )

        # Parse voice command into unconfirmed proposal card
        proposal = parse_voice_intent(
            transcript=str(transcript),
            language_hint=language_hint,
            conn=conn,
        )

        # Generate vernacular TTS confirmation prompt
        spoken_text = proposal.get("spoken_prompt_hi") or "Aadesh darj ho gaya hai."
        tts_res = synthesize_speech(
            text=spoken_text,
            target_language_code=language_hint,
        )
        proposal["tts_audio_base64"] = tts_res.get("audio_base64", "")

        return proposal

    finally:
        close_db_connection(conn)


@router.post("/confirm")
def confirm_voice_proposal(
    request: ProposalConfirmRequest,
) -> Dict[str, Any]:
    """
    Executes an explicit merchant confirmation of a voice proposal.
    Enforces Threat Model T-02-05: requires action == 'APPROVE'.
    Commits deterministic writes to ledger_entries and logs an auditable business_event.
    """
    # 1. Enforce explicit merchant approval
    if request.action != "APPROVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit merchant approval ('action': 'APPROVE') is required to commit ledger entries.",
        )

    conn = get_connection()
    try:
        intent = request.intent.upper()
        result_payload: Dict[str, Any] = {
            "status": "CONFIRMED",
            "proposal_id": request.proposal_id,
            "intent": intent,
        }

        # Case 1: Credit Entry (Udhaar)
        if intent == "CREDIT_UDHAAR":
            if request.customer_id is None or request.amount is None or request.amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valid customer_id and positive amount are required for credit entries.",
                )

            ledger_res = add_credit_entry(
                conn=conn,
                customer_id=request.customer_id,
                amount=request.amount,
                source_utterance=request.source_utterance,
                actor="MERCHANT_APPROVED",
            )
            cust_row = conn.execute(
                "SELECT name FROM customers WHERE id = ?;", (request.customer_id,)
            ).fetchone()
            cust_name = cust_row["name"] if cust_row else f"Customer #{request.customer_id}"
            new_bal = ledger_res["balance"]["net_outstanding_balance"]

            spoken_conf = f"{cust_name} ke khate mein ₹{request.amount:.2f} udhaar darj ho gaya hai. Naya balance ₹{new_bal:.2f} hai."
            result_payload.update({
                "ledger_entry_id": ledger_res["entry_id"],
                "customer_id": request.customer_id,
                "customer_name": cust_name,
                "amount": request.amount,
                "new_balance": new_bal,
                "business_event_id": ledger_res["business_event_id"],
                "spoken_confirmation": spoken_conf,
            })

        # Case 2: Repayment Entry (Jama)
        elif intent == "REPAYMENT_JAMA":
            if request.customer_id is None or request.amount is None or request.amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valid customer_id and positive amount are required for repayment entries.",
                )

            ledger_res = add_repayment_entry(
                conn=conn,
                customer_id=request.customer_id,
                amount=request.amount,
                payment_mode=request.payment_mode or "CASH",
                source_utterance=request.source_utterance,
                actor="MERCHANT_APPROVED",
            )
            cust_row = conn.execute(
                "SELECT name FROM customers WHERE id = ?;", (request.customer_id,)
            ).fetchone()
            cust_name = cust_row["name"] if cust_row else f"Customer #{request.customer_id}"
            new_bal = ledger_res["balance"]["net_outstanding_balance"]

            spoken_conf = f"{cust_name} ka ₹{request.amount:.2f} jama darj ho gaya hai. Naya balance ₹{new_bal:.2f} hai."
            result_payload.update({
                "ledger_entry_id": ledger_res["entry_id"],
                "customer_id": request.customer_id,
                "customer_name": cust_name,
                "amount": request.amount,
                "new_balance": new_bal,
                "business_event_id": ledger_res["business_event_id"],
                "spoken_confirmation": spoken_conf,
            })

        # Case 3: Stock Inward or Stockout Flag
        elif intent in {"STOCK_IN", "STOCKOUT_FLAG"}:
            if request.item_id is None or request.quantity_delta is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valid item_id and quantity_delta are required for inventory events.",
                )

            event_type = "INWARD_VOICE" if intent == "STOCK_IN" else "STOCKOUT_FLAG"
            stock_res = record_stock_event(
                conn=conn,
                item_id=request.item_id,
                event_type=event_type,
                quantity_delta=request.quantity_delta,
                raw_transcript=request.source_utterance,
                actor="MERCHANT_APPROVED",
            )
            sku_name = stock_res["sku_name"]
            new_stock = stock_res["new_stock"]

            spoken_conf = f"{sku_name} ka stock update ho gaya hai. Naya stock {new_stock} hai."
            result_payload.update({
                "stock_event_id": stock_res["event_id"],
                "item_id": request.item_id,
                "sku_name": sku_name,
                "new_stock": new_stock,
                "business_event_id": stock_res["business_event_id"],
                "spoken_confirmation": spoken_conf,
            })

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported intent for proposal confirmation: '{intent}'.",
            )

        # Synthesize spoken confirmation audio
        tts_res = synthesize_speech(
            text=result_payload["spoken_confirmation"],
            target_language_code=request.language_hint or "hi-IN",
        )
        result_payload["tts_audio_base64"] = tts_res.get("audio_base64", "")

        return result_payload

    finally:
        close_db_connection(conn)
