# Roadmap: Munim-AI (powered by KiranaOS)

## Overview

Munim-AI transforms everyday Indian kirana operations through an auditable, voice-first and vision-first AI merchant partner. The roadmap establishes KiranaOS—an immutable, append-only SQLite financial and inventory ledger governed by deterministic Python arithmetic—before layering multimodal voice processing with Sarvam AI, margin protection and settlement reconciliation via Munim AI CFO, cash recovery and break-even promotion tools via Munim AI CMO, and an authentic mobile-first Paytm Merchant interface equipped with an unshakeable Judge Demo Quick-Trigger Bar.

## Milestones

- 🚧 **v1.0 MVP** - Phases 1-5 (in progress)

## Phases

- [x] **Phase 1: KiranaOS Deterministic Memory & Store Engine** - Immutable SQLite ledger, Python math engine, and Mumbai kirana baseline data (completed 2026-11-09)
- [x] **Phase 2: Core Voice & Multimodal Gateway** - Sarvam Saaras STT with SQL keyterm biasing, Bulbul TTS, and survivability fallbacks (completed 2026-11-10)
- [x] **Phase 3: AI CFO — Margin Defense & Settlement Reconciliation** - Wholesale price-creep alerts, dual stock/khata write, settlement waterfall, and ambiguous UPI queue (completed 2026-11-11)
- [ ] **Phase 4: AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual** - Vernacular voice reminders, Soundbox payment webhooks, break-even studio, closing ritual, and bahi-khata scanner
- [ ] **Phase 5: Authentic Paytm Mobile UI & Judge Quick-Trigger Command Bar** - Mobile viewport frame, 4 core tabs, evidence drawers, Soundbox chime simulator, and judge demo quick triggers

## Phase Details

### Phase 1: KiranaOS Deterministic Memory & Store Engine
**Goal**: Establish an immutable, append-only SQLite financial and inventory backbone with pure Python deterministic calculation of customer balances and audit logs, pre-seeded with Dadar kirana store baseline data.
**Depends on**: Nothing (first phase)
**Requirements**: LEDGER-01, LEDGER-02, LEDGER-03, LEDGER-04, LEDGER-05
**Success Criteria** (what must be TRUE):
  1. Customer outstanding balances are computed strictly in Python via SQL `SUM()` over `ledger_entries` with zero UPDATE/DELETE table mutations.
  2. Ledger queries matching duplicate or ambiguous customer names (e.g. "Suresh") halt auto-execution and flag an identity ambiguity status.
  3. Inventory stock deltas, wholesale unit costs, and invoice references record into an append-only `stock_events` table.
  4. System logs every operational action into `business_events` with structured JSON evidence payloads to power auditability.
  5. System seeds and boots cleanly with realistic demo records for "Ganesh Provision & General Store (Dadar, Mumbai)".
**Plans**: 3/3 plans complete

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Database Schema & Append-Only Connection Engine (8 tables from PRD §6 with append-only triggers)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Deterministic Python Engine & Identity Disambiguation (SQL SUM balance calculation, reversal adjustment handling, and identity disambiguation guard)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — Mumbai Kirana Store Demo Seeder & Walking Skeleton Harness (Dadar demo store dataset, FastAPI memory router, and e2e verification suite)

### Phase 2: Core Voice & Multimodal Gateway
**Goal**: Provide shop-counter speech-to-intent and text-to-speech interaction using Sarvam Saaras STT with dynamic SQL keyterm biasing and Bulbul v3 TTS, backed by sub-6-second local synthetic fallbacks.
**Depends on**: Phase 1
**Requirements**: VOICE-01, VOICE-02, VOICE-03
**Success Criteria** (what must be TRUE):
  1. Spoken and typed Hinglish/Marathi shop commands parse into unconfirmed Proposal Cards with key terms biased dynamically from active SQLite customer and inventory tables.
  2. System synthesizes clear vernacular voice confirmations and explanations in Hindi (`hi-IN`) and Marathi (`mr-IN`) using Sarvam Bulbul v3.
  3. External voice API requests enforce a strict 6-second timeout and automatically fall back to authentic pre-recorded audio and transcripts without failing the user flow.
**Plans**: 2/2 plans complete

