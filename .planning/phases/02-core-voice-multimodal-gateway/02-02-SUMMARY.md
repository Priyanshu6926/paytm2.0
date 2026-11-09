---
phase: 02-core-voice-multimodal-gateway
plan: 02
subsystem: voice-multimodal
tags:
  - voice-gateway
  - intent-parser
  - keyterm-biasing
  - propose-confirm-gate
  - disambiguation-guard
status: complete
requires:
  - 02-01
  - 01-01
  - 01-02
provides:
  - Dynamic SQL keyterm biasing extractor from customers & inventory
  - Vernacular voice intent parser with Hinglish and Marathi support
  - Voice proposal & identity disambiguation endpoint (/api/v1/voice/propose)
  - Explicit confirmation endpoint (/api/v1/voice/confirm) committing deterministic ledger writes
  - Direct TTS synthesis endpoint (/api/v1/voice/tts)
  - Voice gateway health check (/api/v1/voice/health)
affects:
  - 02-03
  - 03-01
  - 04-01
tech-stack:
  added:
    - FastAPI APIRouter mounted at /api/v1/voice
    - Regex & heuristic shop-counter grammar parser
  patterns:
    - Propose-Confirm-Commit Gate (zero blind mutations on raw speech)
    - Automated customer identity disambiguation guard for overlapping names
    - Dynamic database biasing term injection for speech-to-text
    - Strict merchant approval enforcement (action == 'APPROVE')
key-files:
  created:
    - backend/services/voice_intent_parser.py
    - backend/routers/voice_router.py
    - tests/test_voice_gateway.py
  modified:
    - backend/main.py
    - backend/services/deterministic_engine.py
decisions:
  - "D-03: Dynamic SQL keyterm biasing pulls customer names, aliases, SKU names, and SKU local aliases to prime Sarvam STT context"
  - "D-04: Enforce Propose-Confirm-Commit gate; ambiguous names trigger NEEDS_DISAMBIGUATION cards and halt auto-execution"
  - "D-05: Restrict uploaded audio files to 10MB and require explicit action='APPROVE' before committing financial transactions"
metrics:
  duration: 5m
  completed_date: "2026-11-10"
actuals:
  tokens: 48000
  tasks: 2
  commits: 2
  plan_head_before: 490118742ca7f14bfa4a6d7f3fb8d2ca058448eb
  plan_head_after: bb91019dfdaaa6a18d363b9bf01bcfc2a0bf2097
---

# Phase 2 Plan 2: Voice Gateway & Propose-Confirm-Commit API Summary

Implemented dynamic SQL keyterm biasing, vernacular intent parsing for shop-counter Hinglish and Marathi commands, and the Propose-Confirm-Commit REST API gateway mounted at `/api/v1/voice/*`.

## Delivered Capabilities

1. **Dynamic SQL Keyterm Biasing Extractor (`extract_keyterm_biasing_from_db`)**:
   - Queries SQLite `customers` (names and JSON aliases) and `inventory_items` (SKU names and JSON local aliases).
   - Extracts and cleans phonetically relevant terms (e.g. "Ramesh Sharma", "Suresh Patil", "Amul Pure Ghee 1L", "Fortune Oil").
   - Case-insensitively deduplicates terms to prime Sarvam Saaras STT context without redundant memory overhead.

2. **Kirana Vernacular Voice Intent Parser (`parse_voice_intent`)**:
   - Classifies voice and text counter commands into typed intents: `CREDIT_UDHAAR`, `REPAYMENT_JAMA`, `STOCK_IN`, `STOCKOUT_FLAG`, and `QUERY`.
   - Extracts numeric monetary amounts (e.g. "200 rupaye", "₹300", "650 rs") across English, Hindi, and Marathi phrasing.
   - Integrates with `deterministic_engine.resolve_customer_identity`:
     - **Ambiguous Match**: Emits `status="NEEDS_DISAMBIGUATION"` with candidate cards, ambiguity reason, `"KiranaOS blocks blind writes when customer names overlap"`, and spoken Hindi prompt (e.g. *"Dukaan mein do Suresh hain: Suresh Patil (Tailor) ya Suresh Kadam (Kirana)? Kiske khate mein 200 likhoon?"*).
     - **Exact Match**: Emits `status="PROPOSAL"` with live balance preview, math breakdown in `why_am_i_seeing_this`, and spoken vernacular confirmation audio.
     - **Inventory Items**: Resolves SKU and inward quantity delta (e.g. *"Amul Ghee 5 packet aaya"*).

3. **Voice Gateway REST Router (`backend/routers/voice_router.py`)**:
   - **`POST /api/v1/voice/propose`**: Accepts `application/json` (`transcript_override`, `language_hint`) or `multipart/form-data` audio uploads. Biases STT with dynamic DB terms, parses intent, synthesizes vernacular confirmation speech via Sarvam Bulbul v3, and returns unconfirmed Proposal Card.
   - **`POST /api/v1/voice/confirm`**: Enforces `action == "APPROVE"` (Threat Model T-02-05). Executes append-only write via `deterministic_engine.add_credit_entry` or `add_repayment_entry`, updates customer last visit, atomically records audit event in `business_events`, and generates spoken confirmation audio.
   - **`POST /api/v1/voice/tts`**: Direct text-to-speech synthesis endpoint for vernacular prompts.
   - **`GET /api/v1/voice/health`**: Reports gateway status, active database connection, and Sarvam engine health.

4. **Engine Enhancements & Main Registration**:
   - Added `add_credit_entry`, `add_repayment_entry`, and `record_stock_event` to `backend/services/deterministic_engine.py`.
   - Registered `voice_router` in `backend/main.py`.

## Verification Results

Full test suite execution passing 100%:
- 16 dedicated voice gateway unit and integration tests in `tests/test_voice_gateway.py`.
- 68 total tests across all project test suites (`test_connection.py`, `test_deterministic_engine.py`, `test_identity_disambiguation.py`, `test_sarvam_engine.py`, `test_schema.py`, `test_seed_demo_data.py`, `test_voice_gateway.py`, `test_walking_skeleton_e2e.py`).
- 0 failures, 1 warning (deprecation notice from starlette testclient).

## Threat Mitigations Applied

| Threat ID | Mitigation Details | Status |
|-----------|-------------------|--------|
| T-02-04 | 10MB payload size limit enforced in `/propose` endpoint; returns HTTP 413 on oversized uploads | Verified |
| T-02-05 | Explicit `action == 'APPROVE'` check in `/confirm`; rejects unapproved or tampered requests with HTTP 400 | Verified |
| T-02-06 | Parameterized SQL queries exclusively used for all keyterm extraction and customer lookups | Verified |
| T-02-SC | FastAPI UploadFile and standard Pydantic models for safe request parsing | Verified |

## Self-Check: PASSED
- [x] `backend/services/voice_intent_parser.py` created and tested
- [x] `backend/routers/voice_router.py` created and mounted at `/api/v1/voice`
- [x] `backend/main.py` updated with `voice_router` inclusion
- [x] `tests/test_voice_gateway.py` created with 16 comprehensive unit & API tests
- [x] All 68 tests in full suite pass cleanly
