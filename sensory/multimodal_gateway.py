"""
MultimodalGateway — ZANA's sensory entry point.
Port: 54446
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
import numpy as np
from datetime import datetime
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root and current dir to sys.path
if getattr(sys, 'frozen', False):
    # PyInstaller bundle path
    root = Path(sys._MEIPASS)
    # Set tiktoken cache dir to bundled folder
    os.environ["TIKTOKEN_CACHE_DIR"] = str(root / "tiktoken_cache")
    
    # --- TIKTOKEN PYINSTALLER FIX ---
    try:
        import tiktoken
        import tiktoken_ext.openai_public
        # Force registration of encodings into tiktoken's registry
        for name, constructor in tiktoken_ext.openai_public.ENCODING_CONSTRUCTORS.items():
            if name not in tiktoken.registry.ENCODINGS:
                tiktoken.registry.ENCODINGS[name] = constructor
    except Exception as e:
        logging.warning(f"Failed to monkey-patch tiktoken: {e}")

    # --- SMOLAGENTS PYINSTALLER FIX ---
    import inspect
    _original_getsource = inspect.getsource
    _original_getsourcelines = inspect.getsourcelines
    
    def _patched_getsource(obj):
        try:
            return _original_getsource(obj)
        except OSError:
            return "def forward(self, *args, **kwargs):\n    pass\n"
            
    def _patched_getsourcelines(obj):
        try:
            return _original_getsourcelines(obj)
        except OSError:
            return (["def forward(self, *args, **kwargs):\n", "    pass\n"], 1)

    inspect.getsource = _patched_getsource
    inspect.getsourcelines = _patched_getsourcelines
else:
    # Development path
    root = Path(__file__).parent.parent

sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "cli"))
sys.path.insert(0, str(root / "sensory"))

from audio_processor import AudioProcessor
from local_llm import get_local_llm
from perception_event import PerceptionEvent, VisionFeatures
from tts_engine import TTSEngine
from vision_processor import VisionProcessor
from armor_middleware import inspect_input, inspect_output, backend as armor_backend
from swarm.apex.orchestrator import ApexOrchestrator
from autonomy.resonance_engine import ResonanceEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("zana.gateway")

# --- CONFIG ---
GATEWAY_PORT = int(os.getenv("ZANA_GATEWAY_PORT", "54446"))
SYMBIOSIS_URL = os.getenv("ZANA_SYMBIOSIS_URL", "http://localhost:58000")

app = FastAPI(
    title="ZANA Multimodal Sensory Gateway",
    description="Audio · Vision · TTS · Reason · Memory · Swarm — The Aeon's sensory layer",
    version="2.9.2",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

resonance_engine = ResonanceEngine()

class RitualRequest(BaseModel):
    answers: Dict[str, Any]
    name: Optional[str] = None
    visual_genes: Optional[Dict[str, Any]] = None
    is_master: Optional[bool] = False

@app.post("/resonance/forge")
async def forge_identity(request: RitualRequest):
    """
    Forges the Aeon identity based on the Resonance Ritual.
    Returns the generated DNA and archetype.
    """
    logger.info(f"Forging new Aeon identity for {request.name}...")
    # Pass name and visual_genes to the engine
    profile = resonance_engine.process_ritual(
        request.answers, 
        user_name=request.name, 
        user_visual_genes=request.visual_genes
    )
    return profile

@app.get("/resonance/profile")
async def get_profile():
    """
    Returns the current active resonance profile.
    """
    if resonance_engine.resonance_path.exists():
        return json.loads(resonance_engine.resonance_path.read_text())
    return {"status": "seed", "message": "No profile forged yet."}

# ─── Power-user routers (v2.1 / v2.2) ─────────────────────────────────────────
try:
    from sensory.reasoning_router import router as _reason_router
    from sensory.memory_router import router as _memory_router
    from sensory.control_router import router as _control_router
    from sensory.projects_router import router as _projects_router # NEW

    app.include_router(_reason_router)
    app.include_router(_memory_router)
    app.include_router(_control_router)
    app.include_router(_projects_router) # NEW
    logger.info("✓  [GATEWAY] reason / memory / control / projects routers loaded")
except Exception as _e:
    logger.warning("Power-user routers not loaded: %s", _e)

# Procesadores (lazy-loaded)
_audio = AudioProcessor()
_vision = VisionProcessor()
_tts = TTSEngine()


# ─── Kalman Filter (Rust Steel Core → numpy fallback) ─────────────────────────


def _build_kalman(dim: int = 64):
    """Returns Rust PyKalmanFilter if available, else Python fallback."""
    try:
        import zana_steel_core

        kf = zana_steel_core.PyKalmanFilter(dim, 1e-4, 1e-2)
        logger.info("⚙️  [KALMAN] Rust Steel Core active (dim=%d)", dim)
        return kf
    except Exception:
        logger.warning("⚠️  [KALMAN] Using numpy fallback (install zana_steel_core.so)")
        return None


class _NumpyKalmanGate:
    def __init__(self, dim: int = 64):
        self.state = np.zeros(dim)
        self.uncertainty = np.ones(dim)

    def update(self, obs: list) -> float:
        obs_arr = np.asarray(obs)
        self.uncertainty += 1e-4
        K = self.uncertainty / (self.uncertainty + 1e-2)
        innovation = obs_arr - self.state
        surprise = float(np.mean((innovation**2) / (self.uncertainty + 1e-2)))
        self.state += K * innovation
        self.uncertainty *= 1 - K
        return surprise


_kalman_registry: Dict[str, Any] = {}

def _get_kalman_filter(project_id: str):
    """Retrieves or creates a Kalman filter specific to a project context."""
    if project_id not in _kalman_registry:
        rust_kf = _build_kalman(64)
        if rust_kf is not None:
            _kalman_registry[project_id] = rust_kf
        else:
            _kalman_registry[project_id] = _NumpyKalmanGate(64)
    return _kalman_registry[project_id]


def _kalman_surprise_text(text: str, project_id: str = "default") -> float:
    """Fused embed+Kalman in one Rust call — 599 ns, 54x faster than numpy path."""
    kf = _get_kalman_filter(project_id)
    if hasattr(kf, "update_text"):
        return kf.update_text(text)
    # Numpy fallback
    h = hash(text) % (2**32)
    emb = np.random.default_rng(h).standard_normal(64)
    return kf.update(emb)  # type: ignore[union-attr]


def _kalman_surprise_buffer(embedding: np.ndarray, project_id: str = "default") -> float:
    """Zero-copy Kalman update from numpy array — used for audio/vision embeddings."""
    kf = _get_kalman_filter(project_id)
    if hasattr(kf, "update_buffer"):
        return kf.update_buffer(embedding)
    return kf.update(embedding)  # type: ignore[union-attr]


# ─── Cortex bridge ────────────────────────────────────────────────────────────


async def _query_cortex(event: PerceptionEvent) -> str:
    """
    Queries the Cortex (Symbiosis) for relevant context.
    Returns a context string, or empty string if Symbiosis is offline.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{SYMBIOSIS_URL}/mcp/context",
                json={
                    "query": event.cortex_input,
                    "session_id": event.session_id or "gateway",
                    "limit": 3,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("context", "")
    except Exception:
        pass
    return ""


async def _build_aeon_response_async(event: PerceptionEvent, cortex_context: str) -> str:
    """
    Generates the Aeon's real response via LocalLLM asynchronously.
    """
    user_input = event.cortex_input or event.text or ""
    if not user_input.strip():
        return ""

    modality_prefix = {
        "audio": f"[User said]: {event.text}",
        "vision": f"[Observed scene]: {event.text}",
        "multimodal": f"[Perceived audio+vision]: {event.text}",
    }.get(event.modality, user_input)

    llm = get_local_llm()
    return await llm.generate_async(
        modality_prefix, context=cortex_context, session_id=event.session_id or ""
    )

def _build_aeon_response(event: PerceptionEvent, cortex_context: str) -> str:
    """
    Generates the Aeon's real response via LocalLLM (Ollama → Claude → template).
    Local-first: llama3.1:8b if Ollama is active, Claude Haiku if API key is available.
    """
    user_input = event.cortex_input or event.text or ""
    if not user_input.strip():
        return ""

    modality_prefix = {
        "audio": f"[User said]: {event.text}",
        "vision": f"[Observed scene]: {event.text}",
        "multimodal": f"[Perceived audio+vision]: {event.text}",
    }.get(event.modality, user_input)

    llm = get_local_llm()
    return llm.generate(
        modality_prefix, context=cortex_context, session_id=event.session_id or ""
    )


# ─── Request models ───────────────────────────────────────────────────────────


class TextSenseRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    respond_with_audio: bool = False


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))


