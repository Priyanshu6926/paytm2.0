import { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { kiranaClient } from '../../api/kiranaClient';
import App from '../../App';
import type {
  BoliBakiRecoveryResponse,
  BusinessEvent,
  CustomerSummary,
  DeadStockCampaignResponse,
  DeadStockResponse,
  DukaanClosingRitualResponse,
  MemoryHealthResponse,
  OverdueDebtorsResponse,
  ScanBahiKhataResponse,
  ScanBillResponse,
  SettlementExplainerResponse,
  UnmatchedPayment,
  VoiceProposeResponse,
} from '../../types/kirana';
import { playSoundboxAudio } from '../../utils/soundboxAudio';
import { AiCmoTab } from '../tabs/AiCmoTab';
import { MemoryTimelineTab } from '../tabs/MemoryTimelineTab';

vi.mock('../../api/kiranaClient', () => ({
  kiranaClient: {
    getMemoryHealth: vi.fn(),
    listCustomers: vi.fn(),
    getCustomerLedger: vi.fn(),
    listBusinessEvents: vi.fn(),
    proposeVoiceCommand: vi.fn(),
    confirmVoiceProposal: vi.fn(),
    scanDistributorBill: vi.fn(),
    confirmDistributorBill: vi.fn(),
    getSettlementExplainer: vi.fn(),
    getUnmatchedPayments: vi.fn(),
    resolveUnmatchedPayment: vi.fn(),
    simulateQrWebhook: vi.fn(),
    getOverdueDebtors: vi.fn(),
    createBoliBakiRecovery: vi.fn(),
    simulateLinkPaid: vi.fn(),
    getDeadStock: vi.fn(),
    createDeadStockCampaign: vi.fn(),
    simulatePromoClick: vi.fn(),
    getDukaanClosingRitual: vi.fn(),
    scanBahiKhata: vi.fn(),
    confirmBahiKhata: vi.fn(),
  },
}));

vi.mock('../../utils/soundboxAudio', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../utils/soundboxAudio')>();
  return {
    ...actual,
    playSoundboxAudio: vi.fn().mockResolvedValue({ mode: 'wav' }),
  };
});

const mockedClient = vi.mocked(kiranaClient);
const mockedSoundbox = vi.mocked(playSoundboxAudio);

const SAMPLE_HEALTH: MemoryHealthResponse = {
  status: 'healthy',
  store_name: 'Ganesh Provision & General Store',
  database: 'connected',
  tables: {
    customers: 6,
    ledger_entries: 12,
    inventory_items: 8,
    stock_events: 10,
    supplier_ledger: 3,
    unmatched_payments_queue: 1,
    campaigns_and_links: 4,
    business_events: 15,
  },
  all_tables_populated: true,
};

const SAMPLE_OVERDUE: OverdueDebtorsResponse = {
  overdue_debtors: [
    {
      customer_id: 3,
      customer_name: 'Ramesh Sharma',
      phone: '9820555666',
      preferred_language: 'mr-IN',
      overdue_days: 18,
      outstanding_amount: 650,
      last_visit_date: '2026-10-22',
      active_campaign: {
        id: 1,
        campaign_title: 'Ramesh Sharma Udhaar Recovery',
        language_code: 'mr-IN',
        paytm_link_slug: 'paytm.me/munim-ramesh-650',
        paytm_payment_link: 'https://paytm.me/munim-ramesh-650',
        link_slug: 'munim-ramesh-650',
        amount_expected: 650,
        status: 'SENT',
        clicks: 0,
        conversions: 0,
        revenue_collected: 0,
        simulate_webhook_endpoint: '/api/v1/cmo/simulate-link-paid/munim-ramesh-650',
      },
    },
  ],
  count: 1,
};

