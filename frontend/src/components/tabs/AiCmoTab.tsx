import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react';
import {
  AlertOctagon,
  BookOpen,
  Camera,
  Check,
  CheckCircle2,
  ClipboardCopy,
  Flame,
  Loader2,
  Megaphone,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  UserPlus,
  Volume2,
  Zap,
} from 'lucide-react';
import { kiranaClient } from '../../api/kiranaClient';
import type {
  AttributedLink,
  BahiKhataConfirmEntry,
  BahiKhataProposalRow,
  BoliBakiRecoveryResponse,
  DeadStockCampaignResponse,
  DeadStockItem,
  DukaanClosingRitualResponse,
  OverdueDebtor,
  ScanBahiKhataResponse,
} from '../../types/kirana';
import { playSoundboxAudio } from '../../utils/soundboxAudio';
import { WhyAmISeeingThis } from '../WhyAmISeeingThis';

export interface AiCmoTabProps {
  recoveryPreview: BoliBakiRecoveryResponse | null;
  onRecoveryPreviewChange: (r: BoliBakiRecoveryResponse | null) => void;
  closingRitual: DukaanClosingRitualResponse | null;
  onClosingRitualChange: (c: DukaanClosingRitualResponse | null) => void;
  refreshToken: number;
  onDataMutated: () => void;
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10MB upload cap per threat model T-05-08

function formatInr(value: number): string {
  return `₹${value.toLocaleString('en-IN', {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`;
}

export function AiCmoTab({
  recoveryPreview,
  onRecoveryPreviewChange,
  closingRitual,
  onClosingRitualChange,
  refreshToken,
  onDataMutated,
}: AiCmoTabProps) {
  // Section A: Boli-Baki Recovery State
  const [overdueDebtors, setOverdueDebtors] = useState<OverdueDebtor[]>([]);
  const [debtorsLoading, setDebtorsLoading] = useState(true);
  const [generatingForId, setGeneratingForId] = useState<number | null>(null);
  const [payingSlug, setPayingSlug] = useState<string | null>(null);
  const [recoveryNotice, setRecoveryNotice] = useState<{
    tone: 'success' | 'error';
    text: string;
  } | null>(null);

  // Section B: Dead-Stock Break-Even Studio State
  const [deadStockItems, setDeadStockItems] = useState<DeadStockItem[]>([]);
  const [deadStockLoading, setDeadStockLoading] = useState(true);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [discountRupees, setDiscountRupees] = useState<number>(10);
  const [campaignResult, setCampaignResult] = useState<DeadStockCampaignResponse | null>(null);
  const [testingCampaign, setTestingCampaign] = useState(false);
  const [simulatingSlug, setSimulatingSlug] = useState<string | null>(null);
  const [deadStockError, setDeadStockError] = useState<string | null>(null);

  // Section C: 60-Second Dukaan Closing Ritual State
  const [ritualLoading, setRitualLoading] = useState(false);
  const [ritualError, setRitualError] = useState<string | null>(null);
  const [copiedDraft, setCopiedDraft] = useState(false);

  // Section D: Handwritten Bahi-Khata Scanner State
  const [scanningBahi, setScanningBahi] = useState(false);
  const [confirmingBahi, setConfirmingBahi] = useState(false);
  const [bahiScan, setBahiScan] = useState<ScanBahiKhataResponse | null>(null);
  const [editableRows, setEditableRows] = useState<BahiKhataProposalRow[]>([]);
  const [bahiError, setBahiError] = useState<string | null>(null);
  const [bahiNotice, setBahiNotice] = useState<string | null>(null);
  const [bahiPreview, setBahiPreview] = useState<{ name: string; url: string | null } | null>(null);
  const bahiPreviewUrlRef = useRef<string | null>(null);

  const revokeBahiPreview = useCallback(() => {
    if (
      bahiPreviewUrlRef.current &&
      typeof URL !== 'undefined' &&
      typeof URL.revokeObjectURL === 'function'
    ) {
      URL.revokeObjectURL(bahiPreviewUrlRef.current);
      bahiPreviewUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      revokeBahiPreview();
    };
  }, [revokeBahiPreview]);

  const loadCmoData = useCallback(
    async (refreshRitual = true) => {
      setDebtorsLoading(true);
      setDeadStockLoading(true);
      if (refreshRitual) {
        setRitualLoading(true);
      }

      try {
        const [debtorsRes, deadStockRes, ritualRes] = await Promise.allSettled([
          kiranaClient.getOverdueDebtors(),
          kiranaClient.getDeadStock(),
          refreshRitual || !closingRitual
            ? kiranaClient.getDukaanClosingRitual()
            : Promise.resolve(closingRitual),
        ]);

        if (debtorsRes.status === 'fulfilled') {
          setOverdueDebtors(debtorsRes.value.overdue_debtors ?? []);
        }

        if (deadStockRes.status === 'fulfilled') {
          const items = deadStockRes.value.dead_stock_items ?? [];
          setDeadStockItems(items);
          setSelectedItemId((prev) =>
            prev !== null && items.some((i) => i.item_id === prev)
              ? prev
              : (items[0]?.item_id ?? null),
          );
        }

        if (ritualRes.status === 'fulfilled' && ritualRes.value) {
          onClosingRitualChange(ritualRes.value);
          setRitualError(null);
        } else if (ritualRes.status === 'rejected' && !closingRitual) {
          setRitualError(
            ritualRes.reason instanceof Error
              ? ritualRes.reason.message
              : 'Unable to load closing ritual.',
          );
        }
      } finally {
        setDebtorsLoading(false);
        setDeadStockLoading(false);
        setRitualLoading(false);
      }
    },
    [closingRitual, onClosingRitualChange],
  );

  useEffect(() => {
    void loadCmoData(refreshToken > 0 || !closingRitual);
  }, [refreshToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // --------------------------------------------------------------------------
  // Section A Handlers: Boli-Baki Recovery
  // --------------------------------------------------------------------------
  const handleGenerateVoiceLink = async (debtor: OverdueDebtor) => {
    if (generatingForId !== null) return;
    setGeneratingForId(debtor.customer_id);
    setRecoveryNotice(null);
    try {
      const targetLang = debtor.preferred_language || 'mr-IN';
      const res = await kiranaClient.createBoliBakiRecovery({
        customer_id: debtor.customer_id,
        target_language: targetLang,
      });
      onRecoveryPreviewChange(res);
      void playSoundboxAudio({
        audioBase64: res.tts_audio_base64,
        announcement: res.translated_message,
        sourceLabel: `Boli-Baki (${res.preferred_language})`,
      });
    } catch (err: unknown) {
      setRecoveryNotice({
        tone: 'error',
        text: err instanceof Error ? err.message : 'Unable to generate Boli-Baki voice link.',
      });
    } finally {
      setGeneratingForId(null);
    }
  };

  const handleSimulateLinkPaid = async (slug: string) => {
    if (payingSlug !== null) return;
    setPayingSlug(slug);
    setRecoveryNotice(null);
    try {
      const res = await kiranaClient.simulateLinkPaid(slug);
      if (res.status === 'ALREADY_PAID') {
        setRecoveryNotice({
          tone: 'success',
          text: res.message || `Link ${res.slug} was already settled.`,
        });
      } else {
        await playSoundboxAudio({
          audioBase64: res.soundbox_audio_base64,
          announcement:
            res.soundbox_announcement ||
            `Paytm par ${formatInr(res.amount_paid ?? 0)} rupaye prapt hue`,
          sourceLabel: 'Paytm Soundbox',
          isPaymentChime: true,
        });
        setRecoveryNotice({
          tone: 'success',
          text: `${res.customer_name ?? 'Customer'} paid ${formatInr(res.amount_paid ?? 0)} via Paytm Link! Remaining balance: ${formatInr(res.balance_after ?? 0)}.`,
        });
        if (recoveryPreview?.link_slug === res.slug) {
          onRecoveryPreviewChange(null);
        }
        await loadCmoData(true);
        onDataMutated();
      }
    } catch (err: unknown) {
      setRecoveryNotice({
        tone: 'error',
        text: err instanceof Error ? err.message : 'Failed to simulate customer payment.',
      });
    } finally {
      setPayingSlug(null);
    }
  };

  // --------------------------------------------------------------------------
  // Section B Handlers: Dead-Stock Break-Even Studio
  // --------------------------------------------------------------------------
  const selectedDeadStock =
    deadStockItems.find((item) => item.item_id === selectedItemId) ?? deadStockItems[0] ?? null;

  const evaluateDeadStockDiscount = async (itemId: number, discount: number) => {
    if (testingCampaign) return;
    setTestingCampaign(true);
    setDeadStockError(null);
    try {
      const res = await kiranaClient.createDeadStockCampaign({
        item_id: itemId,
        proposed_discount_rupees: discount,
      });
      setCampaignResult(res);
    } catch (err: unknown) {
      setDeadStockError(
        err instanceof Error ? err.message : 'Unable to evaluate dead-stock offer math.',
      );
    } finally {
      setTestingCampaign(false);
    }
  };

  const handleDiscountSliderChange = (nextVal: number) => {
    setDiscountRupees(nextVal);
    if (selectedDeadStock) {
      void evaluateDeadStockDiscount(selectedDeadStock.item_id, nextVal);
    }
  };

  const handleSimulatePromoClick = async (link: AttributedLink) => {
    if (simulatingSlug !== null) return;
    setSimulatingSlug(link.slug);
    setDeadStockError(null);
    try {
      const res = await kiranaClient.simulatePromoClick(link.slug, true);
      if (campaignResult) {
        setCampaignResult({
          ...campaignResult,
          attributed_links: res.language_breakdown,
        });
      }
      setDeadStockItems((prev) =>
        prev.map((item) =>
          item.item_id === selectedDeadStock?.item_id
            ? { ...item, attributed_links: res.language_breakdown }
            : item,
        ),
      );
      onDataMutated();
    } catch (err: unknown) {
      setDeadStockError(
        err instanceof Error ? err.message : 'Failed to record promo link attribution.',
      );
    } finally {
      setSimulatingSlug(null);
    }
  };

  const activePromoLinks: AttributedLink[] =
    campaignResult?.status === 'OFFER_BLOCKED_LOSS_MAKING'
      ? []
      : campaignResult?.attributed_links ?? selectedDeadStock?.attributed_links ?? [];

  // --------------------------------------------------------------------------
  // Section C Handlers: 60s Diwali Closing Ritual
  // --------------------------------------------------------------------------
  const handleRunClosingRitual = async () => {
    if (ritualLoading) return;
    setRitualLoading(true);
    setRitualError(null);
    try {
      const res = await kiranaClient.getDukaanClosingRitual();
      onClosingRitualChange(res);
      void playSoundboxAudio({
        audioBase64: res.tts_audio_base64,
        announcement: res.spoken_ritual_hi,
        sourceLabel: 'Diwali EOD Ritual',
      });
    } catch (err: unknown) {
      setRitualError(err instanceof Error ? err.message : 'Unable to run 60s closing ritual.');
    } finally {
      setRitualLoading(false);
    }
  };

  const handleCopyOrderDraft = async (draft: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(draft);
      }
      setCopiedDraft(true);
      setTimeout(() => setCopiedDraft(false), 2000);
    } catch {
      setCopiedDraft(true);
      setTimeout(() => setCopiedDraft(false), 2000);
    }
  };

  // --------------------------------------------------------------------------
  // Section D Handlers: Bahi-Khata Notebook Scanner
  // --------------------------------------------------------------------------
  const handleScanSampleBahi = async () => {
    if (scanningBahi) return;
    setScanningBahi(true);
    setBahiError(null);
    setBahiNotice(null);
    revokeBahiPreview();
    setBahiPreview(null);
    try {
      const res = await kiranaClient.scanBahiKhata({ useDemoSample: true });
      setBahiScan(res);
      setEditableRows(res.proposals.map((row) => ({ ...row })));
    } catch (err: unknown) {
      setBahiError(err instanceof Error ? err.message : 'Failed to scan sample Bahi-Khata page.');
    } finally {
      setScanningBahi(false);
    }
  };

  const handleBahiFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || scanningBahi) return;

