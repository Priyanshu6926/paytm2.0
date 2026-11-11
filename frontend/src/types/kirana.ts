export type LanguageCode = 'hi-IN' | 'mr-IN' | 'en-IN';

export type DialectLabel = 'Hinglish' | 'Marathi' | 'Hindi';

export type PaytmTab = 'mic' | 'cfo' | 'cmo' | 'memory';

export type EventCategory =
  | 'LEDGER'
  | 'INVENTORY'
  | 'CFO_ALERT'
  | 'CMO_GROWTH'
  | 'SETTLEMENT'
  | 'SYSTEM_STARTUP';

export interface MemoryHealthResponse {
  status: string;
  store_name: string;
  database: string;
  tables: Record<string, number>;
  all_tables_populated: boolean;
}

export interface CustomerBalance {
  customer_id: number;
  total_credit: number;
  total_repayment: number;
  total_adjustment: number;
  net_outstanding_balance: number;
}

export interface CustomerSummary {
  id: number;
  name: string;
  aliases: string[];
  phone: string | null;
  preferred_language: LanguageCode | string;
  regular_cycle_days: number | null;
  last_visit_date: string | null;
  last_visit: string;
  outstanding_balance: number;
  total_credit: number;
  total_repayment: number;
  total_adjustment: number;
  days_overdue: number;
}

export interface CustomerCandidate {
  customer_id: number;
  name: string;
  phone: string | null;
  current_udhaar: number;
  last_visit: string;
}

export interface CustomerResolveResponse {
  status: 'EXACT_MATCH' | 'NEEDS_DISAMBIGUATION' | 'NOT_FOUND';
  query_name?: string;
  customer?: {
    id: number;
    name: string;
    phone: string | null;
    preferred_language: string;
    aliases: string[];
    regular_cycle_days: number | null;
    last_visit_date: string | null;
  };
  current_udhaar?: number;
  last_visit_date?: string | null;
  ambiguity_reason?: string;
  candidates?: CustomerCandidate[];
  why_am_i_seeing_this?: string;
  spoken_prompt_hi?: string;
}

export interface LedgerEntry {
  id: number;
  entry_type: 'CREDIT_UDHAAR' | 'REPAYMENT_JAMA' | 'REVERSAL_ADJUSTMENT' | string;
  amount: number;
  payment_mode: string | null;
  provider_ref: string | null;
  source_utterance: string | null;
  confidence_score: number;
  status: string;
  created_at: string;
}

export interface CustomerLedgerResponse {
  customer: {
    id: number;
    name: string;
    phone: string | null;
    preferred_language: string;
    regular_cycle_days: number | null;
    last_visit_date: string | null;
    last_visit: string;
    outstanding_balance: number;
  };
  balance: CustomerBalance;
  total_credit: number;
  total_repayment: number;
  total_adjustment: number;
  net_outstanding_balance: number;
  count: number;
  ledger_entries: LedgerEntry[];
}

export interface InventoryItem {
  id: number;
  sku_name: string;
  local_aliases: string[];
  category: string | null;
  current_stock: number;
  unit: string;
  last_unit_cost: number;
  previous_unit_cost: number;
  selling_price: number;
  avg_daily_burn: number;
  festive_multiplier: number;
  reorder_threshold: number;
  supplier_name: string | null;
  supplier_phone: string | null;
  last_restocked_at: string | null;
  last_sold_at: string | null;
}

export interface BusinessEvent {
  id: number;
  event_category: EventCategory | string;
  summary_text: string;
  evidence: Record<string, unknown>;
  evidence_json: string | null;
  actor: string;
  created_at: string;
}

// --------------------------------------------------------------------------
// Voice Gateway (/api/v1/voice/*)
// --------------------------------------------------------------------------

export interface VoiceHealthResponse {
  status: string;
  gateway: string;
  database: string;
  sarvam_api_key_configured: boolean;
  sarvam_fallback_mode: boolean;
  service: string;
  supported_languages: LanguageCode[];
}

