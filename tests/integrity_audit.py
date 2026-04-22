import sys
import numpy as np
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from autonomy.brain import PolicyBrain
from episodic.kalman import CognitiveKalmanFilter
from world_model.eml import log_eml


def test_steel_core_integrity():
    print("--- 🦾 ZANA STEEL CORE: INTEGRITY AUDIT ---")

    # 1. EML Precision
    val = 5.0
    res = log_eml(val)
    expected = np.log(val)
    print(f"[EML] log_eml({val}) = {res:.10f} (Expected: {expected:.10f})")
    assert abs(res - expected) < 1e-12

    # 2. Kalman Filter Stability
    kf = CognitiveKalmanFilter(dim=384)
    obs = np.random.randn(384)
    surprise = kf.update(obs)
    print(f"[KALMAN] Initial surprise: {surprise:.4f}")
    assert surprise > 0

    # 3. Policy Brain Forward Pass
    brain = PolicyBrain(input_dim=384, hidden_dim=64, output_dim=4)
    probs = brain.forward(obs)
    print(f"[BRAIN] Probs sum: {np.sum(probs):.4f}")
    assert abs(np.sum(probs) - 1.0) < 1e-6

    print("✅ INTEGRITY AUDIT PASSED.")


if __name__ == "__main__":
    test_steel_core_integrity()
