# Phase 1: KiranaOS Deterministic Memory & Store Engine - Context

**Gathered:** 2026-11-09  
**Status:** Ready for planning  
**Source:** PRD Express Path (`munim_ai_kiranaos_master_hackathon_prd.md`)

<domain>
## Phase Boundary

Phase 1 delivers the immutable, append-only SQLite financial and inventory database backbone for KiranaOS. It implements the pure Python deterministic calculation engine (`backend/services/deterministic_engine.py`) to derive customer balances, audit event provenance, and seed realistic demo records for "Ganesh Provision & General Store (Dadar, Mumbai)".
</domain>

<decisions>
## Implementation Decisions

### KiranaOS Append-Only Database Schema (Locked)
- SQLite database (`backend/data/kiranaos.db`) implementing all 8 tables from PRD §6 using `CREATE TABLE IF NOT EXISTS`:
  1. `customers` (id, name, aliases JSON, phone, preferred_language, regular_cycle_days, last_visit_date, created_at)
  2. `ledger_entries` (id, customer_id, entry_type, amount, payment_mode, provider_ref, source_utterance, confidence_score, status, created_at)
  3. `inventory_items` (id, sku_name, local_aliases JSON, category, current_stock, unit, last_unit_cost, previous_unit_cost, selling_price, avg_daily_burn, festive_multiplier, reorder_threshold, supplier_name, supplier_phone, last_restocked_at, last_sold_at)
  4. `stock_events` (id, item_id, event_type, quantity_delta, unit_cost, invoice_number, raw_transcript, created_at)
  5. `supplier_ledger` (id, supplier_name, entry_type, amount, invoice_number, price_creep_flagged, created_at)
  6. `unmatched_payments_queue` (id, upi_txn_id, amount, payer_name, payer_vpa, candidate_customers_json, ambiguity_reason, status, resolved_customer_id, created_at)
  7. `campaigns_and_links` (id, campaign_title, campaign_type, target_customer_id, language_code, paytm_link_slug, amount_expected, discount_per_unit, breakeven_extra_units, message_text, tts_audio_base64, clicks, conversions, revenue_collected, status, created_at)
  8. `business_events` (id, event_category, summary_text, evidence_json, actor, created_at)

### Law of Append-Only Immutability (Locked)
- Absolute zero `UPDATE` or `DELETE` on financial records (`ledger_entries`) and stock movements (`stock_events`).
- Corrections and adjustments require explicit linked entries (`entry_type='REVERSAL_ADJUSTMENT'`).
- Outstanding customer balances are computed dynamically in Python via SQL `SUM()`.

### Law of Zero LLM Math (Locked)
- All arithmetic formulas must live exclusively in `backend/services/deterministic_engine.py`:
  - Customer Outstanding Balance: $\sum \text{Credit}_i - \sum \text{Repayment}_j + \sum \text{Adjustment}_k$
  - Identity Disambiguation Guard: Exact matching vs fuzzy candidate matching returning candidate sets when duplicate names exist (e.g. "Suresh").
  - Audit logging to `business_events` with structured `evidence_json`.

### Pre-Seeded Mumbai Kirana Dataset (Locked)
- `seed_demo_data.py` populates baseline store data on startup for "Ganesh Provision & General Store (Dadar, Mumbai)":
  - Customers: Ramesh Sharma (owes ₹650, 18d overdue), Suresh Patil (Tailor, owes ₹200, 5d ago), Suresh Kadam (Kirana, owes ₹450, 9d ago), Priya Deshmukh (absent 16d).
  - Inventory: Amul Pure Ghee 1L (stock: 4, burn: 2, festive multiplier: 3.5), Fortune Sunlite Oil 1L (old cost: 132, previous cost: 132, selling: 155), Haldiram Aloo Bhujia 400g (stock: 28, unsold: 22d, cost: 72, price: 95).

### Walking Skeleton Execution (Locked)
- Phase 1 serves as the Walking Skeleton: sets up FastAPI project structure, database initialization, repository layer, deterministic balance engine, and verification unit tests.

### the agent's Discretion
- Backend structure: `backend/database/connection.py`, `backend/database/schema.sql`, `backend/services/deterministic_engine.py`, `backend/services/seed_demo_data.py`, `backend/routers/memory_router.py`.
- Automated test suite using `pytest` verifying SQL append-only constraints, balance calculations, identity ambiguity detection, and demo seed data accuracy.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PRD Master Specification
- `munim_ai_kiranaos_master_hackathon_prd.md` §2 (Core Architectural Laws)
- `munim_ai_kiranaos_master_hackathon_prd.md` §5.1 (Customer Outstanding Balance Formula)
- `munim_ai_kiranaos_master_hackathon_prd.md` §6 (Authoritative Database Schema)
- `munim_ai_kiranaos_master_hackathon_prd.md` §9 (Pre-Seeded Mumbai Kirana Dataset)

### Planning Artifacts
- `.planning/REQUIREMENTS.md` (LEDGER-01 through LEDGER-05)
- `.planning/ROADMAP.md` (Phase 1 details & success criteria)
- `.planning/PROJECT.md` (Core values & constraints)

</canonical_refs>

<specifics>
## Specific Ideas
- Provide CLI verification and test endpoints (`/api/v1/memory/health`, `/api/v1/memory/customers`, `/api/v1/memory/ledger`) to inspect balances and provenance immediately.
- Ensure the seed script is idempotent so restarting the backend doesn't duplicate demo records or violate unique constraints.
</specifics>

<deferred>
## Deferred Ideas
- Multi-tenant shop partitioning (out of scope for hackathon single-merchant demo).
- PostgreSQL migration scripts (SQLite is the dedicated single-file store for hackathon reliability).
</deferred>

---

*Phase: 01-kiranaos-deterministic-memory-store-engine*  
*Context gathered: 2026-11-09 via PRD Express Path*
