"""
tests/test_sarvam_engine.py

Unit and survivability tests for Sarvam AI Integration Service Layer.
Tests synthetic WAV generation, Bulbul v3 TTS fallback, and demo-day resilience.
"""

import base64
import io
import time
import wave
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.services.sarvam_engine import (
    REQUEST_TIMEOUT_SECONDS,
    generate_synthetic_wav_base64,
    synthesize_speech,
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
