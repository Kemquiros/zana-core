import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from swarm.dna import ZanaDNA

class HiveNode:
    """
    ZANA Hive Node.
    Handles data-agnostic decoupling and architecture sharing (A2A).
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.dna = ZanaDNA(author=node_id)

    def generate_spec_card(self) -> Dict[str, Any]:
        """Generates a shareable 'Architecture Card' (The NFT metadata)."""
        return {
            "node_id": self.node_id,
            "fingerprint": self.dna.get_fingerprint(),
            "dna": asdict(self.dna) if 'asdict' in globals() else json.loads(self.dna.to_json()),
            "status": "Verified",
            "swarm_synced": True
        }

    def sync_from_swarm(self, peer_spec: Dict[str, Any]):
        """Clones a peer's architecture (A2A Handshake)."""
        print(f"📡 [A2A] Syncing with Peer {peer_spec['node_id']}...")
        self.dna = ZanaDNA.from_json(json.dumps(peer_spec['dna']))
        print(f"✅ [A2A] Architecture CLONED. Fingerprint: {self.dna.get_fingerprint()}")

if __name__ == "__main__":
    from dataclasses import asdict
    print("--- 📡 ZANA HIVE: PEER SYNC TEST ---")
    node_a = HiveNode("ZANA_ALPHA")
    node_b = HiveNode("ZANA_BETA")
    
    # Node B likes Node A's architecture
    card_a = node_a.generate_spec_card()
    node_b.sync_from_swarm(card_a)
    
    if node_a.dna.get_fingerprint() == node_b.dna.get_fingerprint():
        print("✅ SUCCESS: Architectures synchronized via A2A.")
    else:
        print("❌ FAIL: Synchronization mismatch.")
