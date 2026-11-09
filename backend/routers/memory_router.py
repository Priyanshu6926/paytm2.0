"""
KiranaOS Memory Inspection Router
Mounted at /api/v1/memory per PRD §4, §6, D-05, and Threat Model T-01-06 & T-01-07.
Exposes read-only inspection endpoints for health, customers, ledger history,
inventory status, and business event audit timeline.
"""

from datetime import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Query

from backend.database.connection import close_db_connection, get_db_connection
from backend.services.deterministic_engine import (
    calculate_customer_balance,
    format_last_visit,
    resolve_customer_identity,
)
from backend.services.seed_demo_data import STORE_NAME

router = APIRouter(prefix="/api/v1/memory", tags=["KiranaOS Memory"])


def get_connection() -> sqlite3.Connection:
    """Helper to acquire database connection for router requests."""
    return get_db_connection()


@router.get("/health")
def get_memory_health() -> Dict[str, Any]:
    """
    Returns store name, database connection status, and row counts across all 8 tables.
    Verifies that KiranaOS Walking Skeleton is booted and all tables are populated.
    """
    conn = get_connection()
    try:
        tables = [
            "customers",
            "ledger_entries",
            "inventory_items",
            "stock_events",
            "supplier_ledger",
            "unmatched_payments_queue",
            "campaigns_and_links",
            "business_events",
        ]
        table_counts: Dict[str, int] = {}
        for t in tables:
            row = conn.execute(f"SELECT COUNT(*) as count FROM {t};").fetchone()
            table_counts[t] = int(row["count"]) if row else 0

        all_populated = all(count > 0 for count in table_counts.values())

        return {
            "status": "healthy",
            "store_name": STORE_NAME,
            "database": "connected",
            "tables": table_counts,
            "all_tables_populated": all_populated,
        }
    finally:
        close_db_connection(conn)


@router.get("/customers/resolve")
def resolve_customer(
    query: Optional[str] = Query(None, description="Customer name, alias, or search term"),
    name: Optional[str] = Query(None, description="Alternative parameter for customer name"),
) -> Dict[str, Any]:
    """
    Explicit endpoint for customer identity resolution and disambiguation guard.
    Returns EXACT_MATCH, NEEDS_DISAMBIGUATION (with candidates), or NOT_FOUND per D-03.
    """
    search_term = query or name or ""
    conn = get_connection()
    try:
        return resolve_customer_identity(conn, search_term)
    finally:
        close_db_connection(conn)


