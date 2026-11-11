import { useEffect, useState } from 'react';
import { kiranaClient } from './api/kiranaClient';
import { PaytmMobileShell } from './components/PaytmMobileShell';
import type {
  DialectLabel,
  LanguageCode,
  MemoryHealthResponse,
  PaytmTab,
} from './types/kirana';

export function App() {
  const [activeTab, setActiveTab] = useState<PaytmTab>('mic');
  const [language, setLanguage] = useState<LanguageCode>('hi-IN');
  const [dialectLabel, setDialectLabel] = useState<DialectLabel>('Hinglish');
  const [health, setHealth] = useState<MemoryHealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    kiranaClient
      .getMemoryHealth()
      .then((res) => {
        if (active) {
          setHealth(res);
          setHealthError(null);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setHealthError(err instanceof Error ? err.message : 'Backend offline');
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const handleDialectChange = (label: DialectLabel, code: LanguageCode) => {
    setDialectLabel(label);
    setLanguage(code);
  };

  return (
    <PaytmMobileShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      language={language}
      dialectLabel={dialectLabel}
      onDialectChange={handleDialectChange}
      storeName={health?.store_name ?? 'Ganesh Provision & General Store'}
      backendHealthy={Boolean(health?.status === 'healthy')}
    >
      <section className="bg-white rounded-2xl border border-paytm-border p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-paytm-navy">
            KiranaOS Mobile Shell ({activeTab.toUpperCase()})
          </h2>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-paytm-bg text-slate-600">
            {language}
          </span>
        </div>
        {health ? (
          <p className="mt-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2">
            Connected to {health.store_name} ({health.database}) •{' '}
            {Object.keys(health.tables).length} append-only tables ready
          </p>
        ) : healthError ? (
          <p className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
            Waiting for FastAPI backend on port 8000 ({healthError})
          </p>
        ) : (
          <p className="mt-2 text-xs text-slate-500">Checking KiranaOS memory health...</p>
        )}
      </section>
    </PaytmMobileShell>
  );
}

export default App;
