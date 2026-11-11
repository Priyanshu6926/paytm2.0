import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Camera,
  CheckCircle2,
  FileSpreadsheet,
  Landmark,
  Loader2,
  Receipt,
  ShieldCheck,
  Volume2,
  Zap,
} from 'lucide-react';
import { kiranaClient } from '../../api/kiranaClient';
import type {
  CustomerCandidate,
  ScanBillResponse,
  SettlementExplainerResponse,
  UnmatchedPayment,
} from '../../types/kirana';
import { playSoundboxAudio } from '../../utils/soundboxAudio';
import { WhyAmISeeingThis } from '../WhyAmISeeingThis';

export interface AiCfoTabProps {
  billProposal: ScanBillResponse | null;
  onBillProposalChange: (b: ScanBillResponse | null) => void;
  settlementData: SettlementExplainerResponse | null;
  onSettlementDataChange: (s: SettlementExplainerResponse | null) => void;
  refreshToken: number;
  onDataMutated: () => void;
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10MB limit per threat model T-05-05

function formatInr(value: number, forceDecimals = false): string {
  const hasFraction = !Number.isInteger(value);
  return `₹${value.toLocaleString('en-IN', {
    minimumFractionDigits: forceDecimals || hasFraction ? 2 : 0,
    maximumFractionDigits: 2,
  })}`;
}

export function AiCfoTab({
  billProposal,
  onBillProposalChange,
  settlementData,
  onSettlementDataChange,
  refreshToken,
  onDataMutated,
}: AiCfoTabProps) {
  const [scanningBill, setScanningBill] = useState(false);
  const [confirmingBill, setConfirmingBill] = useState(false);
  const [billError, setBillError] = useState<string | null>(null);
  const [billConfirmNotice, setBillConfirmNotice] = useState<string | null>(null);
  const [adoptedPrices, setAdoptedPrices] = useState<Record<string, number>>({});

  const [uploadedPreview, setUploadedPreview] = useState<{
    name: string;
    url: string | null;
  } | null>(null);
  const previewUrlRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [settlementLoading, setSettlementLoading] = useState(false);
  const [settlementError, setSettlementError] = useState<string | null>(null);

  const [unmatchedPayments, setUnmatchedPayments] = useState<UnmatchedPayment[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [simulatingWebhook, setSimulatingWebhook] = useState(false);
  const [resolvingQueueId, setResolvingQueueId] = useState<number | null>(null);
  const [upiNotice, setUpiNotice] = useState<string | null>(null);

  const revokeCurrentPreview = useCallback(() => {
    if (previewUrlRef.current && typeof URL !== 'undefined' && typeof URL.revokeObjectURL === 'function') {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      revokeCurrentPreview();
    };
  }, [revokeCurrentPreview]);

  useEffect(() => {
    // Reset selected MRP toggles whenever a new bill proposal loads
    setAdoptedPrices({});
    setBillConfirmNotice(null);
  }, [billProposal?.invoice_number]);

  const loadSettlementAndQueue = useCallback(
    async (forceSettlement = false) => {
      setQueueLoading(true);
      if (forceSettlement || !settlementData) {
        setSettlementLoading(true);
      }
      try {
        const [queueRes, settlementRes] = await Promise.all([
          kiranaClient.getUnmatchedPayments(),
          forceSettlement || !settlementData
            ? kiranaClient.getSettlementExplainer()
            : Promise.resolve(settlementData),
        ]);
        setUnmatchedPayments(
          Array.isArray(queueRes) ? queueRes.filter((item) => item.status === 'PENDING_REVIEW') : [],
        );
        if (settlementRes) {
          onSettlementDataChange(settlementRes);
          setSettlementError(null);
        }
      } catch (err: unknown) {
        if (!settlementData) {
          setSettlementError(
            err instanceof Error ? err.message : 'Unable to load Paytm settlement data.',
          );
        }
      } finally {
        setQueueLoading(false);
        setSettlementLoading(false);
      }
    },
    [onSettlementDataChange, settlementData],
  );

  useEffect(() => {
    void loadSettlementAndQueue(refreshToken > 0 || !settlementData);
  }, [refreshToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleScanSampleBill = async () => {
    if (scanningBill) return;
    setScanningBill(true);
    setBillError(null);
    setBillConfirmNotice(null);
    revokeCurrentPreview();
    setUploadedPreview(null);
    try {
      const res = await kiranaClient.scanDistributorBill({ useDemoSample: true });
      onBillProposalChange(res);
      if (res.tts_audio_base64 || res.price_creep_alerts.length > 0) {
        void playSoundboxAudio({
          audioBase64: res.tts_audio_base64,
          announcement:
            res.price_creep_alerts[0]?.alert_hi ??
            `${res.supplier_name} bill ${res.invoice_number} scanned.`,
          sourceLabel: 'AI CFO Margin Guard',
        });
      }
    } catch (err: unknown) {
      setBillError(err instanceof Error ? err.message : 'Failed to scan sample bill.');
    } finally {
      setScanningBill(false);
    }
  };

  const handleCustomFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || scanningBill) return;

    const isImageMime = file.type ? file.type.startsWith('image/') : false;
    const isImageExt = /\.(png|jpe?g|webp|gif|bmp|heic|heif)$/i.test(file.name);
    if (!isImageMime && !isImageExt) {
      setBillError('Please select a valid image file (JPG, PNG, or WEBP).');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setBillError('Bill photo exceeds the 10MB limit. Please choose a smaller image.');
      return;
    }

    setBillError(null);
    setBillConfirmNotice(null);
    revokeCurrentPreview();

    const objectUrl =
      typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'
        ? URL.createObjectURL(file)
        : null;
    previewUrlRef.current = objectUrl;
    setUploadedPreview({ name: file.name, url: objectUrl });

    setScanningBill(true);
    try {
      const res = await kiranaClient.scanDistributorBill({ file });
      onBillProposalChange(res);
      if (res.tts_audio_base64 || res.price_creep_alerts.length > 0) {
        void playSoundboxAudio({
          audioBase64: res.tts_audio_base64,
          announcement:
            res.price_creep_alerts[0]?.alert_hi ?? `Custom bill ${res.invoice_number} analyzed.`,
          sourceLabel: 'AI CFO Vision OCR',
        });
      }
    } catch (err: unknown) {
      setBillError(err instanceof Error ? err.message : 'Failed to scan uploaded bill image.');
    } finally {
      setScanningBill(false);
    }
  };

  const toggleAdoptPrice = (skuName: string, recommendedMrp: number) => {
    setAdoptedPrices((prev) => {
      const next = { ...prev };
      if (next[skuName] !== undefined) {
        delete next[skuName];
      } else {
        next[skuName] = recommendedMrp;
      }
      return next;
    });
  };

  const handleConfirmBill = async () => {
    if (!billProposal || confirmingBill) return;
    setConfirmingBill(true);
    setBillError(null);
    try {
      const res = await kiranaClient.confirmDistributorBill({
        invoice_number: billProposal.invoice_number,
        supplier_name: billProposal.supplier_name,
        line_items: billProposal.line_items,
        invoice_total: billProposal.invoice_total,
        price_creep_detected: billProposal.price_creep_alerts.length > 0,
        update_selling_prices:
          Object.keys(adoptedPrices).length > 0 ? adoptedPrices : undefined,
      });

      const notice =
        res.status === 'ALREADY_CONFIRMED'
          ? `Already confirmed: ${res.message}`
          : `${res.message} (${res.stock_events_created ?? billProposal.line_items.length} stock events + supplier khata updated)`;

      setBillConfirmNotice(notice);
      await playSoundboxAudio({
        announcement: `${billProposal.supplier_name} bill ${billProposal.invoice_number} confirmed in KiranaOS.`,
        sourceLabel: 'AI CFO Stock + Khata',
      });
      onDataMutated();
    } catch (err: unknown) {
      setBillError(err instanceof Error ? err.message : 'Failed to confirm distributor bill.');
    } finally {
      setConfirmingBill(false);
    }
  };

  const handleSimulateWebhook = async () => {
    if (simulatingWebhook) return;
    setSimulatingWebhook(true);
    setUpiNotice(null);
    try {
      const txnId = `UPI-SIM-${Date.now()}`;
      const res = await kiranaClient.simulateQrWebhook({
        upi_txn_id: txnId,
        amount: 200,
        payer_name: 'Suresh',
        payer_vpa: 'suresh@paytm',
      });
      await playSoundboxAudio({
        announcement: 'Paytm par ₹200 prapt hue — Ambiguous payer Suresh review queue mein.',
        sourceLabel: 'Paytm QR Webhook',
        isPaymentChime: true,
      });
      setUpiNotice(
        res.status === 'QUEUED_FOR_REVIEW'
          ? `Queued ${txnId} (₹200 from Suresh) for 1-tap merchant verification.`
          : res.message || `Webhook processed: ${res.status}`,
      );
      await loadSettlementAndQueue(false);
      onDataMutated();
    } catch (err: unknown) {
      setUpiNotice(err instanceof Error ? err.message : 'Webhook simulation failed.');
    } finally {
      setSimulatingWebhook(false);
    }
  };

  const handleResolvePayment = async (item: UnmatchedPayment, cand: CustomerCandidate) => {
    if (resolvingQueueId !== null) return;
    setResolvingQueueId(item.id);
    setUpiNotice(null);
    try {
      const res = await kiranaClient.resolveUnmatchedPayment({
        queue_id: item.id,
        resolved_customer_id: cand.customer_id,
      });
      await playSoundboxAudio({
        announcement: `${res.customer_name} ke khate mein ${formatInr(res.amount)} UPI jama ho gaya.`,
        sourceLabel: 'Paytm UPI Reconciled',
        isPaymentChime: true,
      });
      setUpiNotice(
        `Linked ${formatInr(res.amount)} (${item.upi_txn_id}) to ${res.customer_name}. New balance: ${formatInr(res.customer_balance_after)}.`,
      );
      await loadSettlementAndQueue(false);
      onDataMutated();
    } catch (err: unknown) {
      setUpiNotice(err instanceof Error ? err.message : 'Unable to resolve unmatched payment.');
    } finally {
      setResolvingQueueId(null);
    }
  };

  const hasBalancedSeal =
    settlementData?.verification_status === 'DETERMINISTICALLY_BALANCED' ||
    settlementData?.verification_status === 'DETERMINISTICALLY BALANCED';

  return (
    <div className="space-y-3" data-testid="ai-cfo-tab">
      {/* Card A: Distributor Bill Scanner & Price-Creep Guard */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-1.5">
              <Receipt className="w-4 h-4 text-paytm-navy" />
              <h2 className="text-sm font-bold text-paytm-navy">
                Distributor Bill Scanner
              </h2>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              AI Margin Guard • Detects silent wholesale price creep
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-paytm-bg text-paytm-navy border border-paytm-border">
            CFO Guard
          </span>
        </div>

        {/* Dual Triggers: Demo Preset + Custom Image Upload */}
        <div className="grid grid-cols-1 gap-2">
          <button
            type="button"
            disabled={scanningBill}
            onClick={() => void handleScanSampleBill()}
            className="min-h-[44px] w-full rounded-xl bg-paytm-navy hover:bg-paytm-navyDark text-white px-3.5 py-2 text-xs font-bold flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            {scanningBill ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-4 h-4 text-paytm-cyan" />
            )}
            <span>Scan Sample Bill (Gupta Wholesalers)</span>
          </button>

          <label className="min-h-[44px] w-full rounded-xl border border-dashed border-paytm-cyan bg-paytm-cyan/5 hover:bg-paytm-cyan/10 text-paytm-navy px-3.5 py-2 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-colors">
            <Camera className="w-4 h-4 text-paytm-cyan" />
            <span>Upload Custom Bill Photo</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              aria-label="Upload Custom Bill Photo"
              onChange={(e) => void handleCustomFileChange(e)}
              className="sr-only"
            />
          </label>
        </div>

        {/* Uploaded Image Thumbnail & Filename Preview */}
        {uploadedPreview && (
          <div className="rounded-xl bg-paytm-bg border border-paytm-border p-2.5 flex items-center gap-2.5">
            {uploadedPreview.url ? (
              <img
                src={uploadedPreview.url}
                alt={`Preview of ${uploadedPreview.name}`}
                className="w-12 h-12 rounded-lg object-cover border border-paytm-border shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-white border border-paytm-border flex items-center justify-center shrink-0">
                <Camera className="w-5 h-5 text-paytm-cyan" />
              </div>
            )}
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase text-slate-400">
                Custom Invoice Uploaded
              </div>
              <div className="text-xs font-semibold text-paytm-navy truncate">
                {uploadedPreview.name}
              </div>
            </div>
          </div>
        )}

        {billError && (
          <div
            role="alert"
            className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800"
          >
            {billError}
          </div>
        )}

        {billProposal && (
          <div className="space-y-3 pt-1 border-t border-paytm-border">
            {/* Invoice Header */}
            <div className="flex items-start justify-between gap-2 pt-2">
              <div>
                <div className="text-xs font-extrabold text-paytm-navy">
                  {billProposal.supplier_name}
                </div>
                <div className="text-[11px] text-slate-500">
                  {billProposal.invoice_number} • {billProposal.invoice_date}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-extrabold text-paytm-navy tabular-nums">
                  {formatInr(billProposal.invoice_total)}
                </div>
                {billProposal.fallback_used && (
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                    Offline OCR Fallback
                  </span>
                )}
              </div>
            </div>

            {/* Price Creep Alerts */}
            {billProposal.price_creep_alerts.map((alert) => {
              const adopted = adoptedPrices[alert.sku_name] !== undefined;
              return (
                <div
                  key={alert.sku_name}
                  className="rounded-xl bg-[#FEF2F2] border border-[#E11D48]/40 p-3 space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#E11D48] text-white animate-pulse">
                        <AlertOctagon className="w-3 h-3" />
                        <span>+{alert.creep_percentage.toFixed(2)}% PRICE CREEP ALERT</span>
                      </span>
                      <div className="text-xs font-bold text-rose-950">{alert.sku_name}</div>
                      <div className="text-[11px] text-rose-800 tabular-nums">
                        Wholesale Cost: {formatInr(alert.previous_unit_cost)} →{' '}
                        <strong>{formatInr(alert.new_unit_cost)}</strong> (Margin erosion{' '}
                        {formatInr(alert.margin_erosion_per_unit)}/unit)
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        void playSoundboxAudio({
                          audioBase64: billProposal.tts_audio_base64,
                          announcement: alert.alert_hi,
                          sourceLabel: 'Bulbul v3 Price Creep Alert',
                        })
                      }
                      className="min-h-[36px] px-2.5 rounded-lg bg-white border border-rose-200 text-rose-700 text-[11px] font-bold flex items-center gap-1 shrink-0"
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                      <span>Listen Alert</span>
                    </button>
                  </div>

                  <p className="text-[11px] text-rose-900 leading-relaxed">{alert.alert_hi}</p>

                  <label className="min-h-[40px] rounded-lg bg-white border border-rose-200 px-2.5 py-2 flex items-center justify-between gap-2 cursor-pointer">
                    <span className="flex items-center gap-2 text-xs font-semibold text-paytm-navy">
                      <input
                        type="checkbox"
                        checked={adopted}
                        onChange={() =>
                          toggleAdoptPrice(alert.sku_name, alert.recommended_new_mrp)
                        }
                        className="w-4 h-4 accent-paytm-navy rounded"
                      />
                      <span>
                        Adopt Recommended MRP {formatInr(alert.recommended_new_mrp)}
                      </span>
                    </span>
                    <span className="text-[10px] font-bold text-emerald-700">
                      {adopted ? 'Selected' : 'Optional'}
                    </span>
                  </label>
                </div>
              );
            })}

            {/* Extracted Line Items */}
            <div className="rounded-xl border border-paytm-border overflow-hidden">
              <div className="bg-paytm-bg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 flex justify-between">
                <span>Item &amp; Qty</span>
                <span>Rate / Total</span>
              </div>
              <div className="divide-y divide-paytm-border">
                {billProposal.line_items.map((item, idx) => (
                  <div
                    key={`${item.sku_name}-${idx}`}
                    className="px-3 py-2 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-paytm-navy truncate">{item.sku_name}</div>
                      <div className="text-[11px] text-slate-500 tabular-nums">
                        {item.qty} {item.unit ?? 'units'} × {formatInr(item.unit_cost)}
                      </div>
                    </div>
                    <div className="font-bold text-slate-800 tabular-nums shrink-0">
                      {formatInr(item.line_total)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <WhyAmISeeingThis
              summary={
                billProposal.price_creep_alerts.length > 0
                  ? `${billProposal.price_creep_alerts[0].sku_name} wholesale rate rose from ${formatInr(billProposal.price_creep_alerts[0].previous_unit_cost)} to ${formatInr(billProposal.price_creep_alerts[0].new_unit_cost)}, triggering KiranaOS >=2.0% creep protection.`
                  : 'All invoice line items matched baseline KiranaOS wholesale costs.'
              }
              formula="((C_new - C_old) / C_old) * 100"
              beforeLabel={
                billProposal.price_creep_alerts[0]
                  ? formatInr(billProposal.price_creep_alerts[0].previous_unit_cost)
                  : undefined
              }
              afterLabel={
                billProposal.price_creep_alerts[0]
                  ? formatInr(billProposal.price_creep_alerts[0].new_unit_cost)
                  : undefined
              }
              source={`Invoice ${billProposal.invoice_number} (${billProposal.supplier_name})`}
              evidence={{
                price_creep_alerts: billProposal.price_creep_alerts,
                adopted_selling_prices: adoptedPrices,
              }}
            />

            {/* Dual Action Preview */}
            <div className="rounded-xl bg-paytm-bg border border-paytm-border px-3 py-2 text-[11px] text-slate-700">
              <strong className="text-paytm-navy">Dual-Action Preview:</strong>{' '}
              {billProposal.dual_action_preview}
            </div>

            {billConfirmNotice && (
              <div
                role="status"
                className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs text-emerald-900 flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{billConfirmNotice}</span>
              </div>
            )}

            <button
              type="button"
              disabled={confirmingBill}
              onClick={() => void handleConfirmBill()}
              className="min-h-[44px] w-full rounded-xl bg-[#059669] hover:bg-emerald-700 text-white px-4 py-2 text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {confirmingBill ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ShieldCheck className="w-4 h-4" />
              )}
              <span>Confirm &amp; Update Stock + Khata</span>
            </button>
          </div>
        )}
      </section>

      {/* Card B: "Mera Paisa Kam Kyun Aaya?" Settlement Waterfall */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-1.5">
              <Landmark className="w-4 h-4 text-paytm-navy" />
              <h2 className="text-sm font-bold text-paytm-navy">
                “Mera Paisa Kam Kyun Aaya?”
              </h2>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Paytm Settlement Waterfall • Deterministic Audit
            </p>
          </div>

          {settlementData && (
            <button
              type="button"
              onClick={() =>
                void playSoundboxAudio({
                  audioBase64: settlementData.tts_audio_base64,
                  announcement: settlementData.spoken_explanation_hi,
                  sourceLabel: 'Bulbul v3 Settlement Explainer',
                })
              }
              className="min-h-[36px] px-2.5 rounded-xl bg-paytm-navy text-white text-[11px] font-bold flex items-center gap-1 shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5 text-paytm-cyan" />
              <span>Listen in Hindi</span>
            </button>
          )}
        </div>

        {settlementLoading && !settlementData ? (
          <div className="py-4 text-center text-xs text-slate-500">
            Reconciling Paytm settlement...
          </div>
        ) : settlementError ? (
          <div className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800">
            {settlementError}
          </div>
        ) : settlementData ? (
          <>
            <div className="flex items-center justify-between text-[11px] text-slate-600 bg-paytm-bg rounded-xl px-3 py-2 border border-paytm-border">
              <span className="font-semibold text-paytm-navy">{settlementData.bank_account}</span>
              <span>{settlementData.settlement_date}</span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between px-1">
                <span className="font-semibold text-slate-700">Gross QR Collections</span>
                <span className="font-extrabold text-paytm-navy tabular-nums">
                  {formatInr(settlementData.gross_qr_collections, true)}
                </span>
              </div>

              <div className="rounded-xl bg-slate-50 border border-paytm-border divide-y divide-paytm-border">
                {settlementData.deductions.map((ded) => (
                  <div
                    key={ded.type}
                    className="px-3 py-2 flex items-center justify-between gap-2"
                  >
                    <span className="text-[11px] text-slate-700">{ded.label}</span>
                    <span className="px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200 font-bold text-[11px] tabular-nums shrink-0">
                      -{formatInr(ded.amount)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="rounded-xl bg-[#ECFDF5] border border-emerald-200 px-3 py-2.5 flex items-center justify-between gap-2">
                <div>
                  <div className="text-[10px] font-bold uppercase text-emerald-700">
                    Net Settled to Bank
                  </div>
                  <div className="text-base font-extrabold text-emerald-900 tabular-nums">
                    {formatInr(settlementData.net_settled_to_bank, true)}
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#059669] text-white text-[10px] font-extrabold tracking-wide">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>
                    {hasBalancedSeal
                      ? 'DETERMINISTICALLY BALANCED'
                      : settlementData.verification_status}
                  </span>
                </span>
              </div>
            </div>

            <WhyAmISeeingThis
              summary={settlementData.spoken_explanation_hi}
              formula={`Gross ${formatInr(settlementData.gross_qr_collections)} - Total Deductions ${formatInr(settlementData.total_deductions)} = Net ${formatInr(settlementData.net_settled_to_bank)} (Verified to ₹0.01)`}
              beforeLabel={`Gross ${formatInr(settlementData.gross_qr_collections)}`}
              afterLabel={`Net ${formatInr(settlementData.net_settled_to_bank)}`}
              source={`Paytm Daily Settlement (${settlementData.settlement_date})`}
              badgeText="Zero LLM Math"
              evidence={settlementData}
            />
          </>
        ) : null}
      </section>

      {/* Card C: Ambiguous UPI Queue & QR Webhook Simulator */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-[#D97706]" />
              <span>Unmatched UPI Queue ({unmatchedPayments.length})</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Cautious QR reconciliation • Never auto-credits ambiguous payers
            </p>
          </div>
        </div>

        <button
          type="button"
          disabled={simulatingWebhook}
          onClick={() => void handleSimulateWebhook()}
          className="min-h-[44px] w-full rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-950 px-3.5 py-2 text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
        >
          {simulatingWebhook ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4 text-[#D97706]" />
          )}
          <span>⚡ Fire Ambiguous ₹200 QR Webhook</span>
        </button>

        {upiNotice && (
          <div
            role="status"
            className="rounded-xl bg-paytm-bg border border-paytm-border px-3 py-2 text-xs text-paytm-navy font-medium"
          >
            {upiNotice}
          </div>
        )}

        {queueLoading && unmatchedPayments.length === 0 ? (
          <div className="py-3 text-center text-xs text-slate-500">Checking UPI queue...</div>
        ) : unmatchedPayments.length === 0 ? (
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2.5 text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>All Paytm QR payments are reconciled.</span>
          </div>
        ) : (
          <div className="space-y-2.5">
            {unmatchedPayments.map((item) => (
              <div
                key={item.id}
                className="rounded-xl bg-[#FFFBEB] border border-amber-300 p-3 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-xs font-extrabold text-paytm-navy">
                      {item.payer_name} • {formatInr(item.amount)}
                    </div>
                    <div className="text-[10px] font-mono text-slate-500 truncate">
                      {item.upi_txn_id} • {item.payer_vpa ?? 'UPI QR'}
                    </div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-950 shrink-0">
                    PENDING REVIEW
                  </span>
                </div>

                <p className="text-[11px] text-amber-950">{item.ambiguity_reason}</p>

                <div className="flex flex-wrap gap-1.5">
                  {item.candidate_customers.map((cand) => (
                    <button
                      key={cand.customer_id}
                      type="button"
                      disabled={resolvingQueueId === item.id}
                      onClick={() => void handleResolvePayment(item, cand)}
                      className="min-h-[40px] px-3 py-1.5 rounded-lg bg-white hover:bg-emerald-50 border border-amber-300 hover:border-emerald-400 text-xs font-bold text-paytm-navy disabled:opacity-50"
                    >
                      Credit {cand.name} ({formatInr(cand.current_udhaar)})
                    </button>
                  ))}
                </div>

                <WhyAmISeeingThis
                  summary={item.ambiguity_reason}
                  source={`Paytm QR Webhook ${item.upi_txn_id}`}
                  evidence={{
                    upi_txn_id: item.upi_txn_id,
                    payer_name: item.payer_name,
                    payer_vpa: item.payer_vpa,
                    amount: item.amount,
                    candidates: item.candidate_customers,
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