# Initialize the orchestrator (The Apex Quintet)
apex_orchestrator = ApexOrchestrator()


class OrchestratorRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@app.post(
    "/apex/orchestrate",
    response_model=dict,
    summary="Execute a complex task with the Apex Quintet",
)
async def apex_orchestrate(req: OrchestratorRequest):
    """
    Deploys the 5-agent squad (Archivist, Herald, Operator, Analyst, Sentinel)
    to resolve a complex user query.
    """
    logger.info(f"🌀 [APEX GATEWAY] New orchestration request: '{req.query}'")
    try:
        # En un entorno real asíncrono, esto se envolvería en asyncio.to_thread si es bloqueante
        result = apex_orchestrator.process_request(req.query)
        return {"status": "success", "query": req.query, "response": result}
    except Exception as e:
        logger.error(f"❌ [APEX GATEWAY] Orchestration error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/sense/audio", response_model=dict, summary="Audio → STT + TTS response")
async def sense_audio(
    audio: UploadFile = File(..., description="Archivo de audio WAV/MP3/OGG/FLAC"),
    session_id: Optional[str] = Form(None),
    respond_with_audio: bool = Form(True),
    context_hint: Optional[str] = Form(None),
):
    """
    Pipeline:
      1. Receives audio → STT (Whisper)
      2. Extracts acoustic features (energy, ZCR, pitch)
      3. Calculates Bayesian Surprise via Kalman
      4. Queries Cortex with the transcript
      5. Synthesizes Aeon response with TTS
      6. Returns complete PerceptionEvent
    """
    audio_bytes = await audio.read()
    mime = audio.content_type or "audio/wav"

    # 1. STT
    result = _audio.transcribe(audio_bytes, mime)
    emotion = _audio.infer_emotion_from_features(result.features)

    # 2. Construir evento parcial
    event = PerceptionEvent(
        modality="audio",
        session_id=session_id,
        text=result.transcript,
        audio_features=result.features,
        source_mime=mime,
        response_emotion=emotion,
    )

    # 3. Kalman surprise
    event.kalman_surprise = _kalman_surprise_text(result.transcript, session_id or "default")

    # 4. Cortex
    cortex_ctx = await _query_cortex(event)
    event.response_text = _build_aeon_response(event, cortex_ctx)

    # 5. TTS
    if respond_with_audio and event.response_text:
        audio_response = await _tts.synthesize_async(event.response_text)
        event.response_audio_b64 = base64.b64encode(audio_response).decode()

    logger.info(
        "🎤→🧠→🔊 [AUDIO] transcript='%s…' | surprise=%.3f | emotion=%s",
        result.transcript[:50],
        event.kalman_surprise,
        emotion,
    )
    return event.to_dict()


