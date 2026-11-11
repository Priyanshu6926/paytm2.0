"""
Handwritten Bahi-Khata Notebook OCR Parser Service.
Adheres to the Law of Demo-Day Survivability (ONBOARD-01, 04-CONTEXT.md) and
Threat Model T-04-01 / T-04-03 / T-04-SC.
Integrates Sarvam Vision OCR with a 6.0-second timeout and 10MB upload cap,
falling back gracefully to a realistic handwritten Marathi/Hindi khata page.
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

import httpx

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import calculate_customer_balance

logger = logging.getLogger(__name__)

# Constants
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_OCR_URL = os.getenv("SARVAM_OCR_URL", "https://api.sarvam.ai/document/ocr")
REQUEST_TIMEOUT_SECONDS = 6.0
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB limit per threat model T-04-01

# Realistic handwritten Marathi/Hindi Dadar kirana notebook page fallback (ONBOARD-01)
DEMO_BAHI_KHATA_PAGE: Dict[str, Any] = {
    "page_title": "Bahi-Khata Page #14 — Dadar West (Marathi / Hindi)",
    "detected_language": "mr-IN",
    "entries": [
        {
            "customer_name": "Sunita Sawant",
            "phone": "+919821112233",
            "preferred_language": "mr-IN",
            "amount": 340.00,
            "notes": "Atta 5kg + Dal",
            "confidence": 0.94,
        },
        {
            "customer_name": "Prakash Kulkarni",
            "phone": "+919821445566",
            "preferred_language": "mr-IN",
            "amount": 520.00,
            "notes": "Sabudana + Sugar + Tea",
            "confidence": 0.91,
        },
        {
            "customer_name": "Manoj Yadav",
            "phone": "+919821778899",
            "preferred_language": "hi-IN",
            "amount": 280.00,
            "notes": "Biscuit + Oil pouch",
            "confidence": 0.88,
        },
        {
            "customer_name": "Ramesh Sharma",
            "phone": "+919820111222",
            "preferred_language": "mr-IN",
            "amount": 150.00,
            "notes": "Milk + Bread khata",
            "confidence": 0.96,
        },
    ],
}


def _normalize_phone(phone: Optional[str]) -> str:
    """Normalizes a phone string to digits (last 10 when >= 10 digits) for matching."""
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def _parse_aliases(raw_aliases: Optional[str]) -> List[str]:
    """Safely parses JSON aliases column into a list of strings."""
    if not raw_aliases:
        return []
    try:
        parsed = json.loads(raw_aliases)
        if isinstance(parsed, list):
            return [str(a).strip() for a in parsed if str(a).strip()]
    except Exception:
        pass
    return []


def _match_customers_readonly(
    customer_name: str,
    phone: Optional[str],
    db_customers: List[sqlite3.Row],
) -> List[sqlite3.Row]:
    """
    Non-mutating customer lookup for OCR preview.
    Matches by exact phone, exact name/alias, or substring name/alias without
    writing SYSTEM_GUARD events during read-only preview.
    """
    clean_name = (customer_name or "").strip().lower()
    norm_phone = _normalize_phone(phone)

    # Tier 1: Exact phone or exact name/alias match
    exact_matches: Dict[int, sqlite3.Row] = {}
    for row in db_customers:
        cust_id = row["id"]
        db_phone = _normalize_phone(row["phone"])
        if norm_phone and db_phone and norm_phone == db_phone:
            exact_matches[cust_id] = row
            continue

        if clean_name:
            db_name = (row["name"] or "").strip().lower()
            if clean_name == db_name:
                exact_matches[cust_id] = row
                continue
            for alias in _parse_aliases(row["aliases"]):
                if clean_name == alias.lower():
                    exact_matches[cust_id] = row
                    break

    if exact_matches:
        return list(exact_matches.values())

    # Tier 2: Substring match on name or aliases (guard against tiny 1-char queries)
    if len(clean_name) < 2:
        return []

    substring_matches: Dict[int, sqlite3.Row] = {}
    for row in db_customers:
        cust_id = row["id"]
        db_name = (row["name"] or "").strip().lower()
        if db_name and (clean_name in db_name or db_name in clean_name):
            substring_matches[cust_id] = row
            continue

        for alias in _parse_aliases(row["aliases"]):
            alias_lower = alias.lower()
            if alias_lower and (clean_name in alias_lower or alias_lower in clean_name):
                substring_matches[cust_id] = row
                break

    return list(substring_matches.values())


def _extract_raw_entries(ocr_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts structured notebook rows from an OCR JSON response."""
    raw_rows = ocr_json.get("entries")
    if not raw_rows:
        raw_rows = ocr_json.get("rows")
    if not isinstance(raw_rows, list) or not raw_rows:
        return []

    valid_rows: List[Dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("customer_name", "")).strip()
        try:
            amt = round(float(row.get("amount", 0.0)), 2)
        except (TypeError, ValueError):
            continue
        if not name or amt <= 0:
            continue
        valid_rows.append(row)
    return valid_rows


