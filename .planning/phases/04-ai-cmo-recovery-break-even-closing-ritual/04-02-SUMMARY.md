---
phase: 04-ai-cmo-recovery-break-even-closing-ritual
plan: "02"
subsystem: cmo-recovery-and-offers-api
tags: [cmo, boli-baki, soundbox, breakeven, dead-stock, attribution, fastapi, sarvam]
status: complete
requires:
  - "04-01"
  - "01-01"
  - "02-01"
provides:
  - "cmo_router_boli_baki_recovery"
  - "cmo_router_soundbox_webhook_clearing"
  - "cmo_router_dead_stock_breakeven_studio"
  - "cmo_router_per_language_attribution"
affects:
  - "04-03"
  - "backend/routers/cmo_router.py"
  - "backend/main.py"
  - "tests/test_cmo_recovery_and_offers.py"
actuals:
  tokens: 14144
  tasks: 2
  commits: 2
  plan_head_before: 71b2a20b7edc149c990155267e54a9217969594e
  plan_head_after: e1eddd40217f563e7744a95ffad112c655c2e11c
tech-stack:
  added: []
  patterns:
    - "FastAPI APIRouter mounted at /api/v1/cmo with Pydantic request validation"
    - "Idempotent tracked Paytm payment link lifecycle (SENT -> PAID -> ALREADY_PAID) with provider_ref guard"
    - "Atomic SQLite transaction clearing balance via append-only REPAYMENT_JAMA + Soundbox chime TTS"
    - "Idempotent per-language DEAD_STOCK_BUNDLE campaign links preserving clicks, conversions, and revenue"
key-files:
  created:
    - backend/routers/cmo_router.py
    - tests/test_cmo_recovery_and_offers.py
  modified:
    - backend/main.py
key-decisions:
  - "Formatted clean localized Marathi/Hindi Boli-Baki and dead-stock offer strings whenever offline Sarvam Translate returns an unmapped [lang] prefix for dynamic names or prices."
  - "Enforced dual idempotency in simulate-link-paid/{slug} on both campaigns_and_links.status == 'PAID' and ledger_entries.provider_ref == 'PAYTM-LINK-{id}-{slug}' inside an atomic SQLite transaction."
  - "Derived clean SKU promo slug tokens (e.g. 'bhujia' for Haldiram Aloo Bhujia 400g) with collision fallback suffixing item_id only if another SKU owns that slug."
  - "Supported both query parameter and JSON body for converted flag on POST /simulate-promo-click/{slug}."
patterns-established:
  - "CMO campaign links preserve cumulative clicks, conversions, and revenue_collected across repeated campaign generation calls."
  - "All CMO financial clearing and guardrail blocks emit structured CMO_GROWTH audit rows in business_events."
requirements-completed:
  - CMO-01
  - CMO-02
  - CMO-03
  - CMO-04
  - CMO-05
coverage:
  - id: D1
    description: "Overdue debtor detection (>10 days, balance > 0) and Boli-Baki multilingual voice reminder + tracked Paytm link generation"
    requirement: CMO-01
    verification:
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_overdue_debtors"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_boli_baki_recovery_generation"
        status: pass
    human_judgment: false
  - id: D2
    description: "Voice note synthesis in customer native language via Sarvam Bulbul v3 TTS"
    requirement: CMO-02
    verification:
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_boli_baki_recovery_generation"
        status: pass
    human_judgment: false
  - id: D3
    description: "Idempotent Soundbox payment webhook clearing with append-only REPAYMENT_JAMA and Hindi chime"
    requirement: CMO-03
    verification:
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_simulate_link_paid_and_soundbox_chime"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_simulate_link_paid_idempotency"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dead-stock discovery (>15 days unsold) and Break-Even Guardrail blocking loss-making discounts"
    requirement: CMO-04
    verification:
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_dead_stock_query"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_dead_stock_campaign_loss_making_blocked"
        status: pass
    human_judgment: false
  - id: D5
    description: "Idempotent mr-IN vs hi-IN promo links and independent click/conversion/revenue attribution"
    requirement: CMO-05
    verification:
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_dead_stock_campaign_safe_breakeven_and_idempotency"
        status: pass
      - kind: integration
        ref: "tests/test_cmo_recovery_and_offers.py#test_simulate_promo_click_per_language_attribution"
        status: pass
    human_judgment: false
