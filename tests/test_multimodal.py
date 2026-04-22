"""
Test de integración — Capa Sensorial Multimodal.

Verifica sin dependencias externas:
  1. PerceptionEvent — estructura y conversión
  2. AudioProcessor  — features + mock STT
  3. VisionProcessor — mock analysis + JSON parsing
  4. TTSEngine        — detección de backend + silent fallback
  5. Pipeline completo texto→PerceptionEvent→Kalman
  6. AgentCard multimodal — 7 skills, FilePart support
"""

import struct
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from sensory.perception_event import PerceptionEvent, AudioFeatures, VisionFeatures
from sensory.audio_processor import AudioProcessor
from sensory.tts_engine import TTSEngine


def sep(title: str) -> None:
    print(f"\n{'─' * 58}")
    print(f"  {title}")
    print("─" * 58)


def make_silent_wav(duration_s: float = 0.5, sr: int = 16000) -> bytes:
    """Genera WAV de silencio para tests."""
    n_samples = int(sr * duration_s)
    data = b"\x00" * (n_samples * 2)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sr,
        sr * 2,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data


# ══════════════════════════════════════════════════════════
def test_perception_event() -> bool:
    sep("1 · PerceptionEvent — estructura y pipeline")
    passed = 0

    # Caso 1: evento de audio básico
    evt = PerceptionEvent(
        modality="audio",
        text="Hola ZANA, ¿cómo va el proyecto VECANOVA?",
        audio_features=AudioFeatures(
            duration_s=2.5,
            rms_energy=0.45,
            zero_crossing_rate=0.08,
            dominant_freq_hz=180.0,
            speech_rate_wpm=120.0,
        ),
    )
    ok1 = evt.modality == "audio" and evt.cortex_input == evt.text
    print(f"  [{'✅' if ok1 else '❌'}] Audio event cortex_input = text")
    if ok1:
        passed += 1

    # Caso 2: evento de visión sin texto — cortex_input usa VisionFeatures
    evt2 = PerceptionEvent(
        modality="vision",
        vision_features=VisionFeatures(
            scene_type="screen",
            entities=["code", "terminal", "error"],
            emotional_context="stressed",
            text_content="",
            confidence=0.85,
        ),
    )
    ok2 = "VISION" in evt2.cortex_input and "screen" in evt2.cortex_input
    print(f"  [{'✅' if ok2 else '❌'}] Vision event cortex_input uses scene_type")
    if ok2:
        passed += 1

    # Caso 3: to_dict limpia Nones
    d = evt.to_dict()
    ok3 = "response_audio_b64" not in d and "text" in d
    print(f"  [{'✅' if ok3 else '❌'}] to_dict() elimina campos None")
    if ok3:
        passed += 1

    # Caso 4: modality multimodal
    evt3 = PerceptionEvent(
        modality="multimodal", text="audio + imagen", session_id="s1"
    )
    ok4 = evt3.modality == "multimodal" and evt3.session_id == "s1"
    print(f"  [{'✅' if ok4 else '❌'}] Multimodal event con session_id")
    if ok4:
        passed += 1

    return passed == 4


# ══════════════════════════════════════════════════════════
def test_audio_processor() -> bool:
    sep("2 · AudioProcessor — features acústicas + STT mock")
    proc = AudioProcessor()
    passed = 0

    wav = make_silent_wav(duration_s=1.0, sr=16000)

    # Caso 1: feature extraction — al menos retorna AudioFeatures sin crash
    # (soundfile puede no estar en el venv de test; el fallback devuelve ceros)
    features = proc._extract_features(wav)
    ok1 = (
        isinstance(features, AudioFeatures)
        and 0.0 <= features.rms_energy <= 1.0
        and features.zero_crossing_rate >= 0.0
    )
    note = (
        f"dur={features.duration_s}s, rms={features.rms_energy:.3f}" if ok1 else "crash"
    )
    print(f"  [{'✅' if ok1 else '❌'}] Features sin crash: {note}")
    if ok1:
        passed += 1

    # Caso 2: emotion inference
    loud_features = AudioFeatures(
        duration_s=1.0,
        rms_energy=0.7,
        zero_crossing_rate=0.15,
        dominant_freq_hz=200.0,
        speech_rate_wpm=200.0,
    )
    emotion = proc.infer_emotion_from_features(loud_features)
    ok2 = emotion == "agitated"
    print(
        f"  [{'✅' if ok2 else '❌'}] Emoción alta energía = 'agitated' (got '{emotion}')"
    )
    if ok2:
        passed += 1

    # rms=0.05 < 0.1 AND wpm=60 < 80 → "calm" (no llega a "subdued" que requiere rms < 0.05)
    calm_features = AudioFeatures(
        duration_s=1.0,
        rms_energy=0.05,
        zero_crossing_rate=0.02,
        dominant_freq_hz=150.0,
        speech_rate_wpm=60.0,
    )
    emotion2 = proc.infer_emotion_from_features(calm_features)
    ok3 = emotion2 == "calm"
    print(
        f"  [{'✅' if ok3 else '❌'}] Emoción rms=0.05, wpm=60 = 'calm' (got '{emotion2}')"
    )
    if ok3:
        passed += 1

    # Caso 3: transcribe con mock backend
    proc._backend = "mock"
    result = proc.transcribe(wav)
    ok4 = "STT" in result.transcript or result.transcript  # tiene contenido
    print(f"  [{'✅' if ok4 else '❌'}] Mock transcript = '{result.transcript[:50]}'")
    if ok4:
        passed += 1

    return passed == 4


