"""
backend/services/voice_intent_parser.py

Dynamic SQL Keyterm Biasing Extractor & Vernacular Kirana Voice Intent Parser.
Extracts live database terms to bias Sarvam STT (D-03) and parses vernacular
shop-counter commands in Hinglish and Marathi into typed Proposal Cards (D-04).
Enforces PRD §7.1 with automated customer identity disambiguation guards.
"""

from datetime import datetime
import json
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import (
    calculate_customer_balance,
    resolve_customer_identity,
)

logger = logging.getLogger(__name__)


def extract_keyterm_biasing_from_db(conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """
    Queries customers and inventory_items tables to extract dynamic prompt terms
    for Sarvam Saaras STT keyterm biasing per PRD §3 and D-03.
    Extracts customer names, customer aliases, SKU names, and SKU local aliases.
    Deduplicates and cleans terms while preserving natural phonetics.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    terms: List[str] = []
    seen: set = set()

    def _add_term(term: Optional[str]) -> None:
        if not term:
            return
        clean = term.strip()
        if len(clean) >= 2 and clean.lower() not in seen:
            seen.add(clean.lower())
            terms.append(clean)

    try:
        # 1. Customers: names and JSON aliases
        cust_rows = conn.execute("SELECT name, aliases FROM customers;").fetchall()
        for r in cust_rows:
            raw_name = r["name"] or ""
            _add_term(raw_name)
            # Add name without parentheses (e.g. "Suresh Patil" from "Suresh Patil (Tailor)")
            paren_stripped = re.sub(r"\(.*?\)", "", raw_name).strip()
            if paren_stripped:
                _add_term(paren_stripped)

            raw_aliases = r["aliases"]
            if raw_aliases:
                try:
                    aliases_list = json.loads(raw_aliases) if isinstance(raw_aliases, str) else raw_aliases
                    if isinstance(aliases_list, list):
                        for alias in aliases_list:
                            _add_term(str(alias))
                except Exception as exc:
                    logger.debug("Failed parsing customer aliases JSON: %s", exc)

        # 2. Inventory Items: sku_name and JSON local_aliases
        item_rows = conn.execute("SELECT sku_name, local_aliases FROM inventory_items;").fetchall()
        for r in item_rows:
            sku_name = r["sku_name"] or ""
            _add_term(sku_name)
            paren_stripped = re.sub(r"\(.*?\)", "", sku_name).strip()
            if paren_stripped:
                _add_term(paren_stripped)

            raw_aliases = r["local_aliases"]
            if raw_aliases:
                try:
                    aliases_list = json.loads(raw_aliases) if isinstance(raw_aliases, str) else raw_aliases
                    if isinstance(aliases_list, list):
                        for alias in aliases_list:
                            _add_term(str(alias))
                except Exception as exc:
                    logger.debug("Failed parsing inventory local_aliases JSON: %s", exc)

    finally:
        if should_close:
            close_db_connection(conn)

    return terms


def _extract_amount(text: str) -> Optional[float]:
    """
    Extracts numeric monetary amount from shop-counter transcript.
    Supports currency symbols, words (rupaye, rupees, rs, ₹), and implicit patterns.
    """
    # Pattern 1: Symbol or 'rs' prefix, e.g. ₹200, rs 300, rs. 650
    m = re.search(r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Pattern 2: Number followed by currency word or postfix, e.g. 200 rupaye, 300 rupees, 650 rs, 200/-
    m = re.search(
        r"(\d+(?:\.\d{1,2})?)\s*(?:rupaye|rupayee|rupees|rupaya|rs\.?|/-|takka|rupay)",
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Pattern 3: Number between postposition and action verb, e.g. "ka 200 udhaar", "ne 300 jama"
    m = re.search(
        r"(?:ka|ki|ke|ko|ne|se|che|cha)\s+(\d+(?:\.\d{1,2})?)\s+(?:udhaar|udhari|jama|wapas|baki)",
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Pattern 4: General numbers if followed by udhaar or jama, e.g. "udhaar 200", "jama 300"
    m = re.search(r"(?:udhaar|udhari|jama)\s+(\d+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Pattern 5: Standalone integer in credit/repayment context, e.g. "Suresh 200 udhaar"
    m = re.search(r"\b(\d+(?:\.\d{1,2})?)\b", text)
    if m:
        # Check that it's not followed by a quantity unit like packet, dabba, kg, etc.
        after = text[m.end():].strip().lower()
        if not re.match(r"^(?:packet|packets|dabba|dabbe|tin|tins|pouch|pouches|kg|l|litre|units|nug)", after):
            try:
                return float(m.group(1))
            except ValueError:
                pass

    return None


def _classify_intent(text: str) -> str:
    """
    Classifies Kirana voice transcript into typed domain intent.
    Intents:
      - REPAYMENT_JAMA
      - CREDIT_UDHAAR
      - STOCK_IN
      - STOCKOUT_FLAG
      - QUERY
    """
    lower = text.lower()

    # Repayment check (takes precedence over general udhaar query)
    if re.search(
        r"\b(jama|wapas|chukaya|chuka|diye|dile|bharle|bhara|bhugtan|repayment|deposit|paid|jama\s*kiye|jama\s*kele|jama\s*kiya)\b",
        lower,
    ):
        return "REPAYMENT_JAMA"

    # Credit / Udhaar check
    if re.search(
        r"\b(udhaar|udhari|baki|baaki|likho|likh\s*do|likh\s*dijiye|liha|credit|de\s*do)\b",
        lower,
    ):
        return "CREDIT_UDHAAR"

    # Stock Inward check
    if re.search(
        r"\b(stock\s*in|inward|aaya|aaye|aala|aale|packet\s*aaya|dabba\s*aaya|mal\s*aaya|maal\s*aaya|restock)\b",
        lower,
    ):
        return "STOCK_IN"

    # Stockout check
    if re.search(
        r"\b(khatam|stockout|sampala|khatam\s*ho\s*gaya|out\s*of\s*stock|khatam\s*jhale)\b",
        lower,
    ):
        return "STOCKOUT_FLAG"

    # Query check
    if re.search(
        r"\b(khata|hisab|hisaab|balance|kitna|kiti|status|dikhao|batao)\b",
        lower,
    ):
        return "QUERY"

    return "CREDIT_UDHAAR"  # Default fallback shop action


def _extract_customer_name(text: str, conn: sqlite3.Connection) -> Optional[str]:
    """
    Extracts the subject customer name from voice transcript.
    Uses regex postpositions (ka, ki, ke, ne, se, che) and cross-checks against DB memory.
    """
    # Check 1: Regex preceding postpositions (e.g. "Suresh ka", "Ramesh ne", "Suresh che")
    m = re.search(
        r"^\s*([A-Za-z\u0900-\u097F]+(?:\s+[A-Za-z\u0900-\u097F]+)?)\s+(?:ka|ki|ke|ko|ne|se|che|cha)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        extracted = m.group(1).strip()
        # Avoid extracting generic words
        if extracted.lower() not in {"aaj", "aajche", "aajka", "dukaan", "store", "dabba", "packet"}:
            return extracted

    # Check 2: Match against known customers or aliases in DB
    rows = conn.execute("SELECT name, aliases FROM customers;").fetchall()
    candidates: List[str] = []
    for r in rows:
        name = r["name"]
        candidates.append(name)
        cleaned = re.sub(r"\(.*?\)", "", name).strip()
        if cleaned:
            candidates.append(cleaned)
        if r["aliases"]:
            try:
                aliases = json.loads(r["aliases"]) if isinstance(r["aliases"], str) else r["aliases"]
                for a in aliases:
                    candidates.append(str(a))
            except Exception:
                pass

    # Sort candidates by length descending so longer matches take precedence
    candidates.sort(key=lambda s: len(s), reverse=True)
    lower_text = text.lower()
    for cand in candidates:
        cand_lower = cand.lower()
        # Word boundary or space check
        pattern = r"\b" + re.escape(cand_lower) + r"\b"
        if re.search(pattern, lower_text):
            return cand

    return None


def _extract_inventory_item(text: str, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """
    Matches inventory item from database based on SKU name or local aliases in transcript.
    """
    rows = conn.execute("SELECT * FROM inventory_items;").fetchall()
    lower_text = text.lower()

    for r in rows:
        sku = r["sku_name"]
        cleaned_sku = re.sub(r"\(.*?\)", "", sku).strip().lower()
        if cleaned_sku in lower_text or sku.lower() in lower_text:
            return dict(r)

        raw_aliases = r["local_aliases"]
        if raw_aliases:
            try:
                aliases = json.loads(raw_aliases) if isinstance(raw_aliases, str) else raw_aliases
                for a in aliases:
                    if str(a).strip().lower() in lower_text:
                        return dict(r)
            except Exception:
                pass

    return None


def _extract_quantity(text: str) -> int:
    """Extracts integer quantity for inventory events (defaulting to 1)."""
    m = re.search(
        r"\b(\d+)\s*(?:packet|packets|dabba|dabbe|tin|tins|pouch|pouches|kg|l|litre|litres|unit|units|nug)?\b",
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 1
    return 1


def parse_voice_intent(
    transcript: str,
    language_hint: str = "hi-IN",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Parses a Kirana voice transcript into an unconfirmed typed Proposal Card or
    Disambiguation Card adhering strictly to PRD §7.1 and D-04.

    Returns:
        dict: Proposal Card (status='PROPOSAL' or status='NEEDS_DISAMBIGUATION')
    """
    clean_transcript = transcript.strip()
    if not clean_transcript:
        return {
            "status": "NOT_UNDERSTOOD",
            "intent": "QUERY",
            "why_am_i_seeing_this": "Empty or inaudible voice input.",
            "spoken_prompt_hi": "Aapki aawaz theek se sunai nahi di. Kripya dobara bolein.",
            "raw_transcript": transcript,
        }

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        # 1. Classify intent & extract numeric amount
        intent = _classify_intent(clean_transcript)
        extracted_amount = _extract_amount(clean_transcript)

        # 2. Check for customer entity
        extracted_name = _extract_customer_name(clean_transcript, conn)

        # 3. If customer found or likely a customer transaction
        if extracted_name:
            resolution = resolve_customer_identity(conn, extracted_name)

            # Case A: Ambiguous Customer Match -> NEEDS_DISAMBIGUATION guard
            if resolution["status"] == "NEEDS_DISAMBIGUATION":
                spoken_prompt = resolution.get("spoken_prompt_hi", "")
                if extracted_amount is not None:
                    amt_str = f"{int(extracted_amount) if extracted_amount.is_integer() else extracted_amount}"
                    if "Kiske khate mein likhoon?" in spoken_prompt:
                        spoken_prompt = spoken_prompt.replace(
                            "Kiske khate mein likhoon?",
                            f"Kiske khate mein {amt_str} likhoon?",
                        )

                return {
                    "status": "NEEDS_DISAMBIGUATION",
                    "intent": intent,
                    "extracted_amount": extracted_amount,
                    "extracted_name": extracted_name,
                    "ambiguity_reason": resolution.get("ambiguity_reason"),
                    "candidates": resolution.get("candidates", []),
                    "why_am_i_seeing_this": resolution.get(
                        "why_am_i_seeing_this",
                        "KiranaOS blocks blind writes when customer names overlap.",
                    ),
                    "spoken_prompt_hi": spoken_prompt,
                    "raw_transcript": clean_transcript,
                }

            # Case B: Exact Customer Match -> PROPOSAL Card
            elif resolution["status"] == "EXACT_MATCH":
                cust = resolution["customer"]
                curr_udhaar = resolution["current_udhaar"]
                amt = extracted_amount or 0.0
                amt_fmt = int(amt) if amt.is_integer() else amt

                if intent == "CREDIT_UDHAAR":
                    new_balance = round(curr_udhaar + amt, 2)
                    why = f"Current balance ₹{curr_udhaar:.2f} + new credit ₹{amt:.2f} = ₹{new_balance:.2f}."
                    bal_fmt = int(new_balance) if new_balance.is_integer() else new_balance
                    spoken = f"{cust['name']} ke khate mein ₹{amt_fmt} udhaar likha ja raha hai. Naya balance ₹{bal_fmt} hoga. Confirm karein?"
                elif intent == "REPAYMENT_JAMA":
                    new_balance = round(curr_udhaar - amt, 2)
                    why = f"Current balance ₹{curr_udhaar:.2f} - repayment ₹{amt:.2f} = ₹{new_balance:.2f}."
                    bal_fmt = int(new_balance) if new_balance.is_integer() else new_balance
                    spoken = f"{cust['name']} ka ₹{amt_fmt} jama record karein? Naya balance ₹{bal_fmt} hoga."
                else:  # QUERY
                    new_balance = curr_udhaar
                    why = f"Current balance for {cust['name']} is ₹{curr_udhaar:.2f}."
                    bal_fmt = int(curr_udhaar) if curr_udhaar.is_integer() else curr_udhaar
                    spoken = f"{cust['name']} ka khata: ₹{bal_fmt} baki hai."

                return {
                    "status": "PROPOSAL",
                    "proposal_id": f"PROP-{uuid.uuid4().hex[:8].upper()}",
                    "intent": intent,
                    "customer": cust,
                    "customer_id": cust["id"],
                    "customer_name": cust["name"],
                    "extracted_amount": extracted_amount,
                    "current_balance": curr_udhaar,
                    "new_balance": new_balance,
                    "why_am_i_seeing_this": why,
                    "spoken_prompt_hi": spoken,
                    "raw_transcript": clean_transcript,
                }

            # Case C: Customer Not Found
            elif resolution["status"] == "NOT_FOUND":
                return {
                    "status": "CUSTOMER_NOT_FOUND",
                    "intent": intent,
                    "extracted_name": extracted_name,
                    "extracted_amount": extracted_amount,
                    "why_am_i_seeing_this": f"No customer matching '{extracted_name}' found in Kirana memory.",
                    "spoken_prompt_hi": f"Dukaan memory mein '{extracted_name}' naam ka koi grahak nahi mila. Kripya naya grahak jodein.",
                    "raw_transcript": clean_transcript,
                }

        # 4. Check for inventory item (e.g. "Amul Ghee 5 packet aaya" or "Fortune Oil khatam")
        inv_item = _extract_inventory_item(clean_transcript, conn)
        if inv_item:
            qty = _extract_quantity(clean_transcript)
            curr_stock = int(inv_item["current_stock"])
            unit = inv_item["unit"]
            sku_name = inv_item["sku_name"]

            if intent == "STOCK_IN":
                new_stock = curr_stock + qty
                why = f"Current stock {curr_stock} {unit} + inward {qty} {unit} = {new_stock} {unit}."
                spoken = f"{sku_name} ka {qty} {unit} stock mein joda ja raha hai. Confirm karein?"
                quantity_delta = qty
            elif intent == "STOCKOUT_FLAG":
                new_stock = 0
                why = f"Shopkeeper flagged {sku_name} as out of stock."
                spoken = f"{sku_name} stockout mark kiya ja raha hai. Supplier order draft karein?"
                quantity_delta = -curr_stock
            else:
                new_stock = curr_stock
                why = f"Current inventory for {sku_name} is {curr_stock} {unit}."
                spoken = f"{sku_name} ka current stock {curr_stock} {unit} hai."
                quantity_delta = 0

            return {
                "status": "PROPOSAL",
                "proposal_id": f"PROP-{uuid.uuid4().hex[:8].upper()}",
                "intent": intent,
                "item_id": inv_item["id"],
                "sku_name": sku_name,
                "quantity_delta": quantity_delta,
                "current_stock": curr_stock,
                "new_stock": new_stock,
                "why_am_i_seeing_this": why,
                "spoken_prompt_hi": spoken,
                "raw_transcript": clean_transcript,
            }

        # 5. General / Unresolved intent fallback
        return {
            "status": "NOT_UNDERSTOOD",
            "intent": intent,
            "extracted_amount": extracted_amount,
            "why_am_i_seeing_this": "Could not identify customer or inventory item in transcript.",
            "spoken_prompt_hi": "Aapka aadesh theek se samajh nahi aaya. Kripya grahak ya item ka naam saaf bolein.",
            "raw_transcript": clean_transcript,
        }

    finally:
        if should_close:
            close_db_connection(conn)
