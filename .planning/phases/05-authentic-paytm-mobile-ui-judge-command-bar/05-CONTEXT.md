# Phase 5: Authentic Paytm Mobile UI & Judge Quick-Trigger Command Bar - Context

**Gathered:** 2026-11-12  
**Status:** Ready for planning  
**Source:** PRD Express Path (`munim_ai_kiranaos_master_hackathon_prd.md`) + User Explicit Directives

<domain>
## Phase Boundary

Phase 5 delivers the complete **Munim-AI Mobile Merchant App** frontend (`frontend/`), built with **React 18 + Vite + TypeScript + Tailwind CSS**, connecting live to the FastAPI KiranaOS backend (`http://localhost:8000` via Vite dev proxy `/api -> http://localhost:8000` and direct/configurable base URL).

**Critical User Directive:**
- The UI **MUST be an authentic mobile app experience** referencing the **Paytm for Business (Paytm Merchant) App**, NOT a generic desktop dashboard or webpage. On desktop/laptop judge screens, the app renders inside a crisp, high-contrast mobile device frame (`max-w-[430px]`, realistic mobile top status bar, Paytm header, bottom tab bar, floating action bar), and fills full mobile width on smartphones.
- Support both built-in demo sample presets AND **custom user file uploads** for distributor wholesale bills (AI CFO) and handwritten bahi-khata notebook pages (AI CMO / Onboarding).

## Core Requirements Covered
- `UI-01`: Authentic mobile-first Paytm Merchant App interface (`#002970` Deep Paytm Navy, `#00BAF2` Paytm Cyan, crisp Inter/Plus Jakarta Sans + Noto Sans Devanagari typography, authentic Paytm Merchant header, balance/settlement banner, and mobile frame viewport).
- `UI-02`: 4 primary operational tabs with bottom mobile navigation:
  1. **Munim Mic** (Operations & Live Khata)
  2. **AI CFO** (Distributor Bill Scanner + Price Creep + Settlement Waterfall + Unmatched UPI Queue)
  3. **AI CMO** (Boli-Baki Voice Recovery + Dead-Stock Break-Even Studio + 60s Diwali Closing Ritual + Bahi-Khata Scanner)
  4. **Memory** (Unified Business Memory Immutable Audit Timeline)
- `UI-03`: Expandable **"Why am I seeing this?"** evidence drawers on proposal cards, alerts, settlement breakdowns, and timeline events showing formulas, source utterances/documents, and before/after balance deltas—strictly honoring Propose $\rightarrow$ Confirm $\rightarrow$ Commit gates.
- `UI-04`: Collapsible **Judge Demo Quick-Trigger Bar** featuring all 6 one-click live demo flows feeding directly through the real backend endpoints (with zero mocked UI-only shortcuts) so stage demos are 100% immune to venue noise.
- `UI-05`: Embedded interactive **Paytm Soundbox Simulator** banner/toast that visually pulses and plays genuine synthesized WAV audio (`audio/wav` base64 from Bulbul TTS + fallback Web Audio chime) upon receiving payment webhooks or confirmation announcements.
</domain>

<decisions>
## Implementation Decisions

### Mobile Form Factor & Authentic Paytm Merchant Styling (Locked)
- **Strict Mobile Viewport Shell (`UI-01`):**
  - Root layout centers a `max-w-[430px]` mobile phone shell (`h-[100dvh]` / `min-h-screen` on mobile, rounded bezel frame with subtle shadow on desktop backdrop) so judges immediately see an authentic mobile merchant app.
  - **Paytm Design System Tokens:**
    - Primary Navy: `#002970` (headers, primary cards, active navigation accents, Paytm branding bar)
    - Primary Cyan: `#00BAF2` (action highlights, Paytm Verified badges, Soundbox pulses, Soundbox waveform accents)
    - Surface Background: `#F5F7FA` (Paytm crisp light gray canvas) with `#FFFFFF` elevated cards (`rounded-2xl`, hairline `#E5E9F0` borders)
    - Semantic Alerts: `#E11D48` / `#FEF2F2` (Red Price Creep & Loss-Making Guardrail), `#059669` / `#ECFDF5` (Emerald Balanced / Settled / Paid), `#D97706` / `#FFFBEB` (Amber Ambiguity Queue / Disambiguation Hold)
