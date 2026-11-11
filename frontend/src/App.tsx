import { useCallback, useEffect, useState } from 'react';
import { kiranaClient } from './api/kiranaClient';
import { JudgeDemoBar, type JudgeFlowId } from './components/JudgeDemoBar';
import { PaytmMobileShell } from './components/PaytmMobileShell';
import { SoundboxBanner } from './components/SoundboxBanner';
import { AiCfoTab } from './components/tabs/AiCfoTab';
import { AiCmoTab } from './components/tabs/AiCmoTab';
import { MemoryTimelineTab } from './components/tabs/MemoryTimelineTab';
import { MunimMicTab } from './components/tabs/MunimMicTab';
import type {
  BoliBakiRecoveryResponse,
  DialectLabel,
  DukaanClosingRitualResponse,
  LanguageCode,
  MemoryHealthResponse,
  PaytmTab,
  ScanBillResponse,
  SettlementExplainerResponse,
  VoiceProposeResponse,
} from './types/kirana';
import { playSoundboxAudio } from './utils/soundboxAudio';

export function App() {
  const [activeTab, setActiveTab] = useState<PaytmTab>('mic');
  const [language, setLanguage] = useState<LanguageCode>('hi-IN');
  const [dialectLabel, setDialectLabel] = useState<DialectLabel>('Hinglish');
  const [health, setHealth] = useState<MemoryHealthResponse | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const [cfoAlertCount, setCfoAlertCount] = useState(0);
  const [cmoActionCount, setCmoActionCount] = useState(0);

  // Shared cross-tab workflow state (also populated by Judge Demo Quick-Triggers)
  const [voiceProposal, setVoiceProposal] = useState<VoiceProposeResponse | null>(null);
  const [billProposal, setBillProposal] = useState<ScanBillResponse | null>(null);
  const [settlementData, setSettlementData] = useState<SettlementExplainerResponse | null>(null);
  const [recoveryPreview, setRecoveryPreview] = useState<BoliBakiRecoveryResponse | null>(null);
  const [closingRitual, setClosingRitual] = useState<DukaanClosingRitualResponse | null>(null);

  const [activeFlowId, setActiveFlowId] = useState<JudgeFlowId | null>(null);
  const [judgeError, setJudgeError] = useState<string | null>(null);

  const refreshCounts = useCallback(async () => {
    const [upiRes, debtorsRes] = await Promise.allSettled([
      kiranaClient.getUnmatchedPayments(),
      kiranaClient.getOverdueDebtors(),
    ]);

    if (upiRes.status === 'fulfilled' && Array.isArray(upiRes.value)) {
      setCfoAlertCount(
        upiRes.value.filter((item) => item.status === 'PENDING_REVIEW').length,
      );
    }

    if (debtorsRes.status === 'fulfilled' && debtorsRes.value) {
      setCmoActionCount(
        debtorsRes.value.count ?? debtorsRes.value.overdue_debtors?.length ?? 0,
      );
    }
  }, []);

  useEffect(() => {
    let active = true;

    Promise.allSettled([
      kiranaClient.getMemoryHealth(),
      kiranaClient.getUnmatchedPayments(),
      kiranaClient.getOverdueDebtors(),
    ]).then(([healthRes, upiRes, debtorsRes]) => {
      if (!active) return;

      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
      }

      if (upiRes.status === 'fulfilled' && Array.isArray(upiRes.value)) {
        setCfoAlertCount(
          upiRes.value.filter((item) => item.status === 'PENDING_REVIEW').length,
        );
      }

      if (debtorsRes.status === 'fulfilled' && debtorsRes.value) {
        setCmoActionCount(
          debtorsRes.value.count ?? debtorsRes.value.overdue_debtors?.length ?? 0,
        );
      }
    });

    return () => {
      active = false;
    };
  }, []);

  const handleDataMutated = useCallback(() => {
    setRefreshToken((prev) => prev + 1);
    void refreshCounts();
  }, [refreshCounts]);

  const handleDialectChange = (label: DialectLabel, code: LanguageCode) => {
    setDialectLabel(label);
    setLanguage(code);
  };

  const handleLanguageCodeChange = (code: LanguageCode) => {
    setLanguage(code);
    if (code === 'mr-IN') {
      setDialectLabel('Marathi');
    } else if (dialectLabel === 'Marathi') {
      setDialectLabel('Hinglish');
    }
  };

  const handleRunJudgeFlow = async (flowId: JudgeFlowId) => {
    if (activeFlowId !== null) return;
    setActiveFlowId(flowId);
    setJudgeError(null);

    try {
      switch (flowId) {
        case 'voice_suresh': {
          setActiveTab('mic');
          const proposal = await kiranaClient.proposeVoiceCommand({
            transcriptOverride: 'Suresh ka 200 rupaye udhaar likh do',
            languageHint: 'hi-IN',
          });
          setVoiceProposal(proposal);
          void playSoundboxAudio({
            audioBase64: proposal.tts_audio_base64,
            announcement: proposal.spoken_prompt_hi || proposal.raw_transcript,
            sourceLabel: 'Bulbul v3 Disambiguation',
          });
          break;
        }
        case 'bill_creep': {
          setActiveTab('cfo');
          const bill = await kiranaClient.scanDistributorBill({ useDemoSample: true });
          setBillProposal(bill);
          void playSoundboxAudio({
            audioBase64: bill.tts_audio_base64,
            announcement:
              bill.price_creep_alerts[0]?.alert_hi ??
              `${bill.supplier_name} bill ${bill.invoice_number} scanned.`,
            sourceLabel: 'AI CFO Margin Guard',
          });
          break;
        }
        case 'settlement_waterfall': {
          setActiveTab('cfo');
          const settlement = await kiranaClient.getSettlementExplainer();
          setSettlementData(settlement);
          void playSoundboxAudio({
            audioBase64: settlement.tts_audio_base64,
            announcement: settlement.spoken_explanation_hi,
            sourceLabel: 'Bulbul v3 Settlement Explainer',
          });
          break;
        }
        case 'qr_webhook': {
          setActiveTab('cfo');
          await kiranaClient.simulateQrWebhook({
            upi_txn_id: `UPI-JUDGE-${Date.now()}`,
            amount: 200,
            payer_name: 'Suresh',
            payer_vpa: 'suresh@paytm',
          });
          void playSoundboxAudio({
            announcement: 'Paytm par ₹200 prapt hue — Ambiguous payer Suresh review queue mein.',
            sourceLabel: 'Paytm QR Webhook',
            isPaymentChime: true,
          });
          handleDataMutated();
          break;
        }
        case 'boli_baki_paid': {
          setActiveTab('cmo');
          const debtorsRes = await kiranaClient.getOverdueDebtors();
          const debtors = debtorsRes.overdue_debtors ?? [];
          const target =
            debtors.find(
              (d) =>
                d.outstanding_amount > 0 &&
                d.customer_name.toLowerCase().includes('ramesh'),
            ) ?? debtors.find((d) => d.outstanding_amount > 0);

          if (!target) {
            setJudgeError('All overdue debtors are already settled.');
            await refreshCounts();
            break;
          }

          const recovery = await kiranaClient.createBoliBakiRecovery({
            customer_id: target.customer_id,
            target_language: 'mr-IN',
          });
          setRecoveryPreview(recovery);
          void playSoundboxAudio({
            audioBase64: recovery.tts_audio_base64,
            announcement: recovery.translated_message,
            sourceLabel: 'Boli-Baki Marathi Voice',
          });
          handleDataMutated();
          break;
        }
        case 'diwali_ritual': {
          setActiveTab('cmo');
          const ritual = await kiranaClient.getDukaanClosingRitual();
          setClosingRitual(ritual);
          void playSoundboxAudio({
            audioBase64: ritual.tts_audio_base64,
            announcement: ritual.spoken_ritual_hi,
            sourceLabel: 'Diwali EOD Ritual',
          });
          break;
        }
      }
    } catch (err: unknown) {
      setJudgeError(err instanceof Error ? err.message : 'Unable to run demo flow.');
    } finally {
      setActiveFlowId(null);
    }
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
      cfoAlertCount={cfoAlertCount}
      cmoActionCount={cmoActionCount}
      soundboxSlot={<SoundboxBanner />}
      judgeBarSlot={
        <JudgeDemoBar
          onRunFlow={handleRunJudgeFlow}
          activeFlowId={activeFlowId}
          errorMessage={judgeError}
          onDismissError={() => setJudgeError(null)}
        />
      }
    >
      {activeTab === 'mic' && (
        <MunimMicTab
          languageHint={language}
          onLanguageChange={handleLanguageCodeChange}
          activeProposal={voiceProposal}
          onProposalChange={setVoiceProposal}
          refreshToken={refreshToken}
          onDataMutated={handleDataMutated}
        />
      )}

      {activeTab === 'cfo' && (
        <AiCfoTab
          billProposal={billProposal}
          onBillProposalChange={setBillProposal}
          settlementData={settlementData}
          onSettlementDataChange={setSettlementData}
          refreshToken={refreshToken}
          onDataMutated={handleDataMutated}
        />
      )}

      {activeTab === 'cmo' && (
        <AiCmoTab
          recoveryPreview={recoveryPreview}
          onRecoveryPreviewChange={setRecoveryPreview}
          closingRitual={closingRitual}
          onClosingRitualChange={setClosingRitual}
          refreshToken={refreshToken}
          onDataMutated={handleDataMutated}
        />
      )}

      {activeTab === 'memory' && <MemoryTimelineTab refreshToken={refreshToken} />}
    </PaytmMobileShell>
  );
}

export default App;
