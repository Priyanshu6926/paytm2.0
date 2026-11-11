import { useCallback, useEffect, useState } from 'react';
import { History, Loader2, RefreshCw } from 'lucide-react';
import { kiranaClient } from '../../api/kiranaClient';
import type { BusinessEvent, EventCategory } from '../../types/kirana';
import { WhyAmISeeingThis } from '../WhyAmISeeingThis';

export interface MemoryTimelineTabProps {
  refreshToken: number;
}

type FilterOption = 'ALL' | EventCategory;

const FILTER_OPTIONS: FilterOption[] = [
  'ALL',
  'LEDGER',
  'INVENTORY',
  'CFO_ALERT',
  'CMO_GROWTH',
  'SETTLEMENT',
  'SYSTEM_STARTUP',
];

function getCategoryPillStyle(category: string): string {
  switch (category) {
    case 'LEDGER':
      return 'bg-paytm-navy/10 text-paytm-navy border-paytm-navy/20';
    case 'INVENTORY':
      return 'bg-sky-50 text-sky-800 border-sky-200';
    case 'CFO_ALERT':
      return 'bg-rose-50 text-rose-800 border-rose-200';
    case 'CMO_GROWTH':
      return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    case 'SETTLEMENT':
      return 'bg-indigo-50 text-indigo-800 border-indigo-200';
    case 'SYSTEM_STARTUP':
      return 'bg-slate-100 text-slate-700 border-slate-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

function getActorBadgeStyle(actor: string): string {
  if (actor === 'MERCHANT_APPROVED') {
    return 'bg-emerald-100 text-emerald-900 border-emerald-300';
  }
  if (actor === 'SYSTEM_AUTO') {
    return 'bg-cyan-100 text-cyan-900 border-cyan-300';
  }
  if (actor === 'SYSTEM_GUARD') {
    return 'bg-amber-100 text-amber-900 border-amber-300';
  }
  return 'bg-slate-100 text-slate-800 border-slate-300';
}

export function MemoryTimelineTab({ refreshToken }: MemoryTimelineTabProps) {
  const [selectedCategory, setSelectedCategory] = useState<FilterOption>('ALL');
  const [events, setEvents] = useState<BusinessEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async (category: FilterOption) => {
    setLoading(true);
    setError(null);
    try {
      const data = await kiranaClient.listBusinessEvents(
        category === 'ALL' ? undefined : category,
      );
      setEvents(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to load KiranaOS memory timeline.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEvents(selectedCategory);
  }, [loadEvents, selectedCategory, refreshToken]);

  return (
    <div className="space-y-3" data-testid="memory-timeline-tab">
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-paytm-navy flex items-center gap-1.5">
              <History className="w-4 h-4 text-paytm-cyan" />
              <span>Unified Business Memory</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Immutable append-only audit log with deterministic evidence
            </p>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => void loadEvents(selectedCategory)}
            aria-label="Refresh timeline"
            className="min-h-[36px] min-w-[36px] rounded-xl bg-paytm-bg hover:bg-slate-200/70 border border-paytm-border text-paytm-navy flex items-center justify-center disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Horizontal Scrollable Category Filter Pills */}
        <div
          className="flex items-center gap-1.5 overflow-x-auto pb-1"
          role="group"
          aria-label="Business event category filters"
        >
          {FILTER_OPTIONS.map((category) => {
            const active = selectedCategory === category;
            return (
              <button
                key={category}
                type="button"
                aria-pressed={active}
                onClick={() => setSelectedCategory(category)}
                className={`shrink-0 min-h-[34px] px-2.5 py-1 rounded-full text-[11px] font-bold border transition-colors ${
                  active
                    ? 'bg-paytm-navy text-white border-paytm-navy shadow-sm'
                    : 'bg-paytm-bg text-slate-600 border-paytm-border hover:text-paytm-navy'
                }`}
              >
                {category}
              </button>
            );
          })}
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-800"
          >
            {error}
          </div>
        )}

        {loading && events.length === 0 ? (
          <div className="py-6 flex items-center justify-center gap-2 text-xs text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin text-paytm-cyan" />
            <span>Loading immutable business events...</span>
          </div>
        ) : events.length === 0 ? (
          <div className="rounded-xl bg-paytm-bg border border-paytm-border px-3 py-4 text-center text-xs text-slate-500">
            No business events found for {selectedCategory}.
          </div>
        ) : (
          <div className="space-y-2.5">
            {events.map((event) => (
              <article
                key={event.id}
                className="rounded-xl bg-paytm-bg border border-paytm-border p-3 space-y-2"
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${getCategoryPillStyle(
                        event.event_category,
                      )}`}
                    >
                      {event.event_category}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getActorBadgeStyle(
                        event.actor,
                      )}`}
                    >
                      {event.actor}
                    </span>
                  </div>
                  <time className="text-[10px] font-mono text-slate-500 tabular-nums">
                    {event.created_at}
                  </time>
                </div>

                <p className="text-xs font-semibold text-paytm-navy leading-relaxed">
                  {event.summary_text}
                </p>

                <WhyAmISeeingThis
                  source={`Event #${event.id} (${event.actor})`}
                  badgeText={event.event_category}
                  evidence={event.evidence}
                />
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