- **Top Paytm Merchant Header:**
  - Shows store identity: `"Ganesh Provision & General Store"` (`Dadar, Mumbai`), Paytm Verified Merchant badge, Soundbox Online green indicator, and quick language selector (`Hinglish` | `Marathi` | `Hindi`).
- **Bottom 4-Tab Mobile Navigation Bar:**
  - `Mic` (Munim Mic & Khata), `AI CFO` (with live alert badge count), `AI CMO` (with overdue debtor/closing badge), `Memory` (Audit Timeline).

### Tab 1: Munim Mic & Live Khata (`UI-02`, `UI-03`)
- **Voice & Text Command Input:**
  - Pulsing Sarvam Mic button supporting real browser `MediaRecorder` audio capture -> `POST /api/v1/voice/propose` (multipart audio upload) PLUS quick Hinglish/Marathi text input bar for silent/text entry.
  - Language selector (`hi-IN` Hinglish/Hindi, `mr-IN` Marathi).
- **Propose $\rightarrow$ Confirm $\rightarrow$ Commit Rendering:**
  - **`status === "NEEDS_DISAMBIGUATION"`:** Renders high-priority Amber Disambiguation Card showing `"Why am I seeing this?"` + candidate cards (`Suresh Patil (Tailor)` vs `Suresh Kadam (Kirana)`, showing phone, udhaar, last visit) with 1-tap selection that commits via `POST /api/v1/voice/confirm` (using `action: "APPROVE"`, `customer_id`, `intent`, `amount`, `source_utterance`) or re-proposes cleanly.
  - **`status === "PROPOSAL"`:** Renders typed Proposal Card showing current balance/stock $\rightarrow$ proposed delta $\rightarrow$ new balance/stock, expandable `"Why am I seeing this?"` evidence drawer, Bulbul voice preview audio button, and explicit **`Approve (Haan)`** (`POST /api/v1/voice/confirm` with `action: "APPROVE"`) and **`Cancel`** buttons.
- **Ambiguous UPI Review Drawer & Live Customer Khata Strip:**
  - Displays pending items from `GET /api/v1/cfo/unmatched-payments` (pre-seeded Suresh ₹200 QR payment) with 1-tap debtor resolution buttons calling `POST /api/v1/cfo/resolve-unmatched-payment`.
  - Scrollable Customer Khata summary cards (`GET /api/v1/memory/customers`) showing balances and tap-to-inspect ledger history (`GET /api/v1/memory/customers/{id}/ledger`).

### Tab 2: AI CFO — Margin Defense, Bills & Settlement (`UI-02`, `UI-03`, `CFO-01..05`)
- **Distributor Bill Scanner Card (Custom Upload + Demo Sample):**
  - Supports **"Scan Sample Bill (Gupta Wholesalers)"** (`use_demo_sample: true`) AND **"Upload Custom Bill Photo"** (`<input type="file" accept="image/*" capture="environment">`, multipart upload to `POST /api/v1/cfo/scan-distributor-bill`).
  - Displays extracted line items (`Fortune Sunlite Oil 1L`, `Maggi Masala 70g`, `Amul Pure Ghee 1L`), flashing red **`+7.58% PRICE CREEP ALERT`** badge when flagged, margin erosion delta (`₹132 -> ₹142`), optional toggle to adopt recommended new MRP (`₹160`), Bulbul Hindi alert playback, `"Why am I seeing this?"` formula drawer, dual-action preview, and 1-tap **`Confirm & Update Stock + Khata`** (`POST /api/v1/cfo/confirm-distributor-bill`).
