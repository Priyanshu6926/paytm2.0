---
phase: 05-authentic-paytm-mobile-ui-judge-command-bar
plan: 01
subsystem: ui
tags: [react, vite, typescript, tailwind, paytm-ui, soundbox, web-audio, vitest]

# Dependency graph
requires:
  - phase: 01-kiranaos-foundation-append-only-business-memory
    provides: /api/v1/memory/* FastAPI endpoints and SQLite business memory schema
  - phase: 02-voice-gateway-sarvam-stt-tts-and-customer-disambiguation
    provides: /api/v1/voice/* FastAPI endpoints and Bulbul v3 TTS WAV base64 responses
  - phase: 03-ai-cfo-margin-defense-and-settlement-reconciliation
    provides: /api/v1/cfo/* FastAPI endpoints for bill scanning, settlement waterfall, and unmatched QR queue
  - phase: 04-ai-cmo-boli-baki-recovery-dead-stock-studio-closing-ritual
    provides: /api/v1/cmo/* FastAPI endpoints for Boli-Baki, dead-stock campaigns, closing ritual, and bahi-khata OCR
provides:
  - React 18 + Vite + TypeScript + Tailwind CSS frontend scaffold with /api -> http://127.0.0.1:8000 Vite proxy
  - 1:1 typed KiranaOS API client (kiranaClient.ts + types/kirana.ts) matching all FastAPI routers
  - Authentic max-w-[430px] Paytm for Business mobile shell (PaytmMobileShell.tsx) with #002970/#00BAF2 tokens and 4 bottom tabs
  - Paytm Soundbox WAV base64 + Web Audio dual-tone chime fallback engine and animated banner (soundboxAudio.ts + SoundboxBanner.tsx)
  - Reusable expandable WhyAmISeeingThis.tsx evidence/formula/provenance drawer
affects: [05-02, 05-03, ui-integration, judge-demo-bar]

# Actuals (#2632)
actuals:
  tokens: 17244
  tasks: 2
  commits: 3

plan_head_before: c085e6aa5e3f1e5641775e7eb61edb02100255cc
plan_head_after: eb20075777e7d1054466b023046552930e72ab4e

# Tech tracking
tech-stack:
  added: [react@18.3.1, react-dom@18.3.1, vite@5.4.10, typescript@5.6.3, tailwindcss@3.4.14, lucide-react@0.460.0, vitest@2.1.4, "@testing-library/react@16.0.1", "@testing-library/jest-dom@6.6.3", jsdom@25.0.1]
  patterns:
    - "Paytm Mobile Bezel Viewport: centered max-w-[430px] mobile shell with sticky header and 4-tab bottom navigation"
    - "Single-clip Soundbox Singleton: stop-before-play Audio controller with WebAudio C5+E5 chime fallback"
    - "Zero-dangerouslySetInnerHTML Evidence Drawer: strictly escaped React text nodes for transcripts and JSON provenance"

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.json
    - frontend/tailwind.config.js
    - frontend/src/types/kirana.ts
    - frontend/src/api/kiranaClient.ts
    - frontend/src/components/PaytmMobileShell.tsx
    - frontend/src/components/SoundboxBanner.tsx
    - frontend/src/components/WhyAmISeeingThis.tsx
    - frontend/src/utils/soundboxAudio.ts
    - frontend/src/App.tsx
    - frontend/src/api/__tests__/kiranaClient.test.ts
    - frontend/src/utils/__tests__/soundboxAudio.test.ts
  modified:
    - .gitignore

key-decisions:
  - "Preserve native File objects in FormData uploads when no override filename is provided so multipart boundaries and filenames remain intact across browsers and jsdom"
  - "Keep Soundbox audio state in a module-level pub/sub controller (soundboxAudio.ts) so SoundboxBanner stays synchronized across all 4 tabs and the Judge Demo Bar without prop drilling"
  - "Ignore *.tsbuildinfo in .gitignore so tsc -b incremental build caches never pollute git working trees"

patterns-established:
  - "1:1 FastAPI contract types in frontend/src/types/kirana.ts aligned directly against backend/routers/*.py"
  - "44px minimum touch targets on mobile navigation tabs and expandable WhyAmISeeingThis evidence triggers"

requirements-completed: [UI-01, UI-03, UI-05]

coverage:
  - id: D1
    description: "Paytm for Business max-w-[430px] mobile shell with #002970/#00BAF2 design tokens, Plus Jakarta Sans + Noto Sans Devanagari fonts, and 4 bottom tabs"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run build"
        status: pass
    human_judgment: false
  - id: D2
    description: "1:1 typed KiranaOS API client covering all /api/v1/{memory,voice,cfo,cmo}/* endpoints, JSON vs FormData uploads, and KiranaApiError parsing"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/api/__tests__/kiranaClient.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Paytm Soundbox WAV base64 player + WebAudio dual-tone chime fallback (523.25Hz/659.25Hz) and animated equalizer banner"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "frontend/src/utils/__tests__/soundboxAudio.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Reusable expandable WhyAmISeeingThis evidence drawer showing formula, delta, source attribution, and formatted JSON provenance"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/utils/__tests__/soundboxAudio.test.ts#WhyAmISeeingThis"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-11-11
status: complete
---

# Phase 5 Plan 01: Authentic Paytm Mobile Shell, KiranaOS Client & Soundbox Primitives Summary

**React 18 + Vite + TypeScript + Tailwind Paytm for Business mobile shell (`max-w-[430px]`), 1:1 typed FastAPI KiranaOS client across all 23 endpoints, WebAudio/WAV Paytm Soundbox simulator, and expandable `"Why am I seeing this?"` evidence drawer.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-11T18:40:15Z
- **Completed:** 2026-11-11T18:45:41Z
- **Tasks:** 2
- **Files modified:** 20 (19 created in `frontend/`, 1 updated in `.gitignore`)

## Accomplishments
- Scaffolded `frontend/` with React 18, Vite 5, TypeScript 5.6 (strict), Tailwind CSS 3.4, Lucide icons, Vitest, React Testing Library, and jsdom, plus `/api -> http://127.0.0.1:8000` Vite dev proxy.
- Authored `frontend/src/types/kirana.ts` and `frontend/src/api/kiranaClient.ts` aligned 1:1 against `memory_router.py`, `voice_router.py`, `cfo_router.py`, and `cmo_router.py`, supporting both JSON demo presets and `FormData` multipart uploads.
- Built `PaytmMobileShell.tsx` featuring the `#002970` Deep Paytm Navy curved header, `#00BAF2` Paytm Cyan verified badge, `"Ganesh Provision & General Store"` (`Dadar, Mumbai`) identity, dialect selector (`Hinglish` | `Marathi` | `Hindi`), and 4-tab bottom navigation (`Munim Mic`, `AI CFO`, `AI CMO`, `Memory`).
- Implemented `soundboxAudio.ts` + `SoundboxBanner.tsx` with `data:audio/wav;base64,...` playback, automatic Web Audio C5+E5 (`523.25Hz` + `659.25Hz`) chime fallback on empty or autoplay-blocked audio, single-clip overlap prevention, and 5-bar equalizer animation.
- Built `WhyAmISeeingThis.tsx` with `min-h-[44px]` toggle pill expanding deterministic formulas, before/after state deltas, source attribution, and escaped JSON evidence provenance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold React 18 + Vite + TypeScript + Tailwind frontend, typed KiranaOS API client, and Paytm Mobile Shell** - `ba9cef7` (feat)
2. **Task 2: Paytm Soundbox WAV/WebAudio Simulator and reusable "Why am I seeing this?" Evidence Drawer** - `859e9a9` (feat)
3. **Chore: Ignore TypeScript incremental tsbuildinfo artifact** - `eb20075` (chore)

## Files Created/Modified
- `frontend/package.json` & `frontend/package-lock.json` - React 18, Vite, TypeScript, Tailwind, Lucide, and Vitest dependencies and scripts
- `frontend/vite.config.ts` - Vite dev server on port 5173 with `/api -> http://127.0.0.1:8000` proxy and Vitest jsdom config
- `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`, `frontend/src/index.css` - Strict TypeScript config, Paytm design tokens (`#002970`, `#00BAF2`, `#F5F7FA`), Plus Jakarta Sans + Noto Sans Devanagari fonts, and Soundbox equalizer animation
- `frontend/src/types/kirana.ts` - Complete TypeScript request/response interfaces verified against all FastAPI routers and service parsers
- `frontend/src/api/kiranaClient.ts` - Strongly typed fetch wrapper (`KiranaApiError`, JSON & FormData multipart handling)
- `frontend/src/components/PaytmMobileShell.tsx` - `max-w-[430px]` Paytm for Business mobile viewport frame with header, slots, and 4-tab bottom bar
- `frontend/src/utils/soundboxAudio.ts` - Singleton Soundbox audio controller with WAV playback and WebAudio dual-tone chime fallback
- `frontend/src/components/SoundboxBanner.tsx` - Animated 5-bar Soundbox banner with Replay and Mute/Unmute controls
- `frontend/src/components/WhyAmISeeingThis.tsx` - Reusable expandable formula, delta, source, and JSON evidence drawer
- `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/test/setup.ts` - Tracer app entry fetching live `/api/v1/memory/health`
- `frontend/src/api/__tests__/kiranaClient.test.ts` & `frontend/src/utils/__tests__/soundboxAudio.test.ts` - 7 passing Vitest unit/component tests
- `.gitignore` - Added `*.tsbuildinfo` to ignore `tsc -b` incremental build cache

## Decisions Made
- Preserved native `File` instances when constructing `FormData` without an explicit filename override so multipart requests retain original upload metadata cleanly.
- Used a module-level pub/sub store in `soundboxAudio.ts` so any tab or the Judge Demo Bar can trigger Soundbox announcements without prop drilling.
- Added `*.tsbuildinfo` to `.gitignore` so running `npm --prefix frontend run build` (`tsc -b && vite build`) leaves a clean git working tree.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `*.tsbuildinfo` to `.gitignore`**
- **Found during:** Post-build verification after Task 2
- **Issue:** `tsc -b` creates `frontend/tsconfig.tsbuildinfo`, leaving an untracked build artifact in git status.
- **Fix:** Added `*.tsbuildinfo` to `.gitignore`.
- **Files modified:** `.gitignore`
- **Verification:** `npm --prefix frontend run build` leaves `git status` clean of `.tsbuildinfo` untracked files.
- **Committed in:** `eb20075`

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)
**Impact on plan:** Keeps repository clean of TypeScript incremental build artifacts; zero scope creep.

## Issues Encountered
- Initial `kiranaClient.test.ts` upload test compared `FormData.get('file')` with `toBe(billFile)` which failed under jsdom's `FormData` cloning when passing a synthetic filename; updated `kiranaClient.ts` to preserve `File` when no custom filename is passed and asserted `instanceof File` + `.name` in the test.
- `soundboxAudio.test.ts` has a `.ts` extension per plan, so JSX `<WhyAmISeeingThis />` initially caused an esbuild parse error; switched the test to `React.createElement(WhyAmISeeingThis, ...)` while keeping the exact `.ts` test filename.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `PaytmMobileShell`, `kiranaClient`, `SoundboxBanner`, `soundboxAudio`, and `WhyAmISeeingThis` are verified and ready for Wave 2 (`05-02` Tab 1 Munim Mic & Tab 2 AI CFO, `05-03` Tab 3 AI CMO, Tab 4 Memory, & Judge Demo Quick-Trigger Bar).

---
*Phase: 05-authentic-paytm-mobile-ui-judge-command-bar*
*Completed: 2026-11-11*

## Self-Check: PASSED
