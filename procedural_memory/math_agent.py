import sys
from pathlib import Path
from typing import Dict, Any
import numpy as np

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from world_model.eml import exp_eml, log_eml
from procedural_memory.manager import SkillRegistry


class EMLMathAgent:
    """
    Symbolic Math Agent using the EML (Exp-Minus-Log) basis.
    Fulfills Phase 6: Skills Evolution integration.
    """

    def __init__(self):
        self.registry = SkillRegistry()
        self._initialize_skills()

    def _initialize_skills(self):
        # Register core mathematical skills derived from EML
        self.registry.register_skill(
            skill_id="eml_reconstruct_log",
            name="Logarithm Reconstruction (EML)",
            steps=["eml(1, x)", "eml(1, result)", "eml(1, result)"],
            domain="math",
        )
        self.registry.register_skill(
            skill_id="eml_reconstruct_exp",
            name="Exponential Reconstruction (EML)",
            steps=["eml(x, 1)"],
            domain="math",
        )

    def execute_math_task(self, skill_id: str, x: float) -> Dict[str, Any]:
        """
        Executes a math task and evaluates performance.
        """
        success = False
        result = None
        target = None

        try:
            if skill_id == "eml_reconstruct_log":
                result = log_eml(x)
                target = np.log(x)
            elif skill_id == "eml_reconstruct_exp":
                result = exp_eml(x)
                target = np.exp(x)

            # Check precision
            error = abs(result - target)
            score = 1.0 - min(error, 1.0)
            success = error < 1e-10

            # Update Procedural Memory
            self.registry.update_skill_performance(skill_id, success, score)

            return {
                "skill_id": skill_id,
                "result": result,
                "error": error,
                "score": score,
                "success": success,
            }
        except Exception as e:
            self.registry.update_skill_performance(skill_id, False, -1.0)
            return {"error": str(e), "success": False}


if __name__ == "__main__":
    print("--- 📐 EML MATH AGENT: SKILLS TEST ---")
    agent = EMLMathAgent()

    # Test Log reconstruction
    res = agent.execute_math_task("eml_reconstruct_log", 2.0)
    print(f"Log(2.0) Result: {res['result']:.6f} | Score: {res['score']:.4f}")

    # Test Exp reconstruction
    res_exp = agent.execute_math_task("eml_reconstruct_exp", 1.0)
    print(f"Exp(1.0) Result: {res_exp['result']:.6f} | Score: {res_exp['score']:.4f}")