export type VoiceIntentType =
  | 'CREDIT_UDHAAR'
  | 'REPAYMENT_JAMA'
  | 'STOCK_IN'
  | 'STOCKOUT_FLAG'
  | 'QUERY';

export interface VoiceProposeResponse {
  status: 'PROPOSAL' | 'NEEDS_DISAMBIGUATION' | 'CUSTOMER_NOT_FOUND' | 'NOT_UNDERSTOOD';
  proposal_id?: string;
  intent: VoiceIntentType;
  customer?: {
    id: number;
    name: string;
    phone: string | null;
    preferred_language: string;
    aliases: string[];
    regular_cycle_days: number | null;
    last_visit_date: string | null;
  };
  customer_id?: number;
  customer_name?: string;
  extracted_amount?: number | null;
  extracted_name?: string;
  current_balance?: number;
  new_balance?: number;
  item_id?: number;
  sku_name?: string;
  quantity_delta?: number;
  current_stock?: number;
  new_stock?: number;
  ambiguity_reason?: string;
  candidates?: CustomerCandidate[];
  why_am_i_seeing_this: string;
  spoken_prompt_hi: string;
  raw_transcript: string;
  tts_audio_base64: string;
}

export interface ProposalConfirmRequest {
  proposal_id?: string;
  action: 'APPROVE' | 'CANCEL';
  intent: VoiceIntentType | string;
  customer_id?: number;
  amount?: number;
  payment_mode?: string;
  item_id?: number;
  quantity_delta?: number;
  source_utterance?: string;
  language_hint?: LanguageCode | string;
}

export interface ProposalConfirmResponse {
  status: 'CONFIRMED';
  proposal_id: string | null;
  intent: string;
  ledger_entry_id?: number;
  customer_id?: number;
  customer_name?: string;
  amount?: number;
  new_balance?: number;
  stock_event_id?: number;
  item_id?: number;
  sku_name?: string;
  new_stock?: number;
  business_event_id: number;
  spoken_confirmation: string;
  tts_audio_base64: string;
}

export interface TextToSpeechRequest {
  text: string;
  target_language_code?: LanguageCode | string;
  speaker?: string;
}

export interface TextToSpeechResponse {
  audio_base64: string;
  language_code: string;
  fallback_used: boolean;
  error_detail: string | null;
}

// --------------------------------------------------------------------------
// AI CFO (/api/v1/cfo/*)
// --------------------------------------------------------------------------

export interface SettlementDeduction {
  type: string;
  label: string;
  amount: number;
}

export interface SettlementExplainerResponse {
  settlement_date: string;
  bank_account: string;
  gross_qr_collections: number;
  deductions: SettlementDeduction[];
  total_deductions: number;
  net_settled_to_bank: number;
  verification_status: string;
  spoken_explanation_hi: string;
  tts_audio_base64: string;
}

export interface BillLineItem {
  item_id: number | null;
  sku_name: string;
  qty: number;
  unit?: string;
  unit_cost: number;
  line_total: number;
}

export interface PriceCreepAlert {
  sku_name: string;
  previous_unit_cost: number;
  new_unit_cost: number;
  creep_percentage: number;
  margin_erosion_per_unit: number;
  recommended_new_mrp: number;
  alert_hi: string;
}

export interface ScanBillResponse {
  status: 'PROPOSAL';
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  invoice_total: number;
  price_creep_alerts: PriceCreepAlert[];
  line_items: BillLineItem[];
  dual_action_preview: string;
  tts_audio_base64: string;
  fallback_used: boolean;
}

export interface ConfirmBillRequest {
  invoice_number: string;
  supplier_name: string;
  line_items: BillLineItem[];
  invoice_total: number;
  price_creep_detected: boolean;
  update_selling_prices?: Record<string, number>;
}