Plans:
**Wave 1**
- [x] 02-01-PLAN.md — Sarvam Engine Service with 6-Second Timeout & Local Synthetic Fallback (STT saaras:v4, TTS bulbul:v3, Translate, and resilient offline synthetic base64 audio generator)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02-PLAN.md — Dynamic SQL Keyterm Biasing, Intent Parsing & Propose-Confirm Gateway (SQLite keyterm extraction, vernacular intent parsing with identity disambiguation, and FastAPI endpoints mounted at /api/v1/voice/*)

### Phase 3: AI CFO — Margin Defense & Settlement Reconciliation
**Goal**: Guard thin kirana retail margins against distributor wholesale cost increases and demystify daily Paytm payout deductions down to ₹0.01.
**Depends on**: Phase 1, Phase 2
**Requirements**: CFO-01, CFO-02, CFO-03, CFO-04, CFO-05
**Success Criteria** (what must be TRUE):
  1. Scanned distributor invoices (preset demo samples or custom user uploads) parse line-item rates and quantities via Sarvam Vision OCR without LLM arithmetic.
  2. Wholesale price increases $\ge 2\%$ are flagged by pure Python arithmetic with a recommended updated selling price to preserve margin.
  3. Approving a scanned bill triggers an atomic dual write to `stock_events` (inventory received) and `ledger_entries` (supplier khata balance).
  4. "Mera Paisa Kam Kyun Aaya?" waterfall calculation deterministically reconciles Gross QR Sales minus Loan Daily EDI, Soundbox fee, and customer refunds to Net Bank Credit with vernacular Bulbul audio.
  5. Incoming Paytm QR payments matching multiple debtor accounts are held in an Unmatched Payments Queue for 1-tap manual assignment.
**Plans**: 3/3 plans complete

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — Wholesale Price-Creep Engine, Settlement Waterfall & Bill OCR Parser (calculate_price_creep, calculate_settlement_reconciliation in deterministic_engine.py, and bill_parser_service.py with Sarvam Vision OCR and offline fallback)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-02-PLAN.md — AI CFO Router with Distributor Bill Dual Action & Spoken Explainer (cfo_router.py mounted at /api/v1/cfo/* exposing /scan-distributor-bill, /confirm-distributor-bill with atomic stock + supplier khata writes, and /settlement-explainer with Bulbul TTS)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-03-PLAN.md — Ambiguous UPI Reconciliation Queue & QR Webhook Simulator (/unmatched-payments queue, /resolve-unmatched-payment 1-tap debtor assignment, and /simulate-qr-webhook routing collisions to queue)

### Phase 4: AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual
**Goal**: Accelerate store cash recovery through polite vernacular voice reminders, simulated Soundbox payment webhooks, margin-safe discount promotions, notebook OCR onboarding, and an evening closing ritual.
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: CMO-01, CMO-02, CMO-03, CMO-04, CMO-05, CMO-06, ONBOARD-01
**Success Criteria** (what must be TRUE):
  1. System surfaces debtors overdue $>10$ days and creates personalized reminders translated into the customer's native tongue (Hindi or Marathi).
  2. Debtor reminders include synthesized Bulbul voice notes and unique tracked Paytm payment links (`paytm.me/munim-...`).
  3. Simulating payment on a generated payment link fires an instant webhook, clears the debtor ledger balance, and triggers a live Paytm Soundbox chime.
  4. Break-Even Studio calculates required sales volume before allowing discounts on dead stock (>15d unsold) and strictly blocks loss-making promotions.
  5. Campaign performance tracks click and payment conversion metrics partitioned by Hindi and Marathi links.
  6. Merchant can trigger the 60-Second Dukaan Closing Ritual to hear spoken net settlement, recovered udhaar, and a deterministic $3.5\times$ Diwali festive restock forecast.
  7. Physical bahi-khata notebook photos parse via multimodal OCR into batch credit proposals for 1-tap merchant onboarding.
**Plans**: 3 plans

Plans:
**Wave 1**
- [ ] 04-01-PLAN.md — Deterministic CMO & Festive Restock Engines + Handwritten Bahi-Khata OCR Service

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 04-02-PLAN.md — AI CMO Router: Boli-Baki Voice Recovery, Soundbox Webhook & Break-Even Studio Attribution

**Wave 3** *(blocked on Wave 1 & Wave 2 completion)*
- [ ] 04-03-PLAN.md — 60-Second Dukaan Closing Ritual & Handwritten Bahi-Khata Batch Onboarding

### Phase 5: Authentic Paytm Mobile UI & Judge Quick-Trigger Command Bar
**Goal**: Deliver a mobile-first Paytm Merchant web interface with official brand styling (#002970/#00BAF2), 4 operational tabs, "Why am I seeing this?" evidence drawers, live Soundbox audio simulator, and a fail-safe Judge Quick-Trigger Bar.
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. UI displays within a high-contrast mobile viewport frame adhering to authentic Paytm Merchant design tokens (`#002970`, `#00BAF2`, crisp typography).
  2. Merchant can navigate across 4 primary tabs: (1) Munim Mic & Operations, (2) AI CFO, (3) AI CMO, and (4) Business Memory Timeline.
  3. Every proposal card contains an expandable "Why am I seeing this?" drawer showing mathematical formulas, source documents, and ledger balance deltas before confirmation.
  4. Collapsible Judge Demo Quick-Trigger Bar enables hackathon evaluators to run all 6 core product flows with 1-tap certainty regardless of ambient venue noise.
  5. Embedded Paytm Soundbox simulator renders and plays authentic vernacular audio chimes upon receiving payment webhook notifications.
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. KiranaOS Deterministic Memory & Store Engine | 3/3 | Complete    | 2026-11-09 |
| 2. Core Voice & Multimodal Gateway | 2/2 | Complete    | 2026-11-10 |
| 3. AI CFO — Margin Defense & Settlement Reconciliation | 3/3 | Complete    | 2026-11-11 |
| 4. AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual | 0/3 | Planned | - |
| 5. Authentic Paytm Mobile UI & Judge Quick-Trigger Command Bar | 0/TBD | Not started | - |
