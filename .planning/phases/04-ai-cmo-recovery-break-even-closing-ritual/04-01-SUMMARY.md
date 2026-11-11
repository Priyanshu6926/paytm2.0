---
phase: 04-ai-cmo-recovery-break-even-closing-ritual
plan: "01"
subsystem: cmo-deterministic-engine
tags: [cmo, deterministic-math, breakeven, festive-restock, bahi-khata, ocr, sarvam-vision]
status: complete
requires:
  - "01-01"
  - "02-01"
  - "03-01"
provides:
  - "calculate_breakeven_offer"
  - "calculate_festive_restock_forecast"
  - "batch_commit_support_on_ledger_helpers"
  - "parse_bahi_khata_page"
affects:
  - "04-02"
  - "04-03"
  - "backend/services/deterministic_engine.py"
  - "backend/services/bahi_khata_parser_service.py"
  - "tests/test_cmo_engine.py"
actuals:
  tokens: 15398
  tasks: 2
  commits: 2
  plan_head_before: d346a502af1bb6221ef63443f95d06f0ba89f6ac
  plan_head_after: 36fc4d8093cd1d55cd465b0557e281dc6f843cf0
tech-stack:
  added: []
  patterns:
    - "Pure Python Zero-LLM deterministic CMO & festive restock arithmetic"
    - "Hard-stop guardrail OFFER_BLOCKED_LOSS_MAKING when M_new <= 0"
    - "Backwards-compatible commit=False parameter for atomic multi-entry ledger batches"
    - "6.0-second timeout & 10MB upload cap with offline Marathi/Hindi fallback for Bahi-Khata OCR"
key-files:
  created:
    - backend/services/bahi_khata_parser_service.py
    - tests/test_cmo_engine.py
  modified:
    - backend/services/deterministic_engine.py
key-decisions:
  - "calculate_breakeven_offer enforces OFFER_BLOCKED_LOSS_MAKING whenever new_margin_per_unit <= 0 and rounds ratio to 9 decimals before math.ceil to prevent IEEE-754 false ceilings."
  - "calculate_festive_restock_forecast splits supplier_name on comma so 'Gupta Wholesalers, APMC Vashi' and 'Gupta Wholesalers' both produce natural Hindi draft referencing Gupta Wholesalers."
  - "Added optional commit: bool = True to log_business_event, record_ledger_entry, add_credit_entry, and add_repayment_entry for atomic Bahi-Khata batch onboarding without breaking existing callers."
  - "bahi_khata_parser_service uses read-only _match_customers_readonly lookup (exact phone/name/alias, then >=2-char substring) so OCR preview never emits SYSTEM_GUARD business_events."
patterns-established:
  - "CMO deterministic math lives exclusively in backend/services/deterministic_engine.py with finite-number and range validation."
  - "Read-only OCR proposal services classify SQLite customer ambiguity without mutating audit or financial tables."
requirements-completed:
  - CMO-04
  - CMO-06
  - ONBOARD-01
coverage:
  - id: D1
    description: "Deterministic break-even offer guardrail engine (calculate_breakeven_offer) blocking loss-making discounts"
    requirement: CMO-04
    verification:
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_breakeven_offer_benchmark"
        status: pass
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_breakeven_offer_loss_making_hard_stop"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deterministic 3.5x Diwali festive restock forecast engine (calculate_festive_restock_forecast)"
    requirement: CMO-06
    verification:
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_festive_restock_benchmark"
        status: pass
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_festive_restock_surplus_clamps_to_zero"
        status: pass
    human_judgment: false
  - id: D3
    description: "Handwritten Bahi-Khata OCR parser service with 6.0s timeout, 10MB guard, and read-only customer matching"
    requirement: ONBOARD-01
    verification:
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_bahi_khata_demo_preset_parsing"
        status: pass
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_bahi_khata_timeout_survivability_6s"
        status: pass
      - kind: unit
        ref: "tests/test_cmo_engine.py#test_bahi_khata_customer_match_classification"
        status: pass
    human_judgment: false
duration: 4m
completed: "2026-11-11"
---

# Phase 04 Plan 01: Deterministic CMO & Festive Restock Engines + Handwritten Bahi-Khata OCR Service Summary

