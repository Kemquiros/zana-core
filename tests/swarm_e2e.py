import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from swarm.meta_evolution import MetaEvolutionaryModule
from swarm.hive_node import HiveNode


def test_swarm_e2e():
    print("--- 🐝 ZANA SWARM: END-TO-END HIVE TEST ---")

    # 1. Setup Local Hive Node
    node = HiveNode("ZANA_HIVE_01")
    mem = MetaEvolutionaryModule(epsilon=1.0)  # Force exploration for test

    print(f"[STEP 1] Initial Fingerprint: {node.dna.get_fingerprint()}")

    # 2. Simulate Architectural Evolution
    print("\n[STEP 2] Simulating 10 tasks to drive Meta-Evolution...")
    for i in range(10):
        # Mock outcome
        outcome = {"success": True, "score": 0.9, "token_usage": 500, "latency_ms": 100}
        mem.step(outcome)
        # Update node DNA with evolved DNA
        node.dna = mem.get_current_config()

    print(f"Evolved Fingerprint: {node.dna.get_fingerprint()}")

    # 3. Sharing & Peer Sync (The Swarm)
    print("\n[STEP 3] Testing Architecture Sharing (A2A)...")
    spec_card = node.generate_spec_card()

    new_peer = HiveNode("ZANA_PEER_99")
    print(f"Peer Initial Fingerprint: {new_peer.dna.get_fingerprint()}")

    new_peer.sync_from_swarm(spec_card)

    # 4. Validation
    print("\n--- 🧠 SWARM ANALYSIS ---")
    if node.dna.get_fingerprint() == new_peer.dna.get_fingerprint():
        print("✅ SUCCESS: Hive Mind synchronized. Evolution propagated.")
    else:
        print("❌ FAIL: Peer synchronization failed.")

    if node.dna.author == "ZANA_HIVE_01":
        print("✅ SUCCESS: DNA metadata preserved.")


if __name__ == "__main__":
    test_swarm_e2e()
