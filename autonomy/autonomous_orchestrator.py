import sys
import os
import json
import numpy as np
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from autonomy.brain import PolicyBrain
from autonomy.reward_engine import RewardEngine
from procedural_memory.manager import SkillRegistry
from procedural_memory.math_agent import EMLMathAgent

class AutonomousOrchestrator:
    """
    The Heart of ZANA's Autonomy (Phase 7).
    Coordinated Loop: Observe Context -> Consult World Model -> 
    Pick Skill (Policy Brain) -> Execute -> Learn (Reward Engine).
    """
    def __init__(self):
        self.registry = SkillRegistry()
        self.reward_engine = RewardEngine()
        self.math_agent = EMLMathAgent()
        
        # Skills ZANA can choose from
        self.available_skills = ["eml_reconstruct_log", "eml_reconstruct_exp"]
        self.brain = PolicyBrain(output_dim=len(self.available_skills))

    def run_autonomous_step(self, context_embedding: np.ndarray, task_description: str) -> Dict[str, Any]:
        print(f"--- 🔱 ZANA AUTONOMOUS STEP: {task_description} ---")
        
        # 1. Consult World Model (Neo4j simulation placeholder)
        print("SIMULATING causal impact in World Model...")
        
        # 2. Select Action (Skill) based on Policy Brain
        skill_idx = self.brain.select_action(context_embedding)
        chosen_skill = self.available_skills[skill_idx]
        print(f"POLICY BRAIN selected skill: {chosen_skill}")

        # 3. Execute Action
        t0 = time.time()
        # For demo: specific math tasks
        if "log" in task_description.lower() or chosen_skill == "eml_reconstruct_log":
            outcome = self.math_agent.execute_math_task("eml_reconstruct_log", x=np.random.uniform(1.1, 5.0))
        else:
            outcome = self.math_agent.execute_math_task("eml_reconstruct_exp", x=np.random.uniform(0.1, 2.0))
        
        latency = (time.time() - t0) * 1000
        outcome["latency_ms"] = latency
        outcome["token_usage"] = 500 # Simulated base cost

        # 4. Calculate Reward and Train
        reward = self.reward_engine.calculate_reward(outcome)
        print(f"REWARD received: {reward:.4f}")
        
        self.brain.train_step(context_embedding, skill_idx, reward)
        print("BRAIN UPDATED via Policy Gradient.")
        
        return {
            "task": task_description,
            "chosen_skill": chosen_skill,
            "reward": reward,
            "success": outcome["success"]
        }

if __name__ == "__main__":
    orchestrator = AutonomousOrchestrator()
    mock_ctx = np.random.randn(384)
    res = orchestrator.run_autonomous_step(mock_ctx, "Calculate fundamental log constant")
    print(json.dumps(res, indent=2))
