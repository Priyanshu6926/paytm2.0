"""
tests/test_sarvam_engine.py

Comprehensive unit, integration, and survivability tests for the Sarvam AI
multimodal engine layer (STT Saaras, TTS Bulbul v3, Sarvam Translate).
Validates dynamic keyterm injection, strict 6.0s timeouts, offline synthetic fallbacks,
and demo-day resilience under zero network connectivity.
"""

import base64
import io
import time
import wave
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.services.sarvam_engine import (
    MAX_AUDIO_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    SarvamEngine,
    generate_synthetic_wav_base64,
    get_sarvam_health_status,
    synthesize_speech,
    transcribe_audio,
    translate_text,
)


def test_synthetic_wav_header_and_playable_pcm():
    """
    Verifies that generate_synthetic_wav_base64 outputs valid base64 ASCII
    that decodes into a standard RIFF/WAVE header with 16-bit mono 16kHz PCM.
    """
    b64_str = generate_synthetic_wav_base64("Test prompt", "hi-IN", duration_seconds=1.0)
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0

    # Decode and check RIFF/WAVE magic bytes
    raw_wav = base64.b64decode(b64_str)
    assert raw_wav[:4] == b"RIFF"
    assert raw_wav[8:12] == b"WAVE"

    # Open with standard wave module to verify audio parameters
    with wave.open(io.BytesIO(raw_wav), "rb") as reader:
        assert reader.getnchannels() == 1  # Mono
        assert reader.getsampwidth() == 2  # 16-bit (2 bytes)
        assert reader.getframerate() == 16000  # 16kHz
        nframes = reader.getnframes()
        assert nframes == 16000  # 1.0 second * 16000
        frames = reader.readframes(nframes)
        assert len(frames) == 32000  # 16000 frames * 2 bytes


def test_synthesize_speech_fallback_speed_and_format():
    """
    Verifies that synthesize_speech fallback executes in under 100ms
    and returns fallback_used=True without raising exceptions.
    """
    start_time = time.perf_counter()
    result = synthesize_speech("Ramesh ne 300 rupaye diye", "hi-IN", mock_fallback=True)
    duration = time.perf_counter() - start_time

    assert duration < 0.10, f"Fallback execution took {duration:.4f}s (expected <0.10s)"
    assert result["fallback_used"] is True
    assert result["language_code"] == "hi-IN"
    assert "audio_base64" in result
    assert len(result["audio_base64"]) > 0

    # Verify returned fallback audio is a valid WAV
    raw = base64.b64decode(result["audio_base64"])
    assert raw[:4] == b"RIFF"


def test_synthesize_speech_timeout_graceful_degradation():
    """
    Simulates an httpx timeout when calling Sarvam TTS and verifies
    fallback audio is returned safely with fallback_used=True.
    """
    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out after 6.0s")):
            start_time = time.perf_counter()
            result = synthesize_speech("Dukaan band karne ka samay ho gaya", "hi-IN")
            elapsed = time.perf_counter() - start_time

            assert elapsed < 1.0
            assert result["fallback_used"] is True
            assert "audio_base64" in result
            assert "Connection timed out" in result["error_detail"]


def test_synthesize_speech_live_mock_response():
    """
    Simulates a successful 200 OK response from Sarvam Bulbul TTS API.
    """
    fake_audio = base64.b64encode(b"RIFFdummydataWAVE").decode("ascii")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"audios": [fake_audio]}

    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", return_value=mock_resp):
            res = synthesize_speech("Ramesh ka hisab", "hi-IN")
            assert res["fallback_used"] is False
            assert res["audio_base64"] == fake_audio
            assert res["error_detail"] is None


def test_transcribe_audio_fallback_with_keyterm_biasing():
    """
    Verifies that transcribe_audio generates biased fallback transcripts based on
    prompt_terms (customer names and inventory SKUs) without making external calls.
    """
    dummy_audio = b"RIFFmockwavdata16000pcm"

    # Fallback with Ramesh prompt terms
    res_ramesh = transcribe_audio(
        dummy_audio,
        prompt_terms=["Ramesh Sharma", "Udhaar"],
        language_code="hi-IN",
        mock_fallback=True,
    )
    assert res_ramesh["fallback_used"] is True
    assert "Ramesh" in res_ramesh["transcript"]
    assert res_ramesh["language_code"] == "hi-IN"

    # Fallback with Amul Ghee prompt terms
    res_amul = transcribe_audio(
        dummy_audio,
        prompt_terms=["Amul Ghee 1L", "Fortune Oil"],
        language_code="hi-IN",
        mock_fallback=True,
    )
    assert res_amul["fallback_used"] is True
    assert "Amul Ghee" in res_amul["transcript"]

    # Fallback with default Suresh
    res_default = transcribe_audio(
        dummy_audio,
        prompt_terms=None,
        language_code="hi-IN",
        mock_fallback=True,
    )
    assert res_default["fallback_used"] is True
    assert "Suresh" in res_default["transcript"]


def test_transcribe_audio_timeout_survivability():
    """
    Simulates an httpx timeout during speech-to-text and validates that execution
    degrades gracefully to local fallback in under 6.0 seconds.
    """
    dummy_audio = b"RIFFmockwavdata16000pcm"

    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("STT gateway timed out")):
            start_time = time.perf_counter()
            res = transcribe_audio(dummy_audio, prompt_terms=["Suresh"], language_code="hi-IN")
            elapsed = time.perf_counter() - start_time

            assert elapsed < 1.0, f"Timeout handling took too long: {elapsed:.3f}s"
            assert res["fallback_used"] is True
            assert "Suresh" in res["transcript"]
            assert "STT gateway timed out" in res["error_detail"]


