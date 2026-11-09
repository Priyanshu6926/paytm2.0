---
phase: 01-kiranaos-deterministic-memory-store-engine
plan: 02
subsystem: memory-engine
tags:
  - deterministic-math
  - ledger
  - identity-disambiguation
  - append-only
  - audit-trail
  - zero-llm-math
requires:
  - 01-01
provides:
  - deterministic-customer-balance-calculation
  - ledger-entry-recorder
  - compensating-reversal-engine
  - identity-disambiguation-guard
  - structured-business-events-logger
affects:
  - 01-03
  - 01-04
tech-stack:
  added:
    - sqlite3 (standard library)
    - pytest
  patterns:
    - sql-sum-aggregation
    - compensating-reversal-transactions
    - candidate-disambiguation-guard
    - structured-evidence-audit-logging
key-files:
  created:
    - backend/services/__init__.py
    - backend/services/deterministic_engine.py
    - tests/test_deterministic_engine.py
    - tests/test_identity_disambiguation.py
  modified: []
decisions:
  - "D-02: Customer outstanding balance is calculated dynamically via pure SQL SUM over confirmed ledger records (Credit - Repayment + Adjustment), strictly complying with the Law of Zero LLM Math."
  - "D-03: Multi-match customer queries (such as 'Suresh') immediately halt automatic write operations and return a structured NEEDS_DISAMBIGUATION payload containing live candidate udhaar balances and bilingual spoken prompts."
  - "D-03: Every ledger insertion, compensating reversal, and identity disambiguation trigger logs an immutable row in business_events with structured evidence_json."
metrics:
  duration: 6m
  completed: 2026-11-09
status: complete
actuals:
  tokens: 22000
  tasks: 2
  commits: 2
  plan_head_before: 93e8493
  plan_head_after: 412c2bb
---

# Phase 01 Plan 02: Deterministic KiranaOS Memory & Disambiguation Engine Summary

**One-liner:** Implemented the core pure-Python deterministic balance aggregation engine, compensating reversal logic, customer identity disambiguation guard, and structured audit logger.

## Objectives Achieved

1. **Deterministic Customer Balance Engine (`backend/services/deterministic_engine.py`)**:
   - `calculate_customer_balance(conn, customer_id: int)` computes outstanding debt strictly via SQL `SUM` over confirmed entries in `ledger_entries` per PRD §5.1:
     $$\text{Outstanding Balance} = \sum \text{Credit} - \sum \text{Repayment} + \sum \text{Adjustment}$$
   - Returns typed breakdown: `total_credit`, `total_repayment`, `total_adjustment`, `net_outstanding_balance`, and `confirmed_entry_count`.
   - Enforces 2-decimal precision (`round(x, 2)`) to mitigate floating-point drift per threat model T-01-SC.

2. **Immutable Ledger Transactions & Compensating Reversals**:
   - `record_ledger_entry(...)` appends confirmed `CREDIT_UDHAAR`, `REPAYMENT_JAMA`, or `REVERSAL_ADJUSTMENT` entries without issuing `UPDATE` or `DELETE` statements.
   - `reverse_ledger_entry(...)` validates target records and appends an explicit compensating `REVERSAL_ADJUSTMENT` with inverted financial impact, linking via `provider_ref = 'REV-{id}'`.
   - Idempotency guards prevent double reversals and prohibit reversing existing reversal adjustments.

3. **Customer Identity Disambiguation Guard**:
   - `resolve_customer_identity(conn, query_name: str)` inspects the `customers` table across exact name matches, JSON aliases (`aliases`), and substring matches.
   - Single match returns `EXACT_MATCH` with customer profile, live `current_udhaar`, and formatted visit recency.
   - Ambiguous matches (e.g. searching 'Suresh' matching 'Suresh Patil (Tailor)' and 'Suresh Kadam (Kirana)') halt blind database writes and return `NEEDS_DISAMBIGUATION` with candidate cards, live udhaar balances, and bilingual spoken prompt suggestions per PRD §7.1.
   - Missing customer queries return `NOT_FOUND`.

4. **Structured Business Memory Audit Trail**:
   - `log_business_event(...)` inserts immutable records into `business_events` with `event_category`, summary text, and structured `evidence_json`.
   - All balance mutations and identity disambiguation inquiries are logged with actor provenance (`MERCHANT_APPROVED`, `SYSTEM_GUARD`) to prevent repudiation per threat model T-01-04.

## Test Coverage & Verification

16 new automated test cases passing in `pytest` (28 total across the full KiranaOS test suite):
- `tests/test_deterministic_engine.py` (9 tests):
  - `test_initial_zero_balance`: PASSED (0.0 balance on fresh customer)
  - `test_single_credit_and_repayment`: PASSED (credit + repayment arithmetic)
  - `test_multi_transaction_balance_aggregation`: PASSED (interleaved transactions)
  - `test_reversal_of_credit_entry`: PASSED (compensating adjustment reduces debt)
  - `test_reversal_of_repayment_entry`: PASSED (compensating adjustment restores debt)
  - `test_double_reversal_prevented`: PASSED (idempotency guard)
  - `test_reversing_a_reversal_prevented`: PASSED (reversal tree guard)
  - `test_business_events_audit_logging`: PASSED (structured JSON audit trail)
  - `test_validation_rules`: PASSED (positive amount check, non-existent customer check)
- `tests/test_identity_disambiguation.py` (7 tests):
  - `test_exact_name_match`: PASSED (Ramesh Sharma -> EXACT_MATCH)
  - `test_alias_match`: PASSED (Ramesh Bhai -> EXACT_MATCH)
  - `test_unique_substring_match`: PASSED (Priya -> EXACT_MATCH)
  - `test_ambiguous_name_triggers_disambiguation_guard`: PASSED (Suresh -> NEEDS_DISAMBIGUATION with candidate udhaar balances)
  - `test_disambiguation_logs_audit_event`: PASSED (SYSTEM_GUARD audit event logged)
  - `test_customer_not_found`: PASSED (unknown name -> NOT_FOUND)
  - `test_last_visit_timestamp_formatting`: PASSED (ISO/SQLite datetime recency parser)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test Fixture Recency Timestamp Override**
- **Found during:** Task 2 verification (`test_ambiguous_name_triggers_disambiguation_guard`)
- **Issue:** Calling `record_ledger_entry` inside the test fixture updated `customers.last_visit_date` to `CURRENT_TIMESTAMP`, which caused `format_last_visit` to display `"Today"` instead of the seeded historical `"5 days ago"`.
- **Fix:** Explicitly restored the historical `last_visit_date` timestamp in the fixture after creating the initial ledger entry to accurately simulate multi-day overdue credit.
- **Files modified:** `tests/test_identity_disambiguation.py`
- **Commit:** `412c2bb`

## Self-Check: PASSED
- [x] `backend/services/deterministic_engine.py` exists and is verified
- [x] `tests/test_deterministic_engine.py` exists and 9/9 tests pass
- [x] `tests/test_identity_disambiguation.py` exists and 7/7 tests pass
- [x] Full test suite (28/28 tests) passes in 0.11s
- [x] Commits `db33dc3` and `412c2bb` verified in git history
