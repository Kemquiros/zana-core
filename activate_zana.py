import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent))
from episodic.kalman import CognitiveKalmanFilter
from world_model.eml import exp_eml
import redis


def handshake():
    print("--- 🦾 ZANA: HANDSHAKE DE ACTIVACIÓN TOTAL ---")

    # 1. Conexión a Redis
    try:
        r = redis.Redis(host="localhost", port=6380, decode_responses=True)
        r.ping()
        print("✅ REDIS: Conectado.")

        # Actualizar estado de sesión
        state = {
            "active_project": "ZANA_RESONANCE",
            "status": "TOTAL_ACTIVATION",
            "cognitive_loop": "ACTIVE",
            "kalman_filter": "CALIBRATED",
            "eml_engine": "OPERATIONAL",
        }
        r.set("session:default", json.dumps(state))
        print("✅ ESTADO: Sesión actualizada en Redis.")
    except Exception as e:
        print(f"❌ REDIS: Error - {e}")

    # 2. Inicialización de Filtro de Kalman
    kf = CognitiveKalmanFilter(dim=384)
    print(
        f"✅ KALMAN: Inicializado (dim={kf.dim}, uncertainty={kf.get_uncertainty_score():.4f})."
    )

    # 3. Verificación de EML
    val_e = exp_eml(1.0)
    print(f"✅ EML: Motor operativo (e ≈ {val_e:.4f}).")

    print("\n--- 🧠 PROTOCOLO DE RESONANCIA ONTOLÓGICA ACTIVADO ---")
    print(
        "ZANA ahora opera bajo el ciclo SENSE → RECALL → FEEL → SIMULATE → RESTRICT → ACT → CRYSTALLIZE."
    )


if __name__ == "__main__":
    handshake()