@app.post(
    "/sense/vision", response_model=dict, summary="Imagen/Video → descripción + facts"
)
async def sense_vision(
    media: UploadFile = File(
        ..., description="Imagen (JPG/PNG/WebP) o video (MP4/WebM)"
    ),
    session_id: Optional[str] = Form(None),
    context_hint: Optional[str] = Form(None),
    respond_with_audio: bool = Form(False),
):
    """
    Pipeline:
      1. Detects whether input is image or video
      2. Image → direct Claude Vision analysis
         Video → extracts keyframes → analyzes each one
      3. Consolidates description + entities
      4. Queries Cortex
      5. Returns PerceptionEvent with facts for the ReasoningEngine
    """
    media_bytes = await media.read()
    mime = media.content_type or "image/jpeg"
    is_video = mime.startswith("video/")

    if is_video:
        analyses = _vision.analyze_video(media_bytes, mime, context_hint or "")
        # Consolidar: unir todas las descripciones
        descriptions = [d for d, _ in analyses]
        all_entities = list({e for _, f in analyses for e in f.entities})
        combined_desc = " | ".join(descriptions[:3])
        features = (
            analyses[0][1]
            if analyses
            else VisionFeatures("mixed", [], "neutral", "", 0.0)
        )
        features.entities = all_entities[:8]
    else:
        combined_desc, features = _vision.analyze_image(
            media_bytes, mime, context_hint or ""
        )

    event = PerceptionEvent(
        modality="vision",
        session_id=session_id,
        text=combined_desc,
        vision_features=features,
        source_mime=mime,
        response_emotion=features.emotional_context,
    )

    event.kalman_surprise = _kalman_surprise_text(combined_desc, session_id or "default")

    cortex_ctx = await _query_cortex(event)
    event.response_text = _build_aeon_response(event, cortex_ctx)

    if respond_with_audio and event.response_text:
        audio_response = await _tts.synthesize_async(event.response_text)
        event.response_audio_b64 = base64.b64encode(audio_response).decode()

    logger.info(
        "👁️→🧠 [VISION] scene=%s | entities=%s | surprise=%.3f",
        features.scene_type,
        features.entities[:3],
        event.kalman_surprise,
    )
    return event.to_dict()


