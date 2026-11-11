import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  History,
  Loader2,
  Mic,
  MicOff,
  Send,
  ShieldCheck,
  UserCheck,
  Volume2,
  X,
} from 'lucide-react';
import { kiranaClient } from '../../api/kiranaClient';
import type {
  CustomerCandidate,
  CustomerLedgerResponse,
  CustomerSummary,
  DialectLabel,
  LanguageCode,
  UnmatchedPayment,
  VoiceProposeResponse,
} from '../../types/kirana';
import { playSoundboxAudio } from '../../utils/soundboxAudio';
import { WhyAmISeeingThis } from '../WhyAmISeeingThis';

export interface MunimMicTabProps {
  languageHint: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  activeProposal: VoiceProposeResponse | null;
  onProposalChange: (p: VoiceProposeResponse | null) => void;
  refreshToken: number;
  onDataMutated: () => void;
}

const LANGUAGE_PILLS: Array<{ label: DialectLabel; badge: string; code: LanguageCode }> = [
  { label: 'Hinglish', badge: 'hi-IN', code: 'hi-IN' },
  { label: 'Marathi', badge: 'mr-IN', code: 'mr-IN' },
  { label: 'Hindi', badge: 'hi-IN', code: 'hi-IN' },
];

const QUICK_CHIPS = [
  'Suresh ka 200 rupaye udhaar likh do',
  'Ramesh ne 300 rupaye jama kiye',
  'Amul Ghee 5 tin aaya',
];

function formatInr(value: number): string {
  return `₹${value.toLocaleString('en-IN', {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`;
}

