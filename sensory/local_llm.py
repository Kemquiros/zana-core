"""
LocalLLM — provider-agnostic LLM inference backbone for Aeon responses.

Supports multiple providers via LiteLLM:
- OpenAI (openai/...)
- Anthropic (anthropic/...)
- Gemini (gemini/...)
- Groq (groq/...)
- OpenRouter (openrouter/...)
- Ollama (ollama/...)

Configurable via environment:
  XANA_PRIMARY_MODEL — default: "anthropic/claude-3-5-haiku-20241022"
  XANA_VISION_MODEL  — default: "anthropic/claude-3-5-sonnet-20241022"
  OLLAMA_API_BASE    — default: "http://localhost:11434" (when using ollama/... models)
"""
from __future__ import annotations

import logging
import os
from typing import Optional
import litellm

logger = logging.getLogger("xana.local_llm")

# Default models
PRIMARY_MODEL = os.getenv("XANA_PRIMARY_MODEL", "anthropic/claude-3-5-haiku-20241022")
VISION_MODEL = os.getenv("XANA_VISION_MODEL", "anthropic/claude-3-5-sonnet-20241022")

# Suppress verbose litellm logs
litellm.set_verbose = False

_XANA_SYSTEM = """You are XANA, an advanced AI cognitive system and personal assistant.
You help with technical analysis, project management, business strategy, and software engineering.

Rules:
- Respond in the SAME LANGUAGE as the user (Spanish if Spanish, English if English).
- Be concise, direct, and precise. No filler phrases.
- For technical questions: provide architecture-level thinking.
- For project questions: identify the critical path and blockers.
- Maximum 3-4 sentences for conversational responses. Longer for detailed analysis.
- Never refuse a legitimate business or technical question."""


class LocalLLM:
    """
    Unified LLM client using litellm to support OpenAI, Gemini, Anthropic, Ollama, Groq, OpenRouter, etc.
    """
    def __init__(self) -> None:
        self.primary_model = PRIMARY_MODEL
        self.vision_model = VISION_MODEL
        logger.info(f"🧠 [LOCAL_LLM] Engine initialized. Primary: {self.primary_model}")

    def generate(self, user_input: str, context: str = "", session_id: str = "") -> str:
        """
        Generate Aeon response from user input + optional cortex context.
        """
        messages = [{"role": "system", "content": _XANA_SYSTEM}]
        if context:
            messages.append({
                "role": "system",
                "content": f"[MEMORY CONTEXT]\n{context}"
            })
        messages.append({"role": "user", "content": user_input})

        try:
            # LiteLLM resolves the provider from the model prefix and env API keys
            # (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, etc.)
            response = litellm.completion(
                model=self.primary_model,
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"☁️  [LLM] {self.primary_model} → '{text[:60]}…'")
            return text
        except Exception as e:
            logger.error(f"❌ [LLM] Error generating response with {self.primary_model}: {e}")
            return self._template_response(user_input, context)

    def _template_response(self, user_input: str, context: str) -> str:
        if context:
            return f"[Inference Error] {user_input}\n\n[MEMORY CONTEXT]\n{context}"
        return f"[Inference Error] {user_input}"

    def analyze_image_local(
        self, image_bytes: bytes, mime_type: str, context_hint: str = ""
    ) -> Optional[str]:
        """
        Analyze image via vision model.
        Returns raw JSON string.
        """
        import base64
        b64 = base64.standard_b64encode(image_bytes).decode()
        data_uri = f"data:{mime_type};base64,{b64}"

        prompt = """Analyze this image. Return ONLY valid JSON (no markdown):
{"scene_type":"<indoor|outdoor|screen|document|face|mixed>","entities":["..."],"emotional_context":"<neutral|focused|stressed|collaborative|creative|chaotic>","text_content":"<visible text or empty>","description":"<one sentence>","facts":["..."],"confidence":<0.0-1.0>}"""

        if context_hint:
            prompt += f"\nContext: {context_hint}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ]

        try:
            response = litellm.completion(
                model=self.vision_model,
                messages=messages,
                temperature=0.1,
                max_tokens=512
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"🔭 [VISION] {self.vision_model} → '{text[:60]}…'")
            return text
        except Exception as e:
            logger.error(f"❌ [VISION] Error analyzing image with {self.vision_model}: {e}")
            return None

    def backend_info(self) -> dict:
        return {
            "primary_model": self.primary_model,
            "vision_model": self.vision_model,
            "provider_agnostic": True
        }

# Singleton
_local_llm = LocalLLM()

def get_local_llm() -> LocalLLM:
    return _local_llm