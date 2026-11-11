---
phase: 04-ai-cmo-recovery-break-even-closing-ritual
verified: 2026-11-11T17:16:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-01-PLAN.md
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-01-SUMMARY.md
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-02-PLAN.md
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-02-SUMMARY.md
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-03-PLAN.md
  - .planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-03-SUMMARY.md
  - backend/main.py
  - backend/routers/cmo_router.py
  - backend/services/bahi_khata_parser_service.py
  - backend/services/deterministic_engine.py
  - tests/test_cmo_closing_and_bahi_khata.py
  - tests/test_cmo_engine.py
  - tests/test_cmo_recovery_and_offers.py
covered_digest: "v4:sha256:bd44fa03f0d79025d6c9c41a09c21093b9b299a74ad30bd13bdc30db856b1566"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "Merchant can trigger the 60-Second Dukaan Closing Ritual to hear spoken net settlement, recovered udhaar, and a deterministic 3.5x Diwali festive restock forecast (CMO-06, PRD §7.6, FR-09)."
    - "Physical bahi-khata notebook photos parse via multimodal OCR into batch credit proposals for 1-tap merchant onboarding (ONBOARD-01, PRD FR-10)."
  gaps_remaining: []
  regressions: []
---

# Phase 4: AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual Verification Report

**Phase Goal:** Accelerate store cash recovery through polite vernacular voice reminders, simulated Soundbox payment webhooks, margin-safe discount promotions, notebook OCR onboarding, and an evening closing ritual.  
**Verified:** 2026-11-11T17:16:00Z  
**Status:** passed  
**Re-verification:** Yes — after gap closure (execution of `04-03-PLAN.md`)  

---

## Goal Achievement

All 3 Phase 4 plans (`04-01`, `04-02`, `04-03`) are complete, wired, and verified against the codebase. Every roadmap success criterion (7/7), requirement (`CMO-01` through `CMO-06`, `ONBOARD-01`), PRD specification (§5.4, §5.5, §7.4, §7.5, §7.6, FR-07 through FR-10), and all 9 `/api/v1/cmo/*` endpoints pass with zero stubs or placeholders.

### Observable Truths (Roadmap Success Criteria)

