---
phase: 04-ai-cmo-recovery-break-even-closing-ritual
plan: "03"
subsystem: cmo-closing-ritual-and-bahi-khata-onboarding
tags: [cmo, closing-ritual, diwali-forecast, bahi-khata, ocr, atomic-onboarding, fastapi, sarvam]
status: complete
requires:
  - "04-01"
  - "04-02"
provides:
  - "cmo_router_dukaan_closing_ritual"
  - "cmo_router_scan_bahi_khata"
  - "cmo_router_confirm_bahi_khata"
affects:
  - "backend/routers/cmo_router.py"
  - "tests/test_cmo_closing_and_bahi_khata.py"
actuals:
  tokens: 8062
  tasks: 2
  commits: 2
  plan_head_before: b000c726e042d1f6253edf2e1825b5f2862da78f
  plan_head_after: 0592b2e7351c5f0925fe6803f710dad02e69e883
tech-stack:
  added: []
  patterns:
    - "Deterministic EOD SQLite aggregation paired with calculate_festive_restock_forecast and Bulbul TTS"
    - "Multipart upload / JSON demo sample duality on POST /api/v1/cmo/scan-bahi-khata with 6.0s timeout fallback"
    - "Single atomic SQLite transaction onboarding new and existing customers with batch_ref idempotency and rollback safety"
key-files:
  created:
    - tests/test_cmo_closing_and_bahi_khata.py
  modified:
    - backend/routers/cmo_router.py
key-decisions:
  - "Anchored today_qr_sales on the PRD §7.3/§7.6 Rs 6,450.00 daily Paytm QR baseline plus live confirmed PAYTM_QR repayments recorded today."
  - "Enforced exact customer disambiguation in confirm-bahi-khata when a row without customer_id matches multiple customers by name or normalized phone, rolling back the entire batch on HTTP 400."
  - "Reused bahi_khata_parser_service._normalize_phone for consistent 10-digit phone matching across preview and atomic batch confirmation."
patterns-established:
  - "Bahi-khata batch confirmation assigns deterministic provider_ref keys (BAHI-{batch_ref}-{row_index}) for append-only idempotency."
  - "Closing ritual aggregates live recovery and unmatched UPI queue counts dynamically without modifying ledger state."
requirements-completed:
  - CMO-06
  - ONBOARD-01
coverage:
  - id: D1
    description: "60-Second Dukaan Closing Ritual with live QR sales, recovered udhaar, unmatched UPI count, 3.5x Diwali Ghee restock forecast, and Bulbul TTS speech"
    requirement: CMO-06
    verification:
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_dukaan_closing_ritual_baseline"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_dukaan_closing_ritual_reflects_live_udhaar_recovery"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_dukaan_closing_ritual_includes_live_paytm_qr_today"
        status: pass
    human_judgment: false
  - id: D2
    description: "Handwritten Bahi-Khata batch scanning (demo sample and file upload with 6.0s fallback) and 1-tap atomic onboarding with batch_ref idempotency and rollback"
    requirement: ONBOARD-01
    verification:
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_scan_bahi_khata_demo_sample"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_scan_bahi_khata_file_upload_with_timeout_fallback"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_confirm_bahi_khata_atomic_onboarding"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_confirm_bahi_khata_idempotency_and_atomic_rollback"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_closing_and_bahi_khata.py#test_confirm_bahi_khata_ambiguous_customer_blocks_and_rolls_back"
        status: pass
    human_judgment: false
duration: 4m
completed: "2026-11-11"
---

# Phase 04 Plan 03: 60-Second Dukaan Closing Ritual & Bahi-Khata Atomic Onboarding Summary

