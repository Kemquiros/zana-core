"""
PerceptionEvent — canonical structure for all sensory data entering ZANA.

Every multimodal input (audio, video, image, text) is converted to this object
before reaching the Cortex. It is the "atom" of the sensory system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal, Optional


Modality = Literal["text", "audio", "vision", "multimodal"]


@dataclass
class AudioFeatures:
    """Raw acoustic features — proxies for emotional state."""
    duration_s: float
    rms_energy: float        # 0–1, higher = more vocal intensity
    zero_crossing_rate: float  # proxy for voice tension/agitation
    dominant_freq_hz: float  # fundamental pitch estimate
    speech_rate_wpm: float   # estimated words per minute


@dataclass
class VisionFeatures:
    """Structured analysis of a frame or image."""
    scene_type: str          # "indoor", "outdoor", "screen", "document", "face"
    entities: list[str]      # detected objects/people/concepts
    emotional_context: str   # "neutral", "focused", "stressed", "collaborative"
    text_content: str        # visible text in the image (implicit OCR)
    confidence: float        # 0–1


@dataclass
class PerceptionEvent:
    """
    Atomic unit of ZANA perception.
    Produced by the MultimodalGateway, consumed by the Cortex.
    """
    id: str                         = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str                  = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modality: Modality              = "text"
    session_id: Optional[str]       = None

    # ── Content by modality ──────────────────────────────────────────────────
    text: Optional[str]             = None   # raw text or audio transcript
    audio_features: Optional[AudioFeatures] = None
    vision_features: Optional[VisionFeatures] = None
    source_mime: Optional[str]      = None   # "audio/wav", "image/jpeg", "video/mp4"

    # ── ZANA processing ───────────────────────────────────────────────────────
    kalman_surprise: float          = 0.0    # Bayesian novelty score
    facts_asserted: list[str]       = field(default_factory=list)  # Fact keys sent to ReasoningEngine

    # ── Aeon response ─────────────────────────────────────────────────────────
    response_text: Optional[str]    = None
    response_audio_b64: Optional[str] = None  # base64 MP3 from TTS
    response_emotion: str           = "neutral"

    def to_dict(self) -> dict:
        d = asdict(self)
        # Strip Nones for clean response
        return {k: v for k, v in d.items() if v is not None}

    @property
    def cortex_input(self) -> str:
        """Text fed to the Cortex, regardless of the source modality."""
        if self.text:
            return self.text
        if self.vision_features:
            entities = ", ".join(self.vision_features.entities[:5])
            return f"[VISION] {self.vision_features.scene_type}: {self.vision_features.text_content or entities}"
        return "[PERCEPTION] no textual content"
