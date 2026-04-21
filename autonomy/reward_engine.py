import json
import numpy as np
from typing import Dict, Any

class RewardEngine:
    """
    Calculates rewards for XANA's actions to drive Reinforcement Learning.
    Based on Phase 7 specs: Reward = success_score + learning_gain - token_cost - time_penalty.
    """
    def __init__(self, token_price: float = 0.000015):
        self.token_price = token_price

    def calculate_reward(self, outcome: Dict[str, Any]) -> float:
        # 1. Success Score (Primary objective)
        success_score = 1.0 if outcome.get("success") else -1.0
        
        # 2. Accuracy/Score Bonus
        score_bonus = outcome.get("score", 0.0) * 0.5
        
        # 3. Learning Gain (Surprise as a proxy for learning)
        # Higher surprise in a successful task = high learning gain
        surprise = outcome.get("resonance", {}).get("surprise", 0.0)
        learning_gain = min(surprise * 0.1, 0.5) if outcome.get("success") else 0.0
        
        # 4. Penalties (Resource consumption)
        token_count = outcome.get("token_usage", 0)
        token_penalty = token_count * self.token_price
        
        latency = outcome.get("latency_ms", 0)
        time_penalty = (latency / 1000.0) * 0.05 # 0.05 reward penalty per second
        
        total_reward = success_score + score_bonus + learning_gain - token_penalty - time_penalty
        return float(total_reward)

if __name__ == "__main__":
    print("--- ⚖️ REWARD ENGINE TEST ---")
    engine = RewardEngine()
    
    # Simulate a successful but expensive task
    mock_outcome = {
        "success": True,
        "score": 0.95,
        "resonance": {"surprise": 2.5},
        "token_usage": 1500,
        "latency_ms": 2000
    }
    
    r = engine.calculate_reward(mock_outcome)
    print(f"Total Reward (Success/High Surprise/High Cost): {r:.4f}")
