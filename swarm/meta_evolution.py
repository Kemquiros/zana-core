import sys
from pathlib import Path
import numpy as np
from typing import List, Dict, Any

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from swarm.dna import ZanaDNA
from autonomy.reward_engine import RewardEngine

class MetaEvolutionaryModule:
    """
    'The Queen' - Meta-Evolutionary Module (MEM).
    Uses Multi-Armed Bandit / Epsilon-Greedy to optimize the ZANA DNA.
    """
    def __init__(self, epsilon: float = 0.2):
        self.epsilon = epsilon # Exploration rate
        self.dna_history: List[ZanaDNA] = [ZanaDNA()]
        self.performance_history: List[float] = []
        self.current_dna = self.dna_history[0]
        self.reward_engine = RewardEngine()

    def step(self, task_outcome: Dict[str, Any]):
        """
        Evaluate current DNA performance and decide whether to mutate.
        """
        reward = self.reward_engine.calculate_reward(task_outcome)
        self.performance_history.append(reward)
        
        # If we have enough history, consider mutation (Exploration)
        if len(self.performance_history) % 5 == 0:
            avg_perf = np.mean(self.performance_history[-5:])
            print(f"--- 🧬 [MEM] Evaluation: Avg Reward = {avg_perf:.4f} ---")
            
            if np.random.random() < self.epsilon:
                print("🧬 [MEM] EXPLORATION: Mutating DNA...")
                new_dna = ZanaDNA.from_json(self.current_dna.to_json())
                new_dna.mutate(intensity=0.1)
                self.dna_history.append(new_dna)
                self.current_dna = new_dna
            else:
                print("🧬 [MEM] EXPLOITATION: Maintaining current DNA.")

    def get_current_config(self) -> ZanaDNA:
        return self.current_dna

if __name__ == "__main__":
    print("--- 🐝 ZANA HIVE: META-EVOLUTION TEST ---")
    mem = MetaEvolutionaryModule()
    
    # Simulate a stream of tasks
    for i in range(15):
        # Simulate an outcome that depends slightly on a 'hidden' optimal phi
        # Let's say optimal phi is 0.7 for this simulation
        current_phi = mem.get_current_config().phi_ratio
        dist_to_opt = abs(current_phi - 0.7)
        success = np.random.random() > dist_to_opt
        
        mock_outcome = {
            "success": success,
            "score": 1.0 - dist_to_opt,
            "token_usage": 1000,
            "latency_ms": 500
        }
        
        mem.step(mock_outcome)
        print(f"Step {i+1}: Phi={current_phi:.4f}, Reward={mem.performance_history[-1]:.4f}")
