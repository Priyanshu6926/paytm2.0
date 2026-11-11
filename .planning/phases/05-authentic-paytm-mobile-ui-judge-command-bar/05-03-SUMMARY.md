---
phase: 05-authentic-paytm-mobile-ui-judge-command-bar
plan: 03
subsystem: ui
tags: [react, typescript, tailwind, vitest, ai-cmo, memory-timeline, judge-demo-bar, soundbox]

# Dependency graph
requires:
  - phase: 05-authentic-paytm-mobile-ui-judge-command-bar
    provides: PaytmMobileShell, SoundboxBanner, WhyAmISeeingThis, kiranaClient, MunimMicTab, AiCfoTab
  - phase: 04-ai-cmo-recovery-growth-and-closing-ritual
    provides: /api/v1/cmo/* endpoints for Boli-Baki recovery, dead-stock break-even guard, 60s Diwali ritual, and Bahi-Khata OCR onboarding
provides:
  - Tab 3 AiCmoTab.tsx (Boli-Baki voice recovery + Soundbox payment chime, Dead-Stock Break-Even Studio + OFFER_BLOCKED_LOSS_MAKING Hard Stop + mr-IN/hi-IN attribution, 60s Diwali Dukaan Closing Ritual, and Dual-Mode Demo + Custom Upload Handwritten Bahi-Khata Scanner)
  - Tab 4 MemoryTimelineTab.tsx (Unified Business Memory audit log with category filters, actor badges, and expandable JSON evidence drawers)
  - JudgeDemoBar.tsx (Collapsible 6-chip PRD §8.2 Judge Demo Quick-Trigger Bar executing real FastAPI backend flows)
  - Complete App.tsx wiring with live badge counts, cross-tab refresh invalidation, and verified live FastAPI + Vite proxy smoke check
affects: [phase-05-verification, demo-readiness]

# Actuals (#2632)
actuals:
  tokens: 26181
  tasks: 3
  commits: 3

plan_head_before: eaae6209b96e12615ec67b87b625f7b371019db8
plan_head_after: b98962bf1d1a8eb0c9065de5ac466754f9e18968

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-Tab Mutation Invalidation: App.tsx maintains refreshToken and live cfoAlertCount/cmoActionCount badges refreshed on every mutation across Tabs 1-3"
    - "Judge Demo Live Proxy Pattern: Every JudgeDemoBar chip invokes real kiranaClient FastAPI endpoints and routes directly to the target tab with Soundbox playback"
    - "Atomic Bahi-Khata Batch Editing: Client validates non-blank names, positive finite amounts, and ambiguous customer selection before posting confirmBahiKhata"

key-files:
  created:
    - frontend/src/components/tabs/AiCmoTab.tsx
    - frontend/src/components/tabs/MemoryTimelineTab.tsx
    - frontend/src/components/JudgeDemoBar.tsx
    - frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "Evaluated dead-stock break-even math on explicit user interaction (slider change, preset chip click, or Test Offer Math button) rather than auto-posting on mount so browsing Tab 3 never creates unsolicited business_events"
  - "Scoped JudgeDemoBar test queries inside within(judgeBar) because both JudgeDemoBar and AiCfoTab expose the Fire Ambiguous ₹200 QR Webhook simulator action"

patterns-established:
  - "End-to-end 4-tab mobile merchant workflow wired through PaytmMobileShell slots (soundboxSlot, judgeBarSlot) with zero mocked UI-only shortcuts"

requirements-completed: [UI-01, UI-02, UI-03, UI-04, UI-05]

coverage:
  - id: D1
    description: "Tab 3 AiCmoTab Boli-Baki voice recovery + Simulate Customer Paid triggering Soundbox chime"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#executes Boli-Baki voice recovery and triggers live Soundbox chime on Simulate Customer Paid"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tab 3 Dead-Stock Break-Even Studio slider + OFFER_BLOCKED_LOSS_MAKING Hard Stop Guardrail + mr-IN/hi-IN attribution"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#evaluates safe ₹10 break-even math with mr-IN/hi-IN attribution and blocks ₹25 loss-making offer"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tab 3 60-Second Diwali Dukaan Closing Ritual with 3.5x Ghee restock forecast, briefing audio, and order draft copy"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#renders 60-Second Diwali Closing Ritual with 3.5x Ghee restock draft, audio briefing, and copy button"
        status: pass
    human_judgment: false
  - id: D4
    description: "Tab 3 Handwritten Bahi-Khata Scanner supporting Demo Sample + Custom Image Upload + inline edits + ambiguity resolution"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#supports Bahi-Khata demo scan, custom notebook photo upload, inline editing, ambiguity resolution, and atomic confirm"
        status: pass
    human_judgment: false
  - id: D5
    description: "Tab 4 MemoryTimelineTab category filtering and expandable WhyAmISeeingThis JSON evidence drawers"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#filters MemoryTimelineTab by event category and expands JSON evidence drawers"
        status: pass
    human_judgment: false
  - id: D6
    description: "App.tsx 4-tab navigation and collapsible 6-chip JudgeDemoBar executing live backend endpoints"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx#navigates all 4 tabs in App.tsx and executes all 6 JudgeDemoBar live backend flows"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-11-11
status: complete
---

# Phase 5 Plan 03: Tab 3 AI CMO, Tab 4 Memory Timeline, Judge Demo Bar & App Wiring Summary

**Completed the full 4-tab Munim-AI Paytm mobile merchant app by shipping `AiCmoTab` (Boli-Baki Marathi/Hindi voice recovery with Soundbox payment chime, Dead-Stock Break-Even Studio with `OFFER_BLOCKED_LOSS_MAKING` Hard Stop and `mr-IN`/`hi-IN` link attribution, 60-second Diwali Closing Ritual with $3.5\times$ Amul Ghee forecast, and dual-mode Demo + Custom Upload Bahi-Khata onboarding), `MemoryTimelineTab`, the collapsible 6-chip `JudgeDemoBar`, and full `App.tsx` orchestration verified live against FastAPI via the Vite proxy.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-11T18:52:11Z
- **Completed:** 2026-11-11T18:56:51Z
- **Tasks:** 3
- **Files modified:** 4 created, 1 modified in `frontend/src/`

## Accomplishments
- Built `frontend/src/components/tabs/AiCmoTab.tsx` covering all 4 AI CMO capabilities: Boli-Baki voice udhaar recovery (`createBoliBakiRecovery` + `simulateLinkPaid` triggering Soundbox payment chime), Dead-Stock Break-Even Studio (`₹5–₹35` slider + `OFFER_BLOCKED_LOSS_MAKING` Hard Stop + `mr-IN`/`hi-IN` attribution click simulator), 60-Second Diwali Dukaan Closing Ritual (`today_qr_sales`, `today_udhaar_recovered`, `unmatched_upi_count`, `3.5×` Amul Ghee restock draft + 1-tap clipboard copy + Bulbul briefing audio), and Handwritten Bahi-Khata Scanner (demo sample + custom image upload with 10MB guard, inline row editing, `AMBIGUOUS` candidate selector, and atomic `confirmBahiKhata`).
- Built `frontend/src/components/tabs/MemoryTimelineTab.tsx` with `ALL` / `LEDGER` / `INVENTORY` / `CFO_ALERT` / `CMO_GROWTH` / `SETTLEMENT` / `SYSTEM_STARTUP` category filter pills, actor badges (`MERCHANT_APPROVED`, `SYSTEM_AUTO`, `SYSTEM_GUARD`), manual refresh, and expandable `<WhyAmISeeingThis>` JSON evidence drawers.
- Built `frontend/src/components/JudgeDemoBar.tsx` and wired `frontend/src/App.tsx` with `PaytmMobileShell`, `SoundboxBanner`, all 4 operational tabs, live `cfoAlertCount` / `cmoActionCount` bottom badges, cross-tab `refreshToken` invalidation, and all 6 live PRD §8.2 Judge Demo flows.
- Verified with 20 passing Vitest tests (`4` test files), clean `tsc -b && vite build`, 130 passing backend `pytest -v` tests, and a live FastAPI + Vite dev proxy end-to-end smoke check with zero proxy errors.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tab 3 AiCmoTab — Boli-Baki Recovery, Dead-Stock Break-Even Studio, 60s Diwali Closing Ritual, and Bahi-Khata Scanner** - `20ab2e5` (feat)
2. **Task 2: Tab 4 MemoryTimelineTab and Collapsible 6-Chip JudgeDemoBar** - `2f6a471` (feat)
3. **Task 3: Full App.tsx Wiring, Vitest Suite for CMO/Memory/JudgeBar, and Live FastAPI + Frontend Integration Verification** - `b98962b` (feat)

## Files Created/Modified
- `frontend/src/components/tabs/AiCmoTab.tsx` - Tab 3 AI CMO workflows (Boli-Baki voice recovery, dead-stock break-even studio, 60s Diwali ritual, dual-mode Bahi-Khata scanner)
- `frontend/src/components/tabs/MemoryTimelineTab.tsx` - Tab 4 immutable `business_events` audit timeline with category filters and JSON evidence drawers
- `frontend/src/components/JudgeDemoBar.tsx` - Collapsible 6-chip PRD §8.2 Judge Demo Quick-Trigger Bar
- `frontend/src/App.tsx` - Full 4-tab application state, live badge counts, Soundbox & Judge Demo Bar wiring
- `frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx` - 6 Vitest + React Testing Library integration tests for Tab 3, Tab 4, and all 6 Judge Demo chips

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used `kiranaClient.listBusinessEvents` matching the Plan 05-01 client contract**
- **Found during:** Task 2 (`MemoryTimelineTab.tsx`)
- **Issue:** Plan 05-03 task prose mentioned `getBusinessEvents`, whereas `frontend/src/api/kiranaClient.ts` (delivered in Plan 05-01) exposes `listBusinessEvents(category)`.
- **Fix:** Invoked `kiranaClient.listBusinessEvents(...)` in `MemoryTimelineTab.tsx` and mocked `listBusinessEvents` in tests.
- **Files modified:** `frontend/src/components/tabs/MemoryTimelineTab.tsx`, `frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx`
- **Commit:** `2f6a471`, `b98962b`

## Issues Encountered
- Initial Vitest run hit a `getMultipleElementsFoundError` on `/Fire Ambiguous ₹200 QR Webhook/i` in the `App` integration test because both `JudgeDemoBar` and `AiCfoTab` expose that simulator trigger; scoped Judge Demo Bar clicks cleanly with `within(judgeBar)`.

## User Setup Required
None - all 6 Judge Demo flows and all 4 tabs operate out-of-the-box with zero manual setup, with automatic offline fallbacks if Sarvam keys are absent.

## Next Phase Readiness
- Phase 5 (`05-01`, `05-02`, `05-03`) is complete. All UI requirements (`UI-01` through `UI-05`) and all 6 PRD §8.2 live Judge Demo flows are built, tested, and verified against the live FastAPI backend.

---
*Phase: 05-authentic-paytm-mobile-ui-judge-command-bar*
*Completed: 2026-11-11*

## Self-Check: PASSED
- FOUND: `frontend/src/components/tabs/AiCmoTab.tsx`
- FOUND: `frontend/src/components/tabs/MemoryTimelineTab.tsx`
- FOUND: `frontend/src/components/JudgeDemoBar.tsx`
- FOUND: `frontend/src/App.tsx`
- FOUND: `frontend/src/components/__tests__/AiCmoMemoryAndJudgeBar.test.tsx`
- FOUND COMMIT: `20ab2e5`
- FOUND COMMIT: `2f6a471`
- FOUND COMMIT: `b98962b`
