# Product Requirements Document (PRD): Munim-AI (powered by KiranaOS)

**Document Version:** 2.0 (Hackathon Master Specification)  
**Event:** Paytm Build for India AI Hackathon — Mumbai Edition  
**Track:** Track 1 — Merchant Growth AI (*"Build the AI business partner for every Paytm merchant"*)  
**Team:** Code Apex (Parth, Priyanshu, Rachit)  
**Architecture Paradigm:** Voice-First AI CFO & AI CMO over an Append-Only Deterministic Business Memory Layer  

---

## 1. Executive Summary & Mentor's Strategic Thesis

### 1.1 Why 90% of Track 1 Submissions Lose (And Why Munim-AI Wins)
As a hackathon judge and senior fintech architect, I see most teams fall into three predictable traps:
1. **The "ChatGPT Wrapper" Trap:** Teams connect speech-to-text to an LLM and let the LLM calculate ledger balances or invent sales insights (`"Your sales dropped 18% on Tuesday"`). In fintech, LLMs hallucinating arithmetic is an instant disqualification.
2. **The "Defensive Bookkeeper" Trap:** Teams build basic voice *udhaar* (credit) trackers. Khatabook, OkCredit, and Paytm's own merchant app already track basic entries. Recording debt does not equal *Merchant Growth*.
3. **The "Decorative Sponsor" Trap:** Teams use Sarvam AI only for basic transcription and ignore Paytm's actual business pain points (settlement confusion, loan EMI deductions, payment attribution, and supplier margin squeeze).

### 1.2 Our Winning Differentiation: The "Closed-Loop AI CFO & AI CMO"
**Munim-AI** is the vernacular voice- and vision-first front-end; **KiranaOS** is the deterministic, append-only relational memory engine underneath. 

Instead of acting as a passive notebook, Munim-AI acts as two proactive teammates aligned directly with Paytm's strategic roadmap:
* **Munim AI CFO (Protects Margin, Cash Flow & Platform Trust):**
  * **Distributor Bill Scanner & "Price-Creep" Detector:** Uses `Sarvam Vision` to digitize paper wholesale invoices, automatically updating inventory *and* supplier payable khata while alerting the merchant via `Bulbul TTS` when a distributor quietly hikes item rates (e.g., *"Gupta Wholesalers raised Fortune Oil by +7.58%, cutting your margin by ₹10/L"*).
  * **"Mera Paisa Kam Kyun Aaya?" Settlement & Deduction Explainer:** Solves Paytm's #1 merchant support complaint by deterministically reconciling yesterday's gross QR sales against today's net bank credit (accounting for Paytm Merchant Loan daily EDI/EMI, Soundbox subscription fees, and instant refunds).
  * **Cautious UPI Reconciliation with Ambiguity Queue:** Matches incoming Paytm QR payments to customer debt only when identity and amount evidence are strong; routes ambiguous payments (e.g., two customers named "Suresh" owing ₹200) to a 1-tap human review queue.
* **Munim AI CMO (Drives Footfall, Recovery & Attributed Revenue):**
  * **"Boli-Baki" Multilingual Voice Udhaar Recovery:** Identifies overdue credit (>10 days), translates a polite reminder into the customer's native tongue (`Sarvam Translate`), generates a natural `Bulbul v3` voice note from the "Shop Munim," and pairs it with a **unique tracked Paytm Payment Link**.
  * **"Will This Offer Lose Me Money?" Break-Even Studio & Per-Language Attribution:** Identifies dead stock (>15 days unsold) and churned regular buyers (>14 days absent). Before launching a discount, it computes deterministic break-even unit math and generates language-specific Paytm QR/Payment Links (`mr-IN`, `hi-IN`) so every rupee earned is 100% attributed.
  * **60-Second "Dukaan Closing Ritual" (Proactive EOD Soundbox Briefing):** At closing time, the AI speaks first—summarizing net settlement, recovered udhaar, and a **Predictive Festival Restock Alert** (using a deterministic $3.5\times$ Diwali demand multiplier to prevent peak-season stockouts).

---

