import numpy as np
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from autonomy.brain import PolicyBrain

def run_python_brain_benchmark():
    print("--- 🐍 ZANA PYTHON BRAIN: PERFORMANCE BENCHMARK ---")
    dim = 384
    iterations = 1000 # Python scale
    
    brain = PolicyBrain(input_dim=dim, hidden_dim=64, output_dim=4)
    mock_obs = np.random.randn(dim)
    
    start = time.time()
    for _ in range(iterations):
        brain.forward(mock_obs)
    end = time.time()
    
    total_ms = (end - start) * 1000.0
    per_op_ns = (total_ms * 1000000) / iterations
    
    # Estimate 100k
    est_100k_ms = (per_op_ns * 100000) / 1000000
    
    print(f"✅ {iterations:,} ops COMPLETED in {total_ms:.4f}ms")
    print(f"✅ ESTIMATED 100,000 ops: {est_100k_ms:.4f}ms")
    print(f"✅ LATENCY PER OP: {per_op_ns:.2f}ns")
    
if __name__ == "__main__":
    run_python_brain_benchmark()
