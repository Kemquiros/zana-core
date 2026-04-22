"""
TTSEngine — the Aeon's voice.

Stack:
  Primary  : edge-tts (Microsoft Azure TTS, async, free tier, high quality)
  Fallback : pyttsx3 (OS TTS engine, fully offline)
  Mock     : empty bytes with minimal WAV header

Default voice is "es-CO-GonzaloNeural" (neutral Colombian Spanish).
Configurable via AEON_VOICE environment variable.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import Optional

logger = logging.getLogger("zana.tts")

# Available voices map (edge-tts)
VOICES = {
    "es-co": "es-CO-GonzaloNeural",  # Colombian Spanish male
    "es-mx": "es-MX-JorgeNeural",  # Mexican Spanish male
    "es-es": "es-ES-AlvaroNeural",  # Castilian Spanish male
    "en-us": "en-US-AriaNeural",  # American English female
    "en-gb": "en-GB-RyanNeural",  # British English male
}
AEON_VOICE = os.getenv("AEON_VOICE", VOICES["es-co"])


class TTSEngine:
    """
    Converts text → MP3 audio bytes.
    Backend is auto-detected in quality order.
    """

    def __init__(self) -> None:
        self._backend: Optional[str] = None

    def _detect_backend(self) -> str:
        if self._backend:
            return self._backend
        try:
            import edge_tts  # noqa: F401

            self._backend = "edge-tts"
        except ImportError:
            try:
                import pyttsx3  # noqa: F401

                self._backend = "pyttsx3"
                logger.warning(
                    "⚠️  [TTS] edge-tts not available. Using pyttsx3 (basic quality)."
                )
            except ImportError:
                self._backend = "mock"
                logger.warning("⚠️  [TTS] No TTS engine found. uv add edge-tts")
        return self._backend

    # ── Public API ───────────────────────────────────────────────────────────

    def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesizes text to MP3 audio. Synchronous (calls async loop internally).
        Returns empty bytes if TTS is not available.
        """
        if not text or not text.strip():
            return self._silent_mp3()

        backend = self._detect_backend()
        voice = voice or AEON_VOICE

        try:
            if backend == "edge-tts":
                return asyncio.run(self._synthesize_edge(text, voice))
            elif backend == "pyttsx3":
                return self._synthesize_pyttsx3(text)
            else:
                return self._silent_mp3()
        except Exception as e:
            logger.error("❌ [TTS] Synthesis error: %s", e)
            return self._silent_mp3()

    async def synthesize_async(self, text: str, voice: Optional[str] = None) -> bytes:
        """Async version for use within FastAPI handlers."""
        if not text or not text.strip():
            return self._silent_mp3()
        backend = self._detect_backend()
        voice = voice or AEON_VOICE
        if backend == "edge-tts":
            return await self._synthesize_edge(text, voice)
        return self.synthesize(text, voice)

    # ── Backends ──────────────────────────────────────────────────────────────

    async def _synthesize_edge(self, text: str, voice: str) -> bytes:
        import edge_tts

        buf = io.BytesIO()
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        audio_bytes = buf.getvalue()
        logger.info(
            "🔊 [TTS] edge-tts generated %d bytes | '%s…'", len(audio_bytes), text[:40]
        )
        return audio_bytes

    def _synthesize_pyttsx3(self, text: str) -> bytes:
        import pyttsx3

        engine = pyttsx3.init()
        io.BytesIO()
        # pyttsx3 has no native buffer output — save to temp file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp_path)

    def _silent_mp3(self) -> bytes:
        """Minimal valid WAV header — 0.1s of silence."""
        import struct

        sample_rate = 8000
        duration_samples = sample_rate // 10
        data = b"\x00" * (duration_samples * 2)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(data),
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b"data",
            len(data),
        )
        return header + data

    @staticmethod
    def list_voices() -> dict[str, str]:
        """Returns the available voices map."""
        return dict(VOICES)
