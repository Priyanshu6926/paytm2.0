# Requirements: Munim-AI (powered by KiranaOS)

**Defined:** 2026-11-09  
**Core Value:** A closed-loop AI business partner that safeguards margins (AI CFO: invoice price-creep alerts, Paytm settlement waterfall explainer, cautious UPI reconciliation) and drives attributed footfall and recovery (AI CMO: vernacular voice udhaar recovery, break-even offer studio, 60s Diwali closing ritual) with 100% auditable deterministic arithmetic.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Voice & Multimodal Input (VOICE)

- [x] **VOICE-01**: User can speak or type shop-counter commands in Hinglish/Marathi, transcribed via Sarvam Saaras STT with SQL keyterm biasing, producing an unconfirmed Proposal Card.
- [x] **VOICE-02**: System synthesizes high-quality vernacular spoken explanations and confirmation prompts using Sarvam Bulbul v3 TTS (`hi-IN`, `mr-IN`).
- [x] **VOICE-03**: System implements the Law of Demo-Day Survivability with 6-second timeouts and automatic fallback to authentic pre-computed audio and transcripts.

### KiranaOS Deterministic Memory & Ledger (LEDGER)

- [x] **LEDGER-01**: User balances are deterministically computed in Python via SQL `SUM()` over an append-only `ledger_entries` table with zero UPDATE/DELETE mutations.
- [x] **LEDGER-02**: System detects ambiguous customer names (e.g. "Suresh") and halts auto-writing, displaying an interactive 1-tap identity disambiguation card.
- [x] **LEDGER-03**: System logs all inventory movements to an append-only `stock_events` table with quantity deltas, unit costs, and invoice references.
- [x] **LEDGER-04**: System records all business operations into `business_events` with structured JSON evidence powering the "Why am I seeing this?" drawer.
- [x] **LEDGER-05**: System boots with pre-seeded demo dataset for "Ganesh Provision & General Store (Dadar, Mumbai)" including debtors, inventory items, and suppliers.

### Munim AI CFO (CFO)

- [x] **CFO-01**: User can scan distributor wholesale bills via Sarvam Vision OCR from sample presets or custom image uploads.
- [x] **CFO-02**: System calculates price creep percentage in pure Python arithmetic and flags any wholesale cost increase $\ge 2\%$ with recommended new selling price.
- [x] **CFO-03**: User can approve scanned distributor bills with a single tap, executing dual atomic writes to both inventory stock and supplier payable khata.
- [x] **CFO-04**: User can view and listen to "Mera Paisa Kam Kyun Aaya?" settlement waterfall reconciling Gross QR Sales, Loan EDI, Soundbox fee, and refunds down to ₹0.01.
- [x] **CFO-05**: System routes ambiguous Paytm QR payments (matching multiple debtors) to an Unmatched Payments Queue for 1-tap manual assignment.

### Munim AI CMO (CMO)

- [x] **CMO-01**: System identifies debtors overdue $>10$ days and generates personalized polite recovery reminders translated to customer's native language (`Sarvam Translate`).
- [x] **CMO-02**: System synthesizes native Bulbul v3 audio voice notes and issues unique tracked Paytm payment links (`paytm.me/munim-...`).
- [x] **CMO-03**: User can simulate customer paying via Paytm link, which fires an instant webhook, clears the customer ledger live, and triggers a Paytm Soundbox audio chime.
- [x] **CMO-04**: User can test discount offers on dead stock (>15d unsold) in the Break-Even Studio, calculating required sales volume and blocking loss-making promotions.
- [x] **CMO-05**: System tracks per-language campaign attribution across Hindi and Marathi payment links.
- [x] **CMO-06**: User can trigger the 60-Second Dukaan Closing Ritual, playing a spoken evening summary with net sales, recovered udhaar, and a deterministic $3.5\times$ Diwali festive restock order draft.

### Onboarding Vision (ONBOARD)

- [x] **ONBOARD-01**: User can upload an image of a handwritten bahi-khata notebook page, converted via multimodal OCR into batch-editable customer credit proposals.

### Mobile UI & Live Presentation (UI)

- [x] **UI-01**: User experiences an authentic mobile-first Paytm Merchant App interface with Paytm brand colors (`#002970`, `#00BAF2`), crisp typography, and mobile frame viewport.
- [ ] **UI-02**: User navigates 4 primary operational tabs: (1) Munim Mic & Operations, (2) AI CFO, (3) AI CMO, and (4) Business Memory Timeline.
- [x] **UI-03**: Proposal cards feature expandable "Why am I seeing this?" evidence pills and clear Propose $\rightarrow$ Confirm $\rightarrow$ Commit interaction gates.
- [ ] **UI-04**: UI includes a collapsible Judge Demo Quick-Trigger Bar with 6 one-click demo flows for 100% reliable stage presentations.
- [x] **UI-05**: UI integrates an interactive Paytm Soundbox simulator playing genuine audio chimes for received payments.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enterprise & Platform Operations

- **ENT-01**: Multi-store owner RBAC with staff permission tiers.
- **ENT-02**: Background worker queues with Redis and Celery for large batch OCR processing.
- **ENT-03**: Automated outbound IVR phone calls to suppliers via Exotel/Twilio.
- **ENT-04**: Multi-device offline SQLite conflict resolution (CRDTs).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| LLM-based arithmetic calculations | Violates Law of Zero LLM Math; all financial math is executed in deterministic Python. |
| Direct database UPDATE/DELETE on ledger entries | Violates Law of Append-Only Immutability; adjustments use linked reversal records. |
| Full-desktop responsive portal | Violates user constraint; must strictly be an authentic Paytm mobile merchant interface. |
| Real banking payment gateway settlement | Sandbox/simulation environment used for Paytm QR webhooks and link generation. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LEDGER-01 | Phase 1 | Complete |
| LEDGER-02 | Phase 1 | Complete |
| LEDGER-03 | Phase 1 | Complete |
| LEDGER-04 | Phase 1 | Complete |
| LEDGER-05 | Phase 1 | Complete |
| VOICE-01 | Phase 2 | Complete |
| VOICE-02 | Phase 2 | Complete |
| VOICE-03 | Phase 2 | Complete |
| CFO-01 | Phase 3 | Complete |
| CFO-02 | Phase 3 | Complete |
| CFO-03 | Phase 3 | Complete |
| CFO-04 | Phase 3 | Complete |
| CFO-05 | Phase 3 | Complete |
| CMO-01 | Phase 4 | Complete |
| CMO-02 | Phase 4 | Complete |
| CMO-03 | Phase 4 | Complete |
| CMO-04 | Phase 4 | Complete |
| CMO-05 | Phase 4 | Complete |
| CMO-06 | Phase 4 | Complete |
| ONBOARD-01 | Phase 4 | Complete |
| UI-01 | Phase 5 | Complete |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Complete |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-09*
*Last updated: 2026-11-09 after roadmap creation*
