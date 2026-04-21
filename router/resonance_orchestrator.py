import argparse
import sys
import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from router.phi_partition import PhiPartition
from router.context_compressor import ContextCompressor
from router.classify import Route, ClaudeModel, classify, select_claude_model
from router.semantic_cache import SemanticCache
from episodic.kalman import CognitiveKalmanFilter

class ResonanceOrchestrator:
    """
    XANA Resonance Orchestrator (Phase 5).
    Coordinates Bayesian Surprise Filtering, Phi Token Management, and Model Routing.
    """
    def __init__(self, token_budget: int = 128000):
        self.token_budget = token_budget
        self.compressor = ContextCompressor(surprise_threshold=1.5)
        self.partitioner = PhiPartition()
        self.kf = CognitiveKalmanFilter(dim=384)
        self.cache = SemanticCache()

    def route_resonance(self, query: str, query_embedding: np.ndarray, context_segments: List[Dict[str, Any]] = None, context_embeddings: List[np.ndarray] = None) -> Dict[str, Any]:
        """
        Main entry point for Phase 5 Routing.
        """
        print(f"--- 🌀 XANA RESONANCE: ANALYZING '{query[:50]}...' ---")

        # 1. Check Semantic Cache
        cached = self.cache.get(query)
        if cached:
            return {
                "cache_hit": True,
                "result": cached["response"],
                "metadata": cached["metadata"]
            }

        # 2. Calculate Bayesian Surprise for the Query
        surprise = self.kf.update(query_embedding)
        uncertainty = self.kf.get_uncertainty_score()
        print(f"Innovation/Surprise: {surprise:.4f} | Uncertainty: {uncertainty:.4f}")

        # 3. Partition Tokens (Phi Rule)
        partitions = self.partitioner.partition_tokens(self.token_budget)

        # 4. Compress Context (if provided)
        compressed_segments = []
        if context_segments and context_embeddings:
            compressed_segments = self.compressor.filter_segments(context_segments, context_embeddings)
            print(f"Context Filtered: {len(context_segments)} -> {len(compressed_segments)} segments.")

        # 5. Dimension 1: Backend Route
        backend, b_reason = classify(query)

        # 6. Dimension 2: Model Tier (Enhanced by Surprise)
        # If surprise is extremely high (> 5.0), force a higher tier for safety
        if surprise > 5.0 and backend == Route.CLAUDE:
            model = ClaudeModel.OPUS
            m_reason = f"High Surprise ({surprise:.2f}) -> Critical Reasoning Required"
        else:
            model, m_reason = select_claude_model(query)

        return {
            "resonance": {
                "surprise": surprise,
                "uncertainty": uncertainty,
                "innovation_detected": surprise > 1.5
            },
            "routing": {
                "backend": backend.value,
                "model": model.name.lower() if model else None,
                "reasoning": f"{b_reason} | {m_reason}"
            },
            "partitions": partitions,
            "context_count": len(compressed_segments)
        }

def main():
    parser = argparse.ArgumentParser(description="XANA Resonance Orchestrator")
    parser.add_argument("query", help="The user query or task")
    parser.add_argument("--tokens", type=int, default=128000, help="Total token budget")
    args = parser.parse_args()

    # Need an embedding to run
    # For demo purposes, we generate a random 384d vector
    query_emb = np.random.randn(384) * 0.1
    
    orchestrator = ResonanceOrchestrator(token_budget=args.tokens)
    execution_plan = orchestrator.route_resonance(args.query, query_emb)

    print("\n--- 🚀 RESONANCE EXECUTION PLAN ---")
    print(json.dumps(execution_plan, indent=2))

if __name__ == "__main__":
    main()
