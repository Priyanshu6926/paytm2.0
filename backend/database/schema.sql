-- ==============================================================================
-- KiranaOS Authoritative SQLite Database Schema
-- Conforms to PRD §6 & Architectural Laws (Zero LLM Math & Append-Only Immutability)
-- ==============================================================================

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

-- ==============================================================================
-- Query Performance Indices
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_ledger_customer_id ON ledger_entries(customer_id);
CREATE INDEX IF NOT EXISTS idx_stock_events_item_id ON stock_events(item_id);
CREATE INDEX IF NOT EXISTS idx_unmatched_payments_status ON unmatched_payments_queue(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_target_customer ON campaigns_and_links(target_customer_id);
CREATE INDEX IF NOT EXISTS idx_business_events_category ON business_events(event_category);

-- ==============================================================================
-- Append-Only Immutability Triggers (PRD Law of Append-Only Immutability)
-- Strictly aborts any UPDATE or DELETE on financial, stock, and business event tables
-- ==============================================================================

-- 1. ledger_entries triggers
CREATE TRIGGER IF NOT EXISTS trg_ledger_entries_prevent_update
BEFORE UPDATE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_ledger_entries_prevent_delete
BEFORE DELETE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;

-- 2. stock_events triggers
CREATE TRIGGER IF NOT EXISTS trg_stock_events_prevent_update
BEFORE UPDATE ON stock_events
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_events_prevent_delete
BEFORE DELETE ON stock_events
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;

-- 3. business_events triggers
CREATE TRIGGER IF NOT EXISTS trg_business_events_prevent_update
BEFORE UPDATE ON business_events
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_business_events_prevent_delete
BEFORE DELETE ON business_events
BEGIN
    SELECT RAISE(ABORT, 'KiranaOS Law: Table is append-only. UPDATE/DELETE prohibited.');
END;
