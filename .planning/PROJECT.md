# Munim-AI (powered by KiranaOS)

## What This Is

Munim-AI is a vernacular, voice-first and vision-first AI CFO & AI CMO mobile merchant partner for Indian kirana store owners using Paytm Soundbox and QR. Underneath the intuitive mobile UI sits KiranaOS, a deterministic append-only business memory engine ensuring 100% mathematical accuracy without LLM hallucinations. Built for the Paytm Build for India AI Hackathon (Track 1: Merchant Growth AI) by Team Code Apex.

## Core Value

A closed-loop AI business partner that safeguards margins (AI CFO: invoice price-creep alerts, Paytm settlement waterfall explainer, cautious UPI reconciliation) and drives attributed footfall and recovery (AI CMO: vernacular voice udhaar recovery, break-even offer studio, 60s Diwali closing ritual) with 100% auditable deterministic arithmetic.

## Business Context

- **Customer**: Indian Kirana & Mom-and-pop store merchants operating on thin 5-7% net margins.
- **Revenue model**: Paytm merchant ecosystem retention, increased Merchant Loan underwriting volume, Soundbox subscription stickiness, and transaction fee optimization.
- **Success metric**: 100% accurate margin defense, zero LLM math hallucinations, 100% attributed recovered credit, and sub-6-second demo-day survivability.
- **Strategy notes**: Full specification in [munim_ai_kiranaos_master_hackathon_prd.md](munim_ai_kiranaos_master_hackathon_prd.md).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **FR-01: Keyterm-Biased Voice Proposal**: Transcribes shop-counter Hinglish/Marathi via Sarvam Saaras STT with dynamic SQL keyterm biasing and generates unconfirmed proposal cards.
- [ ] **FR-02: Identity Disambiguation Guard**: Blocks blind writes when customer names overlap (e.g., "Suresh Tailor" vs "Suresh Kirana") and prompts a 1-tap disambiguation card.
- [ ] **FR-03: Append-Only Ledger & Business Event Provenance**: Strictly append-only SQLite financial ledger (`ledger_entries`) and stock event store (`stock_events`) with complete audit provenance (`business_events`).
- [ ] **FR-04: Distributor Bill Scanner & Price-Creep Alert**: Scans wholesale invoices via Sarvam Vision OCR, detects $\ge 2\%$ price creep in Python math, and executes dual updates (stock + supplier khata).
- [ ] **FR-05: Ambiguous UPI Reconciliation Queue**: Matches incoming Paytm QR payments; routes ambiguous candidate matches to a 1-tap merchant assignment queue.
- [ ] **FR-06: "Mera Paisa Kam Kyun Aaya?" Settlement Explainer**: Deterministically reconciles Gross QR Sales minus Paytm Loan Daily EDI, Soundbox rental, and refunds to Net Bank Credit, speaking in vernacular via Bulbul TTS.
- [ ] **FR-07: "Boli-Baki" Multilingual Voice Udhaar Recovery**: Filters debtors overdue >10 days, translates polite reminders, synthesizes Bulbul v3 voice notes, and issues tracked Paytm links with simulated live Soundbox payment webhooks.
- [ ] **FR-08: Dead-Stock Break-Even Studio & Per-Language Attribution**: Computes unit margin and required break-even sales volume before allowing discounts on dead stock (>15d unsold) with Marathi/Hindi tracked links.
- [ ] **FR-09: 60-Second Dukaan Closing Ritual**: Proactive EOD spoken briefing with net settlement, recovered udhaar, and deterministic $3.5\times$ Diwali festive restock forecast.
- [ ] **FR-10: Handwritten Bahi-Khata Scanner**: Converts physical notebook ledger images into batch credit proposals for instant merchant onboarding.
- [ ] **UI-01: Mobile-First Paytm Merchant App Experience**: High-contrast, mobile viewport design with Paytm brand styling (#002970, #00BAF2), 4 core tabs, proposal cards with "Why am I seeing this?" drawers, and audio playback.
- [ ] **UI-02: Judge Demo Quick-Trigger Bar**: Collapsible footer with 6 one-click chips executing live end-to-end backend flows reliably in loud hackathon venues.

### Out of Scope

- Multi-tenant RBAC & enterprise auth — single shop ("Ganesh Provision & General Store") focus for hackathon.
- External Redis worker queues / Celery — FastAPI async and SQLite are lightweight, reliable, and portable.
- Automated telecom/PSTN outbound calling — simulated WhatsApp audio notes and Paytm Soundbox voice announcements fulfill the requirements.
- Distributed offline SQLite sync — local deterministic single-node store for stage reliability.

## Context

- Event: Paytm Build for India AI Hackathon — Mumbai Edition (Track 1: Merchant Growth AI)
- Team: Code Apex (Parth, Priyanshu, Rachit)
- Pre-seeded store: "Ganesh Provision & General Store (Dadar, Mumbai)"
- Architecture: 4-Layer model (Multimodal Input Layer $\rightarrow$ Propose-Confirm-Commit Gate $\rightarrow$ KiranaOS Deterministic Memory Engine $\rightarrow$ Vernacular Output Layer)

## Constraints

- **Tech Stack**: FastAPI (Python 3.11+), SQLite (8 append-only tables), React 18 + Vite + TypeScript + Tailwind CSS.
- **Law of Zero LLM Math**: LLM never computes arithmetic, margins, loan deductions, or stock calculations. All math lives in `backend/services/deterministic_engine.py`.
- **Law of Append-Only Immutability**: No `UPDATE` or `DELETE` on financial amounts. Adjustments are explicit `REVERSAL_ADJUSTMENT` entries.
- **Law of Demo-Day Survivability**: All external calls have 6s timeouts with instant high-fidelity local mock fallbacks (realistic synthetic base64 audio and OCR results).
- **Form Factor**: Strictly mobile-first interface adhering to Paytm Merchant design patterns.
- **Custom Invoices**: Support both built-in demo sample invoices and custom user image uploads.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite Append-Only Database | Embedded, zero-configuration, cross-platform, deterministic SQL sums | — Pending |
| Pure Python Math Engine | Eliminates LLM hallucination risk on financial metrics and pricing | — Pending |
| Hybrid Sarvam AI Integration | Supports real `SARVAM_API_KEY` while providing 100% reliable local fallback | — Pending |
| Authentic Paytm Mobile Merchant UI | Delivers familiar, high-contrast, production-grade mobile app feel | — Pending |
| Judge Demo Quick-Trigger Bar | Guarantees smooth presentation in noisy hackathon halls without mic fails | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-09 after initialization*