duration: 4m
completed: "2026-11-11"
---

# Phase 04 Plan 02: AI CMO Boli-Baki Recovery & Dead-Stock Break-Even Studio Summary

**FastAPI AI CMO router (`/api/v1/cmo`) delivering Boli-Baki multilingual voice udhaar recovery with atomic Soundbox webhook clearing and Dead-Stock Break-Even Studio with idempotent `mr-IN` vs `hi-IN` promo link attribution.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-11T17:05:17Z
- **Completed:** 2026-11-11T17:09:14Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `backend/routers/cmo_router.py` and mounted it at `/api/v1/cmo` in `backend/main.py`.
- Implemented `GET /api/v1/cmo/overdue-debtors` surfacing Ramesh Sharma (`₹650.00`, 18 days overdue, `mr-IN`) with active `UDHAAR_VOICE_LINK` status while filtering out non-overdue or zero-balance customers.
- Implemented `POST /api/v1/cmo/boli-baki-recovery` combining Sarvam Translate + Bulbul v3 TTS + idempotent `campaigns_and_links` persistence and `CMO_GROWTH` audit logging.
- Implemented `POST /api/v1/cmo/simulate-link-paid/{slug}` with dual idempotency (`status == 'PAID'` and `provider_ref`), atomic `REPAYMENT_JAMA` (`payment_mode='PAYTM_LINK'`) balance clearing, and playable Hindi Soundbox chime (`"Paytm par 650 rupaye prapt hue"`).
- Implemented `GET /api/v1/cmo/dead-stock`, `POST /api/v1/cmo/dead-stock-campaign`, and `POST /api/v1/cmo/simulate-promo-click/{slug}` enforcing `OFFER_BLOCKED_LOSS_MAKING` for below-cost discounts while creating/preserving `mr-IN` and `hi-IN` promo attribution metrics.
- Wrote 10 comprehensive integration and validation tests in `tests/test_cmo_recovery_and_offers.py` covering every happy path, idempotency guard, hard-stop guardrail, and HTTP 400/404/422 boundary.

## Task Commits

Each task was committed atomically:

1. **Task 1: AI CMO router setup and Boli-Baki voice udhaar recovery with Soundbox webhook clearing** - `9c8044c` (feat)
2. **Task 2: Dead-stock Break-Even Studio and per-language campaign attribution endpoints** - `e1eddd4` (feat)

## Files Created/Modified

- `backend/routers/cmo_router.py` - Added AI CMO router with `/overdue-debtors`, `/boli-baki-recovery`, `/simulate-link-paid/{slug}`, `/dead-stock`, `/dead-stock-campaign`, and `/simulate-promo-click/{slug}`.
- `backend/main.py` - Imported and registered `cmo_router` via `app.include_router(cmo_router)`.
- `tests/test_cmo_recovery_and_offers.py` - Added 10 integration tests covering Boli-Baki recovery, Soundbox clearing, idempotency, Dead-Stock Break-Even guardrails, per-language attribution, and input validation.

## Decisions Made

- Used localized fallback formatting when offline `sarvam_engine.translate_text` returns a `[lang]` prefix for dynamic customer names or discounted prices so voice prompts stay natural offline.
- Added dual idempotency check (`campaigns_and_links.status == 'PAID'` plus `ledger_entries.provider_ref`) in `simulate_link_paid` to prevent duplicate repayments under concurrent or replayed webhooks.
- Supported both query parameter and optional JSON body for `converted` in `POST /api/v1/cmo/simulate-promo-click/{slug}` for clean frontend and test ergonomics.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - works out of the box with deterministic local fallbacks when `SARVAM_API_KEY` is absent and upgrades transparently to live Sarvam APIs when configured.

## Verification & Test Results

- `pytest tests/test_cmo_recovery_and_offers.py -v`: **10 passed, 1 warning in 0.28s**
- `pytest -v`: **122 passed, 1 warning in 0.74s** (zero regressions across all existing suites)

## Self-Check: PASSED

- FOUND: `backend/routers/cmo_router.py`
- FOUND: `backend/main.py`
- FOUND: `tests/test_cmo_recovery_and_offers.py`
- FOUND: `.planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-02-SUMMARY.md`
- FOUND commit: `9c8044c`
- FOUND commit: `e1eddd4`

---
*Phase: 04-ai-cmo-recovery-break-even-closing-ritual*
*Completed: 2026-11-11*
