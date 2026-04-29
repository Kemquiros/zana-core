"""
Transport Abstraction Layer — decouple LLM provider from cognitive modules.

Each ZANA module (curator, compressor, orchestrator, swarm) can use a
different provider and model via env vars, with zero code changes.

Configuration pattern:
    ZANA_PRIMARY_PROVIDER=anthropic        # fallback for all roles
    ZANA_PRIMARY_MODEL=claude-3-5-haiku-20241022

    ZANA_CURATOR_PROVIDER=ollama           # override for curator role
    ZANA_CURATOR_MODEL=gemma4

    ZANA_COMPRESSOR_PROVIDER=anthropic
    ZANA_COMPRESSOR_MODEL=claude-3-5-haiku-20241022

Available providers: anthropic | ollama | openai | groq
"""
from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List

logger = logging.getLogger(__name__)

# Common message format shared by all transports
Msg = Dict[str, str]  # {"role": "user"|"assistant"|"system", "content": str}


# ──────────────────────────────────────────────────────────────────────
# Base
# ──────────────────────────────────────────────────────────────────────

class BaseTransport(ABC):
    """Common interface. Each provider subclasses this — callers never import SDKs directly."""

    def __init__(self, model: str, max_tokens: int = 1024):
        self.model = model
        self.max_tokens = max_tokens

    @abstractmethod
    def invoke(self, messages: List[Msg], **kwargs) -> str:
        """Synchronous inference. Returns plain text response."""

    async def ainvoke(self, messages: List[Msg], **kwargs) -> str:
        """Async inference. Default: runs invoke in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.invoke(messages, **kwargs))

    # Convenience helpers -----------------------------------------------

    def invoke_prompt(self, prompt: str, **kwargs) -> str:
        return self.invoke([{"role": "user", "content": prompt}], **kwargs)

    async def ainvoke_prompt(self, prompt: str, **kwargs) -> str:
        return await self.ainvoke([{"role": "user", "content": prompt}], **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"


# ──────────────────────────────────────────────────────────────────────
# Anthropic
# ──────────────────────────────────────────────────────────────────────

class AnthropicTransport(BaseTransport):
    """Uses langchain-anthropic (already in orchestrator deps)."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022", max_tokens: int = 1024):
        super().__init__(model, max_tokens)
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        self._llm = ChatAnthropic(
            model=model,
            api_key=os.getenv("ANTHROPIC_API_KEY", "sk-placeholder"),
            max_tokens=max_tokens,
        )
        self._msg_map = {
            "user": HumanMessage,
            "assistant": AIMessage,
            "system": SystemMessage,
        }

    def _to_lc(self, messages: List[Msg]):
        return [self._msg_map.get(m["role"], self._msg_map["user"])(content=m["content"])
                for m in messages]

    def invoke(self, messages: List[Msg], **kwargs) -> str:
        response = self._llm.invoke(self._to_lc(messages))
        return response.content

    async def ainvoke(self, messages: List[Msg], **kwargs) -> str:
        response = await self._llm.ainvoke(self._to_lc(messages))
        return response.content


# ──────────────────────────────────────────────────────────────────────
# Ollama  (local sovereign models: Gemma 4, Llama 3, etc.)
# ──────────────────────────────────────────────────────────────────────

class OllamaTransport(BaseTransport):
    """HTTP transport for Ollama. No SDK required — pure httpx."""

    def __init__(self, model: str = "gemma4", max_tokens: int = 1024):
        super().__init__(model, max_tokens)
        self._base_url = os.getenv("OLLAMA_URL",
                                   os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    def _payload(self, messages: List[Msg]) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": self.max_tokens},
        }

    def invoke(self, messages: List[Msg], **kwargs) -> str:
        import httpx
        r = httpx.post(f"{self._base_url}/api/chat",
                       json=self._payload(messages), timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"]

    async def ainvoke(self, messages: List[Msg], **kwargs) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self._base_url}/api/chat",
                                  json=self._payload(messages), timeout=120)
            r.raise_for_status()
            return r.json()["message"]["content"]


# ──────────────────────────────────────────────────────────────────────
# OpenAI-compatible  (OpenAI, Groq, LiteLLM, vLLM, sovereign endpoints)
# ──────────────────────────────────────────────────────────────────────