export interface ConfirmBillResponse {
  status: 'CONFIRMED' | 'ALREADY_CONFIRMED';
  invoice_number: string;
  stock_events_created?: number;
  supplier_ledger_id: number;
  business_event_id?: number;
  message: string;
}

export interface UnmatchedPayment {
  id: number;
  upi_txn_id: string;
  amount: number;
  payer_name: string;
  payer_vpa: string | null;
  candidate_customers: CustomerCandidate[];
  ambiguity_reason: string;
  status: string;
  resolved_customer_id: number | null;
  created_at: string;
}

export interface ResolvePaymentRequest {
  queue_id: number;
  resolved_customer_id: number;
  merchant_notes?: string;
}

export interface ResolvePaymentResponse {
  status: 'LINKED';
  queue_id: number;
  resolved_customer_id: number;
  customer_name: string;
  amount: number;
  customer_balance_after: number;
  business_event_id: number;
}

export interface QRWebhookPayload {
  upi_txn_id: string;
  amount: number;
  payer_name: string;
  payer_vpa?: string;
}

export interface QRWebhookResponse {
  status:
    | 'AUTO_RECONCILED'
    | 'QUEUED_FOR_REVIEW'
    | 'ALREADY_PROCESSED'
    | 'ALREADY_QUEUED';
  upi_txn_id?: string;
  message?: string;
  customer_id?: number;
  customer_name?: string;
  amount?: number;
  balance_after?: number;
  business_event_id?: number;
  queue_id?: number;
  ambiguity_reason?: string;
  candidate_count?: number;
}

// --------------------------------------------------------------------------
// AI CMO (/api/v1/cmo/*)
// --------------------------------------------------------------------------

export interface ActiveUdhaarCampaign {
  id: number;
  campaign_title: string;
  language_code: string;
  paytm_link_slug: string;
  paytm_payment_link: string;
  link_slug: string;
  amount_expected: number;
  status: string;
  clicks: number;
  conversions: number;
  revenue_collected: number;
  simulate_webhook_endpoint: string;
}

export interface OverdueDebtor {
  customer_id: number;
  customer_name: string;
  phone: string | null;
  preferred_language: LanguageCode | string;
  overdue_days: number;
  outstanding_amount: number;
  last_visit_date: string | null;
  active_campaign: ActiveUdhaarCampaign | null;
}

export interface OverdueDebtorsResponse {
  overdue_debtors: OverdueDebtor[];
  count: number;
}

export interface BoliBakiRequest {
  customer_id: number;
  target_language?: LanguageCode | string;
}

export interface BoliBakiRecoveryResponse {
  customer_id: number;
  customer_name: string;
  preferred_language: string;
  overdue_days: number;
  outstanding_amount: number;
  paytm_payment_link: string;
  link_slug: string;
  translated_message: string;
  tts_audio_base64: string;
  fallback_used: boolean;
  simulate_webhook_endpoint: string;
}

export interface SimulateLinkPaidResponse {
  status: 'PAID' | 'ALREADY_PAID';
  slug: string;
  message?: string;
  customer_id?: number;
  customer_name?: string;
  amount_paid?: number;
  balance_after?: number;
  soundbox_announcement?: string;
  soundbox_audio_base64?: string;
  business_event_id?: number;
}

export interface AttributedLink {
  language: string;
  link: string;
  slug: string;
  clicks: number;
  redemptions: number;
  conversions: number;
  revenue: number;
  revenue_collected: number;
  message_text: string;
  simulate_click_endpoint: string;
}

export interface DeadStockItem {
  item_id: number;
  sku_name: string;
  category: string | null;
  current_stock: number;
  unit: string;
  unit_cost: number;
  selling_price: number;
  current_margin_per_unit: number;
  days_unsold: number;
  last_sold_at: string | null;
  supplier_name: string | null;
  attributed_links: AttributedLink[];
}

export interface DeadStockResponse {
  dead_stock_items: DeadStockItem[];
  count: number;
}