const SAMPLE_RECOVERY: BoliBakiRecoveryResponse = {
  customer_id: 3,
  customer_name: 'Ramesh Sharma',
  preferred_language: 'mr-IN',
  overdue_days: 18,
  outstanding_amount: 650,
  paytm_payment_link: 'https://paytm.me/munim-ramesh-650',
  link_slug: 'munim-ramesh-650',
  translated_message:
    'Namaskar Ramesh ji, tumche kirana dukanache 650 rupaye udhari baki aahe. Krupaya dilelya Paytm link varun paise bhara.',
  tts_audio_base64: 'UklGRg==',
  fallback_used: true,
  simulate_webhook_endpoint: '/api/v1/cmo/simulate-link-paid/munim-ramesh-650',
};

const SAMPLE_DEAD_STOCK: DeadStockResponse = {
  dead_stock_items: [
    {
      item_id: 4,
      sku_name: 'Haldiram Aloo Bhujia 400g',
      category: 'Snacks',
      current_stock: 28,
      unit: 'packs',
      unit_cost: 72,
      selling_price: 95,
      current_margin_per_unit: 23,
      days_unsold: 22,
      last_sold_at: '2026-10-20',
      supplier_name: 'Haldiram Distributors',
      attributed_links: [],
    },
  ],
  count: 1,
};

const SAFE_CAMPAIGN: DeadStockCampaignResponse = {
  status: 'CAMPAIGN_READY',
  allowed: true,
  item_id: 4,
  sku_name: 'Haldiram Aloo Bhujia 400g',
  days_unsold: 22,
  current_stock: 28,
  unit_cost: 72,
  selling_price: 95,
  proposed_discount: 10,
  discounted_price: 85,
  math_audit: {
    old_margin_per_unit: 23,
    new_margin_per_unit: 13,
    usual_daily_sales: 4,
    breakeven_daily_sales_needed: 8,
    extra_units_needed_per_day: 4,
    verdict: 'PROFITABLE_AT_TARGET_VOLUME',
  },
  attributed_links: [
    {
      language: 'mr-IN',
      link: 'paytm.me/promo-mr-bhujia',
      slug: 'promo-mr-bhujia',
      clicks: 2,
      redemptions: 1,
      conversions: 1,
      revenue: 85,
      revenue_collected: 85,
      message_text: 'Khas offer! Haldiram Aloo Bhujia 400g aata fakt Rs 85 madhe.',
      simulate_click_endpoint: '/api/v1/cmo/simulate-promo-click/promo-mr-bhujia',
    },
    {
      language: 'hi-IN',
      link: 'paytm.me/promo-hi-bhujia',
      slug: 'promo-hi-bhujia',
      clicks: 1,
      redemptions: 0,
      conversions: 0,
      revenue: 0,
      revenue_collected: 0,
      message_text: 'Special offer! Haldiram Aloo Bhujia 400g ab sirf Rs 85 mein.',
      simulate_click_endpoint: '/api/v1/cmo/simulate-promo-click/promo-hi-bhujia',
    },
  ],
};

const BLOCKED_CAMPAIGN: DeadStockCampaignResponse = {
  status: 'OFFER_BLOCKED_LOSS_MAKING',
  allowed: false,
  item_id: 4,
  sku_name: 'Haldiram Aloo Bhujia 400g',
  days_unsold: 22,
  current_stock: 28,
  unit_cost: 72,
  selling_price: 95,
  proposed_discount: 25,
  reason: 'HARD STOP: Discount Rs 25 drops selling price below wholesale cost Rs 72.',
  math_audit: {
    old_margin_per_unit: 23,
    new_margin_per_unit: -2,
    usual_daily_sales: 4,
    breakeven_daily_sales_needed: null,
    extra_units_needed_per_day: null,
    verdict: 'LOSS_MAKING_BLOCKED',
  },
  attributed_links: [],
};

