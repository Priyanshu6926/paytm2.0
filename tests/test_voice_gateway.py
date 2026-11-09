"""
tests/test_voice_gateway.py

Unit and integration tests for KiranaOS Voice Gateway & Multimodal Input Layer.
Verifies dynamic SQL keyterm biasing, vernacular voice intent parser,
customer identity disambiguation guards, and Propose-Confirm-Commit API endpoints
mounted at /api/v1/voice/*.
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import close_db_connection, get_db_connection, init_db
from backend.services.seed_demo_data import seed_all
from backend.services.voice_intent_parser import (
    extract_keyterm_biasing_from_db,
    parse_voice_intent,
)


@pytest.fixture(autouse=True)
def setup_database():
    """Idempotently re-initializes and seeds test database before each test."""
    init_db()
    conn = get_db_connection()
    try:
        seed_all(conn)
    finally:
        close_db_connection(conn)


def test_keyterm_biasing_extraction():
    """
    Verifies that extract_keyterm_biasing_from_db dynamically pulls all customer
    and inventory names + aliases from active SQLite tables per D-03.
    """
    conn = get_db_connection()
    try:
        terms = extract_keyterm_biasing_from_db(conn)
    finally:
        close_db_connection(conn)

    assert isinstance(terms, list)
    assert len(terms) > 10

    # Verify customer names and aliases
    assert any("Ramesh Sharma" in t for t in terms)
    assert any("Ramesh Bhai" in t for t in terms)
    assert any("Suresh Patil" in t for t in terms)
    assert any("Suresh Tailor" in t for t in terms)
    assert any("Suresh Kadam" in t for t in terms)
    assert any("Suresh Kirana" in t for t in terms)
    assert any("Priya Deshmukh" in t for t in terms)

    # Verify inventory SKUs and local aliases
    assert any("Amul Pure Ghee" in t or "Amul Ghee" in t for t in terms)
    assert any("Fortune Oil" in t or "Fortune Sunlite Oil" in t for t in terms)
    assert any("Haldiram" in t or "Bhujia" in t for t in terms)

    # Verify deduplication
    lowered = [t.lower() for t in terms]
    assert len(lowered) == len(set(lowered))


def test_intent_parser_ambiguous_suresh_triggers_disambiguation():
    """
    Verifies D-04: 'Suresh ka 200 rupaye udhaar likh do' triggers NEEDS_DISAMBIGUATION
    guard without executing blind writes or unconfirmed mutations.
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Suresh ka 200 rupaye udhaar likh do", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "NEEDS_DISAMBIGUATION"
    assert res["intent"] == "CREDIT_UDHAAR"
    assert res["extracted_amount"] == 200.0
    assert "Suresh" in res["extracted_name"]
    assert len(res["candidates"]) == 2
    assert "2 customers matching" in res["ambiguity_reason"]
    assert "KiranaOS blocks blind writes" in res["why_am_i_seeing_this"]
    assert "Dukaan mein do Suresh hain" in res["spoken_prompt_hi"]
    assert "200" in res["spoken_prompt_hi"]


def test_intent_parser_resolved_ramesh_repayment_proposal():
    """
    Verifies D-04: 'Ramesh ne 300 rupaye jama kiye' accurately resolves Ramesh Sharma,
    extracts amount 300.0, and computes new balance (650 - 300 = 350).
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Ramesh ne 300 rupaye jama kiye", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "PROPOSAL"
    assert res["intent"] == "REPAYMENT_JAMA"
    assert res["extracted_amount"] == 300.0
    assert res["customer"]["name"] == "Ramesh Sharma"
    assert res["customer_name"] == "Ramesh Sharma"
    assert res["current_balance"] == 650.0
    assert res["new_balance"] == 350.0
    assert "Current balance ₹650.00 - repayment ₹300.00 = ₹350.00." in res["why_am_i_seeing_this"]
    assert "300 jama record karein?" in res["spoken_prompt_hi"]


def test_intent_parser_marathi_commands():
    """
    Verifies that Marathi vernacular phrases are properly parsed for credit and repayment.
    """
    conn = get_db_connection()
    try:
        # Marathi credit command
        credit_res = parse_voice_intent("Suresh che 200 rupaye udhari liha", language_hint="mr-IN", conn=conn)
        assert credit_res["status"] == "NEEDS_DISAMBIGUATION"
        assert credit_res["intent"] == "CREDIT_UDHAAR"
        assert credit_res["extracted_amount"] == 200.0

        # Marathi repayment command
        repay_res = parse_voice_intent("Ramesh ne 300 rupaye jama kele", language_hint="mr-IN", conn=conn)
        assert repay_res["status"] == "PROPOSAL"
        assert repay_res["intent"] == "REPAYMENT_JAMA"
        assert repay_res["extracted_amount"] == 300.0
        assert repay_res["new_balance"] == 350.0
    finally:
        close_db_connection(conn)


def test_intent_parser_inventory_stock_inward_and_stockout():
    """
    Verifies inventory intent parsing for stock inward and stockout triggers.
    """
    conn = get_db_connection()
    try:
        # Stock Inward
        inward_res = parse_voice_intent("Amul Ghee 5 packet aaya", language_hint="hi-IN", conn=conn)
        assert inward_res["status"] == "PROPOSAL"
        assert inward_res["intent"] == "STOCK_IN"
        assert inward_res["sku_name"] == "Amul Pure Ghee 1L"
        assert inward_res["quantity_delta"] == 5
        assert inward_res["new_stock"] == inward_res["current_stock"] + 5

        # Stockout Flag
        stockout_res = parse_voice_intent("Fortune Oil khatam ho gaya", language_hint="hi-IN", conn=conn)
        assert stockout_res["status"] == "PROPOSAL"
        assert stockout_res["intent"] == "STOCKOUT_FLAG"
        assert stockout_res["sku_name"] == "Fortune Sunlite Oil 1L"
        assert stockout_res["new_stock"] == 0
    finally:
        close_db_connection(conn)


def test_intent_parser_customer_not_found():
    """
    Verifies graceful fallback when speaking a customer name not in shop memory.
    """
    conn = get_db_connection()
    try:
        res = parse_voice_intent("Vikram ka 500 rupaye udhaar likho", language_hint="hi-IN", conn=conn)
    finally:
        close_db_connection(conn)

    assert res["status"] == "CUSTOMER_NOT_FOUND"
    assert res["extracted_name"] == "Vikram"
    assert res["extracted_amount"] == 500.0
