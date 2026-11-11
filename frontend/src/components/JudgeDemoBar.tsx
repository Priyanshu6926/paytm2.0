import { useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, X, Zap } from 'lucide-react';

export type JudgeFlowId =
  | 'voice_suresh'
  | 'bill_creep'
  | 'settlement_waterfall'
  | 'qr_webhook'
  | 'boli_baki_paid'
  | 'diwali_ritual';

export interface JudgeDemoBarProps {
  onRunFlow: (flowId: JudgeFlowId) => Promise<void> | void;
  activeFlowId: JudgeFlowId | null;
  errorMessage?: string | null;
  onDismissError?: () => void;
}

const JUDGE_FLOWS: Array<{
  id: JudgeFlowId;
  label: string;
  subtitle: string;
}> = [
  {
    id: 'voice_suresh',
    label: '🎤 "Suresh ka ₹200 udhaar likho"',
    subtitle: 'Tab 1 • Disambiguation',
  },
  {
    id: 'bill_creep',
    label: '🧾 Scan Bill (+7.58% Oil Creep)',
    subtitle: 'Tab 2 • Margin Guard',
  },
  {
    id: 'settlement_waterfall',
    label: '🏦 "Mera Paisa Kam Kyun Aaya?"',
    subtitle: 'Tab 2 • Loan EDI Waterfall',
  },
  {
    id: 'qr_webhook',
    label: '💸 Fire Ambiguous ₹200 QR Webhook',
    subtitle: 'Tab 2 • Unmatched UPI',
  },
  {
    id: 'boli_baki_paid',
    label: '📢 Marathi Udhaar Link → Pay',
    subtitle: 'Tab 3 • Boli-Baki Voice',
  },
  {
    id: 'diwali_ritual',
    label: '🪔 Run 60s Diwali Closing Ritual',
    subtitle: 'Tab 3 • 3.5× Ghee Forecast',
  },
];

export function JudgeDemoBar({
  onRunFlow,
  activeFlowId,
  errorMessage,
  onDismissError,
}: JudgeDemoBarProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section
      aria-label="Judge Demo Quick-Trigger Bar"
      className="rounded-2xl bg-slate-900 text-white border border-slate-700/80 shadow-sm overflow-hidden"
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="w-full min-h-[38px] px-3 py-1.5 flex items-center justify-between gap-2 text-left hover:bg-slate-800/80 transition-colors"
      >
        <span className="flex items-center gap-1.5 text-[11px] font-bold tracking-tight">
          <Zap className="w-3.5 h-3.5 text-paytm-cyan shrink-0" />
          <span>⚡ Judge Demo Quick-Triggers (6 Flows)</span>
          {activeFlowId && (
            <Loader2 className="w-3 h-3 animate-spin text-paytm-cyan shrink-0" />
          )}
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-paytm-cyan shrink-0">
          <span>{expanded ? 'Hide' : 'Open'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </span>
      </button>

      {expanded && (
        <div className="px-2.5 pb-2.5 pt-1 border-t border-slate-800 space-y-2">
          <div className="grid grid-cols-2 gap-1.5">
            {JUDGE_FLOWS.map((flow) => {
              const isRunning = activeFlowId === flow.id;
              return (
                <button
                  key={flow.id}
                  type="button"
                  disabled={activeFlowId !== null}
                  onClick={() => void onRunFlow(flow.id)}
                  className={`min-h-[44px] rounded-xl px-2.5 py-1.5 text-left border transition-colors flex flex-col justify-center gap-0.5 disabled:opacity-60 ${
                    isRunning
                      ? 'bg-paytm-cyan/20 border-paytm-cyan text-white'
                      : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-100'
                  }`}
                >
                  <span className="text-[11px] font-bold leading-snug flex items-center gap-1">
                    {isRunning && <Loader2 className="w-3 h-3 animate-spin text-paytm-cyan shrink-0" />}
                    <span className="line-clamp-2">{flow.label}</span>
                  </span>
                  <span className="text-[9px] font-medium text-paytm-cyan/90">
                    {flow.subtitle}
                  </span>
                </button>
              );
            })}
          </div>

          {errorMessage && (
            <div
              role="alert"
              className="rounded-xl bg-rose-950/90 border border-rose-500/50 px-2.5 py-1.5 text-[11px] text-rose-200 flex items-center justify-between gap-2"
            >
              <span>{errorMessage}</span>
              {onDismissError && (
                <button
                  type="button"
                  onClick={onDismissError}
                  aria-label="Dismiss judge demo error"
                  className="p-0.5 rounded hover:bg-white/10"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
