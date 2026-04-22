import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from episodic.kalman import CognitiveKalmanFilter


class ContextCompressor:
    """
    Compresses context by keeping only 'high innovation' segments
    calculated by the Cognitive Kalman Filter.
    """

    def __init__(self, surprise_threshold: float = 0.5):
        self.kf = CognitiveKalmanFilter(dim=384)
        self.surprise_threshold = surprise_threshold

    def filter_segments(
        self, segments: List[Dict[str, Any]], embeddings: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """
        Filters a list of context segments based on Bayesian Surprise.

        Args:
            segments: List of dicts, each with 'text' and 'metadata'.
            embeddings: List of embedding vectors corresponding to segments.
        """
        compressed = []
        for seg, emb in zip(segments, embeddings):
            surprise = self.kf.update(emb)
            # If surprise is high, it's a context shift or new information (Keep it)
            # If uncertainty is still high, keep it.
            if (
                surprise > self.surprise_threshold
                or self.kf.get_uncertainty_score() > 0.1
            ):
                seg["surprise"] = surprise
                compressed.append(seg)

        return compressed


if __name__ == "__main__":
    print("--- 🧠 CONTEXT COMPRESSOR TEST ---")
    # Mock segments and embeddings
    compressor = ContextCompressor(surprise_threshold=0.1)

    # Simulate a stream of repetitive info followed by new info
    mock_emb_a = np.random.randn(384) * 0.01 + 0.1
    mock_emb_b = np.random.randn(384) * 0.1 + 0.5  # Shift

    segments = [{"text": f"Seg {i}"} for i in range(10)]
    embeddings = [mock_emb_a for _ in range(5)] + [mock_emb_b for _ in range(5)]

    result = compressor.filter_segments(segments, embeddings)
    print(f"Original segments: {len(segments)}")
    print(f"Compressed segments: {len(result)}")
    for r in result:
        print(f"Kept: {r['text']} (Surprise: {r['surprise']:.4f})")
