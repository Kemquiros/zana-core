import sys
import os
from pathlib import Path
import numpy as np
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from autonomy.autonomous_orchestrator import AutonomousOrchestrator

def test_phase7_e2e():
    print("--- 🚀 ZANA PHASE 7: END-TO-END AUTONOMY TEST ---")
    
    orchestrator = AutonomousOrchestrator()
    
    # 1. Define an Autonomous Campaign (Multiple steps)
    campaign_tasks = [
        "Calculate base log scale",
        "Predict exponential growth for KoruOS",
        "Analyze log variance of resource usage"
    ]
    
    # Constant context for the campaign
    context_emb = np.random.randn(384)
    
    history = []
    print(f"Starting Autonomous Campaign with {len(campaign_tasks)} steps...")
    
    for task in campaign_tasks:
        result = orchestrator.run_autonomous_step(context_emb, task)
        history.append(result)
        print("-" * 50)

    # 2. Validation
    # We check if the brain stored the state and if rewards were non-zero
    print("\n--- 🧠 CAMPAIGN ANALYSIS ---")
    total_reward = sum(h["reward"] for h in history)
    success_rate = sum(1 for h in history if h["success"]) / len(history)
    
    print(f"Total Campaign Reward: {total_reward:.4f}")
    print(f"Success Rate: {success_rate * 100:.1f}%")
    
    brain_path = Path(__file__).parent.parent / "autonomy/zana_brain.pkl"
    if brain_path.exists():
        print("✅ SUCCESS: Policy Brain persisted (zana_brain.pkl).")
    else:
        print("❌ FAIL: Policy Brain not saved.")

    if total_reward != 0:
        print("✅ SUCCESS: Reward Engine is driving learning.")
    else:
        print("❌ FAIL: Zero reward signal.")

if __name__ == "__main__":
    test_phase7_e2e()
