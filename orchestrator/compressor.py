import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# Compress when total message chars exceed this (≈ 10K tokens for Claude)
_COMPRESS_THRESHOLD = 40_000
# Always keep this many recent messages verbatim
_KEEP_RECENT = 4
# Anti-thrashing: skip if fewer than this many new messages since last compression
_MIN_NEW_SINCE_LAST = 2


class ContextCompressor:
    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        self.llm = ChatAnthropic(
            model=model,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=1024,
        )
        self._last_compressed_at: int = 0  # message count at last compression

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_compress(self, messages: List[BaseMessage]) -> bool:
        if len(messages) < _KEEP_RECENT + 2:
            return False
        # Anti-thrashing guard
        if len(messages) - self._last_compressed_at < _MIN_NEW_SINCE_LAST:
            return False
        total = sum(len(str(m.content)) for m in messages)
        return total > _COMPRESS_THRESHOLD

    def compress(
        self, messages: List[BaseMessage], observations: List[str]
    ) -> Tuple[List[BaseMessage], List[str]]:
        """Summarize older messages into a single AIMessage.
        Returns (new_messages, new_observations) with observations cleared into summary.
        On LLM error, returns original inputs unchanged.
        """
        if len(messages) <= _KEEP_RECENT:
            return messages, observations

        to_compress = messages[:-_KEEP_RECENT]
        to_keep = messages[-_KEEP_RECENT:]
        language = self._detect_language(messages[-1])

        summary = self._summarize(to_compress, observations, language)
        if summary is None:
            logger.warning("Compression failed — keeping original context.")
            return messages, observations

        self._last_compressed_at = len(to_keep) + 1
        summary_msg = AIMessage(content=f"[CONTEXT SUMMARY — {language}]\n{summary}")

        logger.info(
            f"Compressed {len(to_compress)} messages into summary "
            f"({len(to_keep)} kept verbatim)."
        )
        return [summary_msg] + list(to_keep), []

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _detect_language(self, last_message: BaseMessage) -> str:
        content = str(last_message.content).lower()
        es_markers = {"el ", "la ", "los ", "las ", "que ", "con ", "por ", "para ", "no "}
        if sum(1 for m in es_markers if m in content) >= 2:
            return "Spanish"
        return "English"

    def _summarize(
        self, messages: List[BaseMessage], observations: List[str], language: str
    ) -> str | None:
        text_parts = [
            f"{m.__class__.__name__}: {m.content}" for m in messages
        ]
        if observations:
            text_parts.append("\nObservations:\n" + "\n".join(f"- {o}" for o in observations))

        prompt = (
            f"Summarize the following conversation context concisely in {language}. "
            "Preserve key decisions, task state, and important facts. Drop small talk.\n\n"
            + "\n".join(text_parts)
            + "\n\nSummary:"
        )
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.warning(f"Compressor LLM call failed: {e}")
            return None


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage as HM, AIMessage as AM

    dummy_messages = (
        [HM(content="Hola ZANA, necesito desplegar la app.")]
        + [AM(content=f"Paso {i}: ejecutando acción {i}.") for i in range(20)]
        + [HM(content="¿Cuál es el estado actual?")]
    )
    dummy_obs = [f"Observación {i}" for i in range(5)]

    comp = ContextCompressor()
    print(f"Chars antes: {sum(len(str(m.content)) for m in dummy_messages)}")
    print(f"should_compress: {comp.should_compress(dummy_messages)}")

    new_msgs, new_obs = comp.compress(dummy_messages, dummy_obs)
    print(f"Mensajes después: {len(new_msgs)} (era {len(dummy_messages)})")
    print(f"Observaciones después: {len(new_obs)} (era {len(dummy_obs)})")
    print(f"\nSummary message preview:\n{new_msgs[0].content[:300]}")
