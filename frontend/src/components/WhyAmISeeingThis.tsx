import { useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, Info, ShieldCheck } from 'lucide-react';

export interface WhyAmISeeingThisProps {
  summary?: string;
  formula?: string;
  source?: string;
  beforeLabel?: string;
  afterLabel?: string;
  evidence?: Record<string, unknown> | unknown;
  defaultOpen?: boolean;
  badgeText?: string;
}

export function WhyAmISeeingThis({
  summary,
  formula,
  source,
  beforeLabel,
  afterLabel,
  evidence,
  defaultOpen = false,
  badgeText,
}: WhyAmISeeingThisProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const formattedEvidence =
    evidence !== undefined && evidence !== null
      ? typeof evidence === 'string'
        ? evidence
        : JSON.stringify(evidence, null, 2)
      : null;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        className="w-full min-h-[44px] px-3 py-2 rounded-xl bg-paytm-bg hover:bg-slate-200/70 border border-paytm-border flex items-center justify-between gap-2 text-left transition-colors"
      >
        <span className="flex items-center gap-2 text-xs font-semibold text-paytm-navy">
          <Info className="w-4 h-4 text-paytm-cyan shrink-0" />
          <span>Why am I seeing this?</span>
          {badgeText && (
            <span className="px-2 py-0.5 rounded-full bg-paytm-navy/10 text-paytm-navy text-[10px] font-bold">
              {badgeText}
            </span>
          )}
        </span>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-slate-500 shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" />
        )}
      </button>

      {isOpen && (
        <div className="mt-2 rounded-xl bg-slate-50 border border-paytm-border p-3 space-y-2.5 text-xs text-slate-700">
          {summary && <p className="leading-relaxed text-slate-700">{summary}</p>}

          {formula && (
            <div className="rounded-lg bg-white border border-paytm-border px-2.5 py-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                Deterministic Formula
              </div>
              <code className="font-mono text-[11px] text-paytm-navy font-semibold break-all">
                {formula}
              </code>
            </div>
          )}

          {(beforeLabel || afterLabel) && (
            <div className="flex flex-wrap items-center gap-1.5 rounded-lg bg-white border border-paytm-border px-2.5 py-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">
                Delta:
              </span>
              {beforeLabel && (
                <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-semibold tabular-nums">
                  {beforeLabel}
                </span>
              )}
              {beforeLabel && afterLabel && (
                <ArrowRight className="w-3.5 h-3.5 text-paytm-cyan shrink-0" />
              )}
              {afterLabel && (
                <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold tabular-nums">
                  {afterLabel}
                </span>
              )}
            </div>
          )}

          {source && (
            <div className="flex items-start gap-1.5 text-[11px] text-slate-600">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
              <span>
                <strong className="text-slate-800">Source:</strong> {source}
              </span>
            </div>
          )}

          {formattedEvidence && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                KiranaOS Evidence Provenance
              </div>
              <pre className="bg-slate-900 text-emerald-300 rounded-xl p-2.5 text-[11px] leading-relaxed overflow-x-auto font-mono">
                {formattedEvidence}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
