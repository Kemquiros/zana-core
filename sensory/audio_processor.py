"""
AudioProcessor — STT + acoustic feature extraction.

Stack:
  Primary  : faster-whisper (local, tiny model, ~75 MB, no API required)
  Fallback : openai-whisper  (if faster-whisper is not available)
  Mock     : empty transcript + zero features (if neither is available)

AudioProcessor is stateless — receives bytes, returns data.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from dataclasses import dataclass

import numpy as np

from .perception_event import AudioFeatures

logger = logging.getLogger("zana.audio")

# Whisper model to use. "tiny" = fast on CPU, low RAM usage.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")


@dataclass
class TranscriptionResult:
    transcript: str
    language: str
    confidence: float  # 0–1, average log-prob of segments
    features: AudioFeatures


class AudioProcessor:
    """
    Converts raw audio → transcript + AudioFeatures.

    Model is lazy-loaded (only when needed).
    """

    def __init__(self) -> None:
        self._model = None
        self._backend: str = "none"

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
            self._backend = "faster-whisper"
            logger.info("🎤 [AUDIO] faster-whisper '%s' loaded.", WHISPER_MODEL)
        except ImportError:
            try:
                import whisper

                self._model = whisper.load_model(WHISPER_MODEL)
                self._backend = "openai-whisper"
                logger.info("🎤 [AUDIO] openai-whisper '%s' loaded.", WHISPER_MODEL)
            except ImportError:
                self._backend = "mock"
                logger.warning(
                    "⚠️  [AUDIO] No STT engine found. Install: uv add faster-whisper"
                )

    # ── Public API ───────────────────────────────────────────────────────────

    def transcribe(
        self, audio_bytes: bytes, mime_type: str = "audio/wav"
    ) -> TranscriptionResult:
        """
        Transcribes audio_bytes to text.
        Accepts WAV, MP3, OGG, FLAC, M4A (any format supported by ffmpeg).
        """
        self._load_model()
        features = self._extract_features(audio_bytes)

        if self._backend == "none" or self._backend == "mock":
            return TranscriptionResult(
                transcript="[STT not available — install faster-whisper]",
                language="es",
                confidence=0.0,
                features=features,
            )

        # Write to temp file (Whisper requires a path or file-like object)
        ext = mime_type.split("/")[-1].replace("mpeg", "mp3")
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            if self._backend == "faster-whisper":
                return self._transcribe_faster(tmp_path, features)
            else:
                return self._transcribe_openai(tmp_path, features)
        finally:
            os.unlink(tmp_path)

    # ── Backends ──────────────────────────────────────────────────────────────

    def _transcribe_faster(
        self, path: str, features: AudioFeatures
    ) -> TranscriptionResult:
        segments, info = self._model.transcribe(path, beam_size=3, language=None)
        transcript = " ".join(s.text.strip() for s in segments).strip()
        avg_conf = float(
            np.mean(
                [
                    np.exp(s.avg_logprob)
                    for s in self._model.transcribe(path, beam_size=3)[0]
                ]
                or [0.0]
            )
        )
        logger.info("🎤 [STT] '%s…' (lang=%s)", transcript[:60], info.language)
        return TranscriptionResult(
            transcript=transcript or "[silence]",
            language=info.language,
            confidence=min(1.0, avg_conf),
            features=features,
        )

    def _transcribe_openai(
        self, path: str, features: AudioFeatures
    ) -> TranscriptionResult:
        result = self._model.transcribe(path)
        return TranscriptionResult(
            transcript=result["text"].strip() or "[silence]",
            language=result.get("language", "es"),
            confidence=0.75,  # openai-whisper does not expose confidence directly
            features=features,
        )

    # ── Feature extraction (Rust DSP → numpy fallback) ───────────────────────

    def _extract_features(self, audio_bytes: bytes) -> AudioFeatures:
        # Primary: Rust zana_audio_dsp (zero-copy, Cooley-Tukey FFT)
        try:
            import zana_audio_dsp

            f = zana_audio_dsp.extract_features(audio_bytes)
            return AudioFeatures(
                duration_s=round(f.duration_s, 2),
                rms_energy=round(f.rms_energy, 3),
                zero_crossing_rate=round(f.zero_crossing_rate, 4),
                dominant_freq_hz=round(f.dominant_freq_hz, 1),
                speech_rate_wpm=round(f.speech_rate_wpm, 1),
            )
        except Exception:
            pass

        # Fallback: numpy/soundfile
        try:
            import soundfile as sf

            with io.BytesIO(audio_bytes) as buf:
                data, sr = sf.read(buf, dtype="float32", always_2d=False)
            if data.ndim > 1:
                data = data.mean(axis=1)
            duration_s = len(data) / sr
            rms = float(np.sqrt(np.mean(data**2)))
            zcr = float(np.mean(np.abs(np.diff(np.sign(data)))) / 2)
            fft = np.abs(np.fft.rfft(data[:sr] if len(data) >= sr else data))
            freqs = np.fft.rfftfreq(len(data[:sr] if len(data) >= sr else data), 1 / sr)
            dom_freq = float(freqs[np.argmax(fft)]) if len(fft) > 0 else 0.0
            voice_activity = float(np.mean(np.abs(data) > 0.01))
            return AudioFeatures(
                duration_s=round(duration_s, 2),
                rms_energy=round(min(1.0, rms * 4), 3),
                zero_crossing_rate=round(zcr, 4),
                dominant_freq_hz=round(dom_freq, 1),
                speech_rate_wpm=round(voice_activity * 180.0, 1),
            )
        except Exception as e:
            logger.debug("Feature extraction fallback: %s", e)
            return AudioFeatures(
                duration_s=0.0,
                rms_energy=0.0,
                zero_crossing_rate=0.0,
                dominant_freq_hz=0.0,
                speech_rate_wpm=0.0,
            )

    def infer_emotion_from_features(self, f: AudioFeatures) -> str:
        # Delegate to Rust if available, otherwise Python heuristic
        try:
            import zana_audio_dsp

            return zana_audio_dsp.infer_emotion(
                f.rms_energy, f.zero_crossing_rate, f.speech_rate_wpm
            )
        except Exception:
            pass
        if f.rms_energy > 0.6 and f.zero_crossing_rate > 0.1:
            return "agitated"
        if f.rms_energy > 0.4 and f.speech_rate_wpm > 160:
            return "excited"
        if f.rms_energy < 0.1 and f.speech_rate_wpm < 80:
            return "calm"
        if f.rms_energy < 0.05:
            return "subdued"
        return "neutral"
