# Phase 4: AI CMO — Boli-Baki Recovery, Break-Even Studio & Closing Ritual - Context

**Gathered:** 2026-11-11  
**Status:** Ready for planning  
**Source:** PRD Express Path (`munim_ai_kiranaos_master_hackathon_prd.md`)

<domain>
## Phase Boundary

Phase 4 implements the Munim AI CMO suite and Bahi-Khata Onboarding Vision in KiranaOS. It accelerates store cash recovery and footfall with 100% deterministic math and vernacular outreach:
1. **"Boli-Baki" Multilingual Voice Udhaar Recovery (`CMO-01`, `CMO-02`, `CMO-03`):** Surfaces debtors overdue >10 days (e.g., Ramesh Sharma ₹650 overdue 18 days), translates polite reminders to the customer's native language via Sarvam Translate (`mr-IN`, `hi-IN`), synthesizes Bulbul v3 voice notes, issues tracked Paytm payment links (`paytm.me/munim-...`), and simulates instant payment webhook clearing with a live Soundbox chime (`"Paytm par 650 rupaye prapt hue"`).
2. **Dead-Stock Break-Even Studio & Per-Language Attribution (`CMO-04`, `CMO-05`):** Computes deterministic break-even daily sales volume ($V_{\text{req}}$) before allowing discounts on dead stock (>15 days unsold, e.g., Haldiram Aloo Bhujia 400g), enforces a hard stop guardrail against loss-making discounts (`OFFER_BLOCKED_LOSS_MAKING`), and tracks per-language Paytm promo link conversions (`mr-IN` vs `hi-IN`).
3. **60-Second Dukaan Closing Ritual (`CMO-06`):** Proactive EOD Soundbox briefing summarizing today's net QR sales, recovered udhaar, unmatched UPI queue count, and a deterministic $3.5\times$ Diwali festive restock forecast (e.g., Amul Pure Ghee 1L: current 4, projected 5-day demand 35, recommend ordering 31 tins from Gupta Wholesalers).
4. **Handwritten Bahi-Khata Page Scanner (`ONBOARD-01`):** Accepts physical notebook photo uploads or demo preset samples via Sarvam Vision OCR (with 6s timeout & offline fallback) and outputs batch-editable customer credit proposals for 1-tap onboarding into `customers` and `ledger_entries`.
</domain>

<decisions>
## Implementation Decisions

### Offer Break-Even Guardrail Engine (Locked)
- Implemented in `backend/services/deterministic_engine.py` using pure Python arithmetic per PRD §5.4:
  - Given item cost $C$, current selling price $P$, usual daily volume $V_{\text{base}}$, and proposed discount $D$:
  - Current Unit Margin: $M_{\text{old}} = P - C$
  - Discounted Unit Margin: $M_{\text{new}} = (P - D) - C$
  - **Hard Stop Guardrail:** If $M_{\text{new}} \le 0$, return `OFFER_BLOCKED_LOSS_MAKING` (*"This discount sells below your wholesale cost of ₹C"*).
  - Required Break-Even Daily Volume: $V_{\text{req}} = \lceil \frac{V_{\text{base}} \times M_{\text{old}}}{M_{\text{new}}} \rceil$
  - Extra Units Needed per Day: $\Delta V = V_{\text{req}} - V_{\text{base}}$
  - Benchmark example from PRD §7.5: Haldiram Aloo Bhujia 400g ($C = ₹72, P = ₹95, D = ₹10, V_{\text{base}} = 4 \rightarrow M_{\text{old}} = 23, M_{\text{new}} = 13, V_{\text{req}} = 8, \Delta V = 4$).

### Proactive Festival Restock Forecast Engine (Locked)
- Implemented in `backend/services/deterministic_engine.py` per PRD §5.5:
  - Given daily burn rate $B_{\text{daily}}$, festival surge multiplier $K_{\text{fest}}$, festival window $D_{\text{days}}$ (5 days), and current stock $S_{\text{curr}}$:
  - $\text{Projected Festive Demand} = \lceil B_{\text{daily}} \times K_{\text{fest}} \times D_{\text{days}} \rceil$
  - $\text{Recommended Order Qty} = \max(0, \text{Projected Festive Demand} - S_{\text{curr}})$
  - Benchmark example from PRD §7.6: Amul Pure Ghee 1L ($B_{\text{daily}} = 2, K_{\text{fest}} = 3.5, D_{\text{days}} = 5, S_{\text{curr}} = 4 \rightarrow \text{Demand} = 35, \text{Order Qty} = 31 \text{ tins}$).

