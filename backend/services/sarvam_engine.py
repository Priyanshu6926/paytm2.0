"""
backend/services/sarvam_engine.py

Sarvam AI Integration Service Layer for KiranaOS / Munim-AI.
Wraps Sarvam Saaras STT (v4), Bulbul v3 TTS, and Sarvam Translate.
Enforces the Law of Demo-Day Survivability with strict 6.0-second timeouts
and high-fidelity synthetic fallbacks.
"""

import base64
import io
import logging
import math
import os
import struct
import wave
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Configuration & Constants
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
REQUEST_TIMEOUT_SECONDS = 6.0
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB limit per threat model T-02-03


def generate_synthetic_wav_base64(
    text: str = "",
    language_code: str = "hi-IN",
    duration_seconds: float = 1.5,
) -> str:
    """
    Generates a dual-tone pleasant acoustic chime (523.25 Hz C5 and 659.25 Hz E5)
    encoded as 16-bit mono 16000Hz PCM WAV, returned as a base64 ASCII string.
    Ensures valid RIFF/WAVE header and 100% offline survivability per D-02.
    """
    sample_rate = 16000
    num_samples = int(sample_rate * max(0.2, duration_seconds))
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit (2 bytes per sample)
        wav_file.setframerate(sample_rate)

        # Generate dual-tone chime: C5 (523.25 Hz) + E5 (659.25 Hz)
        f1 = 523.25
        f2 = 659.25
        frames = bytearray()

        for i in range(num_samples):
            t = float(i) / sample_rate
            # Exponential decay envelope for natural chime sound
            envelope = math.exp(-2.5 * t / max(0.2, duration_seconds))
            # Combine two pure sines
            val = (0.45 * math.sin(2.0 * math.pi * f1 * t) + 0.45 * math.sin(2.0 * math.pi * f2 * t)) * envelope
            # Convert to signed 16-bit integer (-32768 to 32767)
            sample_val = int(val * 32767.0)
            sample_val = max(-32768, min(32767, sample_val))
            frames.extend(struct.pack("<h", sample_val))

        wav_file.writeframes(frames)

    raw_bytes = buffer.getvalue()
    return base64.b64encode(raw_bytes).decode("ascii")


def synthesize_speech(
    text: str,
    target_language_code: str = "hi-IN",
    speaker: str = "meera",
    mock_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Synthesizes speech using Sarvam Bulbul v3 TTS API with a 6.0-second timeout.
    If the API key is missing, network fails, or timeout occurs, immediately
    returns synthetic base64 WAV audio with fallback_used=True per D-02.
    """
    api_key = os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)

    if mock_fallback or not api_key:
        return {
            "audio_base64": generate_synthetic_wav_base64(text, target_language_code),
            "language_code": target_language_code,
            "fallback_used": True,
            "error_detail": "Mock fallback requested" if mock_fallback else "SARVAM_API_KEY not configured",
        }

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": [text],
        "target_language_code": target_language_code,
        "speaker": speaker,
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 16000,
        "enable_preprocessing": True,
        "model": "bulbul:v3",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(SARVAM_TTS_URL, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                audios = data.get("audios", [])
                if audios:
                    return {
                        "audio_base64": audios[0],
                        "language_code": target_language_code,
                        "fallback_used": False,
                        "error_detail": None,
                    }
                else:
                    return {
                        "audio_base64": generate_synthetic_wav_base64(text, target_language_code),
                        "language_code": target_language_code,
                        "fallback_used": True,
                        "error_detail": "Sarvam API returned empty audio list",
                    }
            else:
                return {
                    "audio_base64": generate_synthetic_wav_base64(text, target_language_code),
                    "language_code": target_language_code,
                    "fallback_used": True,
                    "error_detail": f"Sarvam API error: HTTP {response.status_code}",
                }
    except (httpx.TimeoutException, httpx.RequestError, Exception) as exc:
        logger.warning("TTS request failed or timed out: %s. Using synthetic fallback.", exc)
        return {
            "audio_base64": generate_synthetic_wav_base64(text, target_language_code),
            "language_code": target_language_code,
            "fallback_used": True,
            "error_detail": str(exc),
        }
