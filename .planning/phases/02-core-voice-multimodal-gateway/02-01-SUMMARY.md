---
phase: 02-core-voice-multimodal-gateway
plan: 01
subsystem: voice-multimodal
tags:
  - sarvam-ai
  - saaras-stt
  - bulbul-tts
  - vernacular-translation
  - fallback-engine
status: complete
requires:
  - 01-01
  - 01-02
provides:
  - Sarvam Saaras STT with dynamic keyterm biasing
  - Sarvam Bulbul v3 TTS with synthetic WAV fallback
  - Sarvam Translate with deterministic vernacular dictionary
  - SarvamEngine service layer and health status
affects:
  - 02-02
  - 02-03
tech-stack:
  added:
    - httpx (v0.28.1)
    - Python standard library wave/struct/math for 16-bit 16kHz PCM WAV synthesis
  patterns:
    - Law of Demo-Day Survivability (strict 6.0s timeout + synthetic fallback)
    - Keyterm context biasing for codemix Indian retail speech
    - Vernacular domain dictionary fallback
key-files:
  created:
    - backend/services/sarvam_engine.py
    - tests/test_sarvam_engine.py
  modified: []
decisions:
  - "D-01: Wrap Sarvam Saaras STT (saaras:v4), Bulbul v3 TTS, and Translate with SARVAM_API_KEY support"
  - "D-02: Enforce 6.0-second timeout on all external network calls with sub-100ms offline fallback execution"
  - "D-03: Provide deterministic offline dictionary for Kirana debt recovery, price creep, and closing ritual vernacular phrases"
metrics:
  duration: 4m
  completed_date: "2026-11-10"
actuals:
  tokens: 44000
  tasks: 2
  commits: 2
  plan_head_before: 8d7ead67ad45e69db9e64e9a0c0e3a6bb5c689d0
  plan_head_after: c5fb8d9760aa01f5c71b698dd3fa0b322a30ca58
---

# Phase 2 Plan 1: Sarvam Multimodal Service Layer Summary

Sarvam AI multimodal integration service layer wrapping Saaras STT (`saaras:v4`), Bulbul v3 TTS, and Sarvam Translate with strict 6.0-second timeout enforcement, dynamic keyterm biasing, and offline synthetic WAV fallback.

## Delivered Capabilities

1. **Synthetic Audio & TTS Tracer (`synthesize_speech` & `generate_synthetic_wav_base64`)**:
   - Python standard library acoustic chime synthesizer producing valid 16-bit mono 16000Hz PCM WAV base64 audio.
   - Dual-tone frequencies at 523.25 Hz (C5) and 659.25 Hz (E5) with natural exponential decay.
   - Fallback executes in $<100\text{ms}$ when unauthenticated, offline, or timed out.
   - Live endpoint support for Sarvam Bulbul v3 TTS (`https://api.sarvam.ai/text-to-speech`).

2. **Speech-to-Text with Keyterm Biasing (`transcribe_audio`)**:
   - Submits audio to Sarvam Saaras v4 STT in codemix mode (`mode="codemix"`, `model="saaras:v4"`).
   - Injects dynamic `prompt_terms` (customer names and inventory SKUs) into the prompt parameter for phonetic biasing.
   - Enforces a 10MB payload size limit per threat model T-02-03.
   - Gracefully degrades to domain demo phrases ("Suresh ka 200 rupaye udhaar likh do", "Ramesh ne 300 rupaye jama kiye", "Amul Ghee 5 packet aaya") when offline or timed out.

3. **Vernacular Translation Engine (`translate_text`)**:
   - Connects to Sarvam Translate (`https://api.sarvam.ai/translate`).
   - Deterministic offline fallback dictionary for core Kirana domain phrases across Hindi (`hi-IN`), Marathi (`mr-IN`), and English (`en-IN`).
   - Handles Boli-Baki debt reminders, supplier price-creep notifications, and EOD settlement briefings.

4. **Engine Health & Security Guard (`get_sarvam_health_status`)**:
   - Reports `api_key_configured`, `timeout_seconds=6.0`, `fallback_engine_ready=True`, and `supported_languages=["hi-IN", "mr-IN", "en-IN"]`.
   - Never exposes secret API keys in logs or responses per threat model T-02-02.

## Verification & Test Results

- All 12 unit and survivability tests in `tests/test_sarvam_engine.py` passed cleanly in 0.12s.
- Full test suite (52 tests across all backend services, deterministic engine, and API routes) passed with 0 failures in 0.38s.

| Test Case | Scope | Status |
|-----------|-------|--------|
| `test_synthetic_wav_header_and_playable_pcm` | Valid RIFF/WAVE header & 16-bit 16kHz PCM audio | PASSED |
| `test_synthesize_speech_fallback_speed_and_format` | Fallback execution under 100ms | PASSED |
| `test_synthesize_speech_timeout_graceful_degradation` | 6.0s timeout simulation degrades to fallback | PASSED |
| `test_synthesize_speech_live_mock_response` | 200 OK Bulbul response parsing | PASSED |
| `test_transcribe_audio_fallback_with_keyterm_biasing` | Biased fallback transcript matching terms | PASSED |
| `test_transcribe_audio_timeout_survivability` | STT timeout handling within <1s | PASSED |
| `test_transcribe_audio_successful_mock_call_injects_terms` | Form data prompt injection verification | PASSED |
| `test_transcribe_audio_oversized_payload_protection` | >10MB payload rejection per T-02-03 | PASSED |
| `test_translate_text_offline_dictionary_support` | Hindi/Marathi/English vernacular dictionary | PASSED |
| `test_translate_text_timeout_and_mock_response` | Translation timeout and live parsing | PASSED |
| `test_sarvam_health_status_contract_and_security` | Key redaction and health schema verification | PASSED |
| `test_sarvam_engine_class_wrapper` | Static class interface parity | PASSED |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `backend/services/sarvam_engine.py` created and tested
- [x] `tests/test_sarvam_engine.py` created with 12 passing tests
- [x] Commit `75ae42d` exists in git history
- [x] Commit `c5fb8d9` exists in git history