## 2. Core Architectural Laws (Non-Negotiable Guardrails)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        1. MULTIMODAL INPUT LAYER                           │
│  • Sarvam Saaras v4 STT (Hinglish/Marathi + Dynamic DB Keyterm Biasing)    │
│  • Sarvam Vision OCR (Distributor Tax Invoices & Handwritten Bahi-Khata)   │
│  • Paytm Mock Webhook / MCP Adapter (Incoming UPI QR & Payment Links)      │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ Raw Transcript / Extracted Document JSON
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                   2. PROPOSE -> CONFIRM -> COMMIT GATE                     │
│  • Entity Resolution (Detects duplicate names: "Suresh Tailor" vs "Kirana")│
│  • Typed Action Proposal Card rendered on UI with "Why am I seeing this?"  │
│  • ZERO database writes occur until merchant taps Approve / speaks "Haan"  │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ Approved Typed Command + Idempotency Key
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                3. KIRANA-OS DETERMINISTIC MEMORY ENGINE                    │
│  • Strictly Append-Only SQL Ledger (No UPDATE/DELETE on financial amounts) │
│  • 100% Python Math (Balances, Price Creep %, Break-Even Units, EDI Split) │
│  • Closed-Loop Attribution Tracker (Paytm Link Click -> Webhook -> Settled)│
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ Verified Facts & Computed Delta
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       4. VERNACULAR OUTPUT LAYER                           │
│  • Sarvam Translate (Customer-specific Hindi / Marathi / Gujarati copy)    │
│  • Sarvam Bulbul v3 TTS (Simulated Paytm AI Soundbox & WhatsApp Voice Note)│
└────────────────────────────────────────────────────────────────────────────┘
```

1. **Law of Zero LLM Math:** The LLM never adds, subtracts, or calculates percentages. All balances, margin impacts, and festival restock quantities are computed in Python using decimal/float arithmetic over SQL records.
2. **Law of Append-Only Immutability:** Financial entries (`ledger_entries`) and inventory changes (`stock_events`) are append-only. Mistakes are fixed via linked `ADJUSTMENT` or `REVERSAL` records preserving full provenance.
3. **Law of Non-Breaking Additive Integration:** All new CFO/CMO modules mount as modular FastAPI routers (`/api/v1/cfo/*`, `/api/v1/cmo/*`) and isolated frontend tabs without breaking existing base routes.
4. **Law of Demo-Day Survivability:** Every external network call (Sarvam APIs, LLM inference) is wrapped in a 6-second timeout with an automatic fallback to realistic pre-computed Hindi/Marathi payloads so venue Wi-Fi failure cannot crash the live pitch.

---

## 3. Sponsor Stack Integration Matrix (Passing the "Remove Test")

*Judge's Rule: If you remove Sarvam or Paytm from your architecture and the product still works the same, that sponsor is just decoration.*

| Sponsor Capability | Exact Model / Endpoint Used | Where It Is Essential in Munim-AI |
| :--- | :--- | :--- |
| **Sarvam Speech-to-Text** | `saaras:v4` / `saaras:v3` (`mode="codemix"`) | Transcribes noisy shop-counter Hinglish/Marathi commands with **Dynamic Keyterm Biasing** (injecting customer names & Indian FMCG SKUs from SQL). |
| **Sarvam Text-to-Speech** | `bulbul:v3` (`hi-IN`, `mr-IN`) | Powers the **Proactive EOD Soundbox Briefing**, spoken confirmation cards, and **"Boli-Baki" WhatsApp audio reminders** sent to debtors. |
| **Sarvam Document Vision** | `Sarvam Vision` / Multimodal OCR | Reads messy Indian **Distributor Bills** (for stock + price-creep detection) and **Handwritten Bahi-Khata pages** (for instant onboarding). |
| **Sarvam Translation** | `Sarvam Translate` (`hi-IN` $\leftrightarrow$ `mr-IN` / `gu-IN`) | Converts a merchant's single offer or credit reminder into the exact native language of each customer in the database. |
| **Paytm Ecosystem** | Paytm Payment Links, QR Webhooks & Settlement Ledger | Powers **1-tap Udhaar collection links**, **Per-Language Campaign Attribution links**, **Ambiguous QR reconciliation**, and **Loan EDI / Soundbox deduction explanations**. |

---

## 4. Functional Requirements & Priority Matrix

* **P0 (Must Demo Live on Stage):** Core voice/vision loop, deterministic memory, CFO price-creep + settlement explainer, CMO audio recovery + break-even campaign + Diwali EOD briefing.
* **P1 (Built in Backend / Shown if Asked):** Handwritten Bahi-Khata batch import, idempotent retry guard.
* **P2 (Roadmap Slide Only — Do Not Code in 48h):** Multi-tenant RBAC, Redis worker queues, PSTN automated supplier phone calls, offline SQLite conflict resolution.

| ID | Module | Feature Name | Deterministic Logic & Acceptance Criteria | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01** | Core Voice | **Keyterm-Biased Voice Proposal** | Queries top customer names & SKUs from DB, passes to Sarvam STT, parses intent (`CREDIT`, `REPAYMENT`, `STOCK_IN`, `STOCKOUT`, `QUERY`), and returns an unconfirmed Proposal Card. | **P0** |
| **FR-02** | Core Memory | **Identity Disambiguation Guard** | When merchant says *"Suresh ka 200 udhaar likho"* and DB has `Suresh Patil (Tailor)` and `Suresh Kadam (Kirana)`, system blocks auto-write and prompts a 1-tap disambiguation card. | **P0** |
| **FR-03** | Core Memory | **Append-Only Ledger & Provenance** | Every confirmed card writes to `ledger_entries` + `business_events` with `source_utterance` and `idempotency_key`. Balances are derived via SQL `SUM()`. | **P0** |
| **FR-04** | AI CFO | **Supplier Bill Scan & Price-Creep Alert** | Scans distributor invoice (`Sarvam Vision`). Compares `new_unit_cost` vs `last_unit_cost`. Flags any hike $>2\%$ (e.g., Fortune Oil $+7.58\%$). Confirmation updates both `inventory_items` and `supplier_ledger`. | **P0** |
| **FR-05** | AI CFO | **Ambiguous UPI Reconciliation Queue** | Incoming Paytm QR webhook matches exact single debtor $\rightarrow$ auto-proposes settlement. If multiple debtors match amount/name $\rightarrow$ routes to `unmatched_payments_queue` for 1-tap resolution. | **P0** |
| **FR-06** | AI CFO | **"Mera Paisa Kam Kyun Aaya?" Explainer** | Reconciles Gross QR Sales minus Paytm Merchant Loan Daily EDI, Soundbox subscription fee, and refunds $=$ Net Bank Credit. Speaks summary via `Bulbul TTS`. | **P0** |
| **FR-07** | AI CMO | **"Boli-Baki" Voice Udhaar Recovery** | Filters debtors overdue $>10$ days. Generates translated text + `Bulbul TTS` polite audio reminder + tracked `paytm.me/munim-udhaar-{id}` link. Simulated payment clears ledger live. | **P0** |
| **FR-08** | AI CMO | **Dead-Stock Break-Even & Attributed Offers** | Finds stock with $0$ sales in $>15$ days. Calculates break-even extra units required before allowing discount. Generates separate Hindi & Marathi Paytm links to track exact conversion by language. | **P0** |
| **FR-09** | AI CMO | **Dukaan Closing Ritual (Diwali EOD Forecast)** | 60s spoken evening briefing: net sales, recovered credit, and deterministic festival surge check ($\text{Diwali Multiplier} = 3.5\times$) with 1-tap supplier reorder draft. | **P0** |
| **FR-10** | Onboarding | **Handwritten Bahi-Khata Page Scanner** | Photographs a physical notebook page via `Sarvam Vision` and converts rows into a batch of editable customer credit proposals. | **P1** |

---

## 5. Mathematical & Deterministic Formulas (Backend Specification)

All formulas below must live in `backend/services/deterministic_engine.py` and never be delegated to an LLM prompt.

### 5.1 Customer Outstanding Balance
$$\text{Outstanding Balance}(c) = \sum_{i \in \text{Confirmed}} \text{Credit}_i(c) - \sum_{j \in \text{Confirmed}} \text{Repayment}_j(c) + \sum_{k \in \text{Confirmed}} \text{Adjustment}_k(c)$$

### 5.2 Wholesale Price-Creep Detection (AI CFO)
When scanning a distributor invoice line item with `new_unit_cost` ($C_{\text{new}}$) against database `last_unit_cost` ($C_{\text{old}}$) and current retail `selling_price` ($P_{\text{sell}}$):
$$\text{Price Creep \%} = \left( \frac{C_{\text{new}} - C_{\text{old}}}{C_{\text{old}}} \right) \times 100$$
$$\text{Old Margin \%} = \left( \frac{P_{\text{sell}} - C_{\text{old}}}{P_{\text{sell}}} \right) \times 100, \quad \text{New Margin \%} = \left( \frac{P_{\text{sell}} - C_{\text{new}}}{P_{\text{sell}}} \right) \times 100$$
* **Rule:** If $\text{Price Creep \%} \ge 2.0\%$, trigger `PRICE_CREEP_WARNING` and recommend new retail selling price:
  $$P_{\text{recommended}} = \lceil C_{\text{new}} \times (1 + \text{Target Margin Ratio}) \rceil$$

### 5.3 Paytm Settlement & Deduction Reconciliation (AI CFO)
$$\text{Net Bank Settlement} = \text{Gross QR Volume} - \left( \text{Loan Daily EDI} + \text{Soundbox Subscription Fee} + \text{Instant Refunds} + \text{Hold Amount} \right)$$
* **Verification Invariant:** The backend asserts that the sum of components equals the exact settlement payout down to ₹0.01 before rendering the explanation card.

### 5.4 Offer Break-Even Guardrail ("Will This Offer Lose Me Money?" — AI CMO)
Given item cost $C$, current selling price $P$, usual daily volume $V_{\text{base}}$, and proposed discount $D$:
1. **Current Unit Margin:** $M_{\text{old}} = P - C$
2. **Discounted Unit Margin:** $M_{\text{new}} = (P - D) - C$
3. **Hard Stop Guardrail:** If $M_{\text{new}} \le 0$, return `OFFER_BLOCKED_LOSS_MAKING` (*"This discount sells below your wholesale cost of ₹$C$"*).
4. **Required Break-Even Daily Volume ($V_{\text{req}}$):**
   $$V_{\text{req}} = \left\lceil \frac{V_{\text{base}} \times M_{\text{old}}}{M_{\text{new}}} \right\rceil$$
5. **Extra Units Needed per Day:**
   $$\Delta V = V_{\text{req}} - V_{\text{base}}$$

### 5.5 Proactive Festival Restock Forecast (EOD Ritual)
Given daily burn rate $B_{\text{daily}}$, upcoming festival surge multiplier $K_{\text{fest}}$ (e.g., $3.5\times$ for Ghee/Oil/Sweets before Diwali), festival window $D_{\text{days}}$ (5 days), and current stock $S_{\text{curr}}$:
$$\text{Projected Festive Demand} = \lceil B_{\text{daily}} \times K_{\text{fest}} \times D_{\text{days}} \rceil$$
$$\text{Recommended Order Qty} = \max\left(0, \text{Projected Festive Demand} - S_{\text{curr}}\right)$$

---

## 6. Authoritative Database Schema (SQLite / PostgreSQL Compatible)

Use `CREATE TABLE IF NOT EXISTS` so existing tables remain untouched while adding missing structures.

```sql
-- 1. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',          -- JSON list e.g. ["Raju Mistri", "Raju Bhai"]
    phone TEXT,
    preferred_language TEXT DEFAULT 'hi-IN', -- 'hi-IN', 'mr-IN', 'gu-IN'
    regular_cycle_days INTEGER DEFAULT 4,
    last_visit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Append-Only Financial Ledger (NEVER UPDATE OR DELETE ROWS)
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    entry_type TEXT NOT NULL,           -- 'CREDIT_UDHAAR', 'REPAYMENT_JAMA', 'REVERSAL_ADJUSTMENT'
    amount REAL NOT NULL CHECK (amount > 0),
    payment_mode TEXT DEFAULT 'UDHAAR', -- 'UDHAAR', 'CASH', 'PAYTM_QR', 'PAYTM_LINK'
    provider_ref TEXT UNIQUE,           -- Idempotency key / UPI Txn ID
    source_utterance TEXT,              -- Exact transcript or provenance
    confidence_score REAL DEFAULT 1.0,
    status TEXT DEFAULT 'CONFIRMED',    -- 'CONFIRMED', 'REVERSED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Products & Inventory Master
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_name TEXT NOT NULL UNIQUE,
    local_aliases TEXT DEFAULT '[]',    -- JSON list e.g. ["tel", "fortune oil", "sunflower"]
    category TEXT DEFAULT 'Staples',
    current_stock INTEGER DEFAULT 0,
    unit TEXT DEFAULT 'packets',
    last_unit_cost REAL NOT NULL,
    previous_unit_cost REAL NOT NULL,
    selling_price REAL NOT NULL,
    avg_daily_burn REAL DEFAULT 2.0,
    festive_multiplier REAL DEFAULT 1.0,-- e.g. 3.5 for Amul Ghee during Diwali
    reorder_threshold INTEGER DEFAULT 5,
    supplier_name TEXT,
    supplier_phone TEXT,
    last_restocked_at TIMESTAMP,
    last_sold_at TIMESTAMP
);

-- 4. Append-Only Inventory Movements
CREATE TABLE IF NOT EXISTS stock_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    event_type TEXT NOT NULL,           -- 'INWARD_INVOICE', 'INWARD_VOICE', 'STOCKOUT_FLAG', 'EOD_AUDIT'
    quantity_delta INTEGER NOT NULL,    -- e.g. +48 or -5
    unit_cost REAL,
    invoice_number TEXT,
    raw_transcript TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Supplier Payable Ledger (Distributor Khata)
CREATE TABLE IF NOT EXISTS supplier_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    entry_type TEXT NOT NULL,           -- 'INVOICE_CREDIT', 'SUPPLIER_PAYOUT'
    amount REAL NOT NULL,
    invoice_number TEXT,
    price_creep_flagged BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Ambiguous UPI Payment Review Queue
CREATE TABLE IF NOT EXISTS unmatched_payments_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upi_txn_id TEXT NOT NULL UNIQUE,
    amount REAL NOT NULL,
    payer_name TEXT,
    payer_vpa TEXT,
    candidate_customers_json TEXT,      -- JSON array of matching customer objects
    ambiguity_reason TEXT,              -- e.g. "Multiple customers named Suresh owe ₹200"
    status TEXT DEFAULT 'PENDING_REVIEW', -- 'PENDING_REVIEW', 'LINKED'
    resolved_customer_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Closed-Loop Growth Campaigns & Paytm Link Attribution
CREATE TABLE IF NOT EXISTS campaigns_and_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_title TEXT NOT NULL,
    campaign_type TEXT NOT NULL,        -- 'UDHAAR_VOICE_LINK', 'DEAD_STOCK_BUNDLE', 'CHURN_WINBACK'
    target_customer_id INTEGER,
    language_code TEXT NOT NULL,        -- 'hi-IN', 'mr-IN'
    paytm_link_slug TEXT NOT NULL UNIQUE, -- e.g. 'paytm.me/munim-ramesh-650'
    amount_expected REAL,
    discount_per_unit REAL DEFAULT 0.0,
    breakeven_extra_units INTEGER DEFAULT 0,
    message_text TEXT,
    tts_audio_base64 TEXT,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    revenue_collected REAL DEFAULT 0.0,
    status TEXT DEFAULT 'SENT',         -- 'SENT', 'PAID'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Unified Audit Trail (Business Memory Timeline)
CREATE TABLE IF NOT EXISTS business_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_category TEXT NOT NULL,       -- 'LEDGER', 'INVENTORY', 'CFO_ALERT', 'CMO_GROWTH', 'SETTLEMENT'
    summary_text TEXT NOT NULL,
    evidence_json TEXT NOT NULL,        -- Powers the "Why am I seeing this?" drawer
    actor TEXT DEFAULT 'MERCHANT_APPROVED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. Detailed API Contracts (FastAPI Backend)

### 7.1 Voice Proposal & Disambiguation (`POST /api/v1/voice/propose`)
**Request:**
```json
{
  "transcript_override": "Suresh ka 200 rupaye udhaar likh do",
  "language_hint": "hi-IN"
}
```
**Response (When Ambiguous Identity Detected):**
```json
{
  "status": "NEEDS_DISAMBIGUATION",
  "intent": "CREDIT_UDHAAR",
  "extracted_amount": 200.0,
  "ambiguity_reason": "Found 2 customers matching 'Suresh' in shop memory.",
  "candidates": [
    { "customer_id": 2, "name": "Suresh Patil (Tailor)", "current_udhaar": 200.0, "last_visit": "5 days ago" },
    { "customer_id": 3, "name": "Suresh Kadam (Kirana)", "current_udhaar": 450.0, "last_visit": "9 days ago" }
  ],
  "why_am_i_seeing_this": "KiranaOS blocks blind writes when customer names overlap.",
  "spoken_prompt_hi": "Dukaan mein do Suresh hain: Suresh Tailor ya Suresh Kirana? Kiske khate mein 200 likhoon?",
  "tts_audio_base64": "<base64_wav_from_sarvam_bulbul>"
}
```

### 7.2 Distributor Bill Scanner + Price Creep (`POST /api/v1/cfo/scan-distributor-bill`)
**Request:** `multipart/form-data` image OR `{"use_demo_sample": true}`  
**Response:**
```json
{
  "status": "PROPOSAL",
  "supplier_name": "Gupta Wholesalers, APMC Vashi",
  "invoice_number": "GW-2026-994",
  "invoice_total": 4920.00,
  "price_creep_alerts": [
    {
      "sku_name": "Fortune Sunlite Oil 1L",
      "previous_unit_cost": 132.00,
      "new_unit_cost": 142.00,
      "creep_percentage": 7.58,
      "margin_erosion_per_unit": 10.00,
      "recommended_new_mrp": 160.00,
      "alert_hi": "Savdhaan! Gupta ji ne Fortune tel ka rate ₹132 se badha kar ₹142 (+7.58%) kar diya hai."
    }
  ],
  "line_items": [
    { "item_id": 2, "sku_name": "Fortune Sunlite Oil 1L", "qty": 20, "unit": "liters", "unit_cost": 142.00, "line_total": 2840.00 },
    { "item_id": 4, "sku_name": "Maggi Masala 70g", "qty": 96, "unit": "packets", "unit_cost": 11.25, "line_total": 1080.00 },
    { "item_id": 1, "sku_name": "Amul Pure Ghee 1L", "qty": 2, "unit": "tins", "unit_cost": 500.00, "line_total": 1000.00 }
  ],
  "dual_action_preview": "Confirming adds +118 units to Inventory AND records ₹4,920 payable in Gupta Wholesalers Khata.",
  "tts_audio_base64": "<base64_wav>"
}
```

### 7.3 Settlement & Deduction Explainer (`GET /api/v1/cfo/settlement-explainer`)
**Response:**
```json
{
  "settlement_date": "2026-11-09",
  "bank_account": "State Bank of India •••• 4921",
  "gross_qr_collections": 6450.00,
  "deductions": [
    { "type": "PAYTM_MERCHANT_LOAN_EDI", "label": "Paytm Business Loan Daily Installment (Loan #PTM-882)", "amount": 450.00 },
    { "type": "SOUNDBOX_RENTAL", "label": "Paytm AI Soundbox Monthly Subscription", "amount": 125.00 },
    { "type": "CUSTOMER_REFUND", "label": "Instant Refund (Txn #99102)", "amount": 60.00 }
  ],
  "total_deductions": 635.00,
  "net_settled_to_bank": 5815.00,
  "verification_status": "DETERMINISTICALLY_BALANCED",
  "spoken_explanation_hi": "Kal aapki kul QR bikri ₹6,450 thi. Ismein se ₹450 aapke Paytm loan ki daily kist, ₹125 Soundbox kiraya, aur ₹60 refund katne ke baad ₹5,815 aapke SBI bank mein jama ho gaye hain.",
  "tts_audio_base64": "<base64_wav>"
}
```

### 7.4 "Boli-Baki" Multilingual Voice Udhaar Recovery (`POST /api/v1/cmo/boli-baki-recovery`)
**Response:**
```json
{
  "customer_id": 1,
  "customer_name": "Ramesh Sharma",
  "preferred_language": "mr-IN",
  "overdue_days": 18,
  "outstanding_amount": 650.00,
  "paytm_payment_link": "https://paytm.me/munim-ramesh-650",
  "translated_message": "नमस्कार रमेश भाऊ, गणेश किराणा मधून मुनीम-AI बोलत आहे. आपले ₹६५० बाकी आहेत. कृपया खालील Paytm लिंकवर क्लिक करून जमा करा.",
  "tts_audio_base64": "<base64_marathi_bulbul_voice_note>",
  "simulate_webhook_endpoint": "/api/v1/cmo/simulate-link-paid/munim-ramesh-650"
}
```

### 7.5 Dead-Stock Break-Even & Attributed Campaign (`POST /api/v1/cmo/dead-stock-campaign`)
**Request:** `{"item_id": 3, "proposed_discount_rupees": 10.0}`  
**Response:**
```json
{
  "sku_name": "Haldiram Aloo Bhujia 400g",
  "days_unsold": 22,
  "current_stock": 28,
  "unit_cost": 72.00,
  "selling_price": 95.00,
  "proposed_discount": 10.00,
  "math_audit": {
    "old_margin_per_unit": 23.00,
    "new_margin_per_unit": 13.00,
    "usual_daily_sales": 4,
    "breakeven_daily_sales_needed": 8,
    "extra_units_needed_per_day": 4,
    "verdict": "PROFITABLE_IF_VOLUME_DOUBLES"
  },
  "attributed_links": [
    { "language": "mr-IN", "link": "paytm.me/promo-mr-bhujia", "redemptions": 5, "revenue": 425.00 },
    { "language": "hi-IN", "link": "paytm.me/promo-hi-bhujia", "redemptions": 3, "revenue": 255.00 }
  ]
}
```

### 7.6 60-Second Dukaan Closing Ritual (`GET /api/v1/cmo/dukaan-closing-ritual`)
**Response:**
```json
{
  "today_qr_sales": 6450.00,
  "today_udhaar_recovered": 650.00,
  "unmatched_upi_count": 1,
  "festive_restock_forecast": {
    "upcoming_event": "Diwali Peak Week",
    "days_away": 5,
    "sku_name": "Amul Pure Ghee 1L",
    "current_stock": 4,
    "normal_daily_burn": 2,
    "festive_surge_multiplier": 3.5,
    "projected_5day_demand": 35,
    "recommended_order_qty": 31,
    "supplier_name": "Gupta Wholesalers",
    "one_tap_order_draft": "Namaste Gupta ji, Diwali stock ke liye 31 tin Amul Pure Ghee 1L kal subah bhej dijiye."
  },
  "spoken_ritual_hi": "Dukaan band karne ka samay! Aaj ₹6,450 ki QR bikri hui aur Ramesh ji ka ₹650 udhaar wapas aaya. Zaroori sujhav: Diwali 5 din door hai, Amul Ghee ki maang 3.5 guna badhti hai par sirf 4 dabbe bache hain. Kya Gupta ji ko 31 dabbe ka order bhej doon?",
  "tts_audio_base64": "<base64_wav>"
}
```

---

## 8. Frontend Architecture & The "Judge Demo Command Bar"

### 8.1 Mobile/Web 4-Tab Layout (Clean, High-Contrast for Shopkeepers)
1. **Tab 1: Munim Mic & Live Khata (Operations)**
   * Giant pulsing **Sarvam Voice Button** + Language Toggle (`Hinglish` | `Marathi` | `Hindi`).
   * **Active Proposal Card** with `"Why am I seeing this?"` expandable evidence pill and `Approve (Haan)` / `Edit` buttons.
   * **Ambiguous UPI Review Drawer** (shows the ₹200 payment from "Suresh" waiting for 1-tap assignment).
2. **Tab 2: AI CFO (Margin, Bills & Paytm Settlement)**
   * **"Scan Distributor Bill" Card** displaying the parsed invoice table and the flashing red **`+7.58% PRICE CREEP ALERT`** badge on Fortune Oil.
   * **"Mera Paisa Kam Kyun Aaya?" Card** showing the waterfall math from ₹6,450 Gross QR Sales $\rightarrow$ ₹5,815 Net Bank Credit with a **"Listen in Hindi/Marathi"** speaker button.
3. **Tab 3: AI CMO (Recovery, Campaigns & Diwali Ritual)**
   * **"Boli-Baki" Recovery Queue:** Shows Ramesh Sharma (₹650 overdue 18 days) with a playable Marathi audio wave, the `paytm.me/munim-ramesh-650` chip, and a **"⚡ Simulate Customer Paid"** button that triggers a live Paytm Soundbox chime (`"Paytm par 650 rupaye prapt hue"`).
   * **Dead-Stock Break-Even Studio:** Slider to test discount amounts with real-time break-even unit math and per-language attribution counters.
   * **60-Second Dukaan Closing Ritual Card:** Plays the Diwali $3.5\times$ Ghee surge warning and 1-tap supplier WhatsApp order.
4. **Tab 4: Unified Business Memory (Audit Log)**
   * Immutable chronological feed of every voice command, invoice scan, and webhook reconciliation with timestamps and provenance tags.

### 8.2 The Secret Weapon: "⚡ Judge Demo Quick-Trigger Bar"
In a loud hackathon venue, live microphones can pick up crowd noise. Add a sleek, collapsible footer bar with 6 instant-trigger chips that feed real audio/payloads through the exact same backend pipeline:
* `[🎤 "Suresh ka ₹200 udhaar likho" (Disambiguation Demo)]`
* `[🧾 Scan Supplier Bill (+7.58% Oil Price Creep)]`
* `[🏦 "Mera Paisa Kam Kyun Aaya?" (Settlement + Loan EDI)]`
* `[💸 Fire Ambiguous ₹200 Paytm QR Webhook]`
* `[📢 Send Marathi Voice Udhaar Link -> Simulate Paid]`
* `[🪔 Run 60s Diwali EOD Closing Ritual]`

---

## 9. Pre-Seeded Mumbai Kirana Dataset (`seed_demo_data.py`)

Automatically seed **"Ganesh Provision & General Store (Dadar, Mumbai)"** on backend startup:

1. **Customers:**
   * `Ramesh Sharma` (`mr-IN`, owes ₹650 for 18 days — triggers **Boli-Baki Voice Recovery**).
   * `Suresh Patil (Tailor)` (`mr-IN`, owes ₹200 for 5 days) & `Suresh Kadam (Kirana)` (`mr-IN`, owes ₹450 for 9 days) — triggers **Identity Disambiguation** and **Ambiguous UPI Queue**.
   * `Priya Deshmukh` (`mr-IN`, visits every 3 days, absent for 16 days — triggers **Churn Win-back**).
2. **Inventory Items:**
   * `Amul Pure Ghee 1L` (Stock: $4\text{ tins}$, Burn: $2/\text{day}$, Festive Multiplier: $3.5\times \rightarrow$ triggers **Diwali EOD Restock Alert**).
   * `Fortune Sunlite Oil 1L` (Old Cost: ₹132, Scanned Bill Cost: ₹142, MRP: ₹155 $\rightarrow$ triggers **$+7.58\%$ Price Creep Alert**).
   * `Haldiram Aloo Bhujia 400g` (Stock: $28\text{ pkts}$, Unsold: $22\text{ days}$, Cost: ₹72, Price: ₹95 $\rightarrow$ triggers **Dead-Stock Break-Even Studio**).

---

## 10. Team Division & Execution Checklist

| Teammate | Primary Ownership | Key Deliverables |
| :--- | :--- | :--- |
| **Parth** | **Sarvam AI Stack + Guardrails** | `sarvam_engine.py` (`Saaras` keyterm biasing, `Bulbul` TTS audio synthesis, `Vision` invoice parser, `Translate`), LLM structured output schemas, and offline fallback JSONs. |
| **Priyanshu** | **KiranaOS Deterministic Core** | SQLite append-only tables, `deterministic_engine.py` (price-creep math, settlement waterfall, break-even calculator, Diwali surge formula, UPI matching queue), and `seed_demo_data.py`. |
| **Rachit** | **UI/UX + Live Demo Flow** | 4-Tab interface, Proposal Confirmation Cards with `"Why am I seeing this?"` pills, audio playback components, and the **Judge Demo Quick-Trigger Bar**. |

---

## 11. The Winning 3-Minute Pitch & Live Demo Script

* **0:00 – 0:30 (The Hook):**  
  *"Small kiranas run on 6% net margins. They don't fail because they lack charts; they fail because profits leak through silent supplier price hikes, uncollected udhaar, settlement confusion, and festive stockouts. Meet Munim-AI—not a passive bookkeeper, but a deterministic AI CFO and AI CMO powered by Sarvam AI and Paytm."*
* **0:30 – 1:15 (Act 1 — Safe Memory & AI CFO in Action):**  
  * Tap Mic: *"Suresh ka ₹200 udhaar likho."* Show KiranaOS catching the two Sureshes (`Tailor` vs `Kirana`) instead of guessing.
  * Tap **"Scan Distributor Bill"**: Show `Sarvam Vision` extracting 3 items while the deterministic CFO engine flashes red: *"Gupta Wholesalers quietly hiked Fortune Oil by +7.58%!"* Confirm to update both Stock and Supplier Khata in one tap.
  * Tap **"Mera Paisa Kam Kyun Aaya?"**: Play the `Bulbul TTS` voice explaining how ₹6,450 QR sales became ₹5,815 in the bank after Paytm Loan EDI and Soundbox rent.
* **1:15 – 2:15 (Act 2 — AI CMO Closed-Loop Growth):**  
  * Trigger **Boli-Baki Recovery** for Ramesh Sharma (₹650 overdue). Play the polite Marathi `Bulbul` voice note and click **"Simulate Customer Paid Paytm Link"**—watch the Soundbox announce ₹650 received and the ledger auto-settle to ₹0!
  * Show the **Dead-Stock Break-Even Calculator** on 28 unsold packs of Haldiram Bhujia with per-language Paytm link attribution.
* **2:15 – 3:00 (Act 3 — The 60-Second Dukaan Closing Ritual & Close):**  
  * Trigger **EOD Ritual**: Munim-AI speaks first, warning that Diwali is 5 days away, Amul Ghee demand surges $3.5\times$, and only 4 tins remain—drafting a 31-tin order for Gupta Wholesalers.
  * Close: *"Zero LLM math hallucinations. 100% auditable ledger. Full-stack Sarvam voice & vision. Real Paytm attribution and retention."*