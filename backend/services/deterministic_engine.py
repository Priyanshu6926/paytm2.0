"""
KiranaOS Deterministic Memory & Calculation Engine
Enforces PRD §2 "Law of Zero LLM Math" and "Law of Append-Only Immutability".
All financial arithmetic, ledger updates, reversals, and audit logs are computed deterministically.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional


def calculate_customer_balance(conn: sqlite3.Connection, customer_id: int) -> Dict[str, Any]:
    """
    Computes a customer's outstanding balance strictly via SQL SUM over confirmed entries
    in ledger_entries per PRD §5.1 and D-02 / D-03:
      Outstanding Balance = SUM(Credit) - SUM(Repayment) + SUM(Adjustment)
    
    Returns:
        dict: {
            "customer_id": int,
            "total_credit": float,
            "total_repayment": float,
            "total_adjustment": float,
            "net_outstanding_balance": float,
            "confirmed_entry_count": int
        }
    """
    # Verify customer exists
    cust_row = conn.execute(
        "SELECT id, name FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    if cust_row is None:
        raise ValueError(f"Customer with ID {customer_id} does not exist.")

    # Pure SQL SUM aggregation over confirmed ledger entries
    query = """
    SELECT
        COALESCE(SUM(CASE WHEN l.entry_type = 'CREDIT_UDHAAR' THEN l.amount ELSE 0 END), 0.0) AS total_credit,
        COALESCE(SUM(CASE WHEN l.entry_type = 'REPAYMENT_JAMA' THEN l.amount ELSE 0 END), 0.0) AS total_repayment,
        COALESCE(SUM(
            CASE 
                WHEN l.entry_type = 'REVERSAL_ADJUSTMENT' THEN
                    CASE 
                        WHEN l.payment_mode = 'REVERSAL_REPAYMENT' THEN l.amount
                        WHEN l.payment_mode = 'REVERSAL_CREDIT' THEN -l.amount
                        WHEN orig.entry_type = 'REPAYMENT_JAMA' THEN l.amount
                        WHEN orig.entry_type = 'CREDIT_UDHAAR' THEN -l.amount
                        ELSE -l.amount
                    END
                ELSE 0 
            END
        ), 0.0) AS total_adjustment,
        COUNT(l.id) AS confirmed_entry_count
    FROM ledger_entries l
    LEFT JOIN ledger_entries orig ON (
        l.provider_ref LIKE 'REV-%' 
        AND orig.id = CAST(SUBSTR(l.provider_ref, 5) AS INTEGER)
    )
    WHERE l.customer_id = ? AND l.status = 'CONFIRMED';
    """
    row = conn.execute(query, (customer_id,)).fetchone()

    total_credit = round(float(row["total_credit"]), 2)
    total_repayment = round(float(row["total_repayment"]), 2)
    total_adjustment = round(float(row["total_adjustment"]), 2)
    net_outstanding = round(total_credit - total_repayment + total_adjustment, 2)
    confirmed_entry_count = int(row["confirmed_entry_count"])

    return {
        "customer_id": customer_id,
        "total_credit": total_credit,
        "total_repayment": total_repayment,
        "total_adjustment": total_adjustment,
        "net_outstanding_balance": net_outstanding,
        "confirmed_entry_count": confirmed_entry_count,
    }


def log_business_event(
    conn: sqlite3.Connection,
    event_category: str,
    summary_text: str,
    evidence: Dict[str, Any],
    actor: str = "MERCHANT_APPROVED",
) -> int:
    """
    Appends an immutable audit event to business_events table.
    Enforces D-03: every balance mutation or system action logs structured evidence.
    
    Returns:
        int: The newly inserted business_event id.
    """
    valid_categories = {
        "LEDGER",
        "INVENTORY",
        "CFO_ALERT",
        "CMO_GROWTH",
        "SETTLEMENT",
    }
    if event_category not in valid_categories:
        raise ValueError(
            f"Invalid event_category: '{event_category}'. Must be one of {sorted(valid_categories)}"
        )

    evidence_json = json.dumps(evidence, ensure_ascii=False, default=str)

    cursor = conn.execute(
        """
        INSERT INTO business_events (event_category, summary_text, evidence_json, actor)
        VALUES (?, ?, ?, ?);
        """,
        (event_category, summary_text, evidence_json, actor),
    )
    conn.commit()
    return cursor.lastrowid


def record_ledger_entry(
    conn: sqlite3.Connection,
    customer_id: int,
    entry_type: str,
    amount: float,
    payment_mode: str = "UDHAAR",
    provider_ref: Optional[str] = None,
    source_utterance: Optional[str] = None,
    confidence_score: float = 1.0,
    actor: str = "MERCHANT_APPROVED",
) -> Dict[str, Any]:
    """
    Inserts a confirmed entry into ledger_entries and atomically logs an audit row
    to business_events.
    Adheres strictly to the Append-Only Immutability Law (PRD §2).
    """
    # 1. Validate inputs
    valid_entry_types = {"CREDIT_UDHAAR", "REPAYMENT_JAMA", "REVERSAL_ADJUSTMENT"}
    if entry_type not in valid_entry_types:
        raise ValueError(f"Invalid entry_type: '{entry_type}'. Must be one of {sorted(valid_entry_types)}")

    try:
        amount_val = float(amount)
    except (TypeError, ValueError):
        raise ValueError(f"Amount must be a numeric value, got: {amount}")

    amount_val = round(amount_val, 2)
    if amount_val <= 0:
        raise ValueError(f"Amount must be greater than zero, got: {amount_val}")

    # 2. Check customer existence
    cust = conn.execute(
        "SELECT id, name FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    if cust is None:
        raise ValueError(f"Customer with ID {customer_id} does not exist.")

    # 3. Insert ledger entry (NEVER update or delete)
    cursor = conn.execute(
        """
        INSERT INTO ledger_entries (
            customer_id, entry_type, amount, payment_mode, provider_ref, source_utterance, confidence_score, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED');
        """,
        (
            customer_id,
            entry_type,
            amount_val,
            payment_mode,
            provider_ref,
            source_utterance,
            confidence_score,
        ),
    )
    entry_id = cursor.lastrowid

    # 4. Update customer's last_visit_date timestamp
    conn.execute(
        "UPDATE customers SET last_visit_date = CURRENT_TIMESTAMP WHERE id = ?;",
        (customer_id,),
    )

    # 5. Compute new balance deterministically
    balance = calculate_customer_balance(conn, customer_id)

    # 6. Audit log in business_events
    if entry_type == "CREDIT_UDHAAR":
        summary = f"Recorded ₹{amount_val:.2f} credit (udhaar) for {cust['name']}"
    elif entry_type == "REPAYMENT_JAMA":
        summary = f"Recorded ₹{amount_val:.2f} repayment (jama) for {cust['name']} via {payment_mode}"
    else:
        summary = f"Recorded ₹{amount_val:.2f} {entry_type} for {cust['name']}"

    evidence = {
        "ledger_entry_id": entry_id,
        "customer_id": customer_id,
        "customer_name": cust["name"],
        "entry_type": entry_type,
        "amount": amount_val,
        "payment_mode": payment_mode,
        "provider_ref": provider_ref,
        "source_utterance": source_utterance,
        "confidence_score": confidence_score,
        "actor": actor,
        "balance_after": balance["net_outstanding_balance"],
    }
    event_id = log_business_event(
        conn=conn,
        event_category="LEDGER",
        summary_text=summary,
        evidence=evidence,
        actor=actor,
    )

    conn.commit()

    return {
        "entry_id": entry_id,
        "customer_id": customer_id,
        "entry_type": entry_type,
        "amount": amount_val,
        "payment_mode": payment_mode,
        "provider_ref": provider_ref,
        "status": "CONFIRMED",
        "balance": balance,
        "business_event_id": event_id,
    }


def reverse_ledger_entry(
    conn: sqlite3.Connection,
    entry_id: int,
    reason: str,
    actor: str = "MERCHANT_APPROVED",
) -> Dict[str, Any]:
    """
    Validates target entry and records a compensating REVERSAL_ADJUSTMENT entry
    with inverted financial effect, adhering strictly to the append-only constraint
    without issuing UPDATE or DELETE statements per PRD §2 and D-02.
    """
    # 1. Fetch target entry
    target = conn.execute(
        "SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    if target is None:
        raise ValueError(f"Ledger entry with ID {entry_id} does not exist.")

    if target["entry_type"] == "REVERSAL_ADJUSTMENT":
        raise ValueError(f"Cannot reverse an entry that is already a REVERSAL_ADJUSTMENT (ID {entry_id}).")

    # 2. Check if already reversed
    existing_rev = conn.execute(
        "SELECT id FROM ledger_entries WHERE provider_ref = ? AND status = 'CONFIRMED'",
        (f"REV-{entry_id}",),
    ).fetchone()
    if existing_rev:
        raise ValueError(
            f"Ledger entry {entry_id} has already been reversed by entry {existing_rev['id']}."
        )

    # 3. Determine compensating entry details
    customer_id = target["customer_id"]
    amount = round(float(target["amount"]), 2)
    provider_ref = f"REV-{entry_id}"
    payment_mode = "REVERSAL_CREDIT" if target["entry_type"] == "CREDIT_UDHAAR" else "REVERSAL_REPAYMENT"
    source_utterance = f"Compensating reversal of entry #{entry_id}: {reason}"

    # 4. Insert compensating entry into ledger_entries
    cursor = conn.execute(
        """
        INSERT INTO ledger_entries (
            customer_id, entry_type, amount, payment_mode, provider_ref, source_utterance, confidence_score, status
        ) VALUES (?, 'REVERSAL_ADJUSTMENT', ?, ?, ?, ?, 1.0, 'CONFIRMED');
        """,
        (customer_id, amount, payment_mode, provider_ref, source_utterance),
    )
    reversal_id = cursor.lastrowid

    # 5. Update customer visit date
    conn.execute(
        "UPDATE customers SET last_visit_date = CURRENT_TIMESTAMP WHERE id = ?;",
        (customer_id,),
    )

    # 6. Compute new balance
    balance = calculate_customer_balance(conn, customer_id)

    # 7. Audit log in business_events
    summary = f"Compensating reversal of ledger entry #{entry_id} for customer #{customer_id}: {reason}"
    evidence = {
        "reversed_entry_id": entry_id,
        "reversal_entry_id": reversal_id,
        "customer_id": customer_id,
        "original_entry_type": target["entry_type"],
        "original_amount": amount,
        "reversal_amount": amount,
        "reason": reason,
        "actor": actor,
        "balance_after": balance["net_outstanding_balance"],
    }
    event_id = log_business_event(
        conn=conn,
        event_category="LEDGER",
        summary_text=summary,
        evidence=evidence,
        actor=actor,
    )

    conn.commit()

    return {
        "reversal_entry_id": reversal_id,
        "reversed_entry_id": entry_id,
        "customer_id": customer_id,
        "entry_type": "REVERSAL_ADJUSTMENT",
        "amount": amount,
        "reason": reason,
        "balance": balance,
        "business_event_id": event_id,
    }