export function MunimMicTab({
  languageHint,
  onLanguageChange,
  activeProposal,
  onProposalChange,
  refreshToken,
  onDataMutated,
}: MunimMicTabProps) {
  const [selectedDialect, setSelectedDialect] = useState<DialectLabel>(
    languageHint === 'mr-IN' ? 'Marathi' : 'Hinglish',
  );
  const [commandText, setCommandText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<{
    tone: 'success' | 'error';
    text: string;
  } | null>(null);

  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [customersLoading, setCustomersLoading] = useState(true);
  const [unmatchedPayments, setUnmatchedPayments] = useState<UnmatchedPayment[]>([]);
  const [resolvingQueueId, setResolvingQueueId] = useState<number | null>(null);

  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);
  const [ledgerData, setLedgerData] = useState<CustomerLedgerResponse | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerError, setLedgerError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  useEffect(() => {
    if (languageHint === 'mr-IN' && selectedDialect !== 'Marathi') {
      setSelectedDialect('Marathi');
    } else if (languageHint === 'hi-IN' && selectedDialect === 'Marathi') {
      setSelectedDialect('Hinglish');
    }
  }, [languageHint, selectedDialect]);

  const loadShopData = useCallback(async () => {
    setCustomersLoading(true);
    try {
      const [custRes, upiRes] = await Promise.all([
        kiranaClient.listCustomers(),
        kiranaClient.getUnmatchedPayments(),
      ]);
      if (Array.isArray(custRes)) {
        setCustomers(custRes);
      }
      setUnmatchedPayments(
        Array.isArray(upiRes) ? upiRes.filter((item) => item.status === 'PENDING_REVIEW') : [],
      );
    } catch {
      // Keep previous list if backend is temporarily unreachable
    } finally {
      setCustomersLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadShopData();
  }, [loadShopData, refreshToken]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // Ignore recorder teardown issues
        }
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const submitTextCommand = async (rawText: string) => {
    const trimmed = rawText.trim();
    if (!trimmed || proposing) return;
    setMicError(null);
    setActionBanner(null);
    setProposing(true);
    try {
      const proposal = await kiranaClient.proposeVoiceCommand({
        transcriptOverride: trimmed,
        languageHint,
      });
      onProposalChange(proposal);
      setCommandText('');
      if (proposal.tts_audio_base64 || proposal.spoken_prompt_hi) {
        void playSoundboxAudio({
          audioBase64: proposal.tts_audio_base64,
          announcement: proposal.spoken_prompt_hi || proposal.raw_transcript,
          sourceLabel: 'Bulbul v3 Proposal',
        });
      }
    } catch (err: unknown) {
      setMicError(err instanceof Error ? err.message : 'Unable to parse command.');
    } finally {
      setProposing(false);
    }
  };

  const handleToggleMic = async () => {
    if (proposing) return;
    setMicError(null);
    setActionBanner(null);

    if (isRecording && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      return;
    }

    if (
      typeof navigator === 'undefined' ||
      !navigator.mediaDevices ||
      typeof navigator.mediaDevices.getUserMedia !== 'function' ||
      typeof MediaRecorder === 'undefined'
    ) {
      setMicError('Mic recording is unavailable here. Use the Hinglish/Marathi command bar below.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        const audioBlob = new Blob(chunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        chunksRef.current = [];

        if (audioBlob.size === 0) {
          setMicError('No audio captured. Try speaking again or type your command below.');
          return;
        }

        setProposing(true);
        try {
          const proposal = await kiranaClient.proposeVoiceCommand({
            audioBlob,
            filename: 'munim-voice.webm',
            languageHint,
          });
          onProposalChange(proposal);
          if (proposal.tts_audio_base64 || proposal.spoken_prompt_hi) {
            void playSoundboxAudio({
              audioBase64: proposal.tts_audio_base64,
              announcement: proposal.spoken_prompt_hi || proposal.raw_transcript,
              sourceLabel: 'Bulbul v3 Proposal',
            });
          }
        } catch (err: unknown) {
          setMicError(err instanceof Error ? err.message : 'Voice upload failed. Type command below.');
        } finally {
          setProposing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setMicError('Microphone permission denied. Type your Hinglish/Marathi command below.');
      setIsRecording(false);
    }
  };

  const handleConfirmProposal = async (candidateOverride?: CustomerCandidate) => {
    if (!activeProposal || confirming) return;
    setConfirming(true);
    setActionBanner(null);

    const targetCustomerId =
      candidateOverride?.customer_id ?? activeProposal.customer_id ?? activeProposal.customer?.id;

    try {
      const res = await kiranaClient.confirmVoiceProposal({
        proposal_id: candidateOverride ? undefined : activeProposal.proposal_id,
        action: 'APPROVE',
        intent: activeProposal.intent,
        customer_id: targetCustomerId,
        amount: activeProposal.extracted_amount ?? undefined,
        item_id: activeProposal.item_id,
        quantity_delta: activeProposal.quantity_delta,
        source_utterance: activeProposal.raw_transcript,
        language_hint: languageHint,
      });

      await playSoundboxAudio({
        audioBase64: res.tts_audio_base64,
        announcement: res.spoken_confirmation,
        sourceLabel: 'Bulbul v3 Confirmation',
      });

      setActionBanner({
        tone: 'success',
        text: res.spoken_confirmation || 'Entry committed to KiranaOS ledger.',
      });
      onProposalChange(null);
      await loadShopData();
      onDataMutated();
    } catch (err: unknown) {
      setActionBanner({
        tone: 'error',
        text: err instanceof Error ? err.message : 'Failed to commit proposal.',
      });
    } finally {
      setConfirming(false);
    }
  };

  const handleResolveUpi = async (item: UnmatchedPayment, cand: CustomerCandidate) => {
    if (resolvingQueueId !== null) return;
    setResolvingQueueId(item.id);
    setActionBanner(null);
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
      setActionBanner({
        tone: 'success',
        text: `Linked ${formatInr(res.amount)} (${item.upi_txn_id}) to ${res.customer_name}.`,
      });
      await loadShopData();
      onDataMutated();
    } catch (err: unknown) {
      setActionBanner({
        tone: 'error',
        text: err instanceof Error ? err.message : 'Unable to resolve unmatched UPI.',
      });
    } finally {
      setResolvingQueueId(null);
    }
  };

  const handleInspectCustomer = async (customer: CustomerSummary) => {
    setSelectedCustomer(customer);
    setLedgerLoading(true);
    setLedgerError(null);
    try {
      const data = await kiranaClient.getCustomerLedger(customer.id);
      setLedgerData(data);
    } catch (err: unknown) {
      setLedgerError(err instanceof Error ? err.message : 'Unable to load customer ledger.');
      setLedgerData(null);
    } finally {
      setLedgerLoading(false);
    }
  };

  return (
    <div className="space-y-3" data-testid="munim-mic-tab">
      {/* Voice & Text Command Center */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy">Bolke Khata Likhein</h2>
            <p className="text-[11px] text-slate-500">
              Sarvam Saaras Voice • Zero Blind Writes
            </p>
          </div>

          {/* Language Toggle Pills */}
          <div
            className="inline-flex rounded-full bg-paytm-bg p-0.5 border border-paytm-border"
            role="group"
            aria-label="Voice command language"
          >
            {LANGUAGE_PILLS.map((pill) => {
              const active = selectedDialect === pill.label;
              return (
                <button
                  key={pill.label}
                  type="button"
                  onClick={() => {
                    setSelectedDialect(pill.label);
                    onLanguageChange(pill.code);
                  }}
                  className={`px-2 py-1 rounded-full text-[10px] font-semibold transition-colors ${
                    active
                      ? 'bg-paytm-navy text-white shadow-sm'
                      : 'text-slate-600 hover:text-paytm-navy'
                  }`}
                >
                  {pill.label} <span className="opacity-70">{pill.badge}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Pulsing Sarvam Mic Button */}
        <div className="mt-4 flex flex-col items-center">
          <div className="relative flex items-center justify-center">
            {(isRecording || proposing) && (
              <span
                aria-hidden="true"
                className="absolute inset-0 rounded-full bg-paytm-cyan/30 animate-ping"
              />
            )}
            <button
              type="button"
              onClick={() => void handleToggleMic()}
              disabled={proposing}
              aria-label={isRecording ? 'Stop voice recording' : 'Start Sarvam voice mic'}
              className={`relative min-h-[64px] min-w-[64px] w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95 ${
                isRecording
                  ? 'bg-rose-600 text-white ring-4 ring-rose-200'
                  : 'bg-gradient-to-br from-paytm-navy to-paytm-cyan text-white ring-4 ring-paytm-cyan/20 hover:brightness-105'
              }`}
            >
              {proposing ? (
                <Loader2 className="w-7 h-7 animate-spin" />
              ) : isRecording ? (
                <MicOff className="w-7 h-7" />
              ) : (
                <Mic className="w-7 h-7" />
              )}
            </button>
          </div>
          <span className="mt-2 text-xs font-semibold text-paytm-navy">
            {proposing
              ? 'Parsing with KiranaOS...'
              : isRecording
                ? 'Recording... Tap to send audio'
                : 'Tap Mic to speak or type command below'}
          </span>
        </div>

        {micError && (
          <div
            role="alert"
            className="mt-3 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900"
          >
            {micError}
          </div>
        )}

        {/* Hinglish / Marathi Text Command Input */}
        <form
          className="mt-3 flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void submitTextCommand(commandText);
          }}
        >
          <input
            type="text"
            value={commandText}
            onChange={(e) => setCommandText(e.target.value)}
            placeholder="e.g., Suresh ka 200 rupaye udhaar likh do"
            aria-label="Hinglish or Marathi command input"
            className="flex-1 min-h-[44px] rounded-xl border border-paytm-border bg-paytm-bg px-3 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-paytm-cyan"
          />
          <button
            type="submit"
            disabled={proposing || !commandText.trim()}
            aria-label="Send command"
            className="min-h-[44px] min-w-[44px] px-3.5 rounded-xl bg-paytm-navy text-white text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>Propose</span>
          </button>
        </form>

        {/* Quick Example Chips */}
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {QUICK_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              disabled={proposing}
              onClick={() => void submitTextCommand(chip)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-paytm-bg hover:bg-paytm-cyan/15 border border-paytm-border text-paytm-navy font-medium transition-colors text-left"
            >
              “{chip}”
            </button>
          ))}
        </div>
      </section>

      {/* Action Confirmation Feedback Banner */}
      {actionBanner && (
        <div
          role="status"
          className={`rounded-2xl px-3.5 py-2.5 border text-xs font-medium flex items-center justify-between gap-2 ${
            actionBanner.tone === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionBanner.text}</span>
          </span>
          <button
            type="button"
            onClick={() => setActionBanner(null)}
            aria-label="Dismiss notification"
            className="p-1 rounded-lg hover:bg-black/5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Active Propose -> Confirm -> Commit Gate Card */}
      {activeProposal && activeProposal.status === 'NEEDS_DISAMBIGUATION' && (
        <section
          aria-label="Identity disambiguation required"
          className="rounded-2xl bg-[#FFFBEB] border-2 border-[#D97706] p-4 shadow-sm space-y-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-[#D97706] shrink-0 mt-0.5" />
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-200/80 text-amber-950">
                    NEEDS DISAMBIGUATION
                  </span>
                  {activeProposal.extracted_amount !== null &&
                    activeProposal.extracted_amount !== undefined && (
                      <span className="text-xs font-extrabold text-paytm-navy tabular-nums">
                        {formatInr(activeProposal.extracted_amount)}
                      </span>
                    )}
                </div>
                <p className="mt-1 text-xs font-semibold text-amber-950">
                  {activeProposal.ambiguity_reason ||
                    `Multiple customers match "${activeProposal.extracted_name ?? ''}". Tap the exact customer to commit.`}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() =>
                void playSoundboxAudio({
                  audioBase64: activeProposal.tts_audio_base64,
                  announcement:
                    activeProposal.spoken_prompt_hi ||
                    activeProposal.ambiguity_reason ||
                    'Please select customer',
                  sourceLabel: 'Bulbul v3 Disambiguation',
                })
              }
              className="min-h-[36px] px-2.5 rounded-xl bg-amber-100 hover:bg-amber-200 text-amber-950 text-[11px] font-bold flex items-center gap-1 shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5" />
              <span>Listen</span>
            </button>
          </div>

          <div className="space-y-2">
            {(activeProposal.candidates ?? []).map((cand) => (
              <button
                key={cand.customer_id}
                type="button"
                disabled={confirming}
                onClick={() => void handleConfirmProposal(cand)}
                className="w-full min-h-[52px] rounded-xl bg-white hover:bg-emerald-50 border border-amber-300 hover:border-emerald-400 px-3 py-2.5 flex items-center justify-between gap-2 text-left transition-colors disabled:opacity-50"
              >
                <div className="min-w-0">
                  <div className="text-xs font-bold text-paytm-navy flex items-center gap-1.5">
                    <UserCheck className="w-3.5 h-3.5 text-paytm-cyan shrink-0" />
                    <span className="truncate">{cand.name}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {cand.phone ?? 'No phone'} • Last visit: {cand.last_visit}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-bold text-slate-800 tabular-nums">
                    {formatInr(cand.current_udhaar)}
                  </div>
                  <div className="text-[10px] font-semibold text-emerald-700">Tap to Confirm</div>
                </div>
              </button>
            ))}
          </div>

          <WhyAmISeeingThis
            summary={activeProposal.why_am_i_seeing_this}
            source={activeProposal.raw_transcript}
            badgeText="Identity Guard"
            evidence={{
              intent: activeProposal.intent,
              extracted_amount: activeProposal.extracted_amount,
              candidates: activeProposal.candidates ?? [],
            }}
          />

          <button
            type="button"
            disabled={confirming}
            onClick={() => onProposalChange(null)}
            className="w-full min-h-[44px] rounded-xl border border-amber-300 bg-white text-xs font-semibold text-slate-700 hover:bg-amber-100/50"
          >
            Cancel Proposal
          </button>
        </section>
      )}

      {activeProposal && activeProposal.status === 'PROPOSAL' && (
        <section
          aria-label="Confirm voice proposal"
          className="rounded-2xl bg-white border border-paytm-border border-t-4 border-t-paytm-cyan p-4 shadow-sm space-y-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-paytm-cyan/15 text-paytm-navy">
                  {activeProposal.intent}
                </span>
                <span className="text-[10px] font-semibold text-slate-500">
                  Awaiting Merchant Approval
                </span>
              </div>
              <h3 className="mt-1 text-sm font-bold text-paytm-navy">
                {activeProposal.customer_name ||
                  activeProposal.customer?.name ||
                  activeProposal.sku_name ||
                  'KiranaOS Proposal'}
              </h3>
            </div>

            <button
              type="button"
              onClick={() =>
                void playSoundboxAudio({
                  audioBase64: activeProposal.tts_audio_base64,
                  announcement: activeProposal.spoken_prompt_hi || activeProposal.raw_transcript,
                  sourceLabel: 'Bulbul v3 Preview',
                })
              }
              className="min-h-[36px] px-2.5 rounded-xl bg-paytm-bg hover:bg-slate-200 text-paytm-navy text-[11px] font-bold flex items-center gap-1 shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5 text-paytm-cyan" />
              <span>Preview</span>
            </button>
          </div>

          {/* Before -> After Transition Box */}
          <div className="rounded-xl bg-paytm-bg border border-paytm-border p-3 flex items-center justify-between gap-2">
            {activeProposal.current_balance !== undefined &&
            activeProposal.new_balance !== undefined ? (
              <>
                <div>
                  <div className="text-[10px] font-bold uppercase text-slate-400">
                    Current Balance
                  </div>
                  <div className="text-sm font-bold text-slate-700 tabular-nums">
                    {formatInr(activeProposal.current_balance)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] font-bold text-paytm-cyan">
                    {activeProposal.intent === 'REPAYMENT_JAMA' ? '−' : '+'}
                    {formatInr(activeProposal.extracted_amount ?? 0)}
                  </div>
                  <div className="text-xs text-slate-400">→</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] font-bold uppercase text-slate-400">New Balance</div>
                  <div className="text-sm font-extrabold text-paytm-navy tabular-nums">
                    {formatInr(activeProposal.new_balance)}
                  </div>
                </div>
              </>
            ) : (
              <>
                <div>
                  <div className="text-[10px] font-bold uppercase text-slate-400">
                    Current Stock
                  </div>
                  <div className="text-sm font-bold text-slate-700 tabular-nums">
                    {activeProposal.current_stock ?? 0}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] font-bold text-paytm-cyan">
                    {(activeProposal.quantity_delta ?? 0) >= 0 ? '+' : ''}
                    {activeProposal.quantity_delta ?? 0}
                  </div>
                  <div className="text-xs text-slate-400">→</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] font-bold uppercase text-slate-400">New Stock</div>
                  <div className="text-sm font-extrabold text-paytm-navy tabular-nums">
                    {activeProposal.new_stock ?? 0}
                  </div>
                </div>
              </>
            )}
          </div>

          <WhyAmISeeingThis
            summary={activeProposal.why_am_i_seeing_this}
            source={activeProposal.raw_transcript}
            beforeLabel={
              activeProposal.current_balance !== undefined
                ? formatInr(activeProposal.current_balance)
                : activeProposal.current_stock !== undefined
                  ? `${activeProposal.current_stock} units`
                  : undefined
            }
            afterLabel={
              activeProposal.new_balance !== undefined
                ? formatInr(activeProposal.new_balance)
                : activeProposal.new_stock !== undefined
                  ? `${activeProposal.new_stock} units`
                  : undefined
            }
            evidence={activeProposal}
          />

          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              type="button"
              disabled={confirming}
              onClick={() => onProposalChange(null)}
              className="min-h-[44px] rounded-xl border border-paytm-border bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={confirming}
              onClick={() => void handleConfirmProposal()}
              className="min-h-[44px] rounded-xl bg-[#059669] hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {confirming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ShieldCheck className="w-4 h-4" />
              )}
              <span>Approve (Haan)</span>
            </button>
          </div>
        </section>
      )}

      {activeProposal &&
        (activeProposal.status === 'CUSTOMER_NOT_FOUND' ||
          activeProposal.status === 'NOT_UNDERSTOOD') && (
          <section className="rounded-2xl bg-slate-50 border border-slate-300 p-4 space-y-2.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                  {activeProposal.status}
                </span>
                <p className="mt-1.5 text-xs font-semibold text-slate-800">
                  {activeProposal.spoken_prompt_hi || 'Could not match command to a customer or SKU.'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onProposalChange(null)}
                aria-label="Close guidance"
                className="p-1 text-slate-500 hover:text-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <WhyAmISeeingThis
              summary={activeProposal.why_am_i_seeing_this}
              source={activeProposal.raw_transcript}
              evidence={activeProposal}
            />
          </section>
        )}

      {/* Pending Ambiguous UPI Quick-Resolve Drawer */}
      {unmatchedPayments.length > 0 && (
        <section
          aria-label="Ambiguous UPI Pending"
          className="rounded-2xl bg-[#FFFBEB] border border-amber-300 p-3.5 shadow-sm space-y-2.5"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-extrabold text-amber-950 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-[#D97706]" />
              <span>Ambiguous UPI Pending ({unmatchedPayments.length})</span>
            </h3>
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-200/80 text-amber-950">
              1-Tap Resolve
            </span>
          </div>

          {unmatchedPayments.map((item) => (
            <div
              key={item.id}
              className="rounded-xl bg-white border border-amber-200 p-2.5 space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs font-bold text-paytm-navy truncate">
                    {item.payer_name} • {formatInr(item.amount)}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono truncate">
                    {item.upi_txn_id}
                  </div>
                </div>
                <span className="text-[10px] font-semibold text-amber-800 shrink-0">
                  {item.payer_vpa ?? 'QR Payment'}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.candidate_customers.map((cand) => (
                  <button
                    key={cand.customer_id}
                    type="button"
                    disabled={resolvingQueueId === item.id}
                    onClick={() => void handleResolveUpi(item, cand)}
                    className="min-h-[36px] px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-emerald-50 border border-amber-300 hover:border-emerald-400 text-[11px] font-semibold text-paytm-navy disabled:opacity-50"
                  >
                    Link {cand.name} ({formatInr(cand.current_udhaar)})
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {/* Live Customer Khata Strip */}
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-paytm-navy">Customer Khata</h3>
            <p className="text-[11px] text-slate-500">
              Tap any customer to inspect append-only ledger
            </p>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-paytm-bg text-paytm-navy tabular-nums">
            {customers.length} Accounts
          </span>
        </div>

        {customersLoading && customers.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500">Loading khata accounts...</div>
        ) : (
          <div className="space-y-2">
            {customers.map((cust) => (
              <button
                key={cust.id}
                type="button"
                onClick={() => void handleInspectCustomer(cust)}
                className="w-full min-h-[52px] rounded-xl bg-paytm-bg/70 hover:bg-paytm-cyan/10 border border-paytm-border px-3 py-2.5 flex items-center justify-between gap-2 text-left transition-colors"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-bold text-paytm-navy truncate">{cust.name}</span>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-white border border-paytm-border text-slate-600">
                      {cust.preferred_language}
                    </span>
                    {cust.days_overdue > 0 && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                        {cust.days_overdue}d overdue
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {cust.phone ?? 'No phone'} • Last visit: {cust.last_visit}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div
                    className={`text-xs font-extrabold tabular-nums ${
                      cust.outstanding_balance > 0 ? 'text-paytm-navy' : 'text-emerald-700'
                    }`}
                  >
                    {formatInr(cust.outstanding_balance)}
                  </div>
                  <div className="text-[10px] text-paytm-cyan font-semibold">Inspect →</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Customer Append-Only Ledger Sheet */}
      {selectedCustomer && (
        <section
          aria-label="Customer append-only ledger"
          className="rounded-2xl bg-white border-2 border-paytm-navy p-4 shadow-md space-y-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-paytm-cyan flex items-center gap-1">
                <History className="w-3.5 h-3.5" />
                <span>Append-Only Khata Ledger</span>
              </div>
              <h4 className="text-sm font-bold text-paytm-navy mt-0.5">
                {selectedCustomer.name}
              </h4>
            </div>
            <button
              type="button"
              onClick={() => {
                setSelectedCustomer(null);
                setLedgerData(null);
              }}
              aria-label="Close ledger sheet"
              className="min-h-[36px] min-w-[36px] rounded-xl bg-paytm-bg flex items-center justify-center text-slate-600 hover:text-paytm-navy"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {ledgerLoading ? (
            <div className="py-4 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-paytm-cyan" />
              <span>Loading deterministic ledger...</span>
            </div>
          ) : ledgerError ? (
            <div className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800">
              {ledgerError}
            </div>
          ) : ledgerData ? (
            <>
              <div className="grid grid-cols-3 gap-2 rounded-xl bg-paytm-bg border border-paytm-border p-2.5 text-center">
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold">Credit</div>
                  <div className="text-xs font-bold text-slate-800 tabular-nums">
                    {formatInr(ledgerData.total_credit)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold">Repaid</div>
                  <div className="text-xs font-bold text-emerald-700 tabular-nums">
                    {formatInr(ledgerData.total_repayment)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold">Net Balance</div>
                  <div className="text-xs font-extrabold text-paytm-navy tabular-nums">
                    {formatInr(ledgerData.net_outstanding_balance)}
                  </div>
                </div>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {ledgerData.ledger_entries.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-paytm-border px-3 py-2 text-xs flex items-start justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                            entry.entry_type === 'REPAYMENT_JAMA'
                              ? 'bg-emerald-50 text-emerald-700'
                              : entry.entry_type === 'REVERSAL_ADJUSTMENT'
                                ? 'bg-amber-50 text-amber-800'
                                : 'bg-rose-50 text-rose-700'
                          }`}
                        >
                          {entry.entry_type}
                        </span>
                        {entry.payment_mode && (
                          <span className="text-[10px] font-medium text-slate-500">
                            {entry.payment_mode}
                          </span>
                        )}
                      </div>
                      {entry.source_utterance && (
                        <p className="text-[11px] text-slate-600 mt-1 flex items-start gap-1">
                          <FileText className="w-3 h-3 shrink-0 mt-0.5 text-slate-400" />
                          <span>{entry.source_utterance}</span>
                        </p>
                      )}
                      <div className="text-[10px] text-slate-400 mt-0.5">{entry.created_at}</div>
                    </div>
                    <div className="text-xs font-extrabold text-paytm-navy tabular-nums shrink-0">
                      {entry.entry_type === 'REPAYMENT_JAMA' ? '−' : '+'}
                      {formatInr(entry.amount)}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </section>
      )}
    </div>
  );
}
