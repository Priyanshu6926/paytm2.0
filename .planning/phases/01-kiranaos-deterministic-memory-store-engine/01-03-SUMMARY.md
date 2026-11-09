---
phase: 01-kiranaos-deterministic-memory-store-engine
plan: 03
subsystem: memory-api
tags:
  - fast-api
  - seed-data
  - dadar-kirana
  - walking-skeleton
  - rest-api
  - e2e-testing
requires:
  - 01-01
  - 01-02
provides:
  - dadar-mumbai-demo-seeder
  - memory-inspection-rest-api
  - walking-skeleton-e2e-harness
affects:
  - 01-04
  - 02-ai-cfo-engine
tech-stack:
  added:
    - fastapi
    - starlette
    - httpx
  patterns:
    - async-lifespan-startup-seeder
    - idempotent-upsert-seeding
    - memory-inspection-endpoints
    - e2e-testclient-harness
key-files:
  created:
    - backend/services/seed_demo_data.py
    - backend/main.py
    - backend/routers/__init__.py
    - backend/routers/memory_router.py
    - tests/test_seed_demo_data.py
    - tests/test_walking_skeleton_e2e.py
  modified:
    - backend/services/deterministic_engine.py
decisions:
  - "D-04: Seeded 'Ganesh Provision & General Store (Dadar, Mumbai)' dataset with exact deterministic balances: Ramesh Sharma (₹650.00 overdue 18d), Suresh Patil (Tailor, ₹200.00), Suresh Kadam (Kirana, ₹450.00), Priya Deshmukh (₹0.00), and key inventory items with Diwali surge & price creep triggers."
  - "D-04: Idempotent seeder checks unique identifiers (phone, provider_ref, sku_name, upi_txn_id, invoice_number) to ensure multiple seed_all executions never duplicate records or alter financial amounts."
  - "D-05: FastAPI application mounts /api/v1/memory endpoints exposing health, customer debt lists, customer ledger timelines, inventory status, and business event audit logs to serve as the KiranaOS Walking Skeleton."
metrics:
  duration: 7m
  completed: 2026-11-09
status: complete
actuals:
  tokens: 28000
  tasks: 2
  commits: 2
  plan_head_before: b91ccd8
  plan_head_after: 11873ac
---

# Phase 01 Plan 03: Pre-Seeded Mumbai Kirana Dataset & Walking Skeleton Memory Router Summary

**One-liner:** Implemented the idempotent Dadar Mumbai kirana store dataset seeder and mounted the FastAPI memory inspection router with a full end-to-end walking skeleton verification harness.

## Objectives Achieved

1. **Pre-Seeded Dadar Mumbai Kirana Store Dataset (`backend/services/seed_demo_data.py`)**:
   - Idempotently populates baseline records for **"Ganesh Provision & General Store (Dadar, Mumbai)"** per PRD §9, §11, and D-04:
     - **Customers & Balances:**
       - `Ramesh Sharma` (`+919820111222`, `mr-IN`, regular cycle 7d, visited 18d ago) with confirmed ₹650.00 `CREDIT_UDHAAR` (overdue 18 days).
       - `Suresh Patil (Tailor)` (`+919820333444`, `mr-IN`, regular cycle 4d, visited 5d ago) with confirmed ₹200.00 `CREDIT_UDHAAR`.
       - `Suresh Kadam (Kirana)` (`+919820555666`, `mr-IN`, regular cycle 3d, visited 9d ago) with confirmed ₹450.00 `CREDIT_UDHAAR`.
       - `Priya Deshmukh` (`+919820777888`, `mr-IN`, regular cycle 3d, visited 16d ago) with ₹0.00 debt.
     - **Inventory Items:**
       - `Amul Pure Ghee 1L` (stock: 4 tins, burn rate: 2.0/day, festive multiplier: 3.5x, reorder threshold: 10, supplier: Gupta Wholesalers).
       - `Fortune Sunlite Oil 1L` (stock: 12 pouches, cost: ₹132.0, selling: ₹155.0, burn rate: 3.0/day, multiplier: 1.5x).
       - `Haldiram Aloo Bhujia 400g` (stock: 28 packets, cost: ₹72.0, selling: ₹95.0, unsold for 22 days).
     - **Stock Movements & Supplier Khata:**
       - Initial inward movements recorded in `stock_events`.
       - Baseline credit of ₹5,920.00 recorded in `supplier_ledger` for `Gupta Wholesalers, APMC Vashi`.
     - **Ambiguous UPI Queue:**
       - One entry in `unmatched_payments_queue` for ₹200.00 from 'Suresh' matching Suresh Patil and Suresh Kadam with status `PENDING_REVIEW`.
     - **Attributed Growth Links & Audit Trail:**
       - Sample campaign link in `campaigns_and_links` (`paytm.me/munim-ramesh-650`).
       - Initial `SYSTEM_STARTUP` event in `business_events` logged by `SYSTEM_SEEDER`.

