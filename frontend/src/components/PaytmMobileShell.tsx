import type { ReactNode } from 'react';
import {
  BadgeCheck,
  History,
  IndianRupee,
  Megaphone,
  Mic,
  Radio,
  Signal,
  Store,
  Wifi,
} from 'lucide-react';
import type { DialectLabel, LanguageCode, PaytmTab } from '../types/kirana';

export interface PaytmMobileShellProps {
  activeTab: PaytmTab;
  onTabChange: (tab: PaytmTab) => void;
  language: LanguageCode;
  dialectLabel: DialectLabel;
  onDialectChange: (dialect: DialectLabel, code: LanguageCode) => void;
  storeName?: string;
  storeLocation?: string;
  backendHealthy?: boolean;
  cfoAlertCount?: number;
  cmoActionCount?: number;
  soundboxSlot?: ReactNode;
  judgeBarSlot?: ReactNode;
  children: ReactNode;
}

const DIALECT_OPTIONS: Array<{ label: DialectLabel; code: LanguageCode }> = [
  { label: 'Hinglish', code: 'hi-IN' },
  { label: 'Marathi', code: 'mr-IN' },
  { label: 'Hindi', code: 'hi-IN' },
];

export function PaytmMobileShell({
  activeTab,
  onTabChange,
  dialectLabel,
  onDialectChange,
  storeName = 'Ganesh Provision & General Store',
  storeLocation = 'Dadar, Mumbai',
  backendHealthy = true,
  cfoAlertCount = 0,
  cmoActionCount = 0,
  soundboxSlot,
  judgeBarSlot,
  children,
}: PaytmMobileShellProps) {
  const navItems: Array<{
    id: PaytmTab;
    label: string;
    icon: typeof Mic;
    badge?: number;
    badgeTone?: 'red' | 'amber';
  }> = [
    { id: 'mic', label: 'Munim Mic', icon: Mic },
    {
      id: 'cfo',
      label: 'AI CFO',
      icon: IndianRupee,
      badge: cfoAlertCount > 0 ? cfoAlertCount : undefined,
      badgeTone: 'red',
    },
    {
      id: 'cmo',
      label: 'AI CMO',
      icon: Megaphone,
      badge: cmoActionCount > 0 ? cmoActionCount : undefined,
      badgeTone: 'amber',
    },
    { id: 'memory', label: 'Memory', icon: History },
  ];

  return (
    <div className="min-h-[100dvh] w-full bg-[#E2E8F0] flex flex-col items-center justify-start md:py-4">
      <div className="w-full max-w-[430px] min-h-[100dvh] md:min-h-[844px] md:max-h-[900px] bg-paytm-bg flex flex-col relative overflow-hidden md:rounded-[32px] md:border-[6px] md:border-[#0F172A] md:shadow-2xl">
        {/* Realistic Mobile Status Strip */}
        <div className="bg-paytm-navy text-white/90 px-5 pt-2 pb-1 flex items-center justify-between text-[11px] font-semibold tracking-tight shrink-0">
          <span className="tabular-nums">9:41 AM</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#00BAF2] font-bold">Paytm Business</span>
            <span className="text-white/40">•</span>
            <span>5G</span>
            <Signal className="w-3 h-3" />
            <Wifi className="w-3 h-3" />
          </div>
        </div>

        {/* Paytm for Business Curved Merchant Header */}
        <header className="bg-gradient-to-b from-paytm-navy to-paytm-navyDark text-white px-4 pt-2 pb-4 rounded-b-[24px] shadow-md shrink-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-10 h-10 rounded-2xl bg-white/10 border border-white/15 flex items-center justify-center shrink-0">
                <Store className="w-5 h-5 text-paytm-cyan" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <h1 className="text-[14px] font-bold leading-tight truncate text-white">
                    {storeName}
                  </h1>
                  <BadgeCheck
                    className="w-4 h-4 text-paytm-cyan shrink-0"
                    aria-label="Paytm Verified Merchant"
                  />
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[11px] text-white/75">
                  <span>{storeLocation}</span>
                  <span className="text-white/30">•</span>
                  <span className="inline-flex items-center gap-1 text-emerald-300 font-medium">
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        backendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                      }`}
                    />
                    <Radio className="w-3 h-3" />
                    {backendHealthy ? 'Soundbox Online' : 'Connecting...'}
                  </span>
                </div>
              </div>
            </div>

            <span className="shrink-0 rounded-full bg-paytm-cyan/15 border border-paytm-cyan/40 px-2 py-0.5 text-[10px] font-bold text-paytm-cyan">
              KiranaOS
            </span>
          </div>

          {/* Language Dialect Selector */}
          <div className="mt-3 flex items-center justify-between gap-2">
            <span className="text-[11px] text-white/70 font-medium">Voice &amp; Alerts:</span>
            <div
              className="inline-flex rounded-full bg-white/10 p-0.5 border border-white/10"
              role="group"
              aria-label="Language selection"
            >
              {DIALECT_OPTIONS.map((opt) => {
                const isSelected = dialectLabel === opt.label;
                return (
                  <button
                    key={opt.label}
                    type="button"
                    onClick={() => onDialectChange(opt.label, opt.code)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors ${
                      isSelected
                        ? 'bg-paytm-cyan text-paytm-navy shadow-sm'
                        : 'text-white/80 hover:text-white'
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        {/* Optional Soundbox & Judge Demo Slots */}
        {soundboxSlot && <div className="px-3 pt-2.5 shrink-0">{soundboxSlot}</div>}
        {judgeBarSlot && <div className="px-3 pt-2 shrink-0">{judgeBarSlot}</div>}

        {/* Scrollable Mobile Content Area */}
        <main className="flex-1 overflow-y-auto px-3 py-3 space-y-3">{children}</main>

        {/* Sticky Bottom 4-Tab Paytm Mobile Navigation */}
        <nav
          aria-label="Paytm Merchant Primary Navigation"
          className="bg-white border-t border-paytm-border px-2 py-1.5 grid grid-cols-4 gap-1 shrink-0 shadow-[0_-4px_12px_rgba(15,23,42,0.05)]"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onTabChange(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`relative min-h-[44px] rounded-xl flex flex-col items-center justify-center gap-0.5 px-1 py-1 transition-colors ${
                  isActive
                    ? 'bg-paytm-navy/5 text-paytm-navy font-bold'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50 font-medium'
                }`}
              >
                <div className="relative">
                  <Icon
                    className={`w-5 h-5 ${isActive ? 'text-paytm-navy' : 'text-slate-500'}`}
                  />
                  {item.badge !== undefined && (
                    <span
                      className={`absolute -top-1.5 -right-2.5 min-w-[16px] h-[16px] px-1 rounded-full text-[10px] font-bold text-white flex items-center justify-center tabular-nums ${
                        item.badgeTone === 'red' ? 'bg-rose-600' : 'bg-amber-500'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
                <span className="text-[11px] leading-none">{item.label}</span>
                {isActive && (
                  <span className="w-5 h-0.5 rounded-full bg-paytm-cyan mt-0.5" />
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