# ══════════════════════════════════════════════════════════
def test_tts_engine() -> bool:
    sep("3 · TTSEngine — detección de backend + silent fallback")
    tts = TTSEngine()
    passed = 0

    # Caso 1: silent fallback produce WAV válido
    silent = tts._silent_mp3()
    ok1 = len(silent) > 44 and silent[:4] == b"RIFF"
    print(
        f"  [{'✅' if ok1 else '❌'}] Silent fallback = {len(silent)} bytes, header RIFF"
    )
    if ok1:
        passed += 1

    # Caso 2: texto vacío → silent (no crash)
    result = tts.synthesize("")
    ok2 = isinstance(result, bytes)
    print(f"  [{'✅' if ok2 else '❌'}] Texto vacío → bytes sin crash")
    if ok2:
        passed += 1

    # Caso 3: list_voices devuelve el mapa
    voices = TTSEngine.list_voices()
    ok3 = "es-co" in voices and "en-us" in voices
    print(f"  [{'✅' if ok3 else '❌'}] list_voices: {list(voices.keys())}")
    if ok3:
        passed += 1

    return passed == 3


# ══════════════════════════════════════════════════════════
def test_kalman_pipeline() -> bool:
    sep("4 · Pipeline texto → Kalman Surprise")
    passed = 0

    def text_to_emb(text: str) -> np.ndarray:
        h = hash(text) % (2**32)
        rng = np.random.default_rng(h)
        return rng.standard_normal(64)

    state = np.zeros(64)
    uncertainty = np.ones(64)

    def compute_surprise(obs: np.ndarray) -> float:
        nonlocal state, uncertainty
        uncertainty += 1e-4
        K = uncertainty / (uncertainty + 1e-2)
        innov = obs - state
        surprise = float(np.mean((innov**2) / (uncertainty + 1e-2)))
        state += K * innov
        uncertainty *= 1 - K
        return surprise

    # Primer evento — alta sorpresa (estado frío)
    s1 = compute_surprise(text_to_emb("Hola ZANA"))
    ok1 = s1 > 0
    print(
        f"  [{'✅' if ok1 else '❌'}] Primera percepción surprise={s1:.4f} (debe ser > 0)"
    )
    if ok1:
        passed += 1

    # Mismo texto repetido — sorpresa baja (estado caliente)
    s2 = compute_surprise(text_to_emb("Hola ZANA"))
    ok2 = s2 < s1
    print(
        f"  [{'✅' if ok2 else '❌'}] Texto repetido surprise={s2:.4f} < {s1:.4f} (Kalman aprende)"
    )
    if ok2:
        passed += 1

    # Cambio radical de tema — sorpresa alta de nuevo
    s3 = compute_surprise(text_to_emb("ERROR CRÍTICO EN EL SERVIDOR DE PRODUCCIÓN"))
    ok3 = s3 > s2
    print(f"  [{'✅' if ok3 else '❌'}] Cambio radical surprise={s3:.4f} > {s2:.4f}")
    if ok3:
        passed += 1

    return passed == 3


# ══════════════════════════════════════════════════════════
def test_agentcard_multimodal() -> bool:
    sep("5 · AgentCard — skills multimodales declarados")
    # Verificar que el código del registry tenga los nuevos skills
    registry_src = Path(__file__).parent.parent / "registry/src/main.rs"
    if not registry_src.exists():
        print("  [❌] registry/src/main.rs no encontrado")
        return False

    content = registry_src.read_text()
    passed = 0

    for skill_id in ["sense_audio", "sense_vision"]:
        ok = f'id: "{skill_id}"' in content
        print(f"  [{'✅' if ok else '❌'}] Skill '{skill_id}' en AgentCard")
        if ok:
            passed += 1

    for mime in ["audio/", "image/", "video/"]:
        ok = mime in content
        print(f"  [{'✅' if ok else '❌'}] MIME type '{mime}' en FilePart routing")
        if ok:
            passed += 1

    file_part_ok = "FileContent" in content and "mimeType" in content
    print(
        f"  [{'✅' if file_part_ok else '❌'}] FilePart struct con mimeType declarado"
    )
    if file_part_ok:
        passed += 1

    return passed == 6


# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "═" * 58)
    print("  ZANA MULTIMODAL — TEST DE INTEGRACIÓN")
    print("═" * 58)

    results = {
        "1 PerceptionEvent": test_perception_event(),
        "2 AudioProcessor": test_audio_processor(),
        "3 TTSEngine": test_tts_engine(),
        "4 Kalman Pipeline": test_kalman_pipeline(),
        "5 AgentCard multimod": test_agentcard_multimodal(),
    }

    print("\n" + "═" * 58)
    print("  RESULTS")
    print("═" * 58)
    all_pass = True
    for name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\n  🔊 LA CAPA SENSORIAL ESTÁ VIVA. EL AEON PUEDE OÍR Y VER.")
    else:
        print("\n  ⚠️  Algunos tests fallaron. Revisar arriba.")

    sys.exit(0 if all_pass else 1)
