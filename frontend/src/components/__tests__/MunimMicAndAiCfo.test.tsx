import { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { kiranaClient } from '../../api/kiranaClient';
import type {
  CustomerLedgerResponse,
  CustomerSummary,
  LanguageCode,
  ScanBillResponse,
  SettlementExplainerResponse,
  UnmatchedPayment,
  VoiceProposeResponse,
} from '../../types/kirana';
import { playSoundboxAudio } from '../../utils/soundboxAudio';
import { AiCfoTab } from '../tabs/AiCfoTab';
import { MunimMicTab } from '../tabs/MunimMicTab';

vi.mock('../../api/kiranaClient', () => ({
  kiranaClient: {
    listCustomers: vi.fn(),
    getUnmatchedPayments: vi.fn(),
    getCustomerLedger: vi.fn(),
    proposeVoiceCommand: vi.fn(),
    confirmVoiceProposal: vi.fn(),
    scanDistributorBill: vi.fn(),
    confirmDistributorBill: vi.fn(),
    getSettlementExplainer: vi.fn(),
    resolveUnmatchedPayment: vi.fn(),
    simulateQrWebhook: vi.fn(),
  },
}));

vi.mock('../../utils/soundboxAudio', () => ({
  playSoundboxAudio: vi.fn().mockResolvedValue({ mode: 'wav' }),
}));

const mockedClient = vi.mocked(kiranaClient);
const mockedSoundbox = vi.mocked(playSoundboxAudio);

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
  {
    id: 2,
    name: 'Suresh Kadam (Kirana)',
    aliases: ['Suresh'],
    phone: '9820333444',
    preferred_language: 'mr-IN',
    regular_cycle_days: 15,
    last_visit_date: '2026-11-04',
    last_visit: '7 days ago',
    outstanding_balance: 300,
    total_credit: 300,
    total_repayment: 0,
    total_adjustment: 0,
    days_overdue: 0,
  },
  {
    id: 3,
    name: 'Ramesh Sharma',
    aliases: ['Ramesh'],
    phone: '9820555666',
    preferred_language: 'hi-IN',
    regular_cycle_days: 7,
    last_visit_date: '2026-10-22',
    last_visit: '18 days ago',
    outstanding_balance: 650,
    total_credit: 650,
    total_repayment: 0,
    total_adjustment: 0,
    days_overdue: 18,
  },
];

const DISAMBIGUATION_PROPOSAL: VoiceProposeResponse = {
  status: 'NEEDS_DISAMBIGUATION',
  intent: 'CREDIT_UDHAAR',
  extracted_name: 'Suresh',
  extracted_amount: 200,
  ambiguity_reason: '2 customers match "Suresh". Select exact customer before committing.',
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
  why_am_i_seeing_this: 'Identity guard detected two customers named Suresh in KiranaOS.',
  spoken_prompt_hi: 'Do Suresh mile hain. Kripya sahi Suresh chunein.',
  raw_transcript: 'Suresh ka 200 rupaye udhaar likh do',
  tts_audio_base64: 'UklGRg==',
};

const EXACT_PROPOSAL: VoiceProposeResponse = {
  status: 'PROPOSAL',
  proposal_id: 'prop-ramesh-300',
  intent: 'REPAYMENT_JAMA',
  customer_id: 3,
  customer_name: 'Ramesh Sharma',
  extracted_amount: 300,
  current_balance: 650,
  new_balance: 350,
  why_am_i_seeing_this: 'Exact match for Ramesh Sharma. Net balance reduces from ₹650 to ₹350.',
  spoken_prompt_hi: 'Ramesh Sharma ka 300 rupaye jama darj karein?',
  raw_transcript: 'Ramesh ne 300 rupaye jama kiye',
  tts_audio_base64: 'UklGRg==',
};

