import type {
  BoliBakiRecoveryResponse,
  BoliBakiRequest,
  BusinessEvent,
  ConfirmBahiKhataRequest,
  ConfirmBahiKhataResponse,
  ConfirmBillRequest,
  ConfirmBillResponse,
  CustomerLedgerResponse,
  CustomerResolveResponse,
  CustomerSummary,
  DeadStockCampaignRequest,
  DeadStockCampaignResponse,
  DeadStockResponse,
  DukaanClosingRitualResponse,
  EventCategory,
  InventoryItem,
  LanguageCode,
  MemoryHealthResponse,
  OverdueDebtorsResponse,
  ProposalConfirmRequest,
  ProposalConfirmResponse,
  QRWebhookPayload,
  QRWebhookResponse,
  ResolvePaymentRequest,
  ResolvePaymentResponse,
  ScanBahiKhataResponse,
  ScanBillResponse,
  SettlementExplainerResponse,
  SimulateLinkPaidResponse,
  SimulatePromoClickResponse,
  TextToSpeechRequest,
  TextToSpeechResponse,
  UnmatchedPayment,
  VoiceHealthResponse,
  VoiceProposeResponse,
} from '../types/kirana';

export class KiranaApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly payload?: unknown;

  constructor(status: number, detail: string, payload?: unknown) {
    super(`KiranaOS API Error (${status}): ${detail}`);
    this.name = 'KiranaApiError';
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '').replace(/\/+$/, '');

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function parseResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type') ?? '';
  let parsed: unknown = null;

  if (contentType.includes('application/json')) {
    try {
      parsed = await res.json();
    } catch {
      parsed = null;
    }
  } else {
    try {
      const text = await res.text();
      parsed = text ? { detail: text } : null;
    } catch {
      parsed = null;
    }
  }

  if (!res.ok) {
    let detail = res.statusText || 'Request failed';
    if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>;
      if (typeof record.detail === 'string' && record.detail.trim()) {
        detail = record.detail;
      } else if (Array.isArray(record.detail)) {
        detail = record.detail
          .map((item) =>
            item && typeof item === 'object' && 'msg' in item
              ? String((item as Record<string, unknown>).msg)
              : JSON.stringify(item),
          )
          .join('; ');
      } else if (typeof record.message === 'string' && record.message.trim()) {
        detail = record.message;
      }
    }
    throw new KiranaApiError(res.status, detail, parsed);
  }

  return parsed as T;
}

async function requestJson<T>(
  path: string,
  options: { method?: 'GET' | 'POST'; body?: unknown } = {},
): Promise<T> {
  const { method = 'GET', body } = options;
  const init: RequestInit = { method };

  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(body);
  }

  const res = await fetch(buildUrl(path), init);
  return parseResponse<T>(res);
}

async function requestMultipart<T>(path: string, formData: FormData): Promise<T> {
  // Never manually set Content-Type for FormData; browser injects multipart boundary.
  const res = await fetch(buildUrl(path), {
    method: 'POST',
    body: formData,
  });
  return parseResponse<T>(res);
}

export interface ProposeVoiceInput {
  transcriptOverride?: string;
  audioBlob?: Blob;
  filename?: string;
  languageHint?: LanguageCode;
}

export interface ScanUploadOrDemoInput {
  useDemoSample?: boolean;
  file?: File | Blob;
  filename?: string;
}