const SAMPLE_RITUAL: DukaanClosingRitualResponse = {
  today_qr_sales: 6450,
  today_udhaar_recovered: 650,
  unmatched_upi_count: 1,
  festive_restock_forecast: {
    upcoming_event: 'Diwali Peak Week',
    days_away: 4,
    sku_name: 'Amul Pure Ghee 1L',
    unit: 'tins',
    current_stock: 4,
    normal_daily_burn: 2,
    festive_surge_multiplier: 3.5,
    projected_5day_demand: 35,
    recommended_order_qty: 31,
    supplier_name: 'Gupta Wholesalers',
    one_tap_order_draft: 'Namaste Gupta Wholesalers ji, please send 31 tins Amul Pure Ghee 1L before Diwali.',
  },
  spoken_ritual_hi:
    'Aaj 6,450 rupaye ki QR bikri aur 650 rupaye udhaar wapas aaya. Diwali ke liye Amul Pure Ghee 1L ke 31 tin order karein.',
  tts_audio_base64: 'UklGRg==',
  fallback_used: true,
  why_am_i_seeing_this: {
    source: 'Deterministic SQLite Aggregation & Diwali Surge Engine',
    qr_baseline_amount: 6450,
    live_qr_repayments_today: 0,
    today_udhaar_recovered: 650,
    unmatched_upi_pending: 1,
    forecast_item_id: 3,
    formula: 'ceil(daily_burn_rate * festive_multiplier * 5) - current_stock',
  },
};

const SAMPLE_BAHI_KHATA: ScanBahiKhataResponse = {
  status: 'PROPOSAL',
  page_title: 'Bahi-Khata Page #14 (Marathi/Hindi)',
  detected_language: 'hi-IN',
  proposal_count: 2,
  total_proposed_amount: 950,
  fallback_used: true,
  proposals: [
    {
      row_index: 1,
      customer_name: 'Kiran Verma',
      phone: '9820777888',
      preferred_language: 'hi-IN',
      amount: 450,
      notes: 'Atta + Dal',
      confidence: 0.94,
      match_status: 'NEW_CUSTOMER',
      matched_customer_id: null,
      matched_customer_name: null,
      existing_balance: null,
      candidate_customers: [],
    },
    {
      row_index: 2,
      customer_name: 'Suresh',
      phone: '',
      preferred_language: 'mr-IN',
      amount: 500,
      notes: 'Diwali oil',
      confidence: 0.89,
      match_status: 'AMBIGUOUS',
      matched_customer_id: null,
      matched_customer_name: null,
      existing_balance: null,
      candidate_customers: [
        {
          customer_id: 1,
          name: 'Suresh Patil (Tailor)',
          phone: '9820111222',
          existing_balance: 450,
        },
        {
          customer_id: 2,
          name: 'Suresh Kadam (Kirana)',
          phone: '9820333444',
          existing_balance: 300,
        },
      ],
    },
  ],
};

const SAMPLE_EVENTS: BusinessEvent[] = [
  {
    id: 10,
    event_category: 'CFO_ALERT',
    summary_text: 'Flagged +7.58% wholesale price creep on Fortune Sunlite Oil 1L',
    evidence: { previous_cost: 132, new_cost: 142, creep_percentage: 7.58 },
    evidence_json: '{"previous_cost":132,"new_cost":142,"creep_percentage":7.58}',
    actor: 'SYSTEM_GUARD',
    created_at: '2026-11-11 10:00:00',
  },
  {
    id: 9,
    event_category: 'CMO_GROWTH',
    summary_text: 'Boli-Baki link paid by Ramesh Sharma: Rs 650 recovered',
    evidence: { customer_id: 3, amount_paid: 650, balance_after: 0 },
    evidence_json: '{"customer_id":3,"amount_paid":650,"balance_after":0}',
    actor: 'SYSTEM_AUTO',
    created_at: '2026-11-11 09:45:00',
  },
  {
    id: 8,
    event_category: 'LEDGER',
    summary_text: 'Approved Rs 200 credit for Suresh Patil (Tailor)',
    evidence: { customer_id: 1, amount: 200, balance_after: 650 },
    evidence_json: '{"customer_id":1,"amount":200,"balance_after":650}',
    actor: 'MERCHANT_APPROVED',
    created_at: '2026-11-11 09:30:00',
  },
];