### "Boli-Baki" Voice Udhaar Recovery & Simulated Soundbox Chime (Locked)
- Endpoints in `backend/routers/cmo_router.py`:
  - `GET /api/v1/cmo/overdue-debtors`: returns customers with outstanding udhaar > ₹0 and days since last visit > 10 days.
  - `POST /api/v1/cmo/boli-baki-recovery`: generates personalized polite reminder translated via `sarvam_engine.translate_text`, synthesized voice note via `sarvam_engine.synthesize_speech`, records or updates row in `campaigns_and_links` with unique tracked slug `paytm.me/munim-...`, and returns `simulate_webhook_endpoint`.
  - `POST /api/v1/cmo/simulate-link-paid/{slug}`: marks link status `'PAID'`, appends `REPAYMENT_JAMA` (`payment_mode='PAYTM_LINK'`) in `ledger_entries`, updates conversion/revenue metrics, logs `CMO_GROWTH` event in `business_events`, and returns Paytm Soundbox audio chime (`"Paytm par {amount} rupaye prapt hue"`).

### Dead-Stock Break-Even & Per-Language Attribution (Locked)
- `GET /api/v1/cmo/dead-stock`: lists inventory items unsold > 15 days (e.g., Haldiram Aloo Bhujia 400g).
- `POST /api/v1/cmo/dead-stock-campaign`: validates discount via `calculate_breakeven_offer`. Rejects loss-making discounts with `OFFER_BLOCKED_LOSS_MAKING`. If safe, generates/retrieves tracked per-language promo links (`mr-IN`, `hi-IN`) in `campaigns_and_links` and returns `math_audit` + `attributed_links`.
- `POST /api/v1/cmo/simulate-promo-click/{slug}`: increments `clicks`, `conversions`, and `revenue_collected` for per-language campaign attribution metrics.

### 60-Second Dukaan Closing Ritual (Locked)
- `GET /api/v1/cmo/dukaan-closing-ritual`: aggregates today's QR sales, today's recovered udhaar, unmatched UPI count, and calls `calculate_festive_restock_forecast` for high-surge items (Amul Pure Ghee 1L). Synthesizes `spoken_ritual_hi` via Bulbul v3 TTS.

### Handwritten Bahi-Khata Notebook Scanner (`ONBOARD-01`) (Locked)
- Service in `backend/services/bahi_khata_parser_service.py` + endpoints in `backend/routers/cmo_router.py`:
  - `POST /api/v1/cmo/scan-bahi-khata`: parses uploaded notebook page image (with 6s Sarvam Vision OCR timeout & realistic handwritten Marathi/Hindi khata fallback) into batch-editable customer credit proposals.
  - `POST /api/v1/cmo/confirm-bahi-khata`: atomically creates or matches customers and records confirmed `CREDIT_UDHAAR` entries in `ledger_entries` + `business_events` audit log.
</decisions>

<canonical_refs>
## Canonical References

### PRD Master Specification
- `munim_ai_kiranaos_master_hackathon_prd.md` §1.2 (Munim AI CMO - Recovery & Attributed Revenue)
- `munim_ai_kiranaos_master_hackathon_prd.md` §5.4 (Offer Break-Even Guardrail Formula)
- `munim_ai_kiranaos_master_hackathon_prd.md` §5.5 (Proactive Festival Restock Forecast Formula)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.4 ("Boli-Baki" Multilingual Voice Udhaar Recovery API)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.5 (Dead-Stock Break-Even & Attributed Campaign API)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.6 (60-Second Dukaan Closing Ritual API)
- `munim_ai_kiranaos_master_hackathon_prd.md` FR-07, FR-08, FR-09, FR-10

### Planning Artifacts
- `.planning/REQUIREMENTS.md` (CMO-01 through CMO-06, ONBOARD-01)
- `.planning/ROADMAP.md` (Phase 4 details & success criteria)
- `.planning/phases/03-ai-cfo-margin-defense-settlement-reconciliation/03-VERIFICATION.md`
</canonical_refs>

<specifics>
## Specific Ideas
- Keep all campaign attribution links idempotent and queryable so tab switching or page reload preserves click/conversion/revenue totals.
- Soundbox payment chime when simulating link paid must return valid playable base64 audio.
</specifics>

<deferred>
## Deferred Ideas
- Direct WhatsApp Business API outbound messaging (simulated sharing links + Bulbul audio preview in mobile app).
</deferred>

---

*Phase: 04-ai-cmo-recovery-break-even-closing-ritual*  
*Context gathered: 2026-11-11 via PRD Express Path*