- **"Mera Paisa Kam Kyun Aaya?" Settlement Waterfall Card:**
  - Fetches `GET /api/v1/cfo/settlement-explainer`.
  - Visualizes the exact Paytm settlement waterfall: Gross QR Collections (`₹6,450.00`) minus itemized deductions (`Paytm Loan Daily EDI -₹450`, `Soundbox Subscription -₹125`, `Instant Refund -₹60`) = Net Settled to SBI (`₹5,815.00`), green **`DETERMINISTICALLY BALANCED`** seal down to ₹0.01, `"Why am I seeing this?"` invariant drawer, and **"Listen in Hindi"** Bulbul TTS speaker button.
- **Ambiguous UPI Queue & QR Webhook Simulator Card:**
  - Lists pending unmatched QR payments (`GET /api/v1/cfo/unmatched-payments`) with 1-tap resolution (`POST /api/v1/cfo/resolve-unmatched-payment`).
  - Quick simulator button (`POST /api/v1/cfo/simulate-qr-webhook`) to fire a live ambiguous ₹200 "Suresh" QR payment.

### Tab 3: AI CMO — Recovery, Campaigns, Closing Ritual & Bahi-Khata (`UI-02`, `UI-03`, `CMO-01..06`, `ONBOARD-01`)
- **"Boli-Baki" Overdue Udhaar Recovery Queue:**
  - Fetches `GET /api/v1/cmo/overdue-debtors` (Ramesh Sharma ₹650, 18 days overdue).
  - **"Generate Voice Link"** (`POST /api/v1/cmo/boli-baki-recovery`) shows native Marathi/Hindi translated message, Bulbul audio wave playback, tracked link chip (`paytm.me/munim-ramesh-650`), and **"⚡ Simulate Customer Paid"** button (`POST /api/v1/cmo/simulate-link-paid/{slug}`) which settles Ramesh's balance to ₹0 live and triggers the Paytm Soundbox Simulator chime!
- **Dead-Stock Break-Even Studio & Per-Language Attribution:**
  - Fetches `GET /api/v1/cmo/dead-stock` (`Haldiram Aloo Bhujia 400g`, 22 days unsold).
  - Interactive discount slider (`₹5` to `₹35`) triggering `POST /api/v1/cmo/dead-stock-campaign`.
  - Clearly demonstrates the **Hard Stop Guardrail** (`OFFER_BLOCKED_LOSS_MAKING` red block banner when discount $\ge ₹23$ wipes margin) vs safe break-even math (`M_old = ₹23 -> M_new = ₹13, Need 8/day (+4 extra)`).
  - Displays tracked `mr-IN` vs `hi-IN` promo links with **"Simulate Click/Buy"** buttons (`POST /api/v1/cmo/simulate-promo-click/{slug}`) updating live per-language redemption & revenue bars.
- **60-Second Dukaan Closing Ritual Card:**
  - Fetches `GET /api/v1/cmo/dukaan-closing-ritual`.
  - Shows Today's QR Sales (`₹6,450+`), Udhaar Recovered (`₹0 -> ₹650` live), Unmatched UPI count, the **$3.5\times$ Diwali Restock Alert** (`Amul Pure Ghee 1L`: 4 left, 35 projected, order **31 tins**), `"Why am I seeing this?"` formula breakdown, Bulbul Hindi audio briefing button, and 1-tap copy/share order draft.
- **Handwritten Bahi-Khata Notebook Scanner (`ONBOARD-01`):**
  - Supports **"Scan Sample Notebook Page"** AND **"Upload Custom Notebook Photo"** (`POST /api/v1/cmo/scan-bahi-khata`).
  - Displays batch-editable rows (customer name, phone, language, editable amount, match badge `NEW_CUSTOMER` / `EXISTING_CUSTOMER`), and 1-tap **`Confirm & Onboard All`** (`POST /api/v1/cmo/confirm-bahi-khata`).

### Tab 4: Unified Business Memory Timeline (`UI-02`, `UI-03`)
- Fetches `GET /api/v1/memory/events` with category filter pills (`ALL`, `LEDGER`, `INVENTORY`, `CFO_ALERT`, `CMO_GROWTH`, `SETTLEMENT`, `SYSTEM_STARTUP`).
- Renders immutable chronological timeline cards with actor badges (`MERCHANT_APPROVED`, `SYSTEM_AUTO`, `SYSTEM_GUARD`), timestamps, and expandable `"Why am I seeing this?"` JSON evidence viewer.