const SAMPLE_CUSTOMERS: CustomerSummary[] = [
  {
    id: 1,
    name: 'Suresh Patil (Tailor)',
    aliases: ['Suresh'],
    phone: '9820111222',
    preferred_language: 'mr-IN',
    regular_cycle_days: 7,
    last_visit_date: '2026-11-08',
    last_visit: '3 days ago',
    outstanding_balance: 450,
    total_credit: 650,
    total_repayment: 200,
    total_adjustment: 0,
    days_overdue: 0,
  },
];

const SAMPLE_UNMATCHED: UnmatchedPayment[] = [
  {
    id: 7,
    upi_txn_id: 'UPI-SEED-200',
    amount: 200,
    payer_name: 'Suresh',
    payer_vpa: 'suresh@paytm',
    candidate_customers: [
      {
        customer_id: 1,
        name: 'Suresh Patil (Tailor)',
        phone: '9820111222',
        current_udhaar: 450,
        last_visit: '3 days ago',
      },
    ],
    ambiguity_reason: '2 customers match Suresh.',
    status: 'PENDING_REVIEW',
    resolved_customer_id: null,
    created_at: '2026-11-11 11:00:00',
  },
];

const SAMPLE_VOICE_DISAMBIG: VoiceProposeResponse = {
  status: 'NEEDS_DISAMBIGUATION',
  intent: 'CREDIT_UDHAAR',
  extracted_name: 'Suresh',
  extracted_amount: 200,
  ambiguity_reason: '2 customers match "Suresh".',
  candidates: [
    {
      customer_id: 1,
      name: 'Suresh Patil (Tailor)',
      phone: '9820111222',
      current_udhaar: 450,
      last_visit: '3 days ago',
    },
    {
      customer_id: 2,
      name: 'Suresh Kadam (Kirana)',
      phone: '9820333444',
      current_udhaar: 300,
      last_visit: '7 days ago',
    },
  ],
  why_am_i_seeing_this: 'Ambiguous name Suresh.',
  spoken_prompt_hi: 'Kaunse Suresh ka khata likhna hai?',
  raw_transcript: 'Suresh ka 200 rupaye udhaar likh do',
  tts_audio_base64: 'UklGRg==',
};

const SAMPLE_BILL: ScanBillResponse = {
  status: 'PROPOSAL',
  supplier_name: 'Gupta Wholesalers',
  invoice_number: 'GW-2026-8841',
  invoice_date: '2026-11-11',
  invoice_total: 4220,
  price_creep_alerts: [
    {
      sku_name: 'Fortune Sunlite Oil 1L',
      previous_unit_cost: 132,
      new_unit_cost: 142,
      creep_percentage: 7.58,
      margin_erosion_per_unit: 10,
      recommended_new_mrp: 160,
      alert_hi: 'Tel ka bhav 7.58% badh gaya hai.',
    },
  ],
  line_items: [
    {
      item_id: 1,
      sku_name: 'Fortune Sunlite Oil 1L',
      qty: 20,
      unit: 'pouches',
      unit_cost: 142,
      line_total: 2840,
    },
  ],
  dual_action_preview: 'Updates inventory_items and supplier_ledger.',
  tts_audio_base64: 'UklGRg==',
  fallback_used: false,
};

