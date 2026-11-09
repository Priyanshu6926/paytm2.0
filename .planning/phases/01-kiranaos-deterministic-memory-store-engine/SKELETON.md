# Walking Skeleton — Munim-AI (powered by KiranaOS)

**Phase:** 1
**Generated:** 2026-11-09
**Status:** In-flight execution skeleton

## Capability Proven End-to-End

An authenticated store operator can start the KiranaOS service, automatically seed the Dadar kirana baseline database, query a customer's outstanding udhaar calculated deterministically via SQL `SUM()` over immutable append-only ledger entries, and verify that name collisions (e.g. "Suresh") halt auto-commit to trigger an identity disambiguation card.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend Framework | FastAPI (Python 3.11+) | Async web framework providing instant JSON serialization, OpenAPI documentation, and native Pydantic schema validation. |
| Deterministic Engine | Pure Python (`backend/services/deterministic_engine.py`) | Fulfills the "Law of Zero LLM Math" by guaranteeing 100% mathematical precision with zero LLM hallucination for financial balances, margins, and discounts. |
| Data Layer | SQLite 3 (`backend/data/kiranaos.db`) | Single-file zero-latency ACID database ideal for edge deployment on mobile/POS, with hard triggers enforcing the "Law of Append-Only Immutability". |
| Immutability Enforcement | SQLite `BEFORE UPDATE` & `BEFORE DELETE` Triggers | Prevents accidental or programmatic record modification on financial transactions and stock movements at the storage layer. |
| Auditing & Provenance | `business_events` with structured `evidence_json` | Every state transition records an actor and machine-readable evidence dictionary powering the "Why am I seeing this?" UI drawer. |
| Test Harness | `pytest` with in-memory & file-based SQLite fixtures | Provides sub-second regression test suites verifying zero UPDATE/DELETE enforcement, balance math, and seed integrity. |

## Stack Touched in Phase 1

- [x] Project scaffold (`backend/`, `tests/`, `backend/database/`, `backend/services/`, `backend/routers/`)
- [x] Routing — `/api/v1/memory/health`, `/api/v1/memory/customers`, `/api/v1/memory/customers/{id}/ledger`, `/api/v1/memory/inventory`, `/api/v1/memory/events`
- [x] Database — SQLite connection pool, schema migration (`schema.sql`), append-only triggers, and 8 core tables from PRD §6
- [x] Pure Python Math — Deterministic balance calculation $\sum \text{Credit} - \sum \text{Repayment} + \sum \text{Adjustment}$
- [x] Verification Harness — Automated test suite asserting append-only constraints, identity disambiguation, and seed demo accuracy

## Out of Scope (Deferred to Later Slices)

- Sarvam Saaras STT & Bulbul v3 TTS integration (Phase 2)
- Multimodal distributor bill OCR & price creep alerts (Phase 3)
- Soundbox payment webhooks & simulated payment link settlements (Phase 4)
- React 18 frontend UI & Judge Demo Quick-Trigger Bar (Phase 5)
- Multi-store tenancy and user role management (Deferred v2)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: Core Voice & Multimodal Gateway (Sarvam Saaras STT, Bulbul v3 TTS with shop keyterm biasing)
- Phase 3: Munim AI CFO (Distributor invoice scan, price-creep alerts, settlement waterfall reconciliation)
- Phase 4: Munim AI CMO (Vernacular udhaar recovery, Break-Even Studio, Diwali closing ritual)
- Phase 5: Authentic Paytm Merchant Mobile UI & Judge Demo Quick-Trigger Bar
