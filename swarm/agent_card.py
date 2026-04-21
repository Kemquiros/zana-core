"""
ZANA AgentCard — Google A2A Protocol compatible
Exposes ZANA's cognitive capabilities as a standard AgentCard
for interoperability with external agents (CrewAI, LangGraph, etc.)
"""
import json
import hashlib
from typing import Any
from pathlib import Path


def build_agent_card(node_id: str, dna: Any | None = None) -> dict:
    """
    Generate a Google A2A-compliant AgentCard for a ZANA node.
    Served at /.well-known/agent-card.json
    """
    import os

    base_url = os.getenv("ZANA_PUBLIC_URL", f"http://localhost:{os.getenv('ZANA_GATEWAY_PORT', '54446')}")

    card: dict = {
        "name": f"ZANA Aeon — {node_id}",
        "description": (
            "Sistema cognitivo multimodal ZANA. Percibe texto, audio e imágenes. "
            "Razona con Kalman Filter Bayesiano y motor simbólico CLIPS-Rust. "
            "Comparte sabiduría vía Wisdom Hub distribuido."
        ),
        "url": base_url,
        "provider": {
            "name": os.getenv("ZANA_PROVIDER_NAME", "ZANA"),
            "url": os.getenv("ZANA_PROVIDER_URL", "https://your-domain.example.com"),
        },
        "version": "1.1.0",
        "documentationUrl": f"{base_url}/docs",
        "capabilities": {
            "supportsStreaming": True,
            "supportsPushNotifications": False,
            "supportsStateTransitionHistory": True,
        },
        "authentication": {
            "required": False,
            "schemes": [],
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "zana.perception.text",
                "name": "Text Perception",
                "description": "Receives text, calculates Kalman surprise, generates reasoned response.",
                "tags": ["nlp", "reasoning", "bayesian"],
                "examples": [{"input": "What is the status of project X?", "output": "{response_text, emotion, kalman_surprise}"}],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "zana.perception.audio",
                "name": "Audio Perception",
                "description": "Transcribes WAV audio, extracts emotion via DSP, responds.",
                "tags": ["audio", "whisper", "emotion"],
                "inputModes": ["audio/wav"],
                "outputModes": ["application/json"],
            },
            {
                "id": "zana.perception.vision",
                "name": "Vision Perception",
                "description": "Analyzes images via LLaVA or Claude Vision.",
                "tags": ["vision", "multimodal", "llava"],
                "inputModes": ["image/png", "image/jpeg", "image/webp"],
                "outputModes": ["application/json"],
            },
            {
                "id": "zana.wisdom.share",
                "name": "Wisdom Sharing (A2A Internal)",
                "description": "Share and receive WisdomRules via Wisdom Hub voting protocol.",
                "tags": ["a2a", "swarm", "wisdom", "distributed"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            },
            {
                "id": "zana.reasoning.query",
                "name": "Symbolic Reasoning Query",
                "description": "Forward-chain reasoning over structured facts. Returns deduced conclusions.",
                "tags": ["reasoning", "clips", "symbolic"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            },
        ],
    }

    # Embed DNA fingerprint as extension if available
    if dna is not None:
        try:
            fp = dna.get_fingerprint() if hasattr(dna, "get_fingerprint") else hashlib.sha256(str(dna).encode()).hexdigest()
            card["extensions"] = {"zana:dna_fingerprint": fp, "zana:node_id": node_id}
        except Exception:
            pass

    return card


def serve_agent_card(app, node_id: str, dna: Any | None = None) -> None:
    """Register /.well-known/agent-card.json route on a FastAPI app."""
    from fastapi.responses import JSONResponse

    @app.get("/.well-known/agent-card.json", include_in_schema=False)
    async def agent_card():
        return JSONResponse(build_agent_card(node_id, dna))