const SAMPLE_SETTLEMENT: SettlementExplainerResponse = {
  settlement_date: '2026-11-09',
  bank_account: 'State Bank of India •••• 4921',
  gross_qr_collections: 6450,
  deductions: [
    { type: 'PAYTM_MERCHANT_LOAN_EDI', label: 'Loan EDI', amount: 450 },
    { type: 'SOUNDBOX_RENTAL', label: 'Soundbox', amount: 125 },
    { type: 'CUSTOMER_REFUND', label: 'Refund', amount: 60 },
  ],
  total_deductions: 635,
  net_settled_to_bank: 5815,
  verification_status: 'DETERMINISTICALLY_BALANCED',
  spoken_explanation_hi: 'Aaj 6,450 mein se 635 katkar 5,815 rupaye aaye hain.',
  tts_audio_base64: 'UklGRg==',
};

function CmoHarness({ onDataMutated = vi.fn() }: { onDataMutated?: () => void }) {
  const [recoveryPreview, setRecoveryPreview] = useState<BoliBakiRecoveryResponse | null>(null);
  const [closingRitual, setClosingRitual] = useState<DukaanClosingRitualResponse | null>(null);

  return (
    <AiCmoTab
      recoveryPreview={recoveryPreview}
      onRecoveryPreviewChange={setRecoveryPreview}
      closingRitual={closingRitual}
      onClosingRitualChange={setClosingRitual}
      refreshToken={0}
      onDataMutated={onDataMutated}
    />
  );
}

