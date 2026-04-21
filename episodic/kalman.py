import numpy as np
from typing import List, Optional
import xana_steel_core

class CognitiveKalmanFilter:
    """
    XANA Steel Core Wrapper for Cognitive Kalman Filter (Rust implementation).
    Treats the latent task representation as a state to be estimated.
    """
    def __init__(self, dim: int = 384, process_noise: float = 1e-4, measurement_noise: float = 1e-2):
        self.dim = dim
        self.inner = xana_steel_core.PyKalmanFilter(dim, process_noise, measurement_noise)

    def update(self, observation: np.ndarray) -> float:
        """
        Update state with a new observation. Returns Bayesian Surprise.
        """
        if observation.shape[0] != self.dim:
            raise ValueError(f"Observation dimension {observation.shape[0]} does not match state dimension {self.dim}")
        
        # Convert numpy to list for Rust
        return self.inner.update(observation.tolist())

    def get_uncertainty_score(self) -> float:
        return self.inner.get_uncertainty_score()

def segment_episode(surprises: List[float], threshold: float = 2.0) -> bool:
    """
    Decide if a new episode boundary should be created based on surprise.
    """
    if not surprises:
        return False
    return surprises[-1] > threshold