export const kiranaClient = {
  // ------------------------------------------------------------------------
  // Memory Inspection (/api/v1/memory/*)
  // ------------------------------------------------------------------------
  getMemoryHealth(): Promise<MemoryHealthResponse> {
    return requestJson<MemoryHealthResponse>('/api/v1/memory/health');
  },

  listCustomers(query?: string): Promise<CustomerSummary[] | CustomerResolveResponse> {
    const qs = query && query.trim() ? `?query=${encodeURIComponent(query.trim())}` : '';
    return requestJson<CustomerSummary[] | CustomerResolveResponse>(`/api/v1/memory/customers${qs}`);
  },

  resolveCustomer(query: string): Promise<CustomerResolveResponse> {
    return requestJson<CustomerResolveResponse>(
      `/api/v1/memory/customers/resolve?query=${encodeURIComponent(query)}`,
    );
  },

  getCustomerLedger(customerId: number): Promise<CustomerLedgerResponse> {
    return requestJson<CustomerLedgerResponse>(`/api/v1/memory/customers/${customerId}/ledger`);
  },

  listInventory(): Promise<InventoryItem[]> {
    return requestJson<InventoryItem[]>('/api/v1/memory/inventory');
  },

  listBusinessEvents(category?: EventCategory | string): Promise<BusinessEvent[]> {
    const qs = category && category !== 'ALL' ? `?category=${encodeURIComponent(category)}` : '';
    return requestJson<BusinessEvent[]>(`/api/v1/memory/events${qs}`);
  },

  // ------------------------------------------------------------------------
  // Voice Gateway (/api/v1/voice/*)
  // ------------------------------------------------------------------------
  getVoiceHealth(): Promise<VoiceHealthResponse> {
    return requestJson<VoiceHealthResponse>('/api/v1/voice/health');
  },

  proposeVoiceCommand(input: ProposeVoiceInput): Promise<VoiceProposeResponse> {
    const languageHint = input.languageHint ?? 'hi-IN';
    if (input.audioBlob) {
      const formData = new FormData();
      formData.append('language_hint', languageHint);
      formData.append('file', input.audioBlob, input.filename ?? 'voice-command.webm');
      if (input.transcriptOverride) {
        formData.append('transcript_override', input.transcriptOverride);
      }
      return requestMultipart<VoiceProposeResponse>('/api/v1/voice/propose', formData);
    }

    return requestJson<VoiceProposeResponse>('/api/v1/voice/propose', {
      method: 'POST',
      body: {
        transcript_override: input.transcriptOverride ?? '',
        language_hint: languageHint,
      },
    });
  },

  confirmVoiceProposal(req: ProposalConfirmRequest): Promise<ProposalConfirmResponse> {
    return requestJson<ProposalConfirmResponse>('/api/v1/voice/confirm', {
      method: 'POST',
      body: req,
    });
  },

  synthesizeTts(req: TextToSpeechRequest): Promise<TextToSpeechResponse> {
    return requestJson<TextToSpeechResponse>('/api/v1/voice/tts', {
      method: 'POST',
      body: req,
    });
  },

  // ------------------------------------------------------------------------
  // AI CFO (/api/v1/cfo/*)
  // ------------------------------------------------------------------------
  getSettlementExplainer(): Promise<SettlementExplainerResponse> {
    return requestJson<SettlementExplainerResponse>('/api/v1/cfo/settlement-explainer');
  },

  scanDistributorBill(input: ScanUploadOrDemoInput = { useDemoSample: true }): Promise<ScanBillResponse> {
    if (input.file) {
      const formData = new FormData();
      if (input.file instanceof File && !input.filename) {
        formData.append('file', input.file);
      } else {
        formData.append('file', input.file, input.filename ?? 'distributor-bill.jpg');
      }
      return requestMultipart<ScanBillResponse>('/api/v1/cfo/scan-distributor-bill', formData);
    }
    return requestJson<ScanBillResponse>('/api/v1/cfo/scan-distributor-bill', {
      method: 'POST',
      body: { use_demo_sample: input.useDemoSample ?? true },
    });
  },

  confirmDistributorBill(req: ConfirmBillRequest): Promise<ConfirmBillResponse> {
    return requestJson<ConfirmBillResponse>('/api/v1/cfo/confirm-distributor-bill', {
      method: 'POST',
      body: req,
    });
  },

  getUnmatchedPayments(): Promise<UnmatchedPayment[]> {
    return requestJson<UnmatchedPayment[]>('/api/v1/cfo/unmatched-payments');
  },

  resolveUnmatchedPayment(req: ResolvePaymentRequest): Promise<ResolvePaymentResponse> {
    return requestJson<ResolvePaymentResponse>('/api/v1/cfo/resolve-unmatched-payment', {
      method: 'POST',
      body: req,
    });
  },

  simulateQrWebhook(payload: QRWebhookPayload): Promise<QRWebhookResponse> {
    return requestJson<QRWebhookResponse>('/api/v1/cfo/simulate-qr-webhook', {
      method: 'POST',
      body: payload,
    });
  },

  // ------------------------------------------------------------------------
  // AI CMO (/api/v1/cmo/*)
  // ------------------------------------------------------------------------
  getOverdueDebtors(): Promise<OverdueDebtorsResponse> {
    return requestJson<OverdueDebtorsResponse>('/api/v1/cmo/overdue-debtors');
  },

  createBoliBakiRecovery(req: BoliBakiRequest): Promise<BoliBakiRecoveryResponse> {
    return requestJson<BoliBakiRecoveryResponse>('/api/v1/cmo/boli-baki-recovery', {
      method: 'POST',
      body: req,
    });
  },

  simulateLinkPaid(slug: string): Promise<SimulateLinkPaidResponse> {
    const normalized = slug.replace(/^paytm\.me\//, '');
    return requestJson<SimulateLinkPaidResponse>(
      `/api/v1/cmo/simulate-link-paid/${encodeURIComponent(normalized)}`,
      { method: 'POST' },
    );
  },

  getDeadStock(): Promise<DeadStockResponse> {
    return requestJson<DeadStockResponse>('/api/v1/cmo/dead-stock');
  },

  createDeadStockCampaign(req: DeadStockCampaignRequest): Promise<DeadStockCampaignResponse> {
    return requestJson<DeadStockCampaignResponse>('/api/v1/cmo/dead-stock-campaign', {
      method: 'POST',
      body: req,
    });
  },

  simulatePromoClick(slug: string, converted = true): Promise<SimulatePromoClickResponse> {
    const normalized = slug.replace(/^paytm\.me\//, '');
    return requestJson<SimulatePromoClickResponse>(
      `/api/v1/cmo/simulate-promo-click/${encodeURIComponent(normalized)}?converted=${converted}`,
      { method: 'POST', body: { converted } },
    );
  },

  getDukaanClosingRitual(): Promise<DukaanClosingRitualResponse> {
    return requestJson<DukaanClosingRitualResponse>('/api/v1/cmo/dukaan-closing-ritual');
  },

  scanBahiKhata(input: ScanUploadOrDemoInput = { useDemoSample: true }): Promise<ScanBahiKhataResponse> {
    if (input.file) {
      const formData = new FormData();
      if (input.file instanceof File && !input.filename) {
        formData.append('file', input.file);
      } else {
        formData.append('file', input.file, input.filename ?? 'bahi-khata.jpg');
      }
      return requestMultipart<ScanBahiKhataResponse>('/api/v1/cmo/scan-bahi-khata', formData);
    }
    return requestJson<ScanBahiKhataResponse>('/api/v1/cmo/scan-bahi-khata', {
      method: 'POST',
      body: { use_demo_sample: input.useDemoSample ?? true },
    });
  },

  confirmBahiKhata(req: ConfirmBahiKhataRequest): Promise<ConfirmBahiKhataResponse> {
    return requestJson<ConfirmBahiKhataResponse>('/api/v1/cmo/confirm-bahi-khata', {
      method: 'POST',
      body: req,
    });
  },
};
