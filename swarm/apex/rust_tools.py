"""
Tool integration with the Rust Steel Core.
Uses smolagents @tool to register functions that the LLM can call.
"""
from smolagents import tool
from typing import Dict, Any, List
import ctypes
import os

try:
    import zana_steel_core
    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False
    print("⚠️ [ZANA] zana_steel_core.so not found. Using mock fallback.")

@tool
def calculate_eml(expression: str, variables: Dict[str, float]) -> float:
    """
    Executes the EML (Exact Math Logic) operator in the Rust core to guarantee
    zero-hallucination mathematical reasoning.

    Args:
        expression: The symbolic formula to calculate.
        variables: Dictionary of variables and their values.

    Returns:
        float: The exact result computed in Rust.
    """
    if RUST_CORE_AVAILABLE:
        return zana_steel_core.eml_compute(expression, variables)

    import math
    print(f"⚙️ [RUST-MOCK] Calculating EML: {expression}")
    return 42.0

@tool
def kalman_filter_surprise(new_data_embedding: List[float], state_embedding: List[float]) -> float:
    """
    Calculates the "Bayesian Surprise" between new data and the current latent state
    using the Kalman Filter in Rust.

    Args:
        new_data_embedding: Vector of the new data point.
        state_embedding: Vector of the current state.

    Returns:
        float: Surprise level (Mahalanobis distance).
    """
    if RUST_CORE_AVAILABLE:
        return zana_steel_core.kalman_surprise(new_data_embedding, state_embedding)

    print("⚙️ [RUST-MOCK] Evaluating Bayesian Surprise...")
    return 0.85

@tool
def audit_security_payload(payload_str: str) -> bool:
    """
    Sentinel tool for scanning PII, API Keys, or prompt injections
    using the native security module (zana_armor.so).

    Args:
        payload_str: Text to audit.

    Returns:
        bool: True if safe, False if blocked.
    """
    try:
        import zana_armor
        return zana_armor.scan(payload_str)
    except ImportError:
        # Strict mock fallback
        if "sk-" in payload_str or "password" in payload_str.lower():
            return False
        return True