class OpenAICompatTransport(BaseTransport):
    """Covers any OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(model, max_tokens)
        try:
            from openai import OpenAI, AsyncOpenAI
            key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "none"
            kw = dict(api_key=key)
            if base_url:
                kw["base_url"] = base_url
            self._client = OpenAI(**kw)
            self._aclient = AsyncOpenAI(**kw)
        except ImportError:
            raise ImportError("openai package required for OpenAICompatTransport. "
                              "pip install openai")

    def invoke(self, messages: List[Msg], **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self.model, messages=messages, max_tokens=self.max_tokens
        )
        return resp.choices[0].message.content

    async def ainvoke(self, messages: List[Msg], **kwargs) -> str:
        resp = await self._aclient.chat.completions.create(
            model=self.model, messages=messages, max_tokens=self.max_tokens
        )
        return resp.choices[0].message.content


# ──────────────────────────────────────────────────────────────────────
# Registry & factory
# ──────────────────────────────────────────────────────────────────────

_DEFAULT_MODELS: Dict[str, str] = {
    "anthropic": "claude-3-5-haiku-20241022",
    "ollama":    "gemma4",
    "openai":    "gpt-4o-mini",
    "groq":      "llama-3.1-8b-instant",
}

_REGISTRY: Dict[str, type] = {
    "anthropic": AnthropicTransport,
    "ollama":    OllamaTransport,
    "openai":    OpenAICompatTransport,
    "groq":      OpenAICompatTransport,  # same class, different base_url
}

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def transport_from_env(role: str = "default") -> BaseTransport:
    """
    Build a transport from environment variables.

    Resolution order for a given role (e.g. "curator"):
      1. ZANA_CURATOR_PROVIDER  / ZANA_CURATOR_MODEL
      2. ZANA_PRIMARY_PROVIDER  / ZANA_PRIMARY_MODEL
      3. hardcoded defaults (anthropic / claude-3-5-haiku)
    """
    r = role.upper()
    provider = (os.getenv(f"ZANA_{r}_PROVIDER")
                or os.getenv("ZANA_PRIMARY_PROVIDER", "anthropic")).lower()
    model = (os.getenv(f"ZANA_{r}_MODEL")
             or os.getenv("ZANA_PRIMARY_MODEL",
                          _DEFAULT_MODELS.get(provider, _DEFAULT_MODELS["anthropic"])))
    # Strip "anthropic/" or "ollama/" prefix produced by LiteLLM-style notation
    if "/" in model:
        model = model.split("/", 1)[1]
    max_tokens = int(os.getenv(f"ZANA_{r}_MAX_TOKENS", "1024"))

    cls = _REGISTRY.get(provider)
    if cls is None:
        logger.warning(
            f"Unknown provider '{provider}' for role '{role}'. Falling back to Anthropic."
        )
        cls, model = AnthropicTransport, _DEFAULT_MODELS["anthropic"]

    extra: dict = {}
    if provider == "groq":
        extra["base_url"] = _GROQ_BASE_URL
        extra["api_key"] = os.getenv("GROQ_API_KEY")

    transport = cls(model=model, max_tokens=max_tokens, **extra)
    logger.debug(f"Transport[{role}] → {transport}")
    return transport


if __name__ == "__main__":
    # ── Unit tests (no real API calls) ──────────────────────────────
    import unittest
    from unittest.mock import MagicMock, patch

    class TransportTests(unittest.TestCase):

        def test_anthropic_message_conversion(self):
            t = AnthropicTransport.__new__(AnthropicTransport)
            t.model = "test"
            t.max_tokens = 256
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            t._msg_map = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}
            msgs = [{"role": "user", "content": "hi"},
                    {"role": "assistant", "content": "hello"},
                    {"role": "system", "content": "context"}]
            lc = t._to_lc(msgs)
            self.assertIsInstance(lc[0], HumanMessage)
            self.assertIsInstance(lc[1], AIMessage)
            self.assertIsInstance(lc[2], SystemMessage)

        def test_factory_anthropic_default(self):
            env = {"ANTHROPIC_API_KEY": "sk-test"}
            env.pop("ZANA_TEST_PROVIDER", None)
            with patch.dict(os.environ, env):
                os.environ.pop("ZANA_TEST_PROVIDER", None)
                os.environ.pop("ZANA_PRIMARY_PROVIDER", None)
                t = transport_from_env("test")
            self.assertIsInstance(t, AnthropicTransport)

        def test_factory_ollama_override(self):
            with patch.dict(os.environ, {"ZANA_CURATOR_PROVIDER": "ollama",
                                         "ZANA_CURATOR_MODEL": "gemma4"}):
                t = transport_from_env("curator")
            self.assertIsInstance(t, OllamaTransport)
            self.assertEqual(t.model, "gemma4")

        def test_factory_strips_prefix(self):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test",
                                         "ZANA_PRIMARY_MODEL": "anthropic/claude-3-5-haiku-20241022",
                                         "ZANA_PRIMARY_PROVIDER": "anthropic"}):
                t = transport_from_env("orchestrator")
            self.assertEqual(t.model, "claude-3-5-haiku-20241022")

        def test_factory_unknown_provider_fallback(self):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test",
                                         "ZANA_TEST_PROVIDER": "unknown_provider"}):
                t = transport_from_env("test")
            self.assertIsInstance(t, AnthropicTransport)

        def test_invoke_prompt_wraps_message(self):
            t = AnthropicTransport.__new__(AnthropicTransport)
            t.model, t.max_tokens = "test", 256
            captured = []
            t.invoke = lambda msgs, **kw: captured.append(msgs) or "ok"
            result = t.invoke_prompt("hello world")
            self.assertEqual(result, "ok")
            self.assertEqual(captured[0], [{"role": "user", "content": "hello world"}])

    unittest.main(verbosity=2)