@router.get("/customers")
def list_customers(
    query: Optional[str] = Query(None, description="Optional search term for disambiguation/lookup"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns list of customers with their deterministic balance and days overdue.
    If 'query' parameter is supplied, triggers identity disambiguation guard per D-03.
    """
    conn = get_connection()
    try:
        if query:
            return resolve_customer_identity(conn, query)

        rows = conn.execute(
            """
            SELECT id, name, aliases, phone, preferred_language, regular_cycle_days, last_visit_date, created_at
            FROM customers
            ORDER BY id ASC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        ).fetchall()

        now = datetime.now()
        customer_list: List[Dict[str, Any]] = []

        for r in rows:
            cust_id = r["id"]
            bal = calculate_customer_balance(conn, cust_id)

            # Compute days overdue based on last_visit_date
            days_overdue = 0
            if r["last_visit_date"]:
                try:
                    cleaned_date = str(r["last_visit_date"]).replace("T", " ").split(".")[0].strip()
                    if len(cleaned_date) == 10:
                        dt = datetime.strptime(cleaned_date, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(cleaned_date, "%Y-%m-%d %H:%M:%S")
                    diff_days = (now - dt).days
                    if bal["net_outstanding_balance"] > 0:
                        days_overdue = max(0, diff_days)
                except Exception:
                    days_overdue = 0

            aliases = []
            if r["aliases"]:
                try:
                    aliases = json.loads(r["aliases"])
                except Exception:
                    aliases = []

            customer_list.append({
                "id": cust_id,
                "name": r["name"],
                "aliases": aliases,
                "phone": r["phone"],
                "preferred_language": r["preferred_language"],
                "regular_cycle_days": r["regular_cycle_days"],
                "last_visit_date": r["last_visit_date"],
                "last_visit": format_last_visit(r["last_visit_date"]),
                "outstanding_balance": bal["net_outstanding_balance"],
                "total_credit": bal["total_credit"],
                "total_repayment": bal["total_repayment"],
                "total_adjustment": bal["total_adjustment"],
                "days_overdue": days_overdue,
            })

        return customer_list
    finally:
        close_db_connection(conn)


@router.get("/customers/{customer_id}/ledger")
def get_customer_ledger(
    customer_id: int,
    limit: int = Query(50, ge=1, le=100, description="Pagination limit for ledger entries"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> Dict[str, Any]:
    """
    Returns customer detail and their full chronological append-only ledger transaction timeline.
    """
    conn = get_connection()
    try:
        cust = conn.execute(
            "SELECT id, name, phone, preferred_language, regular_cycle_days, last_visit_date FROM customers WHERE id = ?;",
            (customer_id,),
        ).fetchone()

        if cust is None:
            raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found.")

        balance = calculate_customer_balance(conn, customer_id)

        entries = conn.execute(
            """
            SELECT id, entry_type, amount, payment_mode, provider_ref, source_utterance,
                   confidence_score, status, created_at
            FROM ledger_entries
            WHERE customer_id = ?
            ORDER BY created_at ASC, id ASC
            LIMIT ? OFFSET ?;
            """,
            (customer_id, limit, offset),
        ).fetchall()

        timeline = [
            {
                "id": e["id"],
                "entry_type": e["entry_type"],
                "amount": float(e["amount"]),
                "payment_mode": e["payment_mode"],
                "provider_ref": e["provider_ref"],
                "source_utterance": e["source_utterance"],
                "confidence_score": float(e["confidence_score"]),
                "status": e["status"],
                "created_at": str(e["created_at"]),
            }
            for e in entries
        ]

        return {
            "customer": {
                "id": cust["id"],
                "name": cust["name"],
                "phone": cust["phone"],
                "preferred_language": cust["preferred_language"],
                "regular_cycle_days": cust["regular_cycle_days"],
                "last_visit_date": cust["last_visit_date"],
                "last_visit": format_last_visit(cust["last_visit_date"]),
                "outstanding_balance": balance["net_outstanding_balance"],
            },
            "balance": balance,
            "total_credit": balance["total_credit"],
            "total_repayment": balance["total_repayment"],
            "total_adjustment": balance["total_adjustment"],
            "net_outstanding_balance": balance["net_outstanding_balance"],
            "count": len(timeline),
            "ledger_entries": timeline,
        }
    finally:
        close_db_connection(conn)


@router.get("/inventory")
def list_inventory(
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> List[Dict[str, Any]]:
    """
    Returns inventory items including current stock, burn rate, festive multiplier,
    cost/selling price, and supplier metadata.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, sku_name, local_aliases, category, current_stock, unit,
                   last_unit_cost, previous_unit_cost, selling_price,
                   avg_daily_burn, festive_multiplier, reorder_threshold,
                   supplier_name, supplier_phone, last_restocked_at, last_sold_at
            FROM inventory_items
            ORDER BY id ASC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        ).fetchall()

        items: List[Dict[str, Any]] = []
        for r in rows:
            aliases = []
            if r["local_aliases"]:
                try:
                    aliases = json.loads(r["local_aliases"])
                except Exception:
                    aliases = []

            items.append({
                "id": r["id"],
                "sku_name": r["sku_name"],
                "local_aliases": aliases,
                "category": r["category"],
                "current_stock": r["current_stock"],
                "unit": r["unit"],
                "last_unit_cost": float(r["last_unit_cost"]),
                "previous_unit_cost": float(r["previous_unit_cost"]),
                "selling_price": float(r["selling_price"]),
                "avg_daily_burn": float(r["avg_daily_burn"]),
                "festive_multiplier": float(r["festive_multiplier"]),
                "reorder_threshold": r["reorder_threshold"],
                "supplier_name": r["supplier_name"],
                "supplier_phone": r["supplier_phone"],
                "last_restocked_at": r["last_restocked_at"],
                "last_sold_at": r["last_sold_at"],
            })

        return items
    finally:
        close_db_connection(conn)


@router.get("/events")
def list_business_events(
    category: Optional[str] = Query(None, description="Filter by event_category"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> List[Dict[str, Any]]:
    """
    Returns chronological feed of business_events with structured evidence_json
    powers the 'Why am I seeing this?' audit drawer per PRD §4 and D-03.
    """
    conn = get_connection()
    try:
        if category:
            rows = conn.execute(
                """
                SELECT id, event_category, summary_text, evidence_json, actor, created_at
                FROM business_events
                WHERE event_category = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (category, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, event_category, summary_text, evidence_json, actor, created_at
                FROM business_events
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (limit, offset),
            ).fetchall()

        events: List[Dict[str, Any]] = []
        for r in rows:
            evidence_parsed = {}
            if r["evidence_json"]:
                try:
                    evidence_parsed = json.loads(r["evidence_json"])
                except Exception:
                    evidence_parsed = {"raw": r["evidence_json"]}

            events.append({
                "id": r["id"],
                "event_category": r["event_category"],
                "summary_text": r["summary_text"],
                "evidence": evidence_parsed,
                "evidence_json": r["evidence_json"],
                "actor": r["actor"],
                "created_at": str(r["created_at"]),
            })

        return events
    finally:
        close_db_connection(conn)
