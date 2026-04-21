import numpy as np
import os
from pathlib import Path
from typing import List
import zana_steel_core

class PolicyBrain:
    """
    ZANA Steel Core Wrapper for Policy Network (Rust implementation).
    Maps context embeddings to skill probabilities.
    """
    def __init__(self, input_dim: int = 384, hidden_dim: int = 64, output_dim: int = 4):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.inner = zana_steel_core.PyPolicyBrain(input_dim, hidden_dim, output_dim)

    def forward(self, state: np.ndarray) -> np.ndarray:
        probs = self.inner.forward(state.tolist())
        return np.array(probs).reshape(1, -1)

    def select_action(self, state: np.ndarray) -> int:
        return self.inner.select_action(state.tolist())

    def train_step(self, state: np.ndarray, action: int, reward: float, learning_rate: float = 0.01):
        self.inner.train_step(state.tolist(), action, reward, learning_rate)
        # Note: In a real production scenario, we would persist weights 
        # from Rust to disk if needed, but for this memory session we stay in-memory.

    def save(self):
        # Current prototype: persistence handled via DNA SDA
        pass

    def load(self):
        pass
