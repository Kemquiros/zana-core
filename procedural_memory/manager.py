import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

class SkillRegistry:
    """
    Manages the Procedural Memory (Skills) of ZANA.
    Stores recipes, execution metrics, and Q-values for optimal routing.
    """
    def __init__(self, storage_path: str = "skills_registry.json"):
        self.storage_path = Path(__file__).parent / storage_path
        self.skills = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.storage_path.exists():
            return json.loads(self.storage_path.read_text())
        return {}

    def save(self):
        self.storage_path.write_text(json.dumps(self.skills, indent=2))

    def register_skill(self, skill_id: str, name: str, steps: List[str], domain: str = "general"):
        if skill_id not in self.skills:
            self.skills[skill_id] = {
                "name": name,
                "domain": domain,
                "steps": steps,
                "metrics": {
                    "executions": 0,
                    "successes": 0,
                    "avg_score": 0.0,
                    "last_outcome": None
                },
                "q_value": 0.5, # Initial neutrality
                "version": "1.0.0"
            }
            self.save()

    def update_skill_performance(self, skill_id: str, success: bool, score: float):
        """
        Offline RL Lite: Update Q-value based on outcome.
        Q(s,a) = Q(s,a) + alpha * (Reward - Q(s,a))
        """
        if skill_id not in self.skills:
            return

        skill = self.skills[skill_id]
        metrics = skill["metrics"]
        
        # 1. Update basic metrics
        metrics["executions"] += 1
        if success:
            metrics["successes"] += 1
        
        # Incremental average
        metrics["avg_score"] = (metrics["avg_score"] * (metrics["executions"] - 1) + score) / metrics["executions"]
        
        # 2. Update Q-Value (alpha = 0.1, reward = score)
        alpha = 0.1
        reward = score if success else -1.0 # Penalty for failure
        skill["q_value"] += alpha * (reward - skill["q_value"])
        
        # 3. Handle degradation (Self-Healing trigger)
        success_rate = metrics["successes"] / metrics["executions"]
        if metrics["executions"] > 5 and success_rate < 0.6:
            skill["status"] = "NEEDS_REFACTOR"
        
        self.save()

    def get_best_skill(self, domain: str) -> Optional[str]:
        """Returns the skill_id with highest Q-value in a given domain."""
        domain_skills = [s_id for s_id, s in self.skills.items() if s["domain"] == domain]
        if not domain_skills:
            return None
        return max(domain_skills, key=lambda s_id: self.skills[s_id]["q_value"])

if __name__ == "__main__":
    print("--- 🧠 PROCEDURAL MEMORY TEST ---")
    reg = SkillRegistry()
    
    # Register a mock skill
    reg.register_skill("deploy_app", "FastAPI Deployment", ["build", "test", "deploy"], domain="devops")
    
    # Simulate some runs
    reg.update_skill_performance("deploy_app", True, 0.9)
    reg.update_skill_performance("deploy_app", False, -0.5)
    
    best = reg.get_best_skill("devops")
    print(f"Best DevOps skill: {best} (Q={reg.skills[best]['q_value']:.4f})")