@app.post("/sense/text", response_model=dict, summary="Text → standard PerceptionEvent")
async def sense_text(req: TextSenseRequest):
    """Normalized text pipeline. Produces the same PerceptionEvent as audio/vision."""
    event = PerceptionEvent(
        modality="text",
        session_id=req.session_id,
        text=req.text,
        source_mime="text/plain",
    )
    event.kalman_surprise = _kalman_surprise_text(req.text, req.session_id or "default")

    cortex_ctx = await _query_cortex(event)
    event.response_text = _build_aeon_response(event, cortex_ctx)

    if req.respond_with_audio and event.response_text:
        audio_response = await _tts.synthesize_async(event.response_text)
        event.response_audio_b64 = base64.b64encode(audio_response).decode()

    return event.to_dict()


@app.post(
    "/sense/multimodal", response_model=dict, summary="Audio + Imagen simultáneos"
)
async def sense_multimodal(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    respond_with_audio: bool = Form(True),
):
    """
    Combines audio + image into a single PerceptionEvent.
    Use case: the user speaks while sharing their screen or a photo.
    """
    event = PerceptionEvent(modality="multimodal", session_id=session_id)

    if audio:
        audio_bytes = await audio.read()
        result = _audio.transcribe(audio_bytes, audio.content_type or "audio/wav")
        event.audio_features = result.features
        event.text = result.transcript
        event.response_emotion = _audio.infer_emotion_from_features(result.features)

    if image:
        img_bytes = await image.read()
        desc, vfeatures = _vision.analyze_image(
            img_bytes, image.content_type or "image/jpeg"
        )
        event.vision_features = vfeatures
        # Combine transcript + visual description as Cortex input
        event.text = f"{event.text or ''} [+SEE: {desc}]".strip()

    event.kalman_surprise = _kalman_surprise_text(event.text or "", session_id or "default")

    cortex_ctx = await _query_cortex(event)
    event.response_text = _build_aeon_response(event, cortex_ctx)

    if respond_with_audio and event.response_text:
        audio_response = await _tts.synthesize_async(event.response_text)
        event.response_audio_b64 = base64.b64encode(audio_response).decode()

    return event.to_dict()


@app.post("/aeon/speak", response_model=dict, summary="Arbitrary TTS — Aeon's voice")
async def aeon_speak(req: SpeakRequest):
    """
    Synthesizes any text with the Aeon's voice.
    Useful for proactive notifications from the Shadow Observer.
    """
    audio_bytes = await _tts.synthesize_async(req.text, req.voice)
    return {
        "text": req.text,
        "voice": req.voice or _tts._detect_backend(),
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "mime": "audio/mpeg",
        "bytes": len(audio_bytes),
    }