const SAMPLE_LEDGER: CustomerLedgerResponse = {
  customer: {
    id: 3,
    name: 'Ramesh Sharma',
    phone: '9820555666',
    preferred_language: 'hi-IN',
    regular_cycle_days: 7,
    last_visit_date: '2026-10-22',
    last_visit: '18 days ago',
    outstanding_balance: 650,
  },
  balance: {
    customer_id: 3,
    total_credit: 650,
    total_repayment: 0,
    total_adjustment: 0,
    net_outstanding_balance: 650,
  },
  total_credit: 650,
  total_repayment: 0,
  total_adjustment: 0,
  net_outstanding_balance: 650,
  count: 1,
  ledger_entries: [
    {
      id: 101,
      entry_type: 'CREDIT_UDHAAR',
      amount: 650,
      payment_mode: 'UDHAAR',
      provider_ref: null,
      source_utterance: 'Ramesh ka ration udhaar',
      confidence_score: 0.99,
      status: 'COMMITTED',
      created_at: '2026-10-22 10:15:00',
    },
  ],
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
      alert_hi: 'Fortune Sunlite Oil 1L ka rate 7.58% badh gaya hai. Naya MRP 160 rakhein.',
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
    {
      item_id: 2,
      sku_name: 'Maggi Masala 70g',
      qty: 40,
      unit: 'packs',
      unit_cost: 11.5,
      line_total: 460,
    },
    {
      item_id: 3,
      sku_name: 'Amul Pure Ghee 1L',
      qty: 2,
      unit: 'tins',
      unit_cost: 460,
      line_total: 920,
    },
  ],
  dual_action_preview:
    'Adds 62 units across 3 SKUs to inventory_items and credits ₹4,220 to Gupta Wholesalers supplier_ledger.',
  tts_audio_base64: 'UklGRg==',
  fallback_used: false,
};

const SAMPLE_SETTLEMENT: SettlementExplainerResponse = {
  settlement_date: '2026-11-09',
  bank_account: 'State Bank of India •••• 4921',
  gross_qr_collections: 6450,
  deductions: [
    {
      type: 'PAYTM_MERCHANT_LOAN_EDI',
      label: 'Paytm Business Loan Daily Installment (Loan #PTM-882)',
      amount: 450,
    },
    {
      type: 'SOUNDBOX_RENTAL',
      label: 'Paytm AI Soundbox Monthly Subscription',
      amount: 125,
    },
    {
      type: 'CUSTOMER_REFUND',
      label: 'Instant Refund (Txn #99102)',
      amount: 60,
    },
  ],
  total_deductions: 635,
  net_settled_to_bank: 5815,
  verification_status: 'DETERMINISTICALLY_BALANCED',
  spoken_explanation_hi:
    'Aaj aapka kul QR collection 6,450 rupaye tha. 635 rupaye katkar 5,815 rupaye SBI khate mein aaye hain.',
  tts_audio_base64: 'UklGRg==',
};

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
      {
        customer_id: 2,
        name: 'Suresh Kadam (Kirana)',
        phone: '9820333444',
        current_udhaar: 300,
        last_visit: '7 days ago',
      },
    ],
    ambiguity_reason: 'Payer "Suresh" matches 2 customers with pending udhaar.',
    status: 'PENDING_REVIEW',
    resolved_customer_id: null,
    created_at: '2026-11-11 11:00:00',
  },
];

function MunimHarness({
  initialProposal = null,
  onDataMutated = vi.fn(),
}: {
  initialProposal?: VoiceProposeResponse | null;
  onDataMutated?: () => void;
}) {
  const [lang, setLang] = useState<LanguageCode>('hi-IN');
  const [proposal, setProposal] = useState<VoiceProposeResponse | null>(initialProposal);
  return (
    <MunimMicTab
      languageHint={lang}
      onLanguageChange={setLang}
      activeProposal={proposal}
      onProposalChange={setProposal}
      refreshToken={0}
      onDataMutated={onDataMutated}
    />
  );
}