export interface DeadStockCampaignRequest {
  item_id: number;
  proposed_discount_rupees: number;
  usual_daily_sales?: number;
}

export interface DeadStockMathAudit {
  old_margin_per_unit: number;
  new_margin_per_unit: number;
  usual_daily_sales: number;
  breakeven_daily_sales_needed: number | null;
  extra_units_needed_per_day: number | null;
  verdict: string;
}

export interface DeadStockCampaignResponse {
  status: 'CAMPAIGN_READY' | 'OFFER_BLOCKED_LOSS_MAKING';
  allowed: boolean;
  item_id: number;
  sku_name: string;
  days_unsold: number;
  current_stock: number;
  unit_cost: number;
  selling_price: number;
  proposed_discount: number;
  discounted_price?: number;
  reason?: string;
  math_audit: DeadStockMathAudit;
  attributed_links: AttributedLink[];
}

export interface SimulatePromoClickResponse {
  status: 'RECORDED';
  slug: string;
  link: string;
  language: string;
  converted: boolean;
  clicks: number;
  conversions: number;
  redemptions: number;
  revenue_collected: number;
  business_event_id: number;
  language_breakdown: AttributedLink[];
}

export interface FestiveRestockForecast {
  upcoming_event: string;
  days_away: number;
  sku_name: string;
  unit: string;
  current_stock: number;
  normal_daily_burn: number;
  festive_surge_multiplier: number;
  projected_5day_demand: number;
  recommended_order_qty: number;
  supplier_name: string;
  one_tap_order_draft: string;
}

export interface DukaanClosingRitualResponse {
  today_qr_sales: number;
  today_udhaar_recovered: number;
  unmatched_upi_count: number;
  festive_restock_forecast: FestiveRestockForecast;
  spoken_ritual_hi: string;
  tts_audio_base64: string;
  fallback_used: boolean;
  why_am_i_seeing_this: {
    source: string;
    qr_baseline_amount: number;
    live_qr_repayments_today: number;
    today_udhaar_recovered: number;
    unmatched_upi_pending: number;
    forecast_item_id: number;
    formula: string;
  };
}

export interface BahiKhataCandidate {
  customer_id: number;
  name: string;
  phone: string | null;
  existing_balance: number;
}

export interface BahiKhataProposalRow {
  row_index: number;
  customer_name: string;
  phone: string;
  preferred_language: string;
  amount: number;
  notes: string;
  confidence: number;
  match_status: 'EXISTING_CUSTOMER' | 'NEW_CUSTOMER' | 'AMBIGUOUS';
  matched_customer_id: number | null;
  matched_customer_name: string | null;
  existing_balance: number | null;
  candidate_customers: BahiKhataCandidate[];
}

export interface ScanBahiKhataResponse {
  status: 'PROPOSAL';
  page_title: string;
  detected_language: string;
  proposal_count: number;
  total_proposed_amount: number;
  proposals: BahiKhataProposalRow[];
  fallback_used: boolean;
}

export interface BahiKhataConfirmEntry {
  customer_id?: number | null;
  customer_name: string;
  phone?: string;
  preferred_language: string;
  amount: number;
  notes?: string;
}

export interface ConfirmBahiKhataRequest {
  batch_ref?: string;
  entries: BahiKhataConfirmEntry[];
}

export interface ConfirmBahiKhataCustomerResult {
  row_index: number;
  customer_id: number;
  customer_name: string;
  created_new_customer: boolean;
  amount_credited: number;
  ledger_entry_id: number;
  provider_ref: string;
  balance_after: number;
}

export interface ConfirmBahiKhataResponse {
  status: 'CONFIRMED' | 'ALREADY_CONFIRMED';
  batch_ref: string;
  message?: string;
  entries_recorded?: number;
  new_customers_created?: number;
  total_onboarded_amount?: number;
  customer_results?: ConfirmBahiKhataCustomerResult[];
  business_event_id?: number;
}
