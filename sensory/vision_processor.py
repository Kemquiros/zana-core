"""
VisionProcessor — image and video analysis via Claude Vision.

Stack:
  Primary  : claude-sonnet-4-6 (Anthropic Vision API)
  Fallback : descriptive mock (if ANTHROPIC_API_KEY is not configured)

For video: extracts keyframes every N seconds and analyzes each one.
Output is a VisionFeatures object + natural language description.
"""

from __future__ import annotations

import base64
import io
import logging
import os

from .perception_event import VisionFeatures

logger = logging.getLogger("zana.vision")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "claude-sonnet-4-6")
KEYFRAME_INTERVAL = float(os.getenv("KEYFRAME_INTERVAL_S", "3.0"))

_VISION_PROMPT = """Analyze this image as ZANA, an AI cognitive system observing the user's world.
Return a JSON with exactly these fields (no markdown, raw JSON):
{
  "scene_type": "<indoor|outdoor|screen|document|face|mixed>",
  "entities": ["<list of up to 8 key entities/objects/people>"],
  "emotional_context": "<neutral|focused|stressed|collaborative|creative|chaotic>",
  "text_content": "<any readable text visible in the image, or empty string>",
  "description": "<one sentence describing what is happening>",
  "facts": ["<list of up to 5 factual statements ZANA should assert about this scene>"],
  "confidence": <0.0 to 1.0>
}"""


class VisionProcessor:
    """Analyzes images and video. Local-first: Ollama LLaVA → Claude → mock."""

    def __init__(self) -> None:
        self._claude_client = None

    def _get_claude(self):
        if self._claude_client is not None:
            return self._claude_client
        if not ANTHROPIC_API_KEY:
            return None
        try:
            import anthropic

            self._claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("👁️  [VISION] Claude Vision client initialized.")
        except ImportError:
            logger.warning("⚠️  [VISION] anthropic SDK not available.")
        return self._claude_client

    @property
    def _client(self):
        """Legacy compat — health endpoint checks this."""
        return self._get_claude()

    # ── Public API ───────────────────────────────────────────────────────────

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        context_hint: str = "",
    ) -> tuple[str, VisionFeatures]:
        # 1. Try local Ollama vision model
        from .local_llm import get_local_llm

        local = get_local_llm()
        raw = local.analyze_image_local(image_bytes, mime_type, context_hint)
        if raw:
            return self._parse_vision_response(raw)

        # 2. Claude Vision fallback
        claude = self._get_claude()
        if claude is None:
            return self._mock_analysis(context_hint)

        try:
            b64 = base64.standard_b64encode(image_bytes).decode()
            prompt = _VISION_PROMPT
            if context_hint:
                prompt += f"\n\nAdditional context: {context_hint}"

            message = claude.messages.create(
                model=VISION_MODEL,
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            return self._parse_vision_response(message.content[0].text.strip())

        except Exception as e:
            logger.error("❌ [VISION] Claude API error: %s", e)
            return self._mock_analysis(context_hint)

    def analyze_video(
        self,
        video_bytes: bytes,
        mime_type: str = "video/mp4",
        context_hint: str = "",
    ) -> list[tuple[str, VisionFeatures]]:
        """
        Extracts keyframes from a video and analyzes each one.
        Returns list of (description, features) per keyframe.
        """
        frames = self._extract_keyframes(video_bytes, mime_type)
        if not frames:
            logger.warning("⚠️  [VISION] Could not extract keyframes from video.")
            return [self._mock_analysis(context_hint)]

        results = []
        for i, (frame_bytes, frame_mime) in enumerate(frames):
            logger.info("🎬 [VISION] Analyzing keyframe %d/%d", i + 1, len(frames))
            desc, features = self.analyze_image(frame_bytes, frame_mime, context_hint)
            results.append((desc, features))
        return results

    # ── Keyframe extraction ───────────────────────────────────────────────────

    def _extract_keyframes(
        self, video_bytes: bytes, mime_type: str
    ) -> list[tuple[bytes, str]]:
        """
        Extracts 1 frame every KEYFRAME_INTERVAL seconds using imageio (no OpenCV).
        """
        try:
            import imageio.v3 as iio

            with io.BytesIO(video_bytes) as buf:
                meta = iio.immeta(buf, plugin="pyav")
                fps = float(meta.get("fps", 24))
                int(meta.get("n_frames", 0))

            step = max(1, int(fps * KEYFRAME_INTERVAL))
            frames = []

            with io.BytesIO(video_bytes) as buf:
                for idx, frame in enumerate(iio.imiter(buf, plugin="pyav")):
                    if idx % step == 0:
                        # Convert array → JPEG bytes
                        out = io.BytesIO()
                        iio.imwrite(out, frame, extension=".jpg")
                        frames.append((out.getvalue(), "image/jpeg"))
                    if len(frames) >= 8:  # maximum 8 keyframes per video
                        break

            logger.info(
                "🎬 [VISION] %d keyframes extracted (fps=%.1f, step=%d)",
                len(frames),
                fps,
                step,
            )
            return frames

        except ImportError:
            logger.warning("⚠️  [VISION] imageio no disponible. uv add imageio")
            return []
        except Exception as e:
            logger.error("❌ [VISION] Error extrayendo keyframes: %s", e)
            return []

    # ── Parsing and fallback ─────────────────────────────────────────────────

    def _parse_vision_response(self, raw: str) -> tuple[str, VisionFeatures]:
        import json

        try:
            # Strip markdown code blocks if present
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            desc = data.get("description", "Scene analyzed.")
            features = VisionFeatures(
                scene_type=data.get("scene_type", "mixed"),
                entities=data.get("entities", []),
                emotional_context=data.get("emotional_context", "neutral"),
                text_content=data.get("text_content", ""),
                confidence=float(data.get("confidence", 0.7)),
            )
            logger.info(
                "👁️  [VISION] Scene: %s | Entities: %s",
                desc[:60],
                features.entities[:3],
            )
            return desc, features
        except json.JSONDecodeError:
            # Claude returned non-JSON; use raw text as description
            logger.debug("⚠️  [VISION] JSON parsing fallback — using raw text")
            return raw[:200], VisionFeatures(
                scene_type="mixed",
                entities=[],
                emotional_context="neutral",
                text_content="",
                confidence=0.4,
            )

    def _mock_analysis(self, hint: str = "") -> tuple[str, VisionFeatures]:
        desc = f"[VISION MOCK] {hint or 'Image received. Set ANTHROPIC_API_KEY for real analysis.'}"
        return desc, VisionFeatures(
            scene_type="screen",
            entities=["screen", "text", "code"],
            emotional_context="focused",
            text_content="",
            confidence=0.0,
        )
