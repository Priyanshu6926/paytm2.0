---
phase: 05-authentic-paytm-mobile-ui-judge-command-bar
plan: 02
subsystem: ui
tags: [react, typescript, tailwind, vitest, voice-ui, ai-cfo, media-recorder, soundbox]

# Dependency graph
requires:
  - phase: 05-authentic-paytm-mobile-ui-judge-command-bar
    provides: PaytmMobileShell, kiranaClient, kirana.ts types, soundboxAudio, WhyAmISeeingThis
  - phase: 02-voice-gateway-sarvam-stt-tts-and-customer-disambiguation
    provides: /api/v1/voice/propose and /api/v1/voice/confirm endpoints
  - phase: 03-ai-cfo-margin-defense-and-settlement-reconciliation
    provides: /api/v1/cfo/* endpoints for bill scanning, settlement waterfall, and unmatched UPI queue
provides:
  - Tab 1 MunimMicTab.tsx (Sarvam MediaRecorder voice capture, Hinglish/Marathi command bar, NEEDS_DISAMBIGUATION & PROPOSAL approval gates, UPI quick-resolve, Customer Khata ledger inspection)
  - Tab 2 AiCfoTab.tsx (Demo & custom image distributor bill scanner, +7.58% price-creep guard & MRP adoption, atomic dual-write confirmation, settlement waterfall with Bulbul Hindi TTS, unmatched UPI queue & QR webhook simulator)
  - Comprehensive Vitest + React Testing Library flow test suite (MunimMicAndAiCfo.test.tsx)
affects: [05-03, app-integration, judge-demo-bar]

# Actuals (#2632)
actuals:
  tokens: 22400
  tasks: 2
  commits: 2

plan_head_before: 59f101aaac741ecde3c7dce6151849d380c9e119
plan_head_after: 2470259908bfa0531335bfd72464e72d8b59616e

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Propose -> Confirm -> Commit UI Guard: NEEDS_DISAMBIGUATION and PROPOSAL cards never auto-commit; buttons disable during in-flight confirmation"
    - "Safe Client Image Upload: MIME + 10MB validation and deterministic URL.revokeObjectURL cleanup on preview replacement or unmount"
    - "Idempotent Bill Confirmation: Handles both CONFIRMED and ALREADY_CONFIRMED statuses cleanly before triggering parent onDataMutated()"

key-files:
  created:
    - frontend/src/components/tabs/MunimMicTab.tsx
    - frontend/src/components/tabs/AiCfoTab.tsx
    - frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx
  modified: []

key-decisions:
  - "Mounted Customer Khata ledger inspection as an inline mobile card sheet within MunimMicTab so merchants stay inside the 430px viewport without modal z-index or focus-trap issues"
  - "Scoped Vitest assertions inside the Identity disambiguation required region via within() because candidate names intentionally appear in both the disambiguation card and the Customer Khata strip below"

patterns-established:
  - "Shared controlled proposal/bill/settlement props between Tab components and App/Judge Demo Bar for synchronized single-source state"
  - "Soundbox audio announcements triggered on every confirmed ledger write, UPI reconciliation, and Hindi settlement/alert playback"

requirements-completed: [UI-02, UI-03, UI-05]

coverage:
  - id: D1
    description: "Tab 1 MunimMicTab voice/text proposal flow, NEEDS_DISAMBIGUATION 1-tap resolution, explicit Approve (Haan) / Cancel gate, and Soundbox confirmation playback"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#proposes ambiguous voice text, shows NEEDS_DISAMBIGUATION Amber card without blind write, and confirms via 1-tap candidate selection"
        status: pass
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#renders PROPOSAL card with before -> after balance and cancels cleanly without calling confirmVoiceProposal"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tab 1 Customer Khata strip with tap-to-inspect chronological append-only ledger history"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#opens Customer Khata ledger sheet and renders chronological append-only entries"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tab 2 AiCfoTab distributor bill scanner (both Gupta Wholesalers demo preset and custom image upload with <=10MB guard), +7.58% price-creep alert, ₹160 MRP adoption, and atomic dual-write confirmation"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#scans Gupta Wholesalers sample bill, surfaces +7.58% price creep alert, adopts ₹160 MRP, and executes atomic confirm"
        status: pass
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#supports custom distributor bill image upload with preview and rejects >10MB files"
        status: pass
    human_judgment: false
  - id: D4
    description: "Tab 2 Mera Paisa Kam Kyun Aaya? settlement waterfall with DETERMINISTICALLY BALANCED seal, WhyAmISeeingThis invariant drawer, and Bulbul Hindi TTS playback"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#renders Settlement Waterfall with DETERMINISTICALLY BALANCED seal and triggers Bulbul Hindi TTS"
        status: pass
    human_judgment: false
  - id: D5
    description: "Tab 2 Unmatched UPI Queue, QR Webhook Simulator, and 1-tap debtor resolution"
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx#fires ambiguous ₹200 QR webhook simulator and resolves unmatched UPI item in 1 tap"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-11-11
status: complete
---

# Phase 5 Plan 02: Tab 1 Munim Mic & Tab 2 AI CFO Summary

**Sarvam MediaRecorder & Hinglish/Marathi `MunimMicTab` with explicit disambiguation/approval gates and Customer Khata ledger sheet, paired with `AiCfoTab` supporting demo & custom distributor bill scanning (`+7.58%` oil price-creep alert + MRP adoption), `₹6,450 -> ₹5,815` Paytm settlement waterfall with Bulbul Hindi TTS, and unmatched UPI webhook simulation/resolution.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-11T18:47:55Z
- **Completed:** 2026-11-11T18:50:58Z
- **Tasks:** 2
- **Files modified:** 3 created in `frontend/src/components/`

## Accomplishments
- Built `frontend/src/components/tabs/MunimMicTab.tsx` with a pulsing Sarvam Voice Mic (`MediaRecorder` audio capture + graceful fallback notice), `Hinglish`/`Marathi`/`Hindi` dialect pills, quick command chips, `NEEDS_DISAMBIGUATION` Amber Card with 1-tap candidate confirmation, typed `PROPOSAL` card with `WhyAmISeeingThis` evidence and explicit `Approve (Haan)` / `Cancel` gates, pending ambiguous UPI quick-resolve card, and a tap-to-inspect Customer Khata append-only ledger sheet.
- Built `frontend/src/components/tabs/AiCfoTab.tsx` with dual bill-scanning triggers (**Scan Sample Bill (Gupta Wholesalers)** and **Upload Custom Bill Photo** `<input type="file" accept="image/*" capture="environment">` with MIME/10MB validation and `URL.revokeObjectURL` cleanup), flashing `+7.58% PRICE CREEP ALERT` banner with optional `₹160` MRP adoption checkbox, atomic `Confirm & Update Stock + Khata` action, `"Mera Paisa Kam Kyun Aaya?"` settlement waterfall (`₹6,450.00 - ₹635 = ₹5,815.00`) with `DETERMINISTICALLY BALANCED` seal and Bulbul Hindi TTS playback, plus the Unmatched UPI Queue and `⚡ Fire Ambiguous ₹200 QR Webhook` simulator.
- Built `frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx` with 7 Vitest + React Testing Library flow tests covering every Tab 1 and Tab 2 user journey; all 14 frontend tests across 3 test suites pass and `tsc -b && vite build` succeeds cleanly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tab 1 MunimMicTab — Sarvam Voice Mic, Disambiguation & Proposal Gate, UPI Quick-Resolve, and Customer Khata Ledger** - `1b71ec8` (feat)
2. **Task 2: Tab 2 AiCfoTab — Bill Scanner (Demo + Custom Upload), Price Creep Alert, Settlement Waterfall, Unmatched UPI Queue, and Vitest Flow Tests** - `2470259` (feat)

## Files Created/Modified
- `frontend/src/components/tabs/MunimMicTab.tsx` - Tab 1 voice/text command bar, disambiguation & proposal gates, UPI quick-resolve, and Customer Khata ledger sheet
- `frontend/src/components/tabs/AiCfoTab.tsx` - Tab 2 distributor bill scanner (demo + custom upload), price-creep guard & MRP adoption, settlement waterfall, and UPI webhook simulator/queue
- `frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx` - 7 Vitest + React Testing Library flow tests verifying Tab 1 and Tab 2 behaviors

## Decisions Made
- Rendered the Customer Khata append-only ledger drawer as an inline sheet inside `MunimMicTab` to stay strictly within the 430px mobile scroll container without z-index conflicts.
- Scoped Vitest candidate assertions in `MunimMicAndAiCfo.test.tsx` with `within(disambigCard)` because customer names appear in both the disambiguation card and the live Customer Khata list.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial test run hit a duplicate text match (`getMultipleElementsFoundError`) on `Suresh Patil (Tailor)` because the customer name appears in both the `NEEDS DISAMBIGUATION` card and the Customer Khata list; fixed by scoping the test assertion with `within(disambigCard)`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `MunimMicTab` and `AiCfoTab` expose controlled props (`activeProposal`, `billProposal`, `settlementData`, `refreshToken`, `onDataMutated`) ready for Plan `05-03` (`AiCmoTab.tsx`, `MemoryTab.tsx`, `JudgeDemoBar.tsx`, and `App.tsx` orchestration).

---
*Phase: 05-authentic-paytm-mobile-ui-judge-command-bar*
*Completed: 2026-11-11*

## Self-Check: PASSED
- FOUND: `frontend/src/components/tabs/MunimMicTab.tsx`
- FOUND: `frontend/src/components/tabs/AiCfoTab.tsx`
- FOUND: `frontend/src/components/__tests__/MunimMicAndAiCfo.test.tsx`
- FOUND COMMIT: `1b71ec8`
- FOUND COMMIT: `2470259`
