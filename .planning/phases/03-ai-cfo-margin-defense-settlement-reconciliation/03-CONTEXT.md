# Phase 3: AI CFO — Margin Defense & Settlement Reconciliation - Context

**Gathered:** 2026-11-11  
**Status:** Ready for planning  
**Source:** PRD Express Path (`munim_ai_kiranaos_master_hackathon_prd.md`)

<domain>
## Phase Boundary

Phase 3 implements the Munim AI CFO suite in KiranaOS. It guards thin kirana retail margins against supplier price creep via distributor bill scanning (OCR via Sarvam Vision with local demo fallback), executes dual atomic writes to inventory and supplier ledger, deterministically reconciles daily Paytm settlement deductions ("Mera Paisa Kam Kyun Aaya?"), and manages the ambiguous UPI reconciliation queue for Paytm QR webhooks.
</domain>

<decisions>
## Implementation Decisions

### Wholesale Price-Creep Detection Engine (Locked)
- Implemented in `backend/services/deterministic_engine.py` using pure Python arithmetic:
  - $\text{Price Creep \%} = \left(\frac{C_{\text{new}} - C_{\text{old}}}{C_{\text{old}}}\right) \times 100$
  - $\text{Old Margin \%} = \left(\frac{P_{\text{sell}} - C_{\text{old}}}{P_{\text{sell}}}\right) \times 100$
  - $\text{New Margin \%} = \left(\frac{P_{\text{sell}} - C_{\text{new}}}{P_{\text{sell}}}\right) \times 100$
  - Flag triggered when $\text{Price Creep \%} \ge 2.0\%$, generating recommended retail selling price:
    $P_{\text{recommended}} = \lceil C_{\text{new}} \times (1 + \text{Target Margin Ratio}) \rceil$
  - Benchmark example from PRD §7.2: Gupta Wholesalers hikes Fortune Sunlite Oil 1L from ₹132 to ₹142 (+7.58%), eroding ₹10/L margin. Recommended new MRP: ₹160. Spoken Hindi alert attached.

### Distributor Bill Scanner & Dual Action Confirmation (Locked)
- Endpoint `POST /api/v1/cfo/scan-distributor-bill`:
  - Supports custom image file upload (`multipart/form-data`) OR `{"use_demo_sample": true}`.
  - Integrates Sarvam Vision OCR (with realistic offline demo fallback per the Law of Demo-Day Survivability).
  - Returns structured line items (Fortune Oil 20L, Maggi Masala 96pkts, Amul Ghee 2 tins), price creep alerts, invoice total (₹4,920.00), dual action preview, and synthesized Bulbul TTS audio base64.
- Endpoint `POST /api/v1/cfo/confirm-distributor-bill`:
  - Executes atomic dual write:
    1. Updates `inventory_items` stock (+delta) and updates `last_unit_cost` / `previous_unit_cost`.
    2. Logs each line item movement into append-only `stock_events`.
    3. Records the payable total in `supplier_ledger` (`entry_type='INVOICE_CREDIT'`, `supplier_name='Gupta Wholesalers, APMC Vashi'`, `amount=4920.00`).
    4. Logs an audit entry to `business_events` with `event_category='CFO_ALERT'`.

### Paytm Settlement & Deduction Waterfall Explainer (Locked)
- Endpoint `GET /api/v1/cfo/settlement-explainer`:
  - Mathematical Invariant:
    $$\text{Net Bank Settlement} = \text{Gross QR Volume} - (\text{Loan Daily EDI} + \text{Soundbox Subscription Fee} + \text{Instant Refunds} + \text{Hold Amount})$$
  - Assert that components balance down to ₹0.01 before returning (`verification_status='DETERMINISTICALLY_BALANCED'`).
  - Baseline Demo Payout:
    - Gross QR Collections: ₹6,450.00
    - Paytm Business Loan Daily EDI (Loan #PTM-882): ₹450.00
    - Paytm AI Soundbox Monthly Subscription: ₹125.00
    - Customer Refund (Txn #99102): ₹60.00
    - Total Deductions: ₹635.00
    - Net Bank Payout: ₹5,815.00 into State Bank of India •••• 4921
  - Accompanied by synthesized Bulbul TTS spoken explanation in Hindi (`spoken_explanation_hi`).

### Ambiguous UPI Reconciliation Queue (Locked)
- Endpoint `GET /api/v1/cfo/unmatched-payments`: returns pending items from `unmatched_payments_queue`.
- Endpoint `POST /api/v1/cfo/resolve-unmatched-payment`:
  - Merchant selects the correct debtor (e.g., assign ₹200 to Suresh Patil vs Suresh Kadam).
  - Updates queue item status to `LINKED` and records `resolved_customer_id`.
  - Appends `REPAYMENT_JAMA` to `ledger_entries` and updates customer balance to ₹0.
  - Logs audit record to `business_events`.
- Endpoint `POST /api/v1/cfo/simulate-qr-webhook`:
  - Ingests simulated Paytm QR payment webhook.
  - If exact unique customer matches amount/payer name: auto-proposes settlement.
  - If multiple candidate matches exist: inserts into `unmatched_payments_queue` for 1-tap review.

### the agent's Discretion
- Sample Bill Generator: Provide a utility to generate clean sample invoice SVG/PNG in `backend/assets/` representing Gupta Wholesalers invoice `GW-2026-994`.
- Router structure: `backend/routers/cfo_router.py`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PRD Master Specification
- `munim_ai_kiranaos_master_hackathon_prd.md` §1.2 (Munim AI CFO - Margin, Cash Flow & Platform Trust)
- `munim_ai_kiranaos_master_hackathon_prd.md` §5.2 (Wholesale Price-Creep Detection Formula)
- `munim_ai_kiranaos_master_hackathon_prd.md` §5.3 (Paytm Settlement & Deduction Reconciliation Formula)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.2 (Distributor Bill Scanner API Contract)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.3 (Settlement & Deduction Explainer API Contract)

### Planning Artifacts
- `.planning/REQUIREMENTS.md` (CFO-01 through CFO-05)
- `.planning/ROADMAP.md` (Phase 3 details & success criteria)
- `.planning/phases/02-core-voice-multimodal-gateway/02-VERIFICATION.md` (Phase 2 completion evidence)

</canonical_refs>

<specifics>
## Specific Ideas
- Provide high-contrast alerts in response payloads so frontend can display bright red price-creep warning badges.
- Ensure the settlement explainer asserts the exact arithmetic equality before returning, preventing any rounding discrepancies.
</specifics>

<deferred>
## Deferred Ideas
- Automated live bank account integration (mock settlement calculation over Paytm QR records is the hackathon target).
</deferred>

---

*Phase: 03-ai-cfo-margin-defense-settlement-reconciliation*  
*Context gathered: 2026-11-11 via PRD Express Path*