@app.websocket("/sense/stream")
async def sense_stream(ws: WebSocket):
    """
    Stream bidireccional en tiempo real.
    Cliente envía: { "type": "audio"|"text"|"vision", "data": "<base64 o texto>" }
    Servidor responde: PerceptionEvent JSON
    """
    await ws.accept()
    logger.info("🌐 [STREAM] Client connected")
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "text")
            data = msg.get("data", "")
            session_id = msg.get("session_id")

            # ── Armor: inspect input ──────────────────────────────────
            if msg_type == "text":
                verdict = inspect_input(data)
                if not verdict["allowed"]:
                    await ws.send_json(
                        {"type": "error", "content": f"ARMOR_BLOCKED: {verdict['threat_level']}"}
                    )
                    continue
                
                data = verdict["sanitized"]
                
                # Mock PerceptionEvent for the start
                event = PerceptionEvent(modality="text", session_id=session_id, text=data)
                event.kalman_surprise = _kalman_surprise_text(data, session_id or "default")
                ctx = await _query_cortex(event)
                
                # LLM Streaming (ASYNC)
                llm = get_local_llm()
                async for chunk in llm.generate_stream_async(data, context=ctx, session_id=session_id or ""):
                    await ws.send_json({"type": "chunk", "content": chunk})
                
                # End of stream
                await ws.send_json({"type": "end"})
                
            elif msg_type == "audio":
                audio_bytes = base64.b64decode(data)
                # Run sync audio processing in thread to avoid blocking loop
                result = await asyncio.to_thread(_audio.transcribe, audio_bytes)
                event = PerceptionEvent(
                    modality="audio",
                    session_id=session_id,
                    text=result.transcript,
                    audio_features=result.features,
                )
                event.kalman_surprise = _kalman_surprise_text(result.transcript, session_id or "default")
                ctx = await _query_cortex(event)
                event.response_text = await _build_aeon_response_async(event, ctx)
                # TTS in stream
                audio_resp = await _tts.synthesize_async(event.response_text or "")
                event.response_audio_b64 = base64.b64encode(audio_resp).decode()

            elif msg_type == "vision":
                img_bytes = base64.b64decode(data)
                # Run sync vision processing in thread
                desc, features = await asyncio.to_thread(_vision.analyze_image, img_bytes)
                event = PerceptionEvent(
                    modality="vision",
                    session_id=session_id,
                    text=desc,
                    vision_features=features,
                )
                event.kalman_surprise = _kalman_surprise_text(desc, session_id or "default")
                ctx = await _query_cortex(event)
                event.response_text = await _build_aeon_response_async(event, ctx)

            else:
                event = PerceptionEvent(
                    modality="text", text=f"[unknown type: {msg_type}]"
                )

            await ws.send_json(event.to_dict())

    except WebSocketDisconnect:
        logger.info("🌐 [STREAM] Client disconnected")
    except Exception as e:
        logger.error("❌ [STREAM] Error: %s", e)
        await ws.close(code=1011)


@app.websocket("/sense/ambient")
async def sense_ambient(ws: WebSocket):
    """
    Ambient Senses Endpoint.
    ZANA listens passively to the environment. 
    Only triggers orchestration when Voice Activity is detected via Rust DSP.
    """
    await ws.accept()
    logger.info("🎤 [AMBIENT] Passive listener connected")
    audio_buffer = b""
    voice_detected = False
    
    try:
        while True:
            # Receive binary audio data
            data = await ws.receive_bytes()
            
            # Use Rust DSP to detect voice activity
            if _audio.is_voice_active(data):
                if not voice_detected:
                    logger.info("🎤 [AMBIENT] Voice detected, starting capture...")
                    voice_detected = True
                audio_buffer += data
            else:
                if voice_detected and len(audio_buffer) > 16000: # Approx 1s of 16kHz audio
                    logger.info("🎤 [AMBIENT] Silence detected, processing segment...")
                    # Process buffered audio
                    result = _audio.transcribe(audio_buffer)
                    if result.transcript.strip() and result.transcript != "[silence]":
                        logger.info(f"🎤 [AMBIENT] Heard: '{result.transcript}'")
                        
                        # Forward to Orchestrator in a separate thread to avoid blocking loop
                        response = await asyncio.to_thread(apex_orchestrator.process_request, result.transcript)
                        
                        # Generate TTS
                        audio_resp = await _tts.synthesize_async(response)
                        
                        # Send back PerceptionEvent
                        event = PerceptionEvent(
                            modality="audio",
                            text=result.transcript,
                            response_text=response,
                            response_audio_b64=base64.b64encode(audio_resp).decode()
                        )
                        await ws.send_json(event.to_dict())
                        
                    # Reset buffer
                    audio_buffer = b""
                    voice_detected = False
                else:
                    # Keep a small rolling buffer of silence to avoid clipping start of next sentence
                    audio_buffer = data # Basic rolling, could be improved
                    
    except WebSocketDisconnect:
        logger.info("🎤 [AMBIENT] Passive listener disconnected")
    except Exception as e:
        logger.error("❌ [AMBIENT] Error: %s", e)
        await ws.close(code=1011)