describe('Tab 3 (AiCmoTab), Tab 4 (MemoryTimelineTab), & App JudgeDemoBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.getMemoryHealth.mockResolvedValue(SAMPLE_HEALTH);
    mockedClient.listCustomers.mockResolvedValue(SAMPLE_CUSTOMERS);
    mockedClient.getUnmatchedPayments.mockResolvedValue(SAMPLE_UNMATCHED);
    mockedClient.getOverdueDebtors.mockResolvedValue(SAMPLE_OVERDUE);
    mockedClient.getDeadStock.mockResolvedValue(SAMPLE_DEAD_STOCK);
    mockedClient.getDukaanClosingRitual.mockResolvedValue(SAMPLE_RITUAL);
    mockedClient.getSettlementExplainer.mockResolvedValue(SAMPLE_SETTLEMENT);
    mockedClient.listBusinessEvents.mockResolvedValue(SAMPLE_EVENTS);
  });

  it('executes Boli-Baki voice recovery and triggers live Soundbox chime on Simulate Customer Paid', async () => {
    const onDataMutated = vi.fn();
    mockedClient.createBoliBakiRecovery.mockResolvedValue(SAMPLE_RECOVERY);
    mockedClient.simulateLinkPaid.mockResolvedValue({
      status: 'PAID',
      slug: 'munim-ramesh-650',
      customer_id: 3,
      customer_name: 'Ramesh Sharma',
      amount_paid: 650,
      balance_after: 0,
      soundbox_announcement: 'Paytm par 650 rupaye prapt hue',
      soundbox_audio_base64: 'UklGRg==',
      business_event_id: 44,
    });

    render(<CmoHarness onDataMutated={onDataMutated} />);

    await waitFor(() => {
      expect(screen.getByText('Ramesh Sharma')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Generate Voice Link/i }));

    await waitFor(() => {
      expect(mockedClient.createBoliBakiRecovery).toHaveBeenCalledWith({
        customer_id: 3,
        target_language: 'mr-IN',
      });
    });

    const preview = await screen.findByLabelText('Active Boli-Baki Voice Link Preview');
    expect(within(preview).getByText(/tumche kirana dukanache 650 rupaye/i)).toBeInTheDocument();
    expect(within(preview).getByText('https://paytm.me/munim-ramesh-650')).toBeInTheDocument();

    fireEvent.click(within(preview).getByRole('button', { name: /Simulate Customer Paid/i }));

    await waitFor(() => {
      expect(mockedClient.simulateLinkPaid).toHaveBeenCalledWith('munim-ramesh-650');
    });

    await waitFor(() => {
      expect(mockedSoundbox).toHaveBeenCalledWith(
        expect.objectContaining({
          audioBase64: 'UklGRg==',
          announcement: 'Paytm par 650 rupaye prapt hue',
          isPaymentChime: true,
        }),
      );
      expect(onDataMutated).toHaveBeenCalledTimes(1);
    });
  });

  it('evaluates safe ₹10 break-even math with mr-IN/hi-IN attribution and blocks ₹25 loss-making offer', async () => {
    const onDataMutated = vi.fn();
    mockedClient.createDeadStockCampaign
      .mockResolvedValueOnce(SAFE_CAMPAIGN)
      .mockResolvedValueOnce(BLOCKED_CAMPAIGN);
    mockedClient.simulatePromoClick.mockResolvedValue({
      status: 'RECORDED',
      slug: 'promo-mr-bhujia',
      link: 'paytm.me/promo-mr-bhujia',
      language: 'mr-IN',
      converted: true,
      clicks: 3,
      conversions: 2,
      redemptions: 2,
      revenue_collected: 170,
      business_event_id: 51,
      language_breakdown: [
        { ...SAFE_CAMPAIGN.attributed_links[0], clicks: 3, redemptions: 2, conversions: 2, revenue: 170, revenue_collected: 170 },
        SAFE_CAMPAIGN.attributed_links[1],
      ],
    });

    render(<CmoHarness onDataMutated={onDataMutated} />);

    await waitFor(() => {
      expect(screen.getByText('Haldiram Aloo Bhujia 400g')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '₹10 Safe' }));

    await waitFor(() => {
      expect(mockedClient.createDeadStockCampaign).toHaveBeenCalledWith({
        item_id: 4,
        proposed_discount_rupees: 10,
      });
    });

    expect(screen.getByText('8/day')).toBeInTheDocument();
    expect(screen.getByText('+4/day')).toBeInTheDocument();
    expect(screen.getByText('paytm.me/promo-mr-bhujia')).toBeInTheDocument();
    expect(screen.getByText('paytm.me/promo-hi-bhujia')).toBeInTheDocument();

    const simButtons = screen.getAllByRole('button', { name: /Simulate Click\/Buy/i });
    fireEvent.click(simButtons[0]);

    await waitFor(() => {
      expect(mockedClient.simulatePromoClick).toHaveBeenCalledWith('promo-mr-bhujia', true);
      expect(screen.getByText('Clicks: 3')).toBeInTheDocument();
      expect(onDataMutated).toHaveBeenCalledTimes(1);
    });

    const slider = screen.getByLabelText('Dead-stock discount in rupees');
    fireEvent.change(slider, { target: { value: '25' } });

    await waitFor(() => {
      expect(mockedClient.createDeadStockCampaign).toHaveBeenCalledWith({
        item_id: 4,
        proposed_discount_rupees: 25,
      });
    });

    const hardStop = await screen.findByLabelText('Loss-making offer blocked');
    expect(within(hardStop).getByText('OFFER_BLOCKED_LOSS_MAKING')).toBeInTheDocument();
    expect(screen.queryByText('paytm.me/promo-mr-bhujia')).not.toBeInTheDocument();
  });

  it('renders 60-Second Diwali Closing Ritual with 3.5x Ghee restock draft, audio briefing, and copy button', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<CmoHarness />);

    await waitFor(() => {
      expect(screen.getByText('Amul Pure Ghee 1L')).toBeInTheDocument();
    });

    expect(screen.getByText('₹6,450')).toBeInTheDocument();
    expect(screen.getByText('31 tins')).toBeInTheDocument();
    expect(screen.getByText(/3.5× Diwali Peak Week/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Play 60s Briefing/i }));
    expect(mockedSoundbox).toHaveBeenCalledWith(
      expect.objectContaining({
        announcement: SAMPLE_RITUAL.spoken_ritual_hi,
        sourceLabel: 'Diwali EOD Ritual',
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: /Copy Order Draft/i }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        SAMPLE_RITUAL.festive_restock_forecast.one_tap_order_draft,
      );
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('supports Bahi-Khata demo scan, custom notebook photo upload, inline editing, ambiguity resolution, and atomic confirm', async () => {
    const onDataMutated = vi.fn();
    mockedClient.scanBahiKhata.mockResolvedValue(SAMPLE_BAHI_KHATA);
    mockedClient.confirmBahiKhata.mockResolvedValue({
      status: 'CONFIRMED',
      batch_ref: 'BAHI-UI-1',
      entries_recorded: 2,
      new_customers_created: 1,
      total_onboarded_amount: 1000,
    });

    const origCreate = URL.createObjectURL;
    const origRevoke = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => 'blob:bahi-preview');
    URL.revokeObjectURL = vi.fn();

    try {
      render(<CmoHarness onDataMutated={onDataMutated} />);

      fireEvent.click(screen.getByRole('button', { name: /Scan Sample Notebook Page/i }));
      await waitFor(() => {
        expect(mockedClient.scanBahiKhata).toHaveBeenCalledWith({ useDemoSample: true });
      });

      const fileInput = screen.getByLabelText('Upload Custom Notebook Photo');
      const notebookFile = new File(['img-bytes'], 'my-bahi-page.jpg', { type: 'image/jpeg' });
      fireEvent.change(fileInput, { target: { files: [notebookFile] } });

      await waitFor(() => {
        expect(mockedClient.scanBahiKhata).toHaveBeenCalledWith({ file: notebookFile });
      });
      expect(screen.getByAltText('Preview of my-bahi-page.jpg')).toHaveAttribute(
        'src',
        'blob:bahi-preview',
      );

      // Edit first row amount from 450 -> 500 and resolve ambiguous Suresh row
      fireEvent.change(screen.getByLabelText('Amount row 1'), { target: { value: '500' } });
      fireEvent.change(screen.getByLabelText('Resolve candidate for row 2'), {
        target: { value: '1' },
      });

      fireEvent.click(screen.getByRole('button', { name: /Confirm & Onboard All \(2\)/i }));

      await waitFor(() => {
        expect(mockedClient.confirmBahiKhata).toHaveBeenCalledWith(
          expect.objectContaining({
            batch_ref: expect.stringMatching(/^BAHI-UI-\d+$/),
            entries: [
              expect.objectContaining({ customer_name: 'Kiran Verma', amount: 500 }),
              expect.objectContaining({ customer_id: 1, customer_name: 'Suresh', amount: 500 }),
            ],
          }),
        );
        expect(onDataMutated).toHaveBeenCalled();
      });
    } finally {
      URL.createObjectURL = origCreate;
      URL.revokeObjectURL = origRevoke;
    }
  });

  it('filters MemoryTimelineTab by event category and expands JSON evidence drawers', async () => {
    render(<MemoryTimelineTab refreshToken={0} />);

    await waitFor(() => {
      expect(mockedClient.listBusinessEvents).toHaveBeenCalledWith(undefined);
    });

    expect(
      screen.getByText('Flagged +7.58% wholesale price creep on Fortune Sunlite Oil 1L'),
    ).toBeInTheDocument();
    expect(screen.getByText('SYSTEM_GUARD')).toBeInTheDocument();
    expect(screen.getByText('MERCHANT_APPROVED')).toBeInTheDocument();

    const drawerButtons = screen.getAllByRole('button', { name: /Why am I seeing this\?/i });
    fireEvent.click(drawerButtons[0]);
    expect(screen.getByText(/"creep_percentage": 7\.58/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'CFO_ALERT' }));
    await waitFor(() => {
      expect(mockedClient.listBusinessEvents).toHaveBeenCalledWith('CFO_ALERT');
    });
  });

  it('navigates all 4 tabs in App.tsx and executes all 6 JudgeDemoBar live backend flows', async () => {
    mockedClient.proposeVoiceCommand.mockResolvedValue(SAMPLE_VOICE_DISAMBIG);
    mockedClient.scanDistributorBill.mockResolvedValue(SAMPLE_BILL);
    mockedClient.simulateQrWebhook.mockResolvedValue({
      status: 'QUEUED_FOR_REVIEW',
      upi_txn_id: 'UPI-JUDGE-1',
      queue_id: 8,
    });
    mockedClient.createBoliBakiRecovery.mockResolvedValue(SAMPLE_RECOVERY);

    render(<App />);

    await waitFor(() => {
      expect(mockedClient.getMemoryHealth).toHaveBeenCalledTimes(1);
      expect(mockedClient.getUnmatchedPayments).toHaveBeenCalled();
      expect(mockedClient.getOverdueDebtors).toHaveBeenCalled();
    });

    // Verify bottom 4-tab navigation works
    fireEvent.click(screen.getByRole('button', { name: /Memory/i }));
    await waitFor(() => {
      expect(screen.getByTestId('memory-timeline-tab')).toBeInTheDocument();
    });

    // Expand collapsible Judge Demo Quick-Trigger Bar
    const judgeBar = screen.getByLabelText('Judge Demo Quick-Trigger Bar');
    fireEvent.click(
      within(judgeBar).getByRole('button', { name: /Judge Demo Quick-Triggers \(6 Flows\)/i }),
    );

    // 1. Voice Suresh Disambiguation -> Tab 1
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Suresh ka ₹200 udhaar likho/i }));
    await waitFor(() => {
      expect(screen.getByTestId('munim-mic-tab')).toBeInTheDocument();
      expect(mockedClient.proposeVoiceCommand).toHaveBeenCalledWith({
        transcriptOverride: 'Suresh ka 200 rupaye udhaar likh do',
        languageHint: 'hi-IN',
      });
    });

    // 2. Scan Bill (+7.58% Oil Creep) -> Tab 2
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Scan Bill \(\+7\.58% Oil Creep\)/i }));
    await waitFor(() => {
      expect(screen.getByTestId('ai-cfo-tab')).toBeInTheDocument();
      expect(mockedClient.scanDistributorBill).toHaveBeenCalledWith({ useDemoSample: true });
    });

    // 3. Settlement Waterfall -> Tab 2
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Mera Paisa Kam Kyun Aaya\?/i }));
    await waitFor(() => {
      expect(mockedClient.getSettlementExplainer).toHaveBeenCalled();
      expect(mockedSoundbox).toHaveBeenCalledWith(
        expect.objectContaining({ sourceLabel: 'Bulbul v3 Settlement Explainer' }),
      );
    });

    // 4. Fire Ambiguous ₹200 QR Webhook -> Tab 2
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Fire Ambiguous ₹200 QR Webhook/i }));
    await waitFor(() => {
      expect(mockedClient.simulateQrWebhook).toHaveBeenCalledWith(
        expect.objectContaining({
          upi_txn_id: expect.stringMatching(/^UPI-JUDGE-\d+$/),
          amount: 200,
          payer_name: 'Suresh',
          payer_vpa: 'suresh@paytm',
        }),
      );
    });

    // 5. Marathi Udhaar Link -> Tab 3
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Marathi Udhaar Link → Pay/i }));
    await waitFor(() => {
      expect(screen.getByTestId('ai-cmo-tab')).toBeInTheDocument();
      expect(mockedClient.createBoliBakiRecovery).toHaveBeenCalledWith({
        customer_id: 3,
        target_language: 'mr-IN',
      });
    });

    // 6. Run 60s Diwali Closing Ritual -> Tab 3
    fireEvent.click(within(judgeBar).getByRole('button', { name: /Run 60s Diwali Closing Ritual/i }));
    await waitFor(() => {
      expect(mockedClient.getDukaanClosingRitual).toHaveBeenCalled();
      expect(mockedSoundbox).toHaveBeenCalledWith(
        expect.objectContaining({ sourceLabel: 'Diwali EOD Ritual' }),
      );
    });
  });
});