| # | Truth / Success Criterion | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | System surfaces debtors overdue >10 days and creates personalized reminders translated into the customer's native tongue (Hindi or Marathi). | ✓ VERIFIED | `GET /api/v1/cmo/overdue-debtors` and `POST /api/v1/cmo/boli-baki-recovery` in `backend/routers/cmo_router.py` (lines 174–405) compute balances via `calculate_customer_balance`, filter `overdue_days > 10` & `outstanding > 0`, and translate via `sarvam_engine.translate_text` with localized Marathi/Hindi templates. Tested by `test_overdue_debtors` and `test_boli_baki_recovery_generation`. |
| 2 | Debtor reminders include synthesized Bulbul voice notes and unique tracked Paytm payment links (`paytm.me/munim-...`). | ✓ VERIFIED | `create_boli_baki_recovery` synthesizes `tts_audio_base64` via `sarvam_engine.synthesize_speech`, persists `paytm.me/munim-...` in `campaigns_and_links`, and returns `paytm_payment_link` + `simulate_webhook_endpoint`. Valid RIFF/WAVE audio verified by `test_boli_baki_recovery_generation`. |
| 3 | Simulating payment on a generated payment link fires an instant webhook, clears the debtor ledger balance, and triggers a live Paytm Soundbox chime. | ✓ VERIFIED | `POST /api/v1/cmo/simulate-link-paid/{slug}` (lines 408–558) enforces dual idempotency (`status == 'PAID'` and `provider_ref`), appends `REPAYMENT_JAMA` (`payment_mode='PAYTM_LINK'`), logs `CMO_GROWTH`, and generates `"Paytm par 650 rupaye prapt hue"` Soundbox TTS. Verified by `test_simulate_link_paid_and_soundbox_chime` and `test_simulate_link_paid_idempotency`. |
| 4 | Break-Even Studio calculates required sales volume before allowing discounts on dead stock (>15d unsold) and strictly blocks loss-making promotions. | ✓ VERIFIED | `calculate_breakeven_offer` in `backend/services/deterministic_engine.py` (lines 781–868) matches PRD §5.4 benchmark (Haldiram Aloo Bhujia 400g: ₹72 cost, ₹95 price, ₹10 discount, 4/day → 8 required, +4 extra) and blocks `M_new <= 0` with `OFFER_BLOCKED_LOSS_MAKING`. Wired via `GET /api/v1/cmo/dead-stock` and `POST /api/v1/cmo/dead-stock-campaign`. Verified by 11 unit tests + 3 router tests. |
| 5 | Campaign performance tracks click and payment conversion metrics partitioned by Hindi and Marathi links. | ✓ VERIFIED | `create_dead_stock_campaign` creates/updates idempotent `mr-IN` and `hi-IN` rows in `campaigns_and_links` without resetting metrics; `POST /api/v1/cmo/simulate-promo-click/{slug}` (lines 841–970) increments `clicks`, `conversions`, and `revenue_collected` independently. Verified by `test_dead_stock_campaign_safe_breakeven_and_idempotency` and `test_simulate_promo_click_per_language_attribution`. |
| 6 | Merchant can trigger the 60-Second Dukaan Closing Ritual to hear spoken net settlement, recovered udhaar, and a deterministic 3.5x Diwali festive restock forecast. | ✓ VERIFIED | `calculate_festive_restock_forecast` in `deterministic_engine.py` (lines 871–929) and `GET /api/v1/cmo/dukaan-closing-ritual` in `cmo_router.py` (lines 978–1088) aggregate today's QR sales (`6450.00` + live `PAYTM_QR`), today's recovered udhaar (`REPAYMENT_JAMA`), pending `unmatched_payments_queue` count, Amul Pure Ghee 1L 3.5x Diwali forecast (35 demand, 31 order qty for Gupta Wholesalers), `spoken_ritual_hi`, and playable Bulbul `tts_audio_base64`. Verified by `test_dukaan_closing_ritual_baseline`, `test_dukaan_closing_ritual_reflects_live_udhaar_recovery`, and `test_dukaan_closing_ritual_includes_live_paytm_qr_today`. |
| 7 | Physical bahi-khata notebook photos parse via multimodal OCR into batch credit proposals for 1-tap merchant onboarding. | ✓ VERIFIED | `parse_bahi_khata_page` in `bahi_khata_parser_service.py` (6.0s timeout, 10MB cap, offline Marathi/Hindi fallback, read-only `EXISTING_CUSTOMER`/`NEW_CUSTOMER`/`AMBIGUOUS` classification) wired to `POST /api/v1/cmo/scan-bahi-khata` (lines 1096–1133) and `POST /api/v1/cmo/confirm-bahi-khata` (lines 1136–1305) with single atomic SQLite transaction (`commit=False` + `conn.commit()`/`conn.rollback()`), `batch_ref` idempotency (`BAHI-{batch_ref}-%`), ambiguity guard, and `CMO_GROWTH` logging. Verified by 5 tests in `test_cmo_closing_and_bahi_khata.py` + 5 unit tests in `test_cmo_engine.py`. |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

---

### Advisory (New Scope, Unevidenced)

None.

---

### Requirements Coverage

| Requirement | Source Plan(s) | PRD Reference | Status | Evidence |
|-------------|----------------|---------------|--------|----------|
| **CMO-01** | `04-02` | PRD §7.4, FR-07 | ✓ SATISFIED | `GET /api/v1/cmo/overdue-debtors` & `POST /api/v1/cmo/boli-baki-recovery` surface debtors overdue >10 days and translate reminders to `mr-IN`/`hi-IN`. |
| **CMO-02** | `04-02` | PRD §7.4, FR-07 | ✓ SATISFIED | `POST /api/v1/cmo/boli-baki-recovery` synthesizes Bulbul v3 audio (`tts_audio_base64`) and issues tracked `paytm.me/munim-...` links. |
| **CMO-03** | `04-02` | PRD §7.4, FR-07 | ✓ SATISFIED | `POST /api/v1/cmo/simulate-link-paid/{slug}` clears ledger balance idempotently via `REPAYMENT_JAMA` (`PAYTM_LINK`) and returns Soundbox audio chime. |
| **CMO-04** | `04-01`, `04-02` | PRD §5.4, §7.5, FR-08 | ✓ SATISFIED | `calculate_breakeven_offer`, `GET /dead-stock`, and `POST /dead-stock-campaign` compute required volume and block loss-making offers (`OFFER_BLOCKED_LOSS_MAKING`). |
| **CMO-05** | `04-02` | PRD §7.5, FR-08 | ✓ SATISFIED | `POST /dead-stock-campaign` & `POST /simulate-promo-click/{slug}` track `mr-IN` vs `hi-IN` clicks, conversions, and revenue persistently. |
| **CMO-06** | `04-01`, `04-03` | PRD §5.5, §7.6, FR-09 | ✓ SATISFIED | `calculate_festive_restock_forecast` and `GET /api/v1/cmo/dukaan-closing-ritual` deliver EOD QR sales, recovered udhaar, unmatched UPI count, 3.5x Diwali forecast, and Bulbul TTS audio. |
| **ONBOARD-01** | `04-01`, `04-03` | PRD FR-10 | ✓ SATISFIED | `parse_bahi_khata_page`, `POST /api/v1/cmo/scan-bahi-khata`, and `POST /api/v1/cmo/confirm-bahi-khata` deliver 6.0s-fallback OCR proposals and atomic batch onboarding with idempotency and rollback. |

