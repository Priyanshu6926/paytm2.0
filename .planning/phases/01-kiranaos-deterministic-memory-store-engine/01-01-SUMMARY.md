---
phase: 01-kiranaos-deterministic-memory-store-engine
plan: 01
subsystem: database
tags:
  - sqlite
  - wal
  - triggers
  - append-only
  - schema
  - kiranaos
requires: []
provides:
  - authoritative-8-table-schema
  - sqlite-connection-manager
  - append-only-triggers
affects:
  - 01-02
  - 01-03
tech-stack:
  added:
    - sqlite3 (standard library)
    - pytest
  patterns:
    - wal-mode
    - before-update-abort-triggers
    - before-delete-abort-triggers
    - dictionary-row-factory
key-files:
  created:
    - backend/database/schema.sql
    - backend/database/connection.py
    - tests/test_connection.py
    - tests/test_schema.py
  modified: []
decisions:
  - "D-01: Built-in Python sqlite3 driver used exclusively to enforce zero external database driver dependencies."
  - "D-02: Strict BEFORE UPDATE and BEFORE DELETE triggers raise ABORT on ledger_entries, stock_events, and business_events to enforce the Law of Append-Only Immutability at the hardware SQLite level."
  - "D-05: SQLite WAL mode and 5000ms busy timeout configured to guarantee concurrent read performance and avoid database locking."
metrics:
  duration: 5m
  completed: 2026-11-09
status: complete
actuals:
  tokens: 21000
  tasks: 2
  commits: 2
---

# Phase 01 Plan 01: KiranaOS Authoritative Database & Connection Manager Summary

**One-liner:** Established KiranaOS SQLite connection manager with WAL mode and hardware-level append-only triggers across all 8 PRD §6 tables.

## Objectives Achieved

1. **SQLite Connection Manager (`backend/database/connection.py`)**:
   - Thread-safe connection opening with `PRAGMA foreign_keys = ON`.
   - `PRAGMA journal_mode = WAL` on file databases.
   - `PRAGMA busy_timeout = 5000` (5s lock protection per threat model T-01-03).
   - `row_factory = sqlite3.Row` for dictionary-style attribute access.
   - Idempotent directory creation and safe connection closing.

2. **Authoritative 8-Table Schema (`backend/database/schema.sql`)**:
   - `customers` (identity, JSON aliases, phone, language, cycle days).
   - `ledger_entries` (immutable financial records with `CHECK (amount > 0)`).
   - `inventory_items` (SKU catalog, pricing, cost, burn rate, festive multiplier).
   - `stock_events` (immutable inward/outward inventory movements).
   - `supplier_ledger` (distributor khata with price creep flags).
   - `unmatched_payments_queue` (ambiguous UPI review queue).
   - `campaigns_and_links` (attributed growth campaigns & Paytm links).
   - `business_events` (unified audit log with `evidence_json`).

3. **Hardware-Level Append-Only Immutability**:
   - Implemented `BEFORE UPDATE` and `BEFORE DELETE` triggers on `ledger_entries`, `stock_events`, and `business_events`.
   - Triggers execute `RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.')`.
   - Direct mutation attempts fail with `sqlite3.IntegrityError` or `sqlite3.OperationalError`.

## Test Coverage & Verification

12 automated test cases passing in `pytest`:
- `tests/test_connection.py`:
  - `test_get_db_connection_in_memory`: PASSED
  - `test_get_db_connection_file_wal_mode`: PASSED
  - `test_close_db_connection`: PASSED
  - `test_row_factory_dictionary_access`: PASSED
  - `test_init_db_runs_safely`: PASSED
- `tests/test_schema.py`:
  - `test_all_eight_tables_exist`: PASSED (all 8 tables confirmed)
  - `test_ledger_entries_check_constraint`: PASSED (zero and negative amounts rejected)
  - `test_ledger_entries_append_only_triggers`: PASSED (UPDATE/DELETE aborted)
  - `test_stock_events_append_only_triggers`: PASSED (UPDATE/DELETE aborted)
  - `test_business_events_append_only_triggers`: PASSED (UPDATE/DELETE aborted)
  - `test_foreign_key_constraints`: PASSED (foreign key enforcement verified)
  - `test_unique_constraints`: PASSED (SKU, UPI ID, and slug uniqueness enforced)

## Deviations from Plan

### Auto-fixed Issues
None - plan executed exactly as written.

## Self-Check: PASSED
- [x] `backend/database/schema.sql` exists and contains 8 tables + append-only triggers.
- [x] `backend/database/connection.py` exists with `get_db_connection`, `init_db`, `close_db_connection`.
- [x] `tests/test_connection.py` exists and passes.
- [x] `tests/test_schema.py` exists and passes.
- [x] Commits 0a9cbb8 and 02ceb16 exist in git history.
