import numpy as np
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from episodic.kalman import CognitiveKalmanFilter

def run_python_benchmark():
    print("--- 🐍 ZANA PYTHON CORE: PERFORMANCE BENCHMARK ---")
    dim = 384
    iterations = 1000 # Python is much slower, 100k would take too long for quick comparison
    
    kf = CognitiveKalmanFilter(dim=dim)
    mock_obs = np.full(dim, 0.5)
    
    start = time.time()
    for _ in range(iterations):
        kf.update(mock_obs)
    end = time.time()
    
    total_ms = (end - start) * 1000.0
    per_op_ms = total_ms / iterations
    
    # Estimate 100k time based on 1k
    estimated_100k_ms = per_op_ms * 100_000
    
    print(f"✅ 1,000 ops COMPLETED in {total_ms:.4f}ms")
    print(f"✅ ESTIMATED 100,000 ops: {estimated_100k_ms:.4f}ms")
    print(f"✅ LATENCY PER OP: {per_op_ms * 1000000:.2f}ns")
    
if __name__ == "__main__":
    run_python_benchmark()