**Pure Python break-even offer guardrail (`calculate_breakeven_offer`), 3.5x Diwali festive restock forecaster (`calculate_festive_restock_forecast`), transactional `commit=False` ledger batch support, and 6.0s-timeout Handwritten Bahi-Khata OCR service (`parse_bahi_khata_page`).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-11T17:00:20Z
- **Completed:** 2026-11-11T17:04:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented `calculate_breakeven_offer` in `backend/services/deterministic_engine.py` matching the Haldiram Aloo Bhujia 400g benchmark (`₹72` cost, `₹95` price, `₹10` discount, `4/day` -> `8` required, `+4` extra), enforcing `OFFER_BLOCKED_LOSS_MAKING` when `M_new <= 0`, and guarding against zero/negative/non-finite inputs.
- Implemented `calculate_festive_restock_forecast` in `backend/services/deterministic_engine.py` matching the Amul Pure Ghee 1L Diwali benchmark (`2.0/day * 3.5 * 5 days = 35` demand, `4` in stock -> `31 tins` order draft for Gupta Wholesalers) and clamping surplus stock to `0`.
- Added backwards-compatible `commit: bool = True` to `log_business_event`, `record_ledger_entry`, `add_credit_entry`, and `add_repayment_entry` so multi-entry batch workflows can execute inside a single SQLite transaction.
- Created `backend/services/bahi_khata_parser_service.py` with `REQUEST_TIMEOUT_SECONDS = 6.0`, `MAX_IMAGE_BYTES = 10 * 1024 * 1024`, secret-safe logging, `DEMO_BAHI_KHATA_PAGE` Marathi/Hindi fallback (4 rows totaling ₹1,290.00), and non-mutating SQLite customer classification (`EXISTING_CUSTOMER`, `NEW_CUSTOMER`, `AMBIGUOUS`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Deterministic break-even offer guardrail and festive restock forecast engines** - `3a42d52` (feat)
2. **Task 2: Handwritten Bahi-Khata OCR parser service with 6s timeout and customer matching** - `36fc4d8` (feat)

## Files Created/Modified

- `backend/services/deterministic_engine.py` - Added `calculate_breakeven_offer`, `calculate_festive_restock_forecast`, `_to_finite_float`, and `commit: bool = True` parameter on ledger/event helpers.
- `backend/services/bahi_khata_parser_service.py` - Added Sarvam Vision notebook OCR parser with 6.0s timeout, 10MB payload cap, Marathi/Hindi demo fallback, and read-only SQLite customer match classification.
- `tests/test_cmo_engine.py` - Added 19 unit tests covering break-even benchmarks, loss-making hard stops, festive restock forecasts, `commit=False` atomic rollback, Bahi-Khata demo presets, 10MB guardrails, 6s timeout survivability, and customer match classification.

## Decisions Made

- Used `round(..., 9)` before `math.ceil` in `calculate_breakeven_offer` and `calculate_festive_restock_forecast` to eliminate IEEE-754 binary floating-point false-ceiling artifacts while keeping pure stdlib `math`.
- Split `supplier_name` on `,` (`supplier_name.split(",")[0].strip()`) in `calculate_festive_restock_forecast` so both `"Gupta Wholesalers"` and `"Gupta Wholesalers, APMC Vashi"` render naturally in `one_tap_order_draft`.
- Implemented read-only `_match_customers_readonly` in `bahi_khata_parser_service.py` instead of calling `resolve_customer_identity` directly, ensuring OCR preview never writes `SYSTEM_GUARD` rows to `business_events`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required (Sarvam Vision OCR uses `SARVAM_API_KEY` when configured and degrades automatically to `DEMO_BAHI_KHATA_PAGE` otherwise).

## Verification & Test Results

- `pytest tests/test_cmo_engine.py -v`: **19 passed in 0.12s**
- `pytest -v`: **112 passed, 1 warning in 0.67s** (zero regressions across all existing suites)

## Self-Check: PASSED

- FOUND: `backend/services/deterministic_engine.py`
- FOUND: `backend/services/bahi_khata_parser_service.py`
- FOUND: `tests/test_cmo_engine.py`
- FOUND: `.planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-01-SUMMARY.md`
- FOUND commit: `3a42d52`
- FOUND commit: `36fc4d8`

---
*Phase: 04-ai-cmo-recovery-break-even-closing-ritual*
*Completed: 2026-11-11*
