import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { kiranaClient, KiranaApiError } from '../kiranaClient';

describe('kiranaClient', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function mockJsonResponse(body: unknown, status = 200) {
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(JSON.stringify(body)),
    } as Response);
  }

  it('calls exact FastAPI paths across memory, voice, cfo, and cmo endpoints', async () => {
    fetchMock.mockImplementation(() => mockJsonResponse({ ok: true }));

    await kiranaClient.getMemoryHealth();
    await kiranaClient.listCustomers();
    await kiranaClient.listCustomers('Suresh');
    await kiranaClient.getCustomerLedger(3);
    await kiranaClient.listInventory();
    await kiranaClient.listBusinessEvents('CFO_ALERT');
    await kiranaClient.getVoiceHealth();
    await kiranaClient.confirmVoiceProposal({
      proposal_id: 'PROP-1',
      action: 'APPROVE',
      intent: 'CREDIT_UDHAAR',
      customer_id: 2,
      amount: 200,
      source_utterance: 'Suresh ka 200 udhaar likho',
    });
    await kiranaClient.synthesizeTts({ text: 'Namaste', target_language_code: 'hi-IN' });
    await kiranaClient.getSettlementExplainer();
    await kiranaClient.confirmDistributorBill({
      invoice_number: 'GW-2026-994',
      supplier_name: 'Gupta Wholesalers',
      line_items: [
        {
          item_id: 1,
          sku_name: 'Fortune Sunlite Oil 1L',
          qty: 20,
          unit: 'liters',
          unit_cost: 142,
          line_total: 2840,
        },
      ],
      invoice_total: 4920,
      price_creep_detected: true,
    });
    await kiranaClient.getUnmatchedPayments();
    await kiranaClient.resolveUnmatchedPayment({
      queue_id: 1,
      resolved_customer_id: 2,
    });
    await kiranaClient.simulateQrWebhook({
      upi_txn_id: 'PTM-TEST-1',
      amount: 200,
      payer_name: 'Suresh',
    });
    await kiranaClient.getOverdueDebtors();
    await kiranaClient.createBoliBakiRecovery({ customer_id: 1, target_language: 'mr-IN' });
    await kiranaClient.simulateLinkPaid('munim-ramesh-650');
    await kiranaClient.getDeadStock();
    await kiranaClient.createDeadStockCampaign({ item_id: 4, proposed_discount_rupees: 10 });
    await kiranaClient.simulatePromoClick('promo-mr-bhujia', true);
    await kiranaClient.getDukaanClosingRitual();
    await kiranaClient.confirmBahiKhata({
      batch_ref: 'BATCH-1',
      entries: [
        {
          customer_name: 'Sunita Sawant',
          preferred_language: 'mr-IN',
          amount: 340,
        },
      ],
    });

    const calledUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(calledUrls).toEqual([
      '/api/v1/memory/health',
      '/api/v1/memory/customers',
      '/api/v1/memory/customers?query=Suresh',
      '/api/v1/memory/customers/3/ledger',
      '/api/v1/memory/inventory',
      '/api/v1/memory/events?category=CFO_ALERT',
      '/api/v1/voice/health',
      '/api/v1/voice/confirm',
      '/api/v1/voice/tts',
      '/api/v1/cfo/settlement-explainer',
      '/api/v1/cfo/confirm-distributor-bill',
      '/api/v1/cfo/unmatched-payments',
      '/api/v1/cfo/resolve-unmatched-payment',
      '/api/v1/cfo/simulate-qr-webhook',
      '/api/v1/cmo/overdue-debtors',
      '/api/v1/cmo/boli-baki-recovery',
      '/api/v1/cmo/simulate-link-paid/munim-ramesh-650',
      '/api/v1/cmo/dead-stock',
      '/api/v1/cmo/dead-stock-campaign',
      '/api/v1/cmo/simulate-promo-click/promo-mr-bhujia?converted=true',
      '/api/v1/cmo/dukaan-closing-ritual',
      '/api/v1/cmo/confirm-bahi-khata',
    ]);
  });

  it('sends JSON for text/demo commands and FormData without manual Content-Type for uploads', async () => {
    fetchMock.mockImplementation(() => mockJsonResponse({ status: 'PROPOSAL' }));

    await kiranaClient.proposeVoiceCommand({
      transcriptOverride: 'Suresh ka 200 rupaye udhaar likho',
      languageHint: 'hi-IN',
    });

    const [textUrl, textInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(textUrl).toBe('/api/v1/voice/propose');
    expect((textInit.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(String(textInit.body))).toEqual({
      transcript_override: 'Suresh ka 200 rupaye udhaar likho',
      language_hint: 'hi-IN',
    });

    const audioBlob = new Blob(['fake-audio'], { type: 'audio/webm' });
    await kiranaClient.proposeVoiceCommand({
      audioBlob,
      filename: 'shop.webm',
      languageHint: 'mr-IN',
    });

    const [audioUrl, audioInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(audioUrl).toBe('/api/v1/voice/propose');
    expect(audioInit.body).toBeInstanceOf(FormData);
    const audioForm = audioInit.body as FormData;
    expect(audioForm.get('language_hint')).toBe('mr-IN');
    expect(audioForm.get('file')).toBeTruthy();
    expect(audioInit.headers).toBeUndefined();

    await kiranaClient.scanDistributorBill({ useDemoSample: true });
    const [billDemoUrl, billDemoInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect(billDemoUrl).toBe('/api/v1/cfo/scan-distributor-bill');
    expect(JSON.parse(String(billDemoInit.body))).toEqual({ use_demo_sample: true });

    const billFile = new File(['img'], 'bill.jpg', { type: 'image/jpeg' });
    await kiranaClient.scanDistributorBill({ file: billFile });
    const [billUploadUrl, billUploadInit] = fetchMock.mock.calls[3] as [string, RequestInit];
    expect(billUploadUrl).toBe('/api/v1/cfo/scan-distributor-bill');
    expect(billUploadInit.body).toBeInstanceOf(FormData);
    const uploadedBill = (billUploadInit.body as FormData).get('file') as File;
    expect(uploadedBill).toBeInstanceOf(File);
    expect(uploadedBill.name).toBe('bill.jpg');
    expect(billUploadInit.headers).toBeUndefined();

    await kiranaClient.scanBahiKhata({ useDemoSample: true });
    const [bahiDemoUrl, bahiDemoInit] = fetchMock.mock.calls[4] as [string, RequestInit];
    expect(bahiDemoUrl).toBe('/api/v1/cmo/scan-bahi-khata');
    expect(JSON.parse(String(bahiDemoInit.body))).toEqual({ use_demo_sample: true });

    const bahiFile = new File(['notebook'], 'bahi.png', { type: 'image/png' });
    await kiranaClient.scanBahiKhata({ file: bahiFile });
    const [bahiUploadUrl, bahiUploadInit] = fetchMock.mock.calls[5] as [string, RequestInit];
    expect(bahiUploadUrl).toBe('/api/v1/cmo/scan-bahi-khata');
    expect(bahiUploadInit.body).toBeInstanceOf(FormData);
    const uploadedBahi = (bahiUploadInit.body as FormData).get('file') as File;
    expect(uploadedBahi).toBeInstanceOf(File);
    expect(uploadedBahi.name).toBe('bahi.png');
    expect(bahiUploadInit.headers).toBeUndefined();
  });

  it('parses FastAPI error detail into KiranaApiError with status code', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () =>
        Promise.resolve({
          detail: "Explicit merchant approval ('action': 'APPROVE') is required to commit ledger entries.",
        }),
      text: () => Promise.resolve(''),
    } as Response);

    await expect(
      kiranaClient.confirmVoiceProposal({
        action: 'CANCEL',
        intent: 'CREDIT_UDHAAR',
      }),
    ).rejects.toMatchObject({
      name: 'KiranaApiError',
      status: 400,
      detail: "Explicit merchant approval ('action': 'APPROVE') is required to commit ledger entries.",
    });

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      headers: new Headers({ 'content-type': 'text/plain' }),
      json: () => Promise.reject(new Error('not json')),
      text: () => Promise.resolve('Upstream unavailable'),
    } as Response);

    await expect(kiranaClient.getMemoryHealth()).rejects.toBeInstanceOf(KiranaApiError);
  });
});
