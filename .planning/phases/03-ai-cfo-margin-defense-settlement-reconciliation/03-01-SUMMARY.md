---
phase: 03-ai-cfo-margin-defense-settlement-reconciliation
plan: "01"
subsystem: cfo-deterministic-engine
tags: [cfo, deterministic-math, price-creep, settlement-reconciliation, ocr-parser, sarvam-vision]
status: complete
requires:
  - "01-01"
  - "02-01"
provides:
  - "calculate_price_creep"
  - "calculate_settlement_reconciliation"
  - "parse_distributor_bill"
  - "seed_demo_data_maggi_masala"
affects:
  - "03-02"
  - "backend/services/deterministic_engine.py"
  - "backend/services/bill_parser_service.py"
  - "backend/services/seed_demo_data.py"
  - "tests/test_cfo_engine.py"
tech-stack:
  added: []
  patterns:
    - "Pure Python Zero-LLM deterministic arithmetic"
    - "Strict 0.01 rupee invariant check for settlement waterfall"
    - "6.0-second timeout with offline preset fallback for distributor bill OCR"
    - "Synthesized Bulbul TTS Hindi audio alert generation for price creep"
key-files:
  created:
    - backend/services/bill_parser_service.py
    - tests/test_cfo_engine.py
  modified:
    - backend/services/deterministic_engine.py
    - backend/services/seed_demo_data.py
    - tests/test_seed_demo_data.py
    - tests/test_walking_skeleton_e2e.py
decisions:
  - "calculate_price_creep computes wholesale price creep percentage, margin erosion, and recommended retail price preserving unit margins or target markup, with benchmark Rs 160.00 for Fortune Sunlite Oil 1L."
  - "calculate_settlement_reconciliation asserts Gross QR Collections minus Deductions equals Net Bank Settlement down to exactly Rs 0.01, throwing ValueError if violated, and returns spoken Hindi summary."
  - "parse_distributor_bill queries SQLite inventory to identify price creep and outputs a proposal card with dual action preview and synthesized audio base64."
  - "Maggi Masala 70g seeded into inventory_items with current_stock=96, last_unit_cost=11.25, and selling_price=14.0."
metrics:
  duration: 6m
  completed_date: "2026-11-11"
actuals:
  tokens: 22000
  tasks: 2
  commits: 2
---

# Phase 03 Plan 01: Core Mathematical Engines & Distributor Bill OCR Parser Summary

Deterministic wholesale price-creep detection, settlement waterfall reconciliation with strict ₹0.01 balance invariant, and distributor invoice OCR parsing service with offline demo fallback for Munim AI CFO.

## Overview

Plan 03-01 delivers the foundational mathematical and multi-modal services powering the AI CFO suite in KiranaOS, strictly adhering to the **Law of Zero LLM Math** and the **Law of Demo-Day Survivability**:

1. **Deterministic Price-Creep Detection (`calculate_price_creep`)**: Computes wholesale cost increases, margin erosion, flags hikes $\ge 2.0\%$, calculates recommended retail prices (preserving margin with ₹160.00 benchmark for Fortune Oil), and produces Hindi spoken alert copy.
2. **Deterministic Settlement Waterfall Reconciliation (`calculate_settlement_reconciliation`)**: Reconciles daily Paytm QR sales against deductions (Loan EDI ₹450, Soundbox rental ₹125, refunds ₹60) down to ₹0.01 with assertion guards, generating a spoken Hindi payout explanation.
3. **Seed Catalog Enhancement**: Added "Maggi Masala 70g" to `seed_demo_data.py` so distributor invoice items match catalog records.
4. **Distributor Bill Parser Service (`parse_distributor_bill`)**: Wraps Sarvam Vision OCR with a 6.0-second timeout, falling back gracefully to high-fidelity Gupta Wholesalers invoice `GW-2026-994` (₹4,920.00 total across 3 items), detecting Fortune Oil price creep (+7.58%), computing dual-action preview ("Confirming adds +118 units to Inventory AND records Rs 4,920 payable in Gupta Wholesalers Khata"), and attaching synthesized Bulbul TTS Hindi audio.

## Task Execution Breakdown

| Task | Deliverable | Commits | Key Files | Verification |
|------|-------------|---------|-----------|--------------|
| Task 1 | Deterministic price-creep and settlement waterfall arithmetic engines | `ea8f381` | `backend/services/deterministic_engine.py`<br>`backend/services/seed_demo_data.py`<br>`tests/test_cfo_engine.py` | 8 unit tests passed in 0.02s |
| Task 2 | Distributor bill OCR parser service with offline fallback | `39b2e20` | `backend/services/bill_parser_service.py`<br>`tests/test_cfo_engine.py` | 12 unit tests passed in 0.14s |

## Key Decisions & Mitigations

- **Law of Zero LLM Math (PRD §2, §5.2, §5.3)**: Wholesale creep percentage, margin erosion, target MRP, and settlement balances are computed via standard library arithmetic with `round(..., 2)` and strict float tolerances (`< 0.001`). LLMs are never allowed to perform financial arithmetic.
- **Law of Demo-Day Survivability (PRD §2, §7.2, D-02)**: External Sarvam Vision and Bulbul TTS calls have a strict 6.0-second timeout. Any network partition, latency spike, or invalid API key triggers high-fidelity offline fallback with synthetic WAV audio and preset invoice data `GW-2026-994`.
- **Threat Model T-03-01 Mitigation**: Capped invoice upload payloads to 10MB (`MAX_IMAGE_BYTES`) and safely degraded oversized requests to fallback without unhandled server errors.

## Verification & Test Results

```bash
pytest tests/test_cfo_engine.py -v
============================== 12 passed in 0.14s ==============================

pytest -v
======================== 80 passed, 1 warning in 0.53s =========================
```

All 80 test cases across the entire KiranaOS backend pass cleanly with 100% deterministic accuracy.

## Self-Check: PASSED

- [x] `backend/services/deterministic_engine.py` exports `calculate_price_creep` and `calculate_settlement_reconciliation`
- [x] `backend/services/bill_parser_service.py` exports `parse_distributor_bill`
- [x] `backend/services/seed_demo_data.py` contains "Maggi Masala 70g"
- [x] `tests/test_cfo_engine.py` validates all price creep, settlement waterfall, and bill parsing flows
- [x] All commits exist in repository history
