import json
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List
import hashlib

@dataclass
class ZanaDNA:
    """
    Self-Describing Architecture (SDA) - The DNA of ZANA.
    This encapsulates the entire configuration of the Cognitive Architecture.
    """
    version: str = "1.0.0"
    
    # 📐 Core Ratios (Golden Phi)
    phi_ratio: float = 0.61803398875
    context_retention_threshold: float = 0.38196601125
    
    # 🧠 Cognition Parameters (Kalman)
    kalman_surprise_threshold: float = 1.5
    kalman_process_noise: float = 1e-4
    kalman_measurement_noise: float = 1e-2
    
    # 🦾 Autonomy Weights (RL)
    q_learning_rate: float = 0.1
    q_discount_factor: float = 0.9
    
    # 🚀 Routing
    opus_force_threshold: float = 5.0
    haiku_compression_limit: int = 500
    
    # 📐 EML Features
    eml_enabled: bool = True
    eml_max_depth: int = 8
    
    # 🧬 Metadata
    author: str = "ZANA_ORIGIN"
    tags: List[str] = field(default_factory=lambda: ["AGI", "Hive", "Resonance"])

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def get_fingerprint(self) -> str:
        """Architecture fingerprint (Digital Signature)."""
        data = self.to_json()
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def from_json(cls, json_str: str) -> 'ZanaDNA':
        data = json.loads(json_str)
        return cls(**data)

    def mutate(self, intensity: float = 0.05):
        """Random architectural mutation for exploration."""
        import random
        # Mutate phi_ratio slightly
        self.phi_ratio += random.uniform(-intensity, intensity)
        self.phi_ratio = max(0.1, min(0.9, self.phi_ratio))
        # Mutate kalman threshold
        self.kalman_surprise_threshold += random.uniform(-intensity * 10, intensity * 10)
        self.kalman_surprise_threshold = max(0.1, self.kalman_surprise_threshold)
