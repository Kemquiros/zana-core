import numpy as np
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

class OptimizedKalmanFilter:
    def __init__(self, dim: int = 384, process_noise: float = 1e-4, measurement_noise: float = 1e-2):
        self.dim = dim
        self.state = np.zeros(dim)
        self.uncertainty = np.ones(dim) # Vectorized diagonal
        self.Q = process_noise
        self.R = measurement_noise

    def update(self, observation: np.ndarray) -> float:
        # Optimized vectorized update
        self.uncertainty += self.Q
        K = self.uncertainty / (self.uncertainty + self.R)
        innovation = observation - self.state
        surprise = np.mean((innovation**2) / (self.uncertainty + self.R))
        self.state += K * innovation
        self.uncertainty *= (1.0 - K)
        return float(surprise)

def run_python_benchmark():
    print("--- 🐍 ZANA PYTHON CORE (OPTIMIZED): PERFORMANCE BENCHMARK ---")
    dim = 384
    iterations = 100_000
    
    kf = OptimizedKalmanFilter(dim=dim)
    mock_obs = np.full(dim, 0.5)
    
    start = time.time()
    for _ in range(iterations):
        kf.update(mock_obs)
    end = time.time()
    
    total_ms = (end - start) * 1000.0
    per_op_ns = (total_ms * 1000000) / iterations
    
    print(f"✅ {iterations:,} ops COMPLETED in {total_ms:.4f}ms")
    print(f"✅ LATENCY PER OP: {per_op_ns:.2f}ns")
    
if __name__ == "__main__":
    run_python_benchmark()