**Extended `backend/routers/cmo_router.py` with `GET /api/v1/cmo/dukaan-closing-ritual` (deterministic 3.5x Diwali Ghee forecast + Bulbul TTS briefing) and Handwritten Bahi-Khata batch scanning/onboarding endpoints (`POST /api/v1/cmo/scan-bahi-khata`, `POST /api/v1/cmo/confirm-bahi-khata`) backed by atomic SQLite transactions and `batch_ref` idempotency.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-11T17:10:23Z
- **Completed:** 2026-11-11T17:13:46Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented `GET /api/v1/cmo/dukaan-closing-ritual` aggregating today's Paytm QR sales (`6450.00` baseline + today's confirmed `PAYTM_QR` repayments), today's recovered udhaar (`REPAYMENT_JAMA`), pending `unmatched_payments_queue` count, deterministic 3.5x Diwali restock forecast for `Amul Pure Ghee 1L` (4 in stock, 35 projected 5-day demand, 31 order qty for Gupta Wholesalers) via `calculate_festive_restock_forecast`, and synthesized Hindi Bulbul TTS audio (`tts_audio_base64`).
- Implemented `POST /api/v1/cmo/scan-bahi-khata` accepting either multipart notebook image uploads or `use_demo_sample=True` via `bahi_khata_parser_service.parse_bahi_khata_page` with 10MB cap and 6.0s Sarvam Vision fallback.
- Implemented `POST /api/v1/cmo/confirm-bahi-khata` wrapping customer creation/matching, append-only `CREDIT_UDHAAR` entries (`add_credit_entry`), and consolidated `CMO_GROWTH` `business_events` logging inside a single atomic SQLite transaction with `batch_ref` idempotency (`BAHI-{batch_ref}-%`) and rollback on invalid IDs or ambiguous matches.
- Created `tests/test_cmo_closing_and_bahi_khata.py` with 8 integration tests covering closing ritual baselines, live udhaar recovery and QR repayments, demo/upload bahi-khata scanning, atomic batch onboarding, `batch_ref` idempotency, and full transaction rollback on invalid IDs or ambiguous matches.

## Task Commits

Each task was committed atomically:

1. **Task 1: 60-Second Dukaan Closing Ritual endpoint with deterministic Diwali restock forecast** - `74b8fc9` (feat)
2. **Task 2: Handwritten Bahi-Khata batch scan and 1-tap atomic onboarding endpoints** - `0592b2e` (feat)

## Files Created/Modified

- `backend/routers/cmo_router.py` - Added `GET /dukaan-closing-ritual`, `POST /scan-bahi-khata`, `POST /confirm-bahi-khata`, and Pydantic request schemas (`BahiKhataConfirmEntry`, `ConfirmBahiKhataRequest`).
- `tests/test_cmo_closing_and_bahi_khata.py` - Added 8 integration tests verifying closing ritual math/TTS, live recovery reflection, bahi-khata OCR fallback, atomic onboarding, idempotency, and rollback safety.

## Decisions Made

- Anchored `today_qr_sales` on the PRD §7.3/§7.6 ₹6,450.00 daily Paytm QR baseline plus live confirmed `PAYTM_QR` repayments recorded today.
- Enforced strict ambiguity rejection (HTTP 400 + transaction rollback) if a bahi-khata confirmation row without `customer_id` matches multiple customers by lowercase name or normalized phone.
- Reused `_normalize_phone` from `backend/services/bahi_khata_parser_service.py` so OCR preview matching and batch confirmation matching apply identical 10-digit phone normalization.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - runs cleanly offline with deterministic fallbacks when `SARVAM_API_KEY` is absent and upgrades transparently to live Sarvam APIs when configured.

## Verification & Test Results

- `pytest tests/test_cmo_closing_and_bahi_khata.py -v`: **8 passed, 1 warning in 0.21s**
- `pytest -v`: **130 passed, 1 warning in 0.81s** (zero regressions across all suites)

## Self-Check: PASSED

- FOUND: `backend/routers/cmo_router.py`
- FOUND: `tests/test_cmo_closing_and_bahi_khata.py`
- FOUND: `.planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-03-SUMMARY.md`
- FOUND commit: `74b8fc9`
- FOUND commit: `0592b2e`

---
*Phase: 04-ai-cmo-recovery-break-even-closing-ritual*
*Completed: 2026-11-11*
