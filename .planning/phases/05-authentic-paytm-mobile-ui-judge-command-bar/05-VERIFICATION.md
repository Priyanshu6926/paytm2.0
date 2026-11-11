---
phase: 05-authentic-paytm-mobile-ui-judge-command-bar
verified: 2026-11-12T00:30:30Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-01-PLAN.md
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-01-SUMMARY.md
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-02-PLAN.md
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-02-SUMMARY.md
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-03-PLAN.md
  - .planning/phases/05-authentic-paytm-mobile-ui-judge-command-bar/05-03-SUMMARY.md
  - frontend/index.html
  - frontend/package.json
  - frontend/postcss.config.js
  - frontend/src/App.tsx
  - frontend/src/api/__tests__/kiranaClient.test.ts
  - frontend/src/api/kiranaClient.ts
  - frontend/src/components/JudgeDemoBar.tsx
  - frontend/src/components/PaytmMobileShell.tsx
  - frontend/src/components/SoundboxBanner.tsx
  - frontend/src/components/WhyAmISeeingThis.tsx
  - frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx
  - frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx
  - frontend/src/components/tabs/AiCfoTab.tsx
  - frontend/src/components/tabs/AiCmoTab.tsx
  - frontend/src/components/tabs/MemoryTimelineTab.tsx
  - frontend/src/components/tabs/MunimMicTab.tsx
  - frontend/src/index.css
  - frontend/src/main.tsx
  - frontend/src/test/setup.ts
  - frontend/src/types/kirana.ts
  - frontend/src/utils/__tests__/soundboxAudio.test.ts
  - frontend/src/utils/soundboxAudio.ts
  - frontend/tailwind.config.js
  - frontend/tsconfig.json
  - frontend/vite.config.ts
covered_digest: "v4:sha256:014ce5c5f37dd67242779a79a9624aefe3016496d25e278888ef12198c4c6cca"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open the running app (uvicorn backend.main:app --port 8000 + npm --prefix frontend run dev) in Chrome/Safari on desktop and mobile viewport"
    expected: "Centered max-w-[430px] Paytm for Business mobile bezel with #002970 Deep Navy curved header, #00BAF2 Paytm Cyan accents, Plus Jakarta Sans + Noto Sans Devanagari rendering, and smooth scrolling across all 4 tabs without horizontal overflow"
    why_human: "Visual layout fidelity, bezel framing, font rendering, and mobile touch feel cannot be proven by jsdom unit tests"
  - test: "Tap each of the 6 Judge Demo Quick-Trigger Bar flows and the 'Simulate Customer Paid' / 'Listen in Hindi' buttons in a live browser with speakers on"
    expected: "Paytm Soundbox banner equalizer animates and audible Bulbul WAV speech or C5+E5 dual-tone WebAudio chime plays cleanly without overlap or console errors"
    why_human: "Real browser HTMLAudioElement WAV decoding and Web Audio API speaker output are mocked in jsdom Vitest tests"
  - test: "Tap the Sarvam Voice Mic button in Tab 1 and upload real invoice/notebook images in Tabs 2 and 3"
    expected: "Browser MediaRecorder captures microphone audio and posts multipart FormData to /api/v1/voice/propose; custom file uploads show thumbnail previews and return parsed proposals from /api/v1/cfo/scan-distributor-bill and /api/v1/cmo/scan-bahi-khata"
    why_human: "Hardware microphone permission prompt and real MediaRecorder stream encoding require an interactive browser session"
---

# Phase 5: Authentic Paytm Mobile UI & Judge Quick-Trigger Command Bar Verification Report