function CfoHarness({
  initialSettlement = null,
  onDataMutated = vi.fn(),
}: {
  initialSettlement?: SettlementExplainerResponse | null;
  onDataMutated?: () => void;
}) {
  const [billProposal, setBillProposal] = useState<ScanBillResponse | null>(null);
  const [settlementData, setSettlementData] = useState<SettlementExplainerResponse | null>(
    initialSettlement,
  );
  return (
    <AiCfoTab
      billProposal={billProposal}
      onBillProposalChange={setBillProposal}
      settlementData={settlementData}
      onSettlementDataChange={setSettlementData}
      refreshToken={0}
      onDataMutated={onDataMutated}
    />
  );
}

describe('Tab 1 (MunimMicTab) & Tab 2 (AiCfoTab) Flows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.listCustomers.mockResolvedValue(SAMPLE_CUSTOMERS);
    mockedClient.getUnmatchedPayments.mockResolvedValue([]);
    mockedClient.getCustomerLedger.mockResolvedValue(SAMPLE_LEDGER);
    mockedClient.getSettlementExplainer.mockResolvedValue(SAMPLE_SETTLEMENT);
  });

  it('proposes ambiguous voice text, shows NEEDS_DISAMBIGUATION Amber card without blind write, and confirms via 1-tap candidate selection', async () => {
    const onDataMutated = vi.fn();
    mockedClient.proposeVoiceCommand.mockResolvedValue(DISAMBIGUATION_PROPOSAL);
    mockedClient.confirmVoiceProposal.mockResolvedValue({
      status: 'CONFIRMED',
      proposal_id: null,
      intent: 'CREDIT_UDHAAR',
      ledger_entry_id: 42,
      customer_id: 1,
      customer_name: 'Suresh Patil (Tailor)',
      amount: 200,
      new_balance: 650,
      business_event_id: 88,
      spoken_confirmation: 'Suresh Patil (Tailor) ke khate mein ₹200.00 udhaar darj ho gaya hai.',
      tts_audio_base64: 'UklGRg==',
    });

    render(<MunimHarness onDataMutated={onDataMutated} />);

    const input = screen.getByLabelText('Hinglish or Marathi command input');
    fireEvent.change(input, { target: { value: 'Suresh ka 200 rupaye udhaar likh do' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send command' }));

    await waitFor(() => {
      expect(mockedClient.proposeVoiceCommand).toHaveBeenCalledWith({
        transcriptOverride: 'Suresh ka 200 rupaye udhaar likh do',
        languageHint: 'hi-IN',
      });
    });

    const disambigCard = await screen.findByLabelText('Identity disambiguation required');
    expect(within(disambigCard).getByText('NEEDS DISAMBIGUATION')).toBeInTheDocument();
    expect(within(disambigCard).getByText(/Suresh Patil \(Tailor\)/)).toBeInTheDocument();
    expect(within(disambigCard).getByText(/Suresh Kadam \(Kirana\)/)).toBeInTheDocument();
    expect(
      within(disambigCard).getByRole('button', { name: /Why am I seeing this\?/i }),
    ).toBeInTheDocument();
    expect(mockedClient.confirmVoiceProposal).not.toHaveBeenCalled();

    fireEvent.click(within(disambigCard).getByRole('button', { name: /Suresh Patil \(Tailor\)/i }));

    await waitFor(() => {
      expect(mockedClient.confirmVoiceProposal).toHaveBeenCalledWith({
        proposal_id: undefined,
        action: 'APPROVE',
        intent: 'CREDIT_UDHAAR',
        customer_id: 1,
        amount: 200,
        item_id: undefined,
        quantity_delta: undefined,
        source_utterance: 'Suresh ka 200 rupaye udhaar likh do',
        language_hint: 'hi-IN',
      });
    });

    await waitFor(() => {
      expect(onDataMutated).toHaveBeenCalledTimes(1);
      expect(mockedSoundbox).toHaveBeenCalledWith(
        expect.objectContaining({
          announcement: 'Suresh Patil (Tailor) ke khate mein ₹200.00 udhaar darj ho gaya hai.',
        }),
      );
    });
  });

  it('renders PROPOSAL card with before -> after balance and cancels cleanly without calling confirmVoiceProposal', async () => {
    render(<MunimHarness initialProposal={EXACT_PROPOSAL} />);

    expect(screen.getByText('Ramesh Sharma')).toBeInTheDocument();
    expect(screen.getByText('₹650')).toBeInTheDocument();
    expect(screen.getByText('₹350')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Approve \(Haan\)/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Approve \(Haan\)/i })).not.toBeInTheDocument();
    });
    expect(mockedClient.confirmVoiceProposal).not.toHaveBeenCalled();
  });

  it('opens Customer Khata ledger sheet and renders chronological append-only entries', async () => {
    render(<MunimHarness />);

    await waitFor(() => {
      expect(screen.getByText('Ramesh Sharma')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Ramesh Sharma/i }));

    await waitFor(() => {
      expect(mockedClient.getCustomerLedger).toHaveBeenCalledWith(3);
    });

    expect(screen.getByText('Append-Only Khata Ledger')).toBeInTheDocument();
    expect(screen.getByText('CREDIT_UDHAAR')).toBeInTheDocument();
    expect(screen.getByText('Ramesh ka ration udhaar')).toBeInTheDocument();
  });

  it('scans Gupta Wholesalers sample bill, surfaces +7.58% price creep alert, adopts ₹160 MRP, and executes atomic confirm', async () => {
    const onDataMutated = vi.fn();
    mockedClient.scanDistributorBill.mockResolvedValue(SAMPLE_BILL);
    mockedClient.confirmDistributorBill.mockResolvedValue({
      status: 'CONFIRMED',
      invoice_number: 'GW-2026-8841',
      stock_events_created: 3,
      supplier_ledger_id: 19,
      business_event_id: 92,
      message: 'Invoice GW-2026-8841 confirmed.',
    });

    render(<CfoHarness onDataMutated={onDataMutated} />);

    fireEvent.click(screen.getByRole('button', { name: /Scan Sample Bill \(Gupta Wholesalers\)/i }));

    await waitFor(() => {
      expect(mockedClient.scanDistributorBill).toHaveBeenCalledWith({ useDemoSample: true });
    });

    expect(screen.getByText('+7.58% PRICE CREEP ALERT')).toBeInTheDocument();
    expect(screen.getAllByText('Fortune Sunlite Oil 1L').length).toBeGreaterThan(0);

    const mrpToggle = screen.getByRole('checkbox', { name: /Adopt Recommended MRP ₹160/i });
    fireEvent.click(mrpToggle);
    expect(mrpToggle).toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: /Confirm & Update Stock \+ Khata/i }));

    await waitFor(() => {
      expect(mockedClient.confirmDistributorBill).toHaveBeenCalledWith({
        invoice_number: 'GW-2026-8841',
        supplier_name: 'Gupta Wholesalers',
        line_items: SAMPLE_BILL.line_items,
        invoice_total: 4220,
        price_creep_detected: true,
        update_selling_prices: { 'Fortune Sunlite Oil 1L': 160 },
      });
    });

    await waitFor(() => {
      expect(onDataMutated).toHaveBeenCalledTimes(1);
    });
  });

  it('supports custom distributor bill image upload with preview and rejects >10MB files', async () => {
    mockedClient.scanDistributorBill.mockResolvedValue(SAMPLE_BILL);
    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => 'blob:mock-bill-preview');
    URL.revokeObjectURL = vi.fn();

    try {
      render(<CfoHarness />);

      const fileInput = screen.getByLabelText('Upload Custom Bill Photo');
      const customFile = new File(['fake-image-bytes'], 'gupta-custom-bill.jpg', {
        type: 'image/jpeg',
      });

      fireEvent.change(fileInput, { target: { files: [customFile] } });

      await waitFor(() => {
        expect(mockedClient.scanDistributorBill).toHaveBeenCalledWith({ file: customFile });
      });
      expect(screen.getByText('gupta-custom-bill.jpg')).toBeInTheDocument();
      expect(screen.getByAltText('Preview of gupta-custom-bill.jpg')).toHaveAttribute(
        'src',
        'blob:mock-bill-preview',
      );

      // Verify >10MB file upload guard
      const hugeFile = new File(['x'], 'too-big.png', { type: 'image/png' });
      Object.defineProperty(hugeFile, 'size', { value: 11 * 1024 * 1024 });
      fireEvent.change(fileInput, { target: { files: [hugeFile] } });

      expect(screen.getByText(/exceeds the 10MB limit/i)).toBeInTheDocument();
      expect(mockedClient.scanDistributorBill).toHaveBeenCalledTimes(1);
    } finally {
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    }
  });

  it('renders Settlement Waterfall with DETERMINISTICALLY BALANCED seal and triggers Bulbul Hindi TTS', async () => {
    render(<CfoHarness />);

    await waitFor(() => {
      expect(mockedClient.getSettlementExplainer).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText('₹6,450.00')).toBeInTheDocument();
    expect(screen.getByText('-₹450')).toBeInTheDocument();
    expect(screen.getByText('-₹125')).toBeInTheDocument();
    expect(screen.getByText('-₹60')).toBeInTheDocument();
    expect(screen.getByText('₹5,815.00')).toBeInTheDocument();
    expect(screen.getByText('DETERMINISTICALLY BALANCED')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Listen in Hindi/i }));

    expect(mockedSoundbox).toHaveBeenCalledWith(
      expect.objectContaining({
        audioBase64: 'UklGRg==',
        announcement: SAMPLE_SETTLEMENT.spoken_explanation_hi,
        sourceLabel: 'Bulbul v3 Settlement Explainer',
      }),
    );
  });

  it('fires ambiguous ₹200 QR webhook simulator and resolves unmatched UPI item in 1 tap', async () => {
    const onDataMutated = vi.fn();
    mockedClient.getUnmatchedPayments
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(SAMPLE_UNMATCHED)
      .mockResolvedValueOnce([]);
    mockedClient.simulateQrWebhook.mockResolvedValue({
      status: 'QUEUED_FOR_REVIEW',
      upi_txn_id: 'UPI-SIM-123',
      queue_id: 7,
      ambiguity_reason: 'Payer "Suresh" matches 2 customers.',
      candidate_count: 2,
    });
    mockedClient.resolveUnmatchedPayment.mockResolvedValue({
      status: 'LINKED',
      queue_id: 7,
      resolved_customer_id: 1,
      customer_name: 'Suresh Patil (Tailor)',
      amount: 200,
      customer_balance_after: 250,
      business_event_id: 95,
    });

    render(<CfoHarness onDataMutated={onDataMutated} />);

    fireEvent.click(screen.getByRole('button', { name: /Fire Ambiguous ₹200 QR Webhook/i }));

    await waitFor(() => {
      expect(mockedClient.simulateQrWebhook).toHaveBeenCalledWith(
        expect.objectContaining({
          upi_txn_id: expect.stringMatching(/^UPI-SIM-\d+$/),
          amount: 200,
          payer_name: 'Suresh',
          payer_vpa: 'suresh@paytm',
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText('UPI-SEED-200 • suresh@paytm')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Credit Suresh Patil \(Tailor\)/i }));

    await waitFor(() => {
      expect(mockedClient.resolveUnmatchedPayment).toHaveBeenCalledWith({
        queue_id: 7,
        resolved_customer_id: 1,
      });
    });

    await waitFor(() => {
      expect(onDataMutated).toHaveBeenCalled();
    });
  });
});