def parse_bahi_khata_page(
    image_bytes: Optional[bytes] = None,
    use_demo_sample: bool = False,
    conn: Optional[sqlite3.Connection] = None,
    mock_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Parses a physical bahi-khata notebook photo or demo sample into batch-editable
    customer credit proposals with read-only SQLite customer classification.
    """
    fallback_used = False
    raw_page_data: Optional[Dict[str, Any]] = None

    # Enforce 10MB upload size cap before any external call (T-04-01)
    oversized = image_bytes is not None and len(image_bytes) > MAX_IMAGE_BYTES
    if oversized:
        logger.warning(
            "Uploaded bahi-khata image exceeds 10MB (%d bytes). Using offline fallback.",
            len(image_bytes),
        )
        fallback_used = True

    api_key = os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)
    if image_bytes and not mock_fallback and not use_demo_sample and not oversized and api_key:
        try:
            headers = {"api-subscription-key": api_key}
            files = {"file": ("bahi_khata.jpg", image_bytes, "image/jpeg")}
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(SARVAM_OCR_URL, headers=headers, files=files)
            if response.status_code == 200:
                ocr_json = response.json()
                extracted = _extract_raw_entries(ocr_json) if isinstance(ocr_json, dict) else []
                if extracted:
                    raw_page_data = {
                        "page_title": ocr_json.get("page_title", "Uploaded Bahi-Khata Page"),
                        "detected_language": ocr_json.get("detected_language", "mr-IN"),
                        "entries": extracted,
                    }
                else:
                    fallback_used = True
            else:
                logger.warning(
                    "Sarvam Vision OCR returned HTTP %s. Using offline fallback.",
                    response.status_code,
                )
                fallback_used = True
        except (httpx.TimeoutException, httpx.RequestError, Exception) as exc:
            # Never log headers or SARVAM_API_KEY (T-04-03)
            logger.warning(
                "Sarvam Vision OCR unavailable (%s). Degrading cleanly to demo fallback.",
                type(exc).__name__,
            )
            fallback_used = True
    else:
        fallback_used = True

    if raw_page_data is None:
        raw_page_data = DEMO_BAHI_KHATA_PAGE
        fallback_used = True

    page_title = str(raw_page_data.get("page_title", DEMO_BAHI_KHATA_PAGE["page_title"]))
    detected_language = str(raw_page_data.get("detected_language", "mr-IN"))
    raw_entries = raw_page_data.get("entries", [])

    should_close_conn = False
    if conn is None:
        conn = get_db_connection()
        should_close_conn = True

    try:
        db_customers = conn.execute(
            """
            SELECT id, name, aliases, phone, preferred_language, last_visit_date
            FROM customers;
            """
        ).fetchall()

        proposals: List[Dict[str, Any]] = []
        for idx, row in enumerate(raw_entries, start=1):
            customer_name = str(row.get("customer_name", "")).strip()
            phone = str(row.get("phone") or "").strip()
            preferred_language = str(row.get("preferred_language") or detected_language)
            amount = round(float(row.get("amount", 0.0)), 2)
            notes = str(row.get("notes") or "").strip()
            confidence = round(float(row.get("confidence", 0.90)), 2)

            matches = _match_customers_readonly(customer_name, phone, db_customers)

            if len(matches) == 1:
                m = matches[0]
                cust_id = m["id"]
                bal = calculate_customer_balance(conn, cust_id)["net_outstanding_balance"]
                match_status = "EXISTING_CUSTOMER"
                matched_customer_id = cust_id
                matched_customer_name = m["name"]
                existing_balance: Optional[float] = bal
                candidate_customers: List[Dict[str, Any]] = []
            elif len(matches) > 1:
                match_status = "AMBIGUOUS"
                matched_customer_id = None
                matched_customer_name = None
                existing_balance = None
                candidate_customers = [
                    {
                        "customer_id": m["id"],
                        "name": m["name"],
                        "phone": m["phone"],
                        "existing_balance": calculate_customer_balance(conn, m["id"])[
                            "net_outstanding_balance"
                        ],
                    }
                    for m in matches
                ]
            else:
                match_status = "NEW_CUSTOMER"
                matched_customer_id = None
                matched_customer_name = None
                existing_balance = 0.0
                candidate_customers = []

            proposals.append(
                {
                    "row_index": idx,
                    "customer_name": customer_name,
                    "phone": phone,
                    "preferred_language": preferred_language,
                    "amount": amount,
                    "notes": notes,
                    "confidence": confidence,
                    "match_status": match_status,
                    "matched_customer_id": matched_customer_id,
                    "matched_customer_name": matched_customer_name,
                    "existing_balance": existing_balance,
                    "candidate_customers": candidate_customers,
                }
            )

        total_proposed_amount = round(
            sum(round(float(row["amount"]), 2) for row in proposals), 2
        )

        return {
            "status": "PROPOSAL",
            "page_title": page_title,
            "detected_language": detected_language,
            "proposal_count": len(proposals),
            "total_proposed_amount": total_proposed_amount,
            "proposals": proposals,
            "fallback_used": fallback_used,
        }
    finally:
        if should_close_conn:
            close_db_connection(conn)