---

### Required Artifacts

| Artifact | Expected Purpose | Exists | Substantive | Wired | Status |
|----------|------------------|--------|-------------|-------|--------|
| `backend/services/deterministic_engine.py` | Pure Python `calculate_breakeven_offer`, `calculate_festive_restock_forecast`, and `commit: bool = True` batch transaction support | ✓ | ✓ (932 lines) | ✓ (imported by `cmo_router.py`, `bahi_khata_parser_service.py`) | ✓ VERIFIED |
| `backend/services/bahi_khata_parser_service.py` | Sarvam Vision OCR notebook parser (6.0s timeout, 10MB limit, offline fallback, read-only customer match classification) | ✓ | ✓ (323 lines) | ✓ (imported by `cmo_router.py`) | ✓ VERIFIED |
| `backend/routers/cmo_router.py` | AI CMO router mounted at `/api/v1/cmo` exposing all 9 endpoints | ✓ | ✓ (1,305 lines) | ✓ (mounted in `backend/main.py`) | ✓ VERIFIED |
| `backend/main.py` | Application entrypoint mounting `cmo_router` via `app.include_router(cmo_router)` | ✓ | ✓ (72 lines) | ✓ (`app.openapi()['paths']` confirms all 9 `/api/v1/cmo/*` routes) | ✓ VERIFIED |
| `tests/test_cmo_engine.py` | Unit tests for break-even, festive restock, atomic `commit=False`, and bahi-khata OCR | ✓ | ✓ (418 lines, 19 tests) | ✓ (executed by `pytest`) | ✓ VERIFIED |
| `tests/test_cmo_recovery_and_offers.py` | Integration tests for Boli-Baki recovery, Soundbox webhook, dead-stock break-even, and attribution | ✓ | ✓ (458 lines, 10 tests) | ✓ (executed by `pytest`) | ✓ VERIFIED |
| `tests/test_cmo_closing_and_bahi_khata.py` | Integration tests for `/dukaan-closing-ritual`, `/scan-bahi-khata`, and `/confirm-bahi-khata` | ✓ | ✓ (390 lines, 8 tests) | ✓ (executed by `pytest`) | ✓ VERIFIED |
| `.planning/phases/04-ai-cmo-recovery-break-even-closing-ritual/04-03-SUMMARY.md` | Execution summary for Plan `04-03` | ✓ | ✓ (147 lines) | ✓ (commits `74b8fc9`, `0592b2e` verified) | ✓ VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/main.py` | `backend/routers/cmo_router.py` | `app.include_router(cmo_router)` | ✓ WIRED | Mounts all 9 `/api/v1/cmo/*` endpoints into FastAPI `app`. |
| `backend/routers/cmo_router.py` | `backend/services/deterministic_engine.py` | `calculate_customer_balance`, `add_repayment_entry`, `add_credit_entry`, `calculate_breakeven_offer`, `calculate_festive_restock_forecast`, `log_business_event` | ✓ WIRED | Enforces Law of Zero LLM Math & Append-Only Immutability across all CMO actions. |
| `backend/routers/cmo_router.py` | `backend/services/bahi_khata_parser_service.py` | `parse_bahi_khata_page`, `_normalize_phone` | ✓ WIRED | Lines 20–23, 1126, 1198, 1206 power `/scan-bahi-khata` and phone matching in `/confirm-bahi-khata`. |
| `backend/routers/cmo_router.py` | `backend/services/sarvam_engine.py` | `translate_text`, `synthesize_speech` | ✓ WIRED | Powers `/boli-baki-recovery`, `/simulate-link-paid/{slug}`, `/dead-stock-campaign`, and `/dukaan-closing-ritual`. |
| `backend/services/bahi_khata_parser_service.py` | `backend/services/deterministic_engine.py` | `calculate_customer_balance` | ✓ WIRED | Line 18 & lines 262, 278 compute existing balances read-only during OCR preview. |

---

### Data-Flow Trace (Level 4)

| Endpoint / Artifact | Data Variable | Source | Produces Real Data | Status |
|---------------------|---------------|--------|--------------------|--------|
| `GET /api/v1/cmo/overdue-debtors` | `overdue_debtors` | SQLite `customers` + `calculate_customer_balance` + `campaigns_and_links` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/boli-baki-recovery` | `translated_message`, `tts_audio_base64`, `paytm_payment_link` | `customers` + `calculate_customer_balance` + `sarvam_engine` + `campaigns_and_links` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/simulate-link-paid/{slug}` | `balance_after`, `soundbox_audio_base64` | `campaigns_and_links` + `add_repayment_entry` (`ledger_entries`) + `synthesize_speech` | Yes | ✓ FLOWING |
| `GET /api/v1/cmo/dead-stock` | `dead_stock_items` | SQLite `inventory_items` (`days_unsold > 15`) + `campaigns_and_links` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/dead-stock-campaign` | `math_audit`, `attributed_links` | `inventory_items` + `calculate_breakeven_offer` + `campaigns_and_links` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/simulate-promo-click/{slug}` | `clicks`, `conversions`, `revenue_collected`, `language_breakdown` | SQLite `campaigns_and_links` update + sibling query | Yes | ✓ FLOWING |
| `GET /api/v1/cmo/dukaan-closing-ritual` | `today_qr_sales`, `today_udhaar_recovered`, `unmatched_upi_count`, `festive_restock_forecast` | SQLite `ledger_entries` + `unmatched_payments_queue` + `inventory_items` + `calculate_festive_restock_forecast` + `synthesize_speech` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/scan-bahi-khata` | `proposals`, `total_proposed_amount` | `parse_bahi_khata_page` (Sarvam Vision / fallback) + SQLite `customers` | Yes | ✓ FLOWING |
| `POST /api/v1/cmo/confirm-bahi-khata` | `customer_results`, `total_onboarded_amount` | Atomic SQLite `customers` + `add_credit_entry` (`ledger_entries`) + `business_events` | Yes | ✓ FLOWING |

---

### Behavioral Spot-Checks & Full Test Suite Execution

- **Command:** `pytest -v`
- **Observed Result:** **130 passed, 1 warning in 0.80s** (all 130 tests across all 14 test modules passed with 0 failures and 0 skipped tests).
- **Phase 4 Tests (37 tests):**
  - `tests/test_cmo_engine.py`: 19 passed
  - `tests/test_cmo_recovery_and_offers.py`: 10 passed
  - `tests/test_cmo_closing_and_bahi_khata.py`: 8 passed
- **Registered `/api/v1/cmo` Routes (`app.openapi()['paths']`):** All 9 routes confirmed mounted:
  1. `GET /api/v1/cmo/overdue-debtors`
  2. `POST /api/v1/cmo/boli-baki-recovery`
  3. `POST /api/v1/cmo/simulate-link-paid/{slug}`
  4. `GET /api/v1/cmo/dead-stock`
  5. `POST /api/v1/cmo/dead-stock-campaign`
  6. `POST /api/v1/cmo/simulate-promo-click/{slug}`
  7. `GET /api/v1/cmo/dukaan-closing-ritual`
  8. `POST /api/v1/cmo/scan-bahi-khata`
  9. `POST /api/v1/cmo/confirm-bahi-khata`
- **Git Commit Verification (`gsd-tools query verify.commits`):** All 7 Phase 4 commits (`3a42d52`, `36fc4d8`, `9c8044c`, `e1eddd4`, `74b8fc9`, `0592b2e`, `99548e4`) verified valid in git history.

---

### Anti-Patterns Found

- **Blocker Debt Markers (`TBD`, `FIXME`, `XXX`):** 0 found across all Phase 4 files.
- **Warning Markers (`TODO`, `HACK`, `PLACEHOLDER`, `coming soon`, `not yet implemented`):** 0 found (line 102 of `cmo_router.py` is a docstring explaining offline `[lang]` prefix handling in `sarvam_engine`).
- **Stub / Empty Return Patterns:** 0 found. All endpoints execute live SQLite transactions, deterministic Python arithmetic, and Sarvam API / offline fallback orchestration.

---

### Human Verification Required

None — all Phase 4 backend APIs, deterministic arithmetic invariants, timeout fallbacks, idempotency guards, and atomic rollback behaviors are deterministically verified by automated tests.

---

### Verification Conclusion

**Verdict: passed**  
Phase 4 (AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual) has achieved **7/7** roadmap must-haves, satisfied all requirements (`CMO-01` through `CMO-06`, `ONBOARD-01`), fulfilled PRD §5.4, §5.5, §7.4, §7.5, §7.6 and FR-07 through FR-10, exposed all 9 `/api/v1/cmo/*` endpoints cleanly, and passed all **130/130** automated tests in the repository.

---

_Verified: 2026-11-11T17:16:00Z_  
_Verifier: the agent (gsd-verifier)_