2. **Strict Idempotency Verification (`tests/test_seed_demo_data.py`)**:
   - Verified that running `seed_all()` multiple times preserves exact row counts across all 8 tables.
   - Guaranteed that balances do not drift, duplicate transactions are never created, and append-only constraints are respected.

3. **FastAPI Application & Memory Router (`backend/main.py`, `backend/routers/memory_router.py`)**:
   - `backend/main.py` configures FastAPI with CORS middleware and an `asynccontextmanager` lifespan handler that calls `init_db()` and `seed_all()` upon boot.
   - Mounted `/api/v1/memory` inspection router per D-05:
     - `GET /api/v1/memory/health`: Returns store name, DB connection, and validates all 8 authoritative tables are populated.
     - `GET /api/v1/memory/customers`: Lists all customers with deterministic balances, visit recency, and days overdue.
     - `GET /api/v1/memory/customers?query=Suresh` & `GET /api/v1/memory/customers/resolve`: Triggers identity disambiguation guard, returning 2 candidates with live udhaar balances and bilingual spoken prompt.
     - `GET /api/v1/memory/customers/{customer_id}/ledger`: Returns customer detail and full append-only ledger transaction history.
     - `GET /api/v1/memory/inventory`: Returns inventory items with stock, burn rate, festive multiplier, and supplier info.
     - `GET /api/v1/memory/events`: Returns chronological audit trail from `business_events` with structured `evidence_json`.

4. **End-to-End Walking Skeleton Verification (`tests/test_walking_skeleton_e2e.py`)**:
   - Using `fastapi.testclient.TestClient`, asserts all endpoints boot cleanly and respond with 200 OK.
   - Validates that Ramesh owes ₹650.00, Suresh query flags disambiguation, all 8 tables are non-empty, and unknown customer ledger returns HTTP 404.

## Test Coverage & Verification

12 new automated test cases passing in `pytest` (40 total across the full KiranaOS test suite):
- `tests/test_seed_demo_data.py` (4 tests):
  - `test_seed_demo_data_customers_and_balances`: PASSED (Ramesh ₹650, Suresh Patil ₹200, Suresh Kadam ₹450, Priya ₹0)
  - `test_seed_demo_data_inventory_and_supplier`: PASSED (Amul Ghee 4 tins 3.5x, Fortune Oil ₹132, Haldiram Bhujia 28 pkts, Supplier Khata ₹5920)
  - `test_seed_demo_data_unmatched_payments_and_business_events`: PASSED (Unmatched ₹200 Suresh payment, System startup audit event)
  - `test_seed_all_strict_idempotence`: PASSED (Repeated seed_all runs yield identical table counts and balances)
- `tests/test_walking_skeleton_e2e.py` (8 tests):
  - `test_root_endpoint`: PASSED (200 OK, online status)
  - `test_memory_health_all_eight_tables_populated`: PASSED (all 8 tables row_count > 0)
  - `test_customers_list_and_ramesh_balance`: PASSED (Ramesh ₹650.00, 18 days overdue)
  - `test_customer_identity_disambiguation_suresh_query`: PASSED (2 candidates with udhaar balances & spoken prompt)
  - `test_customer_ledger_timeline`: PASSED (append-only ledger timeline)
  - `test_customer_ledger_404_for_unknown_id`: PASSED (404 error handling)
  - `test_inventory_list`: PASSED (stock, burn rate, multipliers)
  - `test_business_events_feed`: PASSED (provenance and evidence JSON)

## Self-Check: PASSED
- Created files exist:
  - `backend/services/seed_demo_data.py`: FOUND
  - `backend/main.py`: FOUND
  - `backend/routers/memory_router.py`: FOUND
  - `tests/test_seed_demo_data.py`: FOUND
  - `tests/test_walking_skeleton_e2e.py`: FOUND
- Atomic commits exist:
  - `510b1d5`: feat(01-03): implement idempotent Dadar Mumbai kirana store dataset seeder (FOUND)
  - `11873ac`: feat(01-03): implement FastAPI memory router and walking skeleton e2e harness (FOUND)
- Full pytest test suite: 40 passed in 0.24s.
