# Phase 2: Core Voice & Multimodal Gateway - Context

**Gathered:** 2026-11-10  
**Status:** Ready for planning  
**Source:** PRD Express Path (`munim_ai_kiranaos_master_hackathon_prd.md`)

<domain>
## Phase Boundary

Phase 2 implements the multimodal voice-first gateway connecting KiranaOS to Sarvam AI. It delivers shop-counter speech-to-intent transcription via Sarvam Saaras STT with dynamic SQLite keyterm biasing, spoken vernacular prompts via Bulbul v3 TTS, the Propose-Confirm-Commit interaction gate, and a fail-safe local fallback engine guaranteeing sub-6-second demo-day survivability.
</domain>

<decisions>
## Implementation Decisions

### Sarvam AI Integration & Service Layer (Locked)
- Create `backend/services/sarvam_engine.py` wrapping:
  1. Speech-to-Text (`saaras:v4` / `saaras:v3`): Hinglish and Marathi codemix speech recognition with dynamic keyterm biasing.
  2. Text-to-Speech (`bulbul:v3`): Vernacular audio synthesis in `hi-IN` and `mr-IN`.
  3. Translation (`Sarvam Translate`): Bidirectional translation across Hindi, Marathi, and English.
- Supports `SARVAM_API_KEY` from environment variables (`.env`).

### Law of Demo-Day Survivability & Fallback Engine (Locked)
- Every external call to Sarvam or LLM services is wrapped in a strict 6.0-second timeout.
- If `SARVAM_API_KEY` is missing, or an API call exceeds 6.0 seconds, or the network fails:
  - Automatically fall back to realistic pre-computed / synthetic payloads without throwing 500 errors.
  - Return authentic base64 WAV audio (generated via standard Python `wave` module synthesizers or pre-recorded clips).
  - Guarantee 100% demo continuity regardless of venue Wi-Fi conditions.

### Dynamic SQL Keyterm Biasing (Locked)
- To prevent mistranscribing Indian Kirana store terms, the gateway queries active SQLite tables before invoking STT:
  - Top customer names and aliases from `customers` table (e.g., "Ramesh", "Suresh Patil", "Priya").
  - Top FMCG brand names and SKUs from `inventory_items` (e.g., "Fortune Oil", "Amul Ghee", "Aloo Bhujia").
- Injects these terms into Sarvam STT context/prompt biasing.

### Propose $\rightarrow$ Confirm $\rightarrow$ Commit Gate (Locked)
- Zero database writes occur on raw transcript extraction.
- Voice commands produce an unconfirmed typed Proposal Card:
  - Intent classified (`CREDIT_UDHAAR`, `REPAYMENT_JAMA`, `STOCK_IN`, `STOCKOUT_FLAG`, `QUERY`).
  - Extracted amount, target customer, or item.
  - Disambiguation check via `deterministic_engine.resolve_customer_identity`.
  - Spoken Hindi confirmation prompt (`spoken_prompt_hi`) and synthesized `tts_audio_base64`.
- A dedicated confirmation endpoint executes the transaction only after explicit merchant approval (`CONFIRM`).

### REST API Endpoints (Locked)
- `POST /api/v1/voice/propose`: Accepts transcript string or audio bytes, returns proposal card or disambiguation card.
- `POST /api/v1/voice/confirm`: Confirms an active proposal and writes to `ledger_entries` + `business_events`.
- `POST /api/v1/voice/tts`: Direct text-to-speech generation for custom notifications.
- `GET /api/v1/voice/health`: Reports Sarvam API status, key presence, and fallback state.

### the agent's Discretion
- Intent parsing: Regex and rule-based heuristic parser for Kirana shop commands with optional LLM refinement.
- Synthetic WAV generation: Python standard library `wave` / `math.sin` generating recognizable clean audio tones/chimes when offline.
- Route location: `backend/routers/voice_router.py`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PRD Master Specification
- `munim_ai_kiranaos_master_hackathon_prd.md` §2 (Multimodal Input Layer & Propose-Confirm-Commit Gate)
- `munim_ai_kiranaos_master_hackathon_prd.md` §3 (Sponsor Stack Integration Matrix — Sarvam AI)
- `munim_ai_kiranaos_master_hackathon_prd.md` §7.1 (Voice Proposal & Disambiguation API Contract)

### Planning Artifacts
- `.planning/REQUIREMENTS.md` (VOICE-01, VOICE-02, VOICE-03)
- `.planning/ROADMAP.md` (Phase 2 details & success criteria)
- `.planning/phases/01-kiranaos-deterministic-memory-store-engine/01-VERIFICATION.md` (Phase 1 completion evidence)

</canonical_refs>

<specifics>
## Specific Ideas
- Provide sample phrases in Hindi/Hinglish:
  - "Suresh ka 200 udhaar likho" $\rightarrow$ triggers Suresh disambiguation
  - "Ramesh ne 300 rupaye jama kiye" $\rightarrow$ triggers repayment proposal
  - "Amul ghee 5 packet aaya" $\rightarrow$ triggers stock inward proposal
- Ensure proposal cards return `why_am_i_seeing_this` evidence strings for UI drawers.
</specifics>

<deferred>
## Deferred Ideas
- Streaming WebSockets for real-time live STT streaming (REST multipart/form-data audio upload is sufficient and more robust for demo).
</deferred>

---

*Phase: 02-core-voice-multimodal-gateway*  
*Context gathered: 2026-11-10 via PRD Express Path*