**Phase Goal:** Deliver a mobile-first Paytm Merchant web interface with official brand styling (#002970/#00BAF2), 4 operational tabs, "Why am I seeing this?" evidence drawers, live Soundbox audio simulator, and a fail-safe Judge Quick-Trigger Bar.  
**Verified:** 2026-11-12T00:30:30Z  
**Status:** human_needed  
**Re-verification:** No — initial verification  

---

## Goal Achievement

All 3 Phase 5 plans (`05-01`, `05-02`, `05-03`) are implemented, wired, and verified against the codebase and live FastAPI router contracts. Automated verification passes across every ROADMAP Success Criterion (5/5), every requirement (`UI-01` through `UI-05`), and all test/build suites (`20` Vitest tests, `tsc -b && vite build`, `130` backend `pytest` tests, and `11` FastAPI `TestClient` contract spot-checks). Status is `human_needed` strictly for live-browser visual, speaker audio, and hardware microphone verification per Step 8.

### Observable Truths (ROADMAP Success Criteria)

| # | Truth / Success Criterion | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | UI displays within a high-contrast mobile viewport frame adhering to authentic Paytm Merchant design tokens (`#002970`, `#00BAF2`, crisp typography). | ✓ VERIFIED | [`frontend/tailwind.config.js`](frontend/tailwind.config.js) defines `paytm.navy: '#002970'`, `paytm.navyDark: '#001D52'`, `paytm.cyan: '#00BAF2'`, `paytm.bg: '#F5F7FA'`, `paytm.border: '#E5E9F0'`, and `Plus Jakarta Sans` + `Noto Sans Devanagari` font stack (loaded in [`frontend/index.html`](frontend/index.html) and [`frontend/src/index.css`](frontend/src/index.css)). [`PaytmMobileShell.tsx`](frontend/src/components/PaytmMobileShell.tsx) (line 78) enforces `max-w-[430px]`, mobile status strip (`9:41 AM`, `Paytm Business`, `5G`), curved `#002970` merchant header (`Ganesh Provision & General Store`, `Dadar, Mumbai`, `Soundbox Online`), and `Hinglish`/`Marathi`/`Hindi` dialect selector. |
| 2 | Merchant can navigate across 4 primary tabs: (1) Munim Mic & Operations, (2) AI CFO, (3) AI CMO, and (4) Business Memory Timeline. | ✓ VERIFIED | [`PaytmMobileShell.tsx`](frontend/src/components/PaytmMobileShell.tsx) renders the 4-tab sticky bottom navigation bar (`Mic`, `AI CFO`, `AI CMO`, `Memory`, `min-h-[44px]`) with live `cfoAlertCount` / `cmoActionCount` badges; [`App.tsx`](frontend/src/App.tsx) wires all 4 tabs (`MunimMicTab.tsx`, `AiCfoTab.tsx`, `AiCmoTab.tsx`, `MemoryTimelineTab.tsx`), verified by `AiCmoMemoryAndJudgeBar.test.tsx`. |
| 3 | Every proposal card contains an expandable "Why am I seeing this?" drawer showing mathematical formulas, source documents, and ledger balance deltas before confirmation. | ✓ VERIFIED | [`WhyAmISeeingThis.tsx`](frontend/src/components/WhyAmISeeingThis.tsx) renders collapsed `min-h-[44px]` toggle expanding deterministic formulas, before/after state deltas, source attribution, and escaped JSON provenance (`JSON.stringify`). Mounted across `MunimMicTab.tsx` (`NEEDS_DISAMBIGUATION` & `PROPOSAL` cards with explicit `Approve (Haan)` / `Cancel` gates), `AiCfoTab.tsx` (bill price creep, settlement waterfall, unmatched UPI queue), `AiCmoTab.tsx` (Boli-Baki, Break-Even Studio, Diwali Closing Ritual), and `MemoryTimelineTab.tsx` (each `business_events` item). |
| 4 | Collapsible Judge Demo Quick-Trigger Bar enables hackathon evaluators to run all 6 core product flows with 1-tap certainty regardless of ambient venue noise. | ✓ VERIFIED | [`JudgeDemoBar.tsx`](frontend/src/components/JudgeDemoBar.tsx) starts collapsed (`⚡ Judge Demo Quick-Triggers (6 Flows)`) and expands into all 6 PRD §8.2 chips (`voice_suresh`, `bill_creep`, `settlement_waterfall`, `qr_webhook`, `boli_baki_paid`, `diwali_ritual`) with in-flight locking (`disabled={activeFlowId !== null}`). [`App.tsx`](frontend/src/App.tsx) (`handleRunJudgeFlow`, lines 113–221) routes each flow to its target tab and invokes real `kiranaClient` endpoints. Verified by `AiCmoMemoryAndJudgeBar.test.tsx`. |
| 5 | Embedded Paytm Soundbox simulator renders and plays authentic vernacular audio chimes upon receiving payment webhook notifications. | ✓ VERIFIED | [`soundboxAudio.ts`](frontend/src/utils/soundboxAudio.ts) decodes `data:audio/wav;base64,...`, prevents clip overlap (`stopSoundboxAudio()`), and falls back cleanly to a `523.25 Hz` (C5) + `659.25 Hz` (E5) Web Audio API chime when base64 is empty or autoplay is blocked. [`SoundboxBanner.tsx`](frontend/src/components/SoundboxBanner.tsx) subscribes to live playback state, animates the 5-bar `.animate-soundbox-bar` equalizer, and exposes Replay/Mute controls. Triggered on `confirmVoiceProposal`, `resolveUnmatchedPayment`, `simulateQrWebhook`, `simulateLinkPaid`, settlement/price-creep/closing-ritual TTS, and Judge Demo flows. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

---

### Plan-Level Must-Haves Breakdown

All 12 plan-level truths across `05-01-PLAN.md` (4), `05-02-PLAN.md` (4), and `05-03-PLAN.md` (4) are verified in code and covered by Vitest unit/integration tests:
- `05-01`: `PaytmMobileShell.tsx` (`max-w-[430px]`, `#002970`/`#00BAF2`, 4 bottom tabs), `kiranaClient.ts` + `types/kirana.ts` (23 FastAPI endpoint methods + `KiranaApiError` + Vite `/api -> http://127.0.0.1:8000` proxy), `soundboxAudio.ts` + `SoundboxBanner.tsx`, and `WhyAmISeeingThis.tsx`.
- `05-02`: `MunimMicTab.tsx` (`MediaRecorder` mic + Hinglish/Marathi text input, dialect toggle, `NEEDS_DISAMBIGUATION` & `PROPOSAL` confirmation gates, pending UPI quick-resolve, Customer Khata append-only ledger sheet) and `AiCfoTab.tsx` (both `Scan Sample Bill (Gupta Wholesalers)` and custom `<input type="file" accept="image/*">` upload with 10MB guard + preview cleanup, `+7.58% PRICE CREEP ALERT` & `₹160` MRP toggle, atomic `Confirm & Update Stock + Khata`, `Mera Paisa Kam Kyun Aaya?` waterfall with `DETERMINISTICALLY BALANCED` seal + Bulbul Hindi TTS, and Unmatched UPI Queue + `⚡ Fire Ambiguous ₹200 QR Webhook`).
- `05-03`: `AiCmoTab.tsx` (`Boli-Baki` voice recovery + `⚡ Simulate Customer Paid` Soundbox trigger, `Dead-Stock Break-Even Studio` slider + `OFFER_BLOCKED_LOSS_MAKING` Hard Stop + `mr-IN`/`hi-IN` attribution click simulator, `60-Second Dukaan Closing Ritual` with `3.5×` Diwali Ghee restock draft + clipboard copy + Bulbul briefing, and `Handwritten Bahi-Khata Scanner` supporting both sample preset and custom `<input type="file" accept="image/*">` upload + editable rows + ambiguity selector + atomic `confirmBahiKhata`), `MemoryTimelineTab.tsx` (7 category filter pills, actor badges, `WhyAmISeeingThis` JSON evidence drawers), `JudgeDemoBar.tsx`, and `App.tsx` orchestration.

---

### Required Artifacts (4-Level Verification: Exists, Substantive, Wired, Data Flowing)

| Artifact | Purpose | Exists | Substantive | Wired | Data Flows | Status |
|----------|---------|--------|-------------|-------|------------|--------|
| `frontend/package.json` | React 18, Vite 5, TS 5.6, Tailwind 3.4, Vitest, RTL | ✓ | ✓ (30 lines) | ✓ (`npm test` & `build`) | N/A (config) | ✓ VERIFIED |
| `frontend/vite.config.ts` | `/api -> http://127.0.0.1:8000` proxy & Vitest jsdom config | ✓ | ✓ (20 lines) | ✓ (Vite + Vitest) | ✓ (proxies `/api/v1/*`) | ✓ VERIFIED |
| `frontend/tailwind.config.js` | Paytm design tokens (`#002970`, `#00BAF2`, `#F5F7FA`, `#E5E9F0`) | ✓ | ✓ (21 lines) | ✓ (imported by PostCSS/CSS) | N/A (styles) | ✓ VERIFIED |
| `frontend/src/types/kirana.ts` | 1:1 TypeScript contracts for all FastAPI routers | ✓ | ✓ (603 lines) | ✓ (imported by client, tabs, App) | ✓ (aligned with backend schemas) | ✓ VERIFIED |
| `frontend/src/api/kiranaClient.ts` | Typed fetch wrapper (JSON + FormData + `KiranaApiError`) | ✓ | ✓ (329 lines) | ✓ (imported by App & all 4 tabs) | ✓ (calls live `/api/v1/*` routes) | ✓ VERIFIED |
| `frontend/src/utils/soundboxAudio.ts` | Singleton WAV base64 player + WebAudio C5/E5 chime fallback | ✓ | ✓ (253 lines) | ✓ (subscribed by `SoundboxBanner`) | ✓ (pub/sub playback state) | ✓ VERIFIED |
| `frontend/src/components/PaytmMobileShell.tsx` | `max-w-[430px]` Paytm Merchant mobile frame & 4-tab nav | ✓ | ✓ (210 lines) | ✓ (rendered by `App.tsx`) | ✓ (renders live health/badges) | ✓ VERIFIED |
| `frontend/src/components/SoundboxBanner.tsx` | Animated 5-bar Soundbox banner with Replay & Mute controls | ✓ | ✓ (95 lines) | ✓ (slotted in `App.tsx`) | ✓ (`subscribeSoundbox`) | ✓ VERIFIED |
| `frontend/src/components/WhyAmISeeingThis.tsx` | Reusable expandable formula, delta, source & JSON evidence drawer | ✓ | ✓ (117 lines) | ✓ (used across Tabs 1–4) | ✓ (renders live backend evidence) | ✓ VERIFIED |
| `frontend/src/components/JudgeDemoBar.tsx` | Collapsible 6-chip PRD §8.2 Judge Quick-Trigger Bar | ✓ | ✓ (139 lines) | ✓ (slotted in `App.tsx`) | ✓ (triggers `handleRunJudgeFlow`) | ✓ VERIFIED |
| `frontend/src/components/tabs/MunimMicTab.tsx` | Tab 1: Mic, dialect, disambiguation/proposal gates, UPI & Khata | ✓ | ✓ (970 lines) | ✓ (rendered in `App.tsx`) | ✓ (`propose`, `confirm`, `ledger`) | ✓ VERIFIED |
| `frontend/src/components/tabs/AiCfoTab.tsx` | Tab 2: Bill scanner (demo+upload), price creep, waterfall, UPI | ✓ | ✓ (767 lines) | ✓ (rendered in `App.tsx`) | ✓ (`scan`, `confirm`, `settlement`, `upi`) | ✓ VERIFIED |
| `frontend/src/components/tabs/AiCmoTab.tsx` | Tab 3: Boli-Baki, Break-Even Studio, Diwali Ritual, Bahi-Khata | ✓ | ✓ (1,299 lines) | ✓ (rendered in `App.tsx`) | ✓ (`debtors`, `dead-stock`, `ritual`, `bahi`) | ✓ VERIFIED |
| `frontend/src/components/tabs/MemoryTimelineTab.tsx` | Tab 4: Filtered immutable `business_events` audit timeline | ✓ | ✓ (194 lines) | ✓ (rendered in `App.tsx`) | ✓ (`listBusinessEvents`) | ✓ VERIFIED |
| `frontend/src/App.tsx` | 4-tab orchestration, live badge counts, Judge Demo live handlers | ✓ | ✓ (282 lines) | ✓ (mounted in `main.tsx`) | ✓ (`health`, `badges`, `refreshToken`) | ✓ VERIFIED |
| `frontend/src/api/__tests__/kiranaClient.test.ts` | API client URL, FormData/JSON & error tests (3 tests) | ✓ | ✓ (215 lines) | ✓ (run by Vitest) | ✓ (passes) | ✓ VERIFIED |
| `frontend/src/utils/__tests__/soundboxAudio.test.ts` | Soundbox WAV/chime/overlap & `WhyAmISeeingThis` tests (4 tests) | ✓ | ✓ (199 lines) | ✓ (run by Vitest) | ✓ (passes) | ✓ VERIFIED |
| `frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx` | Tab 1 & Tab 2 user flow tests (7 tests) | ✓ | ✓ (593 lines) | ✓ (run by Vitest) | ✓ (passes) | ✓ VERIFIED |
| `frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx` | Tab 3, Tab 4 & JudgeDemoBar 6-flow integration tests (6 tests) | ✓ | ✓ (794 lines) | ✓ (run by Vitest) | ✓ (passes) | ✓ VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/vite.config.ts` | `http://127.0.0.1:8000` | `server.proxy['/api']` | ✓ WIRED | Proxies `/api/v1/*` requests to FastAPI backend with `changeOrigin: true` |
| `kiranaClient.ts` | `backend/routers/*.py` | `fetch('/api/v1/...')` + `types/kirana.ts` | ✓ WIRED | Verified 1:1 path and JSON key parity across all 23 endpoints via `TestClient` and `kiranaClient.test.ts` |
| `SoundboxBanner.tsx` | `soundboxAudio.ts` | `subscribeSoundbox` / `replayLastSoundbox` / `toggleSoundboxMute` | ✓ WIRED | Real-time state synchronization without prop drilling |
| `App.tsx` | `PaytmMobileShell.tsx` & Tabs 1–4 | `activeTab`, `refreshToken`, `onDataMutated`, live badge counts | ✓ WIRED | `handleDataMutated` increments `refreshToken` and refreshes `cfoAlertCount` + `cmoActionCount` |
| `JudgeDemoBar.tsx` | `App.tsx` (`handleRunJudgeFlow`) | `onRunFlow(flowId)` | ✓ WIRED | Switches `activeTab`, invokes real `kiranaClient` endpoints, updates shared state, and triggers Soundbox audio |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `App.tsx` | `health`, `cfoAlertCount`, `cmoActionCount` | `getMemoryHealth()`, `getUnmatchedPayments()`, `getOverdueDebtors()` | Yes (SQLite counts) | ✓ FLOWING |
| `MunimMicTab.tsx` | `customers`, `unmatchedPayments`, `ledgerData`, `activeProposal` | `listCustomers()`, `getUnmatchedPayments()`, `getCustomerLedger()`, `proposeVoiceCommand()` | Yes (SQLite ledger & voice engine) | ✓ FLOWING |
| `AiCfoTab.tsx` | `billProposal`, `settlementData`, `unmatchedPayments` | `scanDistributorBill()`, `getSettlementExplainer()`, `getUnmatchedPayments()` | Yes (Bill OCR + SQLite + deterministic waterfall) | ✓ FLOWING |
| `AiCmoTab.tsx` | `overdueDebtors`, `deadStockItems`, `campaignResult`, `closingRitual`, `bahiScan` | `getOverdueDebtors()`, `getDeadStock()`, `createDeadStockCampaign()`, `getDukaanClosingRitual()`, `scanBahiKhata()` | Yes (SQLite + deterministic CMO math + Vision OCR) | ✓ FLOWING |
| `MemoryTimelineTab.tsx` | `events` | `listBusinessEvents(category)` | Yes (`business_events` SQLite table) | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frontend Vitest test suite (all 4 files) | `npm --prefix frontend test` | 4 test files, 20/20 tests passed in 840ms | ✓ PASS |
| TypeScript typecheck & Vite production bundle | `npm --prefix frontend run build` | `tsc -b && vite build` succeeded cleanly (`dist/assets/index-D7W03wc2.js` 262.68 kB) | ✓ PASS |
| Backend full pytest regression suite | `pytest -q` | 130/130 tests passed in 0.85s | ✓ PASS |
| Live FastAPI endpoint schema spot-check (11 core UI-backed routes) | `python3 -c '...TestClient(app)...'` (isolated temp DB) | All 11 routes returned HTTP 200 with exact expected JSON keys | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| **UI-01** | `05-01`, `05-03` | Authentic mobile-first Paytm Merchant App interface (`#002970`, `#00BAF2`, crisp typography, mobile viewport frame) | ✓ SATISFIED | `PaytmMobileShell.tsx` (`max-w-[430px]`), `tailwind.config.js`, `index.html`, `index.css` |
| **UI-02** | `05-02`, `05-03` | 4 primary operational tabs: Munim Mic, AI CFO, AI CMO, Business Memory Timeline | ✓ SATISFIED | `App.tsx`, `MunimMicTab.tsx`, `AiCfoTab.tsx`, `AiCmoTab.tsx`, `MemoryTimelineTab.tsx` |
| **UI-03** | `05-01`, `05-02`, `05-03` | Expandable "Why am I seeing this?" evidence pills and Propose -> Confirm -> Commit gates | ✓ SATISFIED | `WhyAmISeeingThis.tsx` across Tabs 1–4; explicit `Approve (Haan)` / `Confirm` gates |
| **UI-04** | `05-03` | Collapsible Judge Demo Quick-Trigger Bar with 6 one-click live demo flows | ✓ SATISFIED | `JudgeDemoBar.tsx` + `handleRunJudgeFlow` in `App.tsx` |
| **UI-05** | `05-01`, `05-02`, `05-03` | Embedded Paytm Soundbox simulator playing authentic audio chimes / TTS | ✓ SATISFIED | `soundboxAudio.ts` + `SoundboxBanner.tsx` triggered across payment/voice/ritual flows |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | Scanned `frontend/src/` for `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, `PLACEHOLDER`, `dangerouslySetInnerHTML`, and empty handlers | - | 0 blockers, 0 warnings |

*Minor informational note (non-blocking):* In `AiCmoTab.tsx` line 426, the validation message for unresolved `AMBIGUOUS` Bahi-Khata rows reads `Please pick an existing customer or choose "Create New Customer"`, while the `<select>` on lines 1248–1268 lists `Select matching customer...` and candidate customers without a separate `"Create New Customer"` option (an ambiguous row must pick one of the matched candidates). This does not break any flow or requirement.

---

### Human Verification Required

### 1. Authentic Paytm Mobile Viewport & Visual Polish
**Test:** Start backend (`uvicorn backend.main:app --port 8000`) and frontend (`npm --prefix frontend run dev`), open `http://localhost:5173` on a desktop browser and mobile device/DevTools responsive mode.  
**Expected:** App renders centered inside a `max-w-[430px]` Paytm mobile bezel on desktop (and full-width on mobile), with `#002970` Deep Navy header, `#00BAF2` Cyan accents, clean `Plus Jakarta Sans` + `Noto Sans Devanagari` typography, and zero horizontal overflow across all 4 tabs.  
**Why human:** Visual fidelity, bezel ergonomics, font rendering, and mobile tap comfort require visual inspection in a real browser.

### 2. Audible Paytm Soundbox WAV & WebAudio Chime Playback
**Test:** Expand `⚡ Judge Demo Quick-Triggers (6 Flows)` and trigger flows 3 (`Mera Paisa Kam Kyun Aaya?`), 5 (`Marathi Udhaar Link → Pay` + `⚡ Simulate Customer Paid`), and 6 (`Run 60s Diwali Closing Ritual`) with system audio enabled.  
**Expected:** `SoundboxBanner` equalizer bars animate during playback and audible Bulbul WAV speech or C5+E5 WebAudio chime plays cleanly without overlapping clips.  
**Why human:** `Audio` and `AudioContext` are mocked in jsdom unit tests; real speaker output and browser autoplay behavior require live browser verification.

### 3. Live Browser Mic Recording & Custom File Uploads
**Test:** Tap the Sarvam Mic button in Tab 1 (`Munim Mic`) to speak a Hinglish/Marathi command, and upload real photo files via `Upload Custom Bill Photo` (Tab 2) and `Upload Custom Notebook Photo` (Tab 3).  
**Expected:** `MediaRecorder` captures audio and submits multipart `FormData` to `/api/v1/voice/propose`; custom images render thumbnail previews and parse cleanly through `/api/v1/cfo/scan-distributor-bill` and `/api/v1/cmo/scan-bahi-khata`.  
**Why human:** Microphone hardware permissions and real file picker / `MediaRecorder` stream capture require an interactive browser session.

---

### Gaps Summary

No automated gaps or blockers were found. All 5 ROADMAP success criteria, all 5 UI requirements (`UI-01`..`UI-05`), all 20 Vitest tests, the TypeScript + Vite production build, and all 130 backend pytest tests pass. Phase 5 is marked `human_needed` solely for live-browser visual, speaker audio, and microphone verification.

---

_Verified: 2026-11-12T00:30:30Z_  
_Verifier: the agent (gsd-verifier)_