    const isImageMime = file.type ? file.type.startsWith('image/') : false;
    const isImageExt = /\.(png|jpe?g|webp|gif|bmp|heic|heif)$/i.test(file.name);
    if (!isImageMime && !isImageExt) {
      setBahiError('Please upload a valid notebook image (JPG, PNG, or WEBP).');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setBahiError('Notebook photo exceeds the 10MB limit. Please choose a smaller image.');
      return;
    }

    setBahiError(null);
    setBahiNotice(null);
    revokeBahiPreview();

    const objectUrl =
      typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'
        ? URL.createObjectURL(file)
        : null;
    bahiPreviewUrlRef.current = objectUrl;
    setBahiPreview({ name: file.name, url: objectUrl });

    setScanningBahi(true);
    try {
      const res = await kiranaClient.scanBahiKhata({ file });
      setBahiScan(res);
      setEditableRows(res.proposals.map((row) => ({ ...row })));
    } catch (err: unknown) {
      setBahiError(err instanceof Error ? err.message : 'Failed to parse uploaded notebook photo.');
    } finally {
      setScanningBahi(false);
    }
  };

  const updateEditableRow = (
    rowIndex: number,
    patch: Partial<BahiKhataProposalRow>,
  ) => {
    setEditableRows((prev) =>
      prev.map((row) => (row.row_index === rowIndex ? { ...row, ...patch } : row)),
    );
  };

  const removeEditableRow = (rowIndex: number) => {
    setEditableRows((prev) => prev.filter((row) => row.row_index !== rowIndex));
  };

  const handleConfirmBahiKhata = async () => {
    if (confirmingBahi || editableRows.length === 0) return;

    for (let i = 0; i < editableRows.length; i += 1) {
      const row = editableRows[i];
      if (!row.customer_name.trim()) {
        setBahiError(`Row ${i + 1}: Customer name cannot be blank.`);
        return;
      }
      if (!Number.isFinite(row.amount) || row.amount <= 0) {
        setBahiError(`Row ${i + 1}: Amount must be greater than ₹0.`);
        return;
      }
      if (row.match_status === 'AMBIGUOUS' && !row.matched_customer_id) {
        setBahiError(
          `Row ${i + 1} (${row.customer_name}): Please pick an existing customer or choose "Create New Customer".`,
        );
        return;
      }
    }

    setConfirmingBahi(true);
    setBahiError(null);
    setBahiNotice(null);
    try {
      const entries: BahiKhataConfirmEntry[] = editableRows.map((row) => ({
        customer_id: row.matched_customer_id ?? null,
        customer_name: row.customer_name.trim(),
        phone: row.phone.trim() || undefined,
        preferred_language: row.preferred_language || 'hi-IN',
        amount: Math.round(row.amount * 100) / 100,
        notes: row.notes || undefined,
      }));

      const res = await kiranaClient.confirmBahiKhata({
        batch_ref: `BAHI-UI-${Date.now()}`,
        entries,
      });

      const noticeText =
        res.status === 'ALREADY_CONFIRMED'
          ? res.message || 'Bahi-Khata batch was already onboarded.'
          : `Onboarded ${res.entries_recorded ?? entries.length} Bahi-Khata entries (${res.new_customers_created ?? 0} new customers, total ${formatInr(res.total_onboarded_amount ?? 0)}).`;

      setBahiNotice(noticeText);
      void playSoundboxAudio({
        announcement: noticeText,
        sourceLabel: 'Bahi-Khata Onboarded',
      });
      await loadCmoData(true);
      onDataMutated();
    } catch (err: unknown) {
      setBahiError(err instanceof Error ? err.message : 'Failed to onboard Bahi-Khata batch.');
    } finally {
      setConfirmingBahi(false);
    }
  };

  return (
    <div className="space-y-3" data-testid="ai-cmo-tab">
      {/* Section A: Boli-Baki Overdue Udhaar Recovery */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <Megaphone className="w-4 h-4 text-paytm-cyan" />
              <span>Boli-Baki Voice Udhaar Recovery</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Vernacular Sarvam voice note + tracked Paytm Payment Link
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            {overdueDebtors.length} Overdue
          </span>
        </div>

        {recoveryNotice && (
          <div
            role="status"
            className={`rounded-xl px-3 py-2 text-xs font-medium border flex items-center gap-2 ${
              recoveryNotice.tone === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-rose-50 border-rose-200 text-rose-900'
            }`}
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{recoveryNotice.text}</span>
          </div>
        )}

        {/* Active Boli-Baki Voice Recovery Preview Card */}
        {recoveryPreview && (
          <div
            aria-label="Active Boli-Baki Voice Link Preview"
            className="rounded-xl bg-paytm-bg border-2 border-paytm-cyan p-3 space-y-2.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs font-extrabold text-paytm-navy">
                    {recoveryPreview.customer_name}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-paytm-navy text-white">
                    {recoveryPreview.preferred_language}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900">
                    {recoveryPreview.overdue_days}d overdue
                  </span>
                </div>
                <div className="text-xs font-bold text-rose-700 mt-0.5 tabular-nums">
                  Due: {formatInr(recoveryPreview.outstanding_amount)}
                </div>
              </div>

              <button
                type="button"
                onClick={() =>
                  void playSoundboxAudio({
                    audioBase64: recoveryPreview.tts_audio_base64,
                    announcement: recoveryPreview.translated_message,
                    sourceLabel: `Boli-Baki (${recoveryPreview.preferred_language})`,
                  })
                }
                className="min-h-[36px] px-2.5 rounded-xl bg-paytm-navy text-white text-[11px] font-bold flex items-center gap-1 shrink-0"
              >
                <Volume2 className="w-3.5 h-3.5 text-paytm-cyan" />
                <span>Play Voice Note</span>
              </button>
            </div>

            <p className="rounded-lg bg-white border border-paytm-border p-2.5 text-xs text-slate-800 leading-relaxed">
              {recoveryPreview.translated_message}
            </p>

            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-paytm-cyan/15 text-paytm-navy text-[11px] font-mono font-bold">
                {recoveryPreview.paytm_payment_link}
              </span>

              <button
                type="button"
                disabled={payingSlug !== null}
                onClick={() => void handleSimulateLinkPaid(recoveryPreview.link_slug)}
                className="min-h-[40px] px-3 py-1.5 rounded-xl bg-[#059669] hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {payingSlug === recoveryPreview.link_slug ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                <span>⚡ Simulate Customer Paid</span>
              </button>
            </div>

            <WhyAmISeeingThis
              summary={`Triggered because ${recoveryPreview.customer_name} has ${formatInr(recoveryPreview.outstanding_amount)} unpaid for ${recoveryPreview.overdue_days} days (> 10 days rule).`}
              formula="net_outstanding_balance = SUM(CREDIT_UDHAAR) - SUM(REPAYMENT_JAMA)"
              source={`KiranaOS Customer #${recoveryPreview.customer_id} • Fallback: ${String(recoveryPreview.fallback_used)}`}
              badgeText="Boli-Baki Guard"
              evidence={recoveryPreview}
            />
          </div>
        )}

        {debtorsLoading && overdueDebtors.length === 0 ? (
          <div className="py-3 text-center text-xs text-slate-500">
            Loading overdue udhaar accounts...
          </div>
        ) : overdueDebtors.length === 0 ? (
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2.5 text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>All overdue udhaar accounts (&gt;10 days) are settled!</span>
          </div>
        ) : (
          <div className="space-y-2.5">
            {overdueDebtors.map((debtor) => {
              const activeCamp = debtor.active_campaign;
              const isShowingPreview = recoveryPreview?.customer_id === debtor.customer_id;
              return (
                <div
                  key={debtor.customer_id}
                  className="rounded-xl bg-paytm-bg border border-paytm-border p-3 space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs font-extrabold text-paytm-navy">
                          {debtor.customer_name}
                        </span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-white border border-paytm-border text-slate-700">
                          {debtor.preferred_language}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {debtor.overdue_days} days overdue • {debtor.phone ?? 'No phone'}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-sm font-extrabold text-rose-700 tabular-nums">
                        {formatInr(debtor.outstanding_amount)}
                      </div>
                      <div className="text-[10px] font-semibold text-slate-500">Outstanding</div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={generatingForId === debtor.customer_id}
                      onClick={() => void handleGenerateVoiceLink(debtor)}
                      className="min-h-[40px] flex-1 rounded-xl bg-paytm-navy hover:bg-paytm-navyDark text-white px-3 py-1.5 text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      {generatingForId === debtor.customer_id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Volume2 className="w-3.5 h-3.5 text-paytm-cyan" />
                      )}
                      <span>Generate Voice Link</span>
                    </button>

                    {activeCamp && activeCamp.status !== 'PAID' && !isShowingPreview && (
                      <button
                        type="button"
                        disabled={payingSlug !== null}
                        onClick={() => void handleSimulateLinkPaid(activeCamp.link_slug)}
                        className="min-h-[40px] flex-1 rounded-xl bg-[#059669] hover:bg-emerald-700 text-white px-3 py-1.5 text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        {payingSlug === activeCamp.link_slug ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Zap className="w-3.5 h-3.5" />
                        )}
                        <span>⚡ Simulate Customer Paid</span>
                      </button>
                    )}
                  </div>

                  {activeCamp && (
                    <div className="text-[11px] text-slate-600 flex items-center justify-between gap-2 bg-white rounded-lg border border-paytm-border px-2.5 py-1.5">
                      <span className="font-mono text-paytm-navy truncate">
                        {activeCamp.paytm_link_slug}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                          activeCamp.status === 'PAID'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {activeCamp.status}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Section B: Dead-Stock Break-Even Studio & Per-Language Attribution */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <SlidersHorizontal className="w-4 h-4 text-paytm-cyan" />
              <span>Dead-Stock Break-Even Studio</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Zero-loss promo guardrail + mr-IN / hi-IN link attribution
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-paytm-bg text-paytm-navy border border-paytm-border">
            Margin Guard
          </span>
        </div>

        {deadStockLoading && deadStockItems.length === 0 ? (
          <div className="py-3 text-center text-xs text-slate-500">
            Scanning inventory for slow-moving SKUs...
          </div>
        ) : !selectedDeadStock ? (
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs text-emerald-800">
            No dead-stock items (&gt;15 days unsold) detected.
          </div>
        ) : (
          <div className="space-y-3">
            {/* Primary Dead-Stock SKU Summary */}
            <div className="rounded-xl bg-paytm-bg border border-paytm-border p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-xs font-extrabold text-paytm-navy">
                    {selectedDeadStock.sku_name}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {selectedDeadStock.days_unsold} days unsold • {selectedDeadStock.current_stock}{' '}
                    {selectedDeadStock.unit} in stock
                  </div>
                </div>
                <div className="text-right text-[11px] tabular-nums">
                  <div className="text-slate-500">
                    Cost: <strong className="text-slate-800">{formatInr(selectedDeadStock.unit_cost)}</strong>
                  </div>
                  <div className="text-slate-500">
                    MRP: <strong className="text-paytm-navy">{formatInr(selectedDeadStock.selling_price)}</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Discount Slider + Presets */}
            <div className="rounded-xl border border-paytm-border p-3 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <label
                  htmlFor="dead-stock-discount-slider"
                  className="text-xs font-bold text-paytm-navy"
                >
                  Proposed Discount: <span className="text-paytm-cyan">{formatInr(discountRupees)}</span>
                </label>
                <span className="text-[11px] font-semibold text-slate-500 tabular-nums">
                  Max safe margin: {formatInr(selectedDeadStock.current_margin_per_unit)}
                </span>
              </div>

              <input
                id="dead-stock-discount-slider"
                type="range"
                min={5}
                max={35}
                step={1}
                value={discountRupees}
                aria-label="Dead-stock discount in rupees"
                onChange={(e) => handleDiscountSliderChange(Number(e.target.value))}
                className="w-full accent-paytm-navy cursor-pointer"
              />

              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  disabled={testingCampaign}
                  onClick={() => handleDiscountSliderChange(10)}
                  className="min-h-[36px] px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 text-[11px] font-bold"
                >
                  ₹10 Safe
                </button>
                <button
                  type="button"
                  disabled={testingCampaign}
                  onClick={() => handleDiscountSliderChange(25)}
                  className="min-h-[36px] px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-800 text-[11px] font-bold"
                >
                  ₹25 Loss Test
                </button>
                <button
                  type="button"
                  disabled={testingCampaign}
                  onClick={() =>
                    void evaluateDeadStockDiscount(selectedDeadStock.item_id, discountRupees)
                  }
                  className="min-h-[36px] ml-auto px-3 py-1 rounded-lg bg-paytm-navy text-white text-[11px] font-bold flex items-center gap-1 disabled:opacity-50"
                >
                  {testingCampaign && <Loader2 className="w-3 h-3 animate-spin" />}
                  <span>Test Offer Math</span>
                </button>
              </div>
            </div>

            {deadStockError && (
              <div
                role="alert"
                className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800"
              >
                {deadStockError}
              </div>
            )}

            {/* Hard Stop Loss-Making Guardrail Banner */}
            {campaignResult && campaignResult.status === 'OFFER_BLOCKED_LOSS_MAKING' && (
              <div
                role="alert"
                aria-label="Loss-making offer blocked"
                className="rounded-xl bg-[#FEF2F2] border-2 border-[#E11D48] p-3.5 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <AlertOctagon className="w-5 h-5 text-[#E11D48] shrink-0" />
                  <span className="text-[11px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#E11D48] text-white">
                    OFFER_BLOCKED_LOSS_MAKING
                  </span>
                </div>
                <p className="text-xs font-bold text-rose-950">
                  {campaignResult.reason ||
                    `Discount of ${formatInr(campaignResult.proposed_discount)} drops selling price below wholesale cost.`}
                </p>
                <div className="rounded-lg bg-white/90 border border-rose-200 px-2.5 py-2 text-[11px] text-rose-900 tabular-nums">
                  Margin Delta: {formatInr(campaignResult.math_audit.old_margin_per_unit)} →{' '}
                  <strong>{formatInr(campaignResult.math_audit.new_margin_per_unit)}</strong> •{' '}
                  {campaignResult.math_audit.verdict}
                </div>
              </div>
            )}

            {/* Safe Break-Even Math Output */}
            {campaignResult && campaignResult.status === 'CAMPAIGN_READY' && (
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#059669] text-white">
                    CAMPAIGN READY • {campaignResult.math_audit.verdict}
                  </span>
                  {campaignResult.discounted_price !== undefined && (
                    <span className="text-xs font-extrabold text-paytm-navy tabular-nums">
                      Promo Price: {formatInr(campaignResult.discounted_price)}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-white border border-emerald-200 p-2">
                    <div className="text-[10px] text-slate-500 font-semibold">Margin Delta</div>
                    <div className="text-xs font-extrabold text-paytm-navy tabular-nums">
                      {formatInr(campaignResult.math_audit.old_margin_per_unit)} →{' '}
                      {formatInr(campaignResult.math_audit.new_margin_per_unit)}
                    </div>
                  </div>
                  <div className="rounded-lg bg-white border border-emerald-200 p-2">
                    <div className="text-[10px] text-slate-500 font-semibold">Break-Even</div>
                    <div className="text-xs font-extrabold text-emerald-700 tabular-nums">
                      {campaignResult.math_audit.breakeven_daily_sales_needed ?? 0}/day
                    </div>
                  </div>
                  <div className="rounded-lg bg-white border border-emerald-200 p-2">
                    <div className="text-[10px] text-slate-500 font-semibold">Extra Needed</div>
                    <div className="text-xs font-extrabold text-paytm-navy tabular-nums">
                      +{campaignResult.math_audit.extra_units_needed_per_day ?? 0}/day
                    </div>
                  </div>
                </div>

                <WhyAmISeeingThis
                  summary={`Break-even protects baseline profit (${campaignResult.math_audit.usual_daily_sales} units/day × ${formatInr(campaignResult.math_audit.old_margin_per_unit)}).`}
                  formula="ceil((V_base * M_old) / M_new)"
                  beforeLabel={`${formatInr(campaignResult.math_audit.old_margin_per_unit)}/unit`}
                  afterLabel={`${formatInr(campaignResult.math_audit.new_margin_per_unit)}/unit`}
                  source={`KiranaOS Break-Even Engine (${campaignResult.sku_name})`}
                  badgeText="Zero LLM Math"
                  evidence={campaignResult.math_audit}
                />
              </div>
            )}

            {/* Side-by-side mr-IN vs hi-IN Attribution Cards */}
            {activePromoLinks.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {activePromoLinks.map((lnk) => {
                  const maxClicks = Math.max(
                    1,
                    ...activePromoLinks.map((item) => Math.max(item.clicks, item.conversions, 1)),
                  );
                  const barPct = Math.min(100, Math.round((lnk.clicks / maxClicks) * 100));
                  return (
                    <div
                      key={lnk.slug}
                      className="rounded-xl bg-paytm-bg border border-paytm-border p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-1.5">
                        <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-paytm-navy text-white">
                          {lnk.language}
                        </span>
                        <span className="text-[11px] font-bold text-emerald-700 tabular-nums">
                          {formatInr(lnk.revenue_collected ?? lnk.revenue)}
                        </span>
                      </div>

                      <div className="text-[11px] font-mono font-bold text-paytm-navy truncate">
                        {lnk.link}
                      </div>

                      <div className="text-[11px] text-slate-600 tabular-nums flex items-center justify-between">
                        <span>Clicks: {lnk.clicks}</span>
                        <span>Redemptions: {lnk.redemptions}</span>
                      </div>

                      <div className="w-full h-1.5 rounded-full bg-slate-200 overflow-hidden">
                        <div
                          className="h-full bg-paytm-cyan rounded-full transition-all"
                          style={{ width: `${barPct}%` }}
                        />
                      </div>

                      <button
                        type="button"
                        disabled={simulatingSlug !== null}
                        onClick={() => void handleSimulatePromoClick(lnk)}
                        className="min-h-[36px] w-full rounded-lg bg-white hover:bg-paytm-cyan/10 border border-paytm-border text-paytm-navy text-[11px] font-bold flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        {simulatingSlug === lnk.slug ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Sparkles className="w-3 h-3 text-paytm-cyan" />
                        )}
                        <span>Simulate Click/Buy</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Section C: 60-Second Dukaan Closing Ritual Card */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <Flame className="w-4 h-4 text-amber-500" />
              <span>60-Second Dukaan Closing Ritual</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Live EOD summary + 3.5× Diwali seasonal demand forecast
            </p>
          </div>
          <button
            type="button"
            disabled={ritualLoading}
            onClick={() => void handleRunClosingRitual()}
            className="min-h-[36px] px-2.5 rounded-xl bg-paytm-navy text-white text-[11px] font-bold flex items-center gap-1 shrink-0 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-paytm-cyan ${ritualLoading ? 'animate-spin' : ''}`} />
            <span>Run 60s Closing Ritual</span>
          </button>
        </div>

        {ritualError && (
          <div className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800">
            {ritualError}
          </div>
        )}

        {ritualLoading && !closingRitual ? (
          <div className="py-4 text-center text-xs text-slate-500">
            Aggregating today&apos;s QR sales &amp; Diwali restock forecast...
          </div>
        ) : closingRitual ? (
          <div className="space-y-3">
            {/* 3 Crisp KPI Pills */}
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-xl bg-paytm-bg border border-paytm-border p-2.5 text-center">
                <div className="text-[10px] font-bold text-slate-500">Today&apos;s QR</div>
                <div className="text-xs font-extrabold text-paytm-navy tabular-nums mt-0.5">
                  {formatInr(closingRitual.today_qr_sales)}
                </div>
              </div>
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-2.5 text-center">
                <div className="text-[10px] font-bold text-emerald-700">Udhaar Recovered</div>
                <div className="text-xs font-extrabold text-emerald-900 tabular-nums mt-0.5">
                  {formatInr(closingRitual.today_udhaar_recovered)}
                </div>
              </div>
              <div className="rounded-xl bg-amber-50 border border-amber-200 p-2.5 text-center">
                <div className="text-[10px] font-bold text-amber-800">Pending UPI</div>
                <div className="text-xs font-extrabold text-amber-950 tabular-nums mt-0.5">
                  {closingRitual.unmatched_upi_count}
                </div>
              </div>
            </div>

            {/* 3.5x Diwali Restock Alert Card */}
            <div className="rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-300 p-3 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500 text-white">
                    {closingRitual.festive_restock_forecast.festive_surge_multiplier}×{' '}
                    {closingRitual.festive_restock_forecast.upcoming_event}
                  </span>
                  <h3 className="text-xs font-extrabold text-paytm-navy mt-1.5">
                    {closingRitual.festive_restock_forecast.sku_name}
                  </h3>
                  <p className="text-[11px] text-amber-950 mt-0.5 tabular-nums">
                    Only {closingRitual.festive_restock_forecast.current_stock}{' '}
                    {closingRitual.festive_restock_forecast.unit} left • 5-day surge demand:{' '}
                    <strong>
                      {closingRitual.festive_restock_forecast.projected_5day_demand}{' '}
                      {closingRitual.festive_restock_forecast.unit}
                    </strong>
                  </p>
                </div>

                <div className="rounded-xl bg-white border border-amber-300 px-2.5 py-1.5 text-center shrink-0">
                  <div className="text-[9px] font-bold uppercase text-amber-700">Order Qty</div>
                  <div className="text-sm font-extrabold text-paytm-navy tabular-nums">
                    {closingRitual.festive_restock_forecast.recommended_order_qty}{' '}
                    {closingRitual.festive_restock_forecast.unit}
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-white/90 border border-amber-200 px-2.5 py-2 text-[11px] text-slate-700">
                <strong className="text-paytm-navy">
                  {closingRitual.festive_restock_forecast.supplier_name}:
                </strong>{' '}
                {closingRitual.festive_restock_forecast.one_tap_order_draft}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() =>
                    void playSoundboxAudio({
                      audioBase64: closingRitual.tts_audio_base64,
                      announcement: closingRitual.spoken_ritual_hi,
                      sourceLabel: 'Diwali EOD Ritual',
                    })
                  }
                  className="min-h-[40px] rounded-xl bg-paytm-navy text-white text-xs font-bold flex items-center justify-center gap-1.5"
                >
                  <Volume2 className="w-4 h-4 text-paytm-cyan" />
                  <span>Play 60s Briefing</span>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    void handleCopyOrderDraft(
                      closingRitual.festive_restock_forecast.one_tap_order_draft,
                    )
                  }
                  className="min-h-[40px] rounded-xl bg-white hover:bg-amber-100/60 border border-amber-300 text-paytm-navy text-xs font-bold flex items-center justify-center gap-1.5"
                >
                  {copiedDraft ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <ClipboardCopy className="w-4 h-4 text-amber-700" />
                      <span>Copy Order Draft</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <WhyAmISeeingThis
              summary={closingRitual.spoken_ritual_hi}
              formula={closingRitual.why_am_i_seeing_this.formula}
              beforeLabel={`${closingRitual.festive_restock_forecast.current_stock} ${closingRitual.festive_restock_forecast.unit} stock`}
              afterLabel={`Order ${closingRitual.festive_restock_forecast.recommended_order_qty} ${closingRitual.festive_restock_forecast.unit}`}
              source={closingRitual.why_am_i_seeing_this.source}
              badgeText="Diwali Forecast"
              evidence={closingRitual.why_am_i_seeing_this}
            />
          </div>
        ) : null}
      </section>

      {/* Section D: Handwritten Bahi-Khata Notebook Scanner */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-paytm-cyan" />
              <span>Handwritten Bahi-Khata Scanner</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Digitize paper notebook pages with 1-tap editable batch onboarding
            </p>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-paytm-bg text-paytm-navy border border-paytm-border">
            Vision OCR
          </span>
        </div>

        <div className="grid grid-cols-1 gap-2">
          <button
            type="button"
            disabled={scanningBahi}
            onClick={() => void handleScanSampleBahi()}
            className="min-h-[44px] w-full rounded-xl bg-paytm-navy hover:bg-paytm-navyDark text-white px-3.5 py-2 text-xs font-bold flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            {scanningBahi ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <BookOpen className="w-4 h-4 text-paytm-cyan" />
            )}
            <span>Scan Sample Notebook Page</span>
          </button>

          <label className="min-h-[44px] w-full rounded-xl border border-dashed border-paytm-cyan bg-paytm-cyan/5 hover:bg-paytm-cyan/10 text-paytm-navy px-3.5 py-2 text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-colors">
            <Camera className="w-4 h-4 text-paytm-cyan" />
            <span>Upload Custom Notebook Photo</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              aria-label="Upload Custom Notebook Photo"
              onChange={(e) => void handleBahiFileUpload(e)}
              className="sr-only"
            />
          </label>
        </div>

        {bahiPreview && (
          <div className="rounded-xl bg-paytm-bg border border-paytm-border p-2.5 flex items-center gap-2.5">
            {bahiPreview.url ? (
              <img
                src={bahiPreview.url}
                alt={`Preview of ${bahiPreview.name}`}
                className="w-12 h-12 rounded-lg object-cover border border-paytm-border shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-white border border-paytm-border flex items-center justify-center shrink-0">
                <Camera className="w-5 h-5 text-paytm-cyan" />
              </div>
            )}
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase text-slate-400">
                Custom Bahi-Khata Photo
              </div>
              <div className="text-xs font-semibold text-paytm-navy truncate">
                {bahiPreview.name}
              </div>
            </div>
          </div>
        )}

        {bahiError && (
          <div
            role="alert"
            className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800"
          >
            {bahiError}
          </div>
        )}

        {bahiNotice && (
          <div
            role="status"
            className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs text-emerald-900 flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{bahiNotice}</span>
          </div>
        )}

        {bahiScan && (
          <div className="space-y-2.5 pt-2 border-t border-paytm-border">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="font-bold text-paytm-navy">{bahiScan.page_title}</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-paytm-bg border border-paytm-border text-slate-700">
                {editableRows.length} rows •{' '}
                {formatInr(editableRows.reduce((sum, r) => sum + (Number(r.amount) || 0), 0))}
              </span>
            </div>

            <div className="space-y-2">
              {editableRows.map((row) => (
                <div
                  key={row.row_index}
                  className="rounded-xl bg-paytm-bg border border-paytm-border p-2.5 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                        row.match_status === 'EXISTING_CUSTOMER'
                          ? 'bg-emerald-100 text-emerald-800'
                          : row.match_status === 'AMBIGUOUS'
                            ? 'bg-amber-100 text-amber-900'
                            : 'bg-sky-100 text-sky-800'
                      }`}
                    >
                      {row.match_status}
                    </span>

                    <button
                      type="button"
                      onClick={() => removeEditableRow(row.row_index)}
                      aria-label={`Remove row ${row.customer_name}`}
                      className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      value={row.customer_name}
                      onChange={(e) =>
                        updateEditableRow(row.row_index, { customer_name: e.target.value })
                      }
                      aria-label={`Customer name row ${row.row_index}`}
                      placeholder="Customer Name"
                      className="min-h-[36px] rounded-lg border border-paytm-border bg-white px-2.5 text-xs font-semibold text-paytm-navy"
                    />
                    <input
                      type="number"
                      min={1}
                      step="1"
                      value={Number.isFinite(row.amount) ? row.amount : ''}
                      onChange={(e) =>
                        updateEditableRow(row.row_index, {
                          amount: e.target.value === '' ? 0 : Number(e.target.value),
                        })
                      }
                      aria-label={`Amount row ${row.row_index}`}
                      placeholder="Amount ₹"
                      className="min-h-[36px] rounded-lg border border-paytm-border bg-white px-2.5 text-xs font-bold text-paytm-navy tabular-nums"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      value={row.phone}
                      onChange={(e) => updateEditableRow(row.row_index, { phone: e.target.value })}
                      aria-label={`Phone row ${row.row_index}`}
                      placeholder="Phone (optional)"
                      className="min-h-[36px] rounded-lg border border-paytm-border bg-white px-2.5 text-[11px] text-slate-700"
                    />
                    <select
                      value={row.preferred_language}
                      onChange={(e) =>
                        updateEditableRow(row.row_index, { preferred_language: e.target.value })
                      }
                      aria-label={`Language row ${row.row_index}`}
                      className="min-h-[36px] rounded-lg border border-paytm-border bg-white px-2 text-[11px] font-semibold text-slate-700"
                    >
                      <option value="hi-IN">hi-IN (Hindi)</option>
                      <option value="mr-IN">mr-IN (Marathi)</option>
                      <option value="en-IN">en-IN (English)</option>
                    </select>
                  </div>

                  {row.match_status === 'AMBIGUOUS' && row.candidate_customers.length > 0 && (
                    <select
                      value={row.matched_customer_id ?? ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        updateEditableRow(row.row_index, {
                          matched_customer_id: val ? Number(val) : null,
                        });
                      }}
                      aria-label={`Resolve candidate for row ${row.row_index}`}
                      className="w-full min-h-[36px] rounded-lg border border-amber-300 bg-amber-50 px-2.5 text-[11px] font-semibold text-amber-950"
                    >
                      <option value="">Select matching customer...</option>
                      {row.candidate_customers.map((cand) => (
                        <option key={cand.customer_id} value={cand.customer_id}>
                          {cand.name} ({cand.phone ?? 'No phone'} • Bal{' '}
                          {formatInr(cand.existing_balance)})
                        </option>
                      ))}
                    </select>
                  )}

                  {row.notes && (
                    <div className="text-[11px] text-slate-500 italic">{row.notes}</div>
                  )}
                </div>
              ))}
            </div>

            {editableRows.length > 0 && (
              <button
                type="button"
                disabled={confirmingBahi}
                onClick={() => void handleConfirmBahiKhata()}
                className="min-h-[44px] w-full rounded-xl bg-[#059669] hover:bg-emerald-700 text-white px-4 py-2 text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {confirmingBahi ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <UserPlus className="w-4 h-4" />
                )}
                <span>
                  Confirm &amp; Onboard All ({editableRows.length})
                </span>
              </button>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