### Judge Demo Quick-Trigger Bar & Embedded Paytm Soundbox Simulator (`UI-04`, `UI-05`)
- **Interactive Paytm Soundbox Simulator (`UI-05`):**
  - Persistent compact Soundbox widget inside the Paytm mobile shell header/overlay that animates equalizer bars + plays decoded `audio/wav` base64 (with safe browser WebAudio fallback chime if audio autoplay is restricted or audio is empty) whenever any voice confirmation, settlement explanation, closing ritual, or `simulate-link-paid` payment arrives.
- **Collapsible "⚡ Judge Demo Quick-Trigger Bar" (`UI-04`):**
  - Docked collapsible drawer/bar right above or attached to the mobile frame containing all 6 PRD §8.2 one-click demo buttons that automatically switch to the right tab and execute the real FastAPI endpoint:
    1. `[🎤 "Suresh ka ₹200 udhaar likho"]` $\rightarrow$ Tab 1 + `/api/v1/voice/propose`
    2. `[🧾 Scan Bill (+7.58% Oil Creep)]` $\rightarrow$ Tab 2 + `/api/v1/cfo/scan-distributor-bill`
    3. `[🏦 "Mera Paisa Kam Kyun Aaya?"]` $\rightarrow$ Tab 2 + `/api/v1/cfo/settlement-explainer` + plays Hindi audio
    4. `[💸 Fire Ambiguous ₹200 QR Webhook]` $\rightarrow$ Tab 2 + `/api/v1/cfo/simulate-qr-webhook` (unique txn id) + refreshes queue
    5. `[📢 Marathi Udhaar Link -> Simulate Paid]` $\rightarrow$ Tab 3 + `/api/v1/cmo/boli-baki-recovery` (and quick Paid action)
    6. `[🪔 Run 60s Diwali Closing Ritual]` $\rightarrow$ Tab 3 + `/api/v1/cmo/dukaan-closing-ritual` + plays Soundbox briefing
</decisions>

<canonical_refs>
## Canonical References

### PRD Master Specification
- `munim_ai_kiranaos_master_hackathon_prd.md` §8.1 (Mobile/Web 4-Tab Layout)
- `munim_ai_kiranaos_master_hackathon_prd.md` §8.2 (Judge Demo Quick-Trigger Bar)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.1–§7.6 (Exact API Contracts)

### Backend Contracts (Live FastAPI Routers)
- `backend/routers/memory_router.py` (`/api/v1/memory/*`)
- `backend/routers/voice_router.py` (`/api/v1/voice/*`)
- `backend/routers/cfo_router.py` (`/api/v1/cfo/*`)
- `backend/routers/cmo_router.py` (`/api/v1/cmo/*`)

### Planning Artifacts
- `.planning/REQUIREMENTS.md` (`UI-01` through `UI-05`)
- `.planning/ROADMAP.md` (Phase 5 details & success criteria)
</canonical_refs>

<specifics>
## Specific Ideas
- Keep the mobile shell feeling unmistakably like **Paytm for Business**: deep `#002970` top curved header blending into `#F5F7FA` cards, `#00BAF2` live status indicators, ₹ Rupee tabular-nums formatting, and crisp mobile tap targets (`min-h-[44px]`).
- Make sure custom invoice/bahi-khata file uploads show a clean thumbnail/filename preview before/after scanning.
- Ensure every backend mutation refreshes impacted queries immediately (e.g., resolving an unmatched payment updates customer balances, unmatched count, and memory timeline; confirming a bill updates inventory; simulating link paid updates debtor balance and closing ritual recovery amount).
</specifics>

<deferred>
## Deferred Ideas
- Full multi-column desktop analytics dashboard (explicitly out of scope per user instruction: strict Paytm mobile merchant interface).
</deferred>

---

*Phase: 05-authentic-paytm-mobile-ui-judge-command-bar*  
*Context gathered: 2026-11-12 via PRD Express Path*

