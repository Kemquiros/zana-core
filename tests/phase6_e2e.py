import sys
import os
import json
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from procedural_memory.math_agent import EMLMathAgent
from procedural_memory.manager import SkillRegistry

def test_phase6_e2e():
    print("--- 🧠 ZANA PHASE 6: END-TO-END PROCEDURAL MEMORY TEST ---")
    
    # 1. Setup
    agent = EMLMathAgent()
    registry = agent.registry
    
    # 2. Baseline State
    skill_id = "eml_reconstruct_log"
    initial_q = registry.skills[skill_id]["q_value"]
    print(f"[STEP 1] Baseline Q-Value for {skill_id}: {initial_q:.4f}")

    # 3. Execution Loop (Simulating Learning)
    print("\n[STEP 2] Simulating 5 successful executions...")
    for _ in range(5):
        agent.execute_math_task(skill_id, x=np.random.uniform(1.1, 10.0))
    
    intermediate_q = registry.skills[skill_id]["q_value"]
    print(f"Intermediate Q-Value: {intermediate_q:.4f}")

    print("\n[STEP 3] Simulating 3 failures (forcing domain errors)...")
    for _ in range(3):
        # Log of negative number will trigger exception/failure
        agent.execute_math_task(skill_id, x=-1.0)
    
    final_q = registry.skills[skill_id]["q_value"]
    print(f"Final Q-Value after failures: {final_q:.4f}")

    # 4. Persistence Check
    print("\n[STEP 4] Verifying persistence...")
    new_registry = SkillRegistry()
    persisted_q = new_registry.skills[skill_id]["q_value"]
    print(f"Persisted Q-Value: {persisted_q:.4f}")

    # 5. Analysis
    print("\n--- 🧠 ANALYSIS ---")
    if intermediate_q > initial_q and final_q < intermediate_q:
        print("✅ SUCCESS: Procedural Memory evolves based on performance (Offline RL Lite).")
    else:
        print("❌ FAIL: Q-Value evolution logic inconsistent.")

    if abs(persisted_q - final_q) < 1e-9:
        print("✅ SUCCESS: Skills Registry persisted correctly.")
    else:
        print("❌ FAIL: Persistence mismatch.")

if __name__ == "__main__":
    test_phase6_e2e()