@app.get("/sync/status")
async def get_sync_status():
    """Check the status of the Aegis Sync engine."""
    vault_path = Path(os.getenv("ZANA_CORE_DIR", ".")) / "data" / "zana.vault"
    last_sync = None
    if vault_path.exists():
        last_sync = datetime.fromtimestamp(vault_path.stat().st_mtime).isoformat()
    
    return {
        "enabled": os.getenv("ZANA_SYNC_SEED") is not None,
        "last_sync": last_sync,
        "provider": "S3" if os.getenv("ZANA_SYNC_S3_URL") else "Local Only"
    }

@app.post("/sync/trigger")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a manual memory sync in the background."""
    from autonomy.crypto import AegisCrypto
    from autonomy.sync_engine import SyncEngine
    from autonomy.storage_adapters import S3StorageAdapter
    
    seed = os.getenv("ZANA_SYNC_SEED")
    if not seed:
        return {"status": "error", "message": "Sync not configured (no seed)"}

    async def _do_sync():
        try:
            core_dir = Path(os.getenv("ZANA_CORE_DIR", "."))
            crypto = AegisCrypto(seed)
            engine = SyncEngine(crypto, core_dir)
            
            # Create snapshot
            vault_path = engine.create_snapshot()
            
            # Upload if S3 is configured
            url = os.getenv("ZANA_SYNC_S3_URL")
            if url:
                key = os.getenv("ZANA_SYNC_S3_KEY")
                secret = os.getenv("ZANA_SYNC_S3_SECRET")
                bucket = os.getenv("ZANA_SYNC_S3_BUCKET", "zana-vault")
                storage = S3StorageAdapter(url, key, secret, bucket)
                storage.upload(vault_path)
                logger.info("☁️ [SYNC] Cloud push complete.")
        except Exception as e:
            logger.error(f"❌ [SYNC] Failed: {e}")

    background_tasks.add_task(_do_sync)
    return {"status": "started", "message": "Sync initiated in background."}

@app.get("/health")
def health():
    """Gateway status and availability of each backend."""
    audio_backend = _audio._backend or "not_loaded"
    tts_backend = _tts._backend or "not_loaded"
    llm_info = get_local_llm().backend_info()
    llm_backend = (
        f"ollama:{llm_info.get('text_model')}"
        if llm_info.get("ollama")
        else ("claude-haiku" if llm_info.get("claude") else "template")
    )
    vision_backend = (
        f"ollama:{llm_info.get('vision_model')}"
        if llm_info.get("vision_model")
        else ("claude-vision" if getattr(_vision, '_client', None) else "mock")
    )
    return {
        "status": "online",
        "backends": {
            "stt": audio_backend,
            "tts": tts_backend,
            "llm": llm_backend,
            "vision": vision_backend,
            "kalman": "rust-steel-core" if _kalman_registry.get("default") and hasattr(_kalman_registry["default"], "update_text") else "numpy (dynamic)",
            "armor": armor_backend(),
        },
        "endpoints": {
            "audio": "POST /sense/audio",
            "vision": "POST /sense/vision",
            "text": "POST /sense/text",
            "multimodal": "POST /sense/multimodal",
            "stream": "WS   /sense/stream",
            "speak": "POST /aeon/speak",
            "reason": "POST /reason",
            "memory": "GET  /memory/episodic  GET /memory/stats",
            "shadow": "POST /shadow/enable|disable  GET /shadow/status",
            "swarm": "POST /swarm/init|stop|assimilate|query  GET /swarm/status",
            "agent_card": "GET  /.well-known/agent-card.json",
        },
    }


# ─── A2A Agent Card ──────────────────────────────────────────────────────────

try:
    from swarm.agent_card import serve_agent_card

    serve_agent_card(app, node_id=os.getenv("ZANA_NODE_ID", "AEON-001"))
except Exception as _e:
    logger.warning("AgentCard not registered: %s", _e)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("╔══════════════════════════════════════════════════╗")
    print("║   ZANA MULTIMODAL SENSORY GATEWAY  v1.0          ║")
    print("║   Audio · Vision · TTS                           ║")
    print(f"║   http://0.0.0.0:{GATEWAY_PORT}                         ║")
    print("╚══════════════════════════════════════════════════╝")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=GATEWAY_PORT,
        reload=False,
    )