def test_transcribe_audio_successful_mock_call_injects_terms():
    """
    Verifies that when STT succeeds, multipart payload contains prompt biasing
    and the transcript returned is from the API response.
    """
    dummy_audio = b"RIFFmockwavdata16000pcm"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "transcript": "Ramesh ne teen sau rupaye jama kiye",
        "language_code": "hi-IN",
    }

    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            res = transcribe_audio(
                dummy_audio,
                prompt_terms=["Ramesh Sharma", "Amul"],
                language_code="hi-IN",
            )
            assert res["fallback_used"] is False
            assert res["transcript"] == "Ramesh ne teen sau rupaye jama kiye"
            # Verify prompt parameter was sent in form data
            call_kwargs = mock_post.call_args[1]
            assert "prompt" in call_kwargs["data"]
            assert "Ramesh Sharma" in call_kwargs["data"]["prompt"]


def test_transcribe_audio_oversized_payload_protection():
    """
    Verifies that payloads exceeding MAX_AUDIO_BYTES (10MB limit) are rejected safely
    without crashing or invoking external endpoints per T-02-03.
    """
    oversized = b"0" * (MAX_AUDIO_BYTES + 1024)
    res = transcribe_audio(oversized, mock_fallback=False)
    assert res["fallback_used"] is True
    assert "exceeds" in res["error_detail"]


def test_translate_text_offline_dictionary_support():
    """
    Tests vernacular Kirana phrase translations across Hindi, Marathi, and English
    using the deterministic offline dictionary fallback.
    """
    debt_msg = "Namaste Ramesh ji, aapka kirana dukan ka 650 rupaye udhaar baki hai. Kripya diye gaye Paytm link se bhugtan karein."

    # Hindi to Marathi translation
    mr_res = translate_text(debt_msg, "hi-IN", "mr-IN", mock_fallback=True)
    assert mr_res["fallback_used"] is True
    assert "Namaskar Ramesh ji" in mr_res["translated_text"]
    assert "udhari baki aahe" in mr_res["translated_text"]

    # Hindi to English translation
    en_res = translate_text(debt_msg, "hi-IN", "en-IN", mock_fallback=True)
    assert en_res["fallback_used"] is True
    assert "Hello Ramesh ji" in en_res["translated_text"]
    assert "Paytm link" in en_res["translated_text"]

    # Supplier price-creep alert
    oil_msg = "Gupta Wholesalers ne Fortune Oil ka rate 7.58% badha diya hai."
    oil_mr = translate_text(oil_msg, "hi-IN", "mr-IN", mock_fallback=True)
    assert oil_mr["fallback_used"] is True
    assert "Fortune Oil che dar 7.58%" in oil_mr["translated_text"]

    # EOD Settlement briefing
    eod_msg = "Aaj ka net settlement 5815 rupaye bank mein transfer ho gaya hai."
    eod_mr = translate_text(eod_msg, "hi-IN", "mr-IN", mock_fallback=True)
    assert eod_mr["fallback_used"] is True
    assert "5815 rupaye banket transfer" in eod_mr["translated_text"]


def test_translate_text_timeout_and_mock_response():
    """
    Tests timeout handling and mock 200 API response for Sarvam Translate.
    """
    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Translation timed out")):
            res = translate_text("Suresh ka 200 rupaye udhaar likh do", "hi-IN", "mr-IN")
            assert res["fallback_used"] is True
            assert "Suresh che 200 rupaye" in res["translated_text"]
            assert "Translation timed out" in res["error_detail"]

    # Test mock 200 OK
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"translated_text": "Live translated text in Marathi"}

    with patch.dict("os.environ", {"SARVAM_API_KEY": "dummy_test_key"}):
        with patch("httpx.Client.post", return_value=mock_resp):
            res2 = translate_text("Suresh ka udhaar", "hi-IN", "mr-IN")
            assert res2["fallback_used"] is False
            assert res2["translated_text"] == "Live translated text in Marathi"


def test_sarvam_health_status_contract_and_security():
    """
    Verifies the health status structure, supported languages, and ensures
    SARVAM_API_KEY is never exposed in the health response per T-02-02.
    """
    with patch.dict("os.environ", {"SARVAM_API_KEY": "super_secret_production_key_12345"}):
        status = get_sarvam_health_status()

        assert status["api_key_configured"] is True
        assert status["timeout_seconds"] == REQUEST_TIMEOUT_SECONDS
        assert status["timeout_seconds"] == 6.0
        assert status["fallback_engine_ready"] is True
        assert "hi-IN" in status["supported_languages"]
        assert "mr-IN" in status["supported_languages"]
        assert "en-IN" in status["supported_languages"]
        assert status["models"]["stt"] == "saaras:v4"
        assert status["models"]["tts"] == "bulbul:v3"

        # T-02-02 Security assertion: raw key must NEVER appear in output
        status_str = str(status)
        assert "super_secret_production_key_12345" not in status_str


def test_sarvam_engine_class_wrapper():
    """
    Validates that the SarvamEngine wrapper class exposes all methods accurately.
    """
    assert SarvamEngine.get_health_status()["fallback_engine_ready"] is True

    synth = SarvamEngine.synthesize_speech("Test", mock_fallback=True)
    assert synth["fallback_used"] is True

    trans = SarvamEngine.transcribe_audio(b"dummy", mock_fallback=True)
    assert trans["fallback_used"] is True

    tr = SarvamEngine.translate_text("Suresh ka 200 rupaye udhaar likh do", "hi-IN", "mr-IN", mock_fallback=True)
    assert tr["fallback_used"] is True
