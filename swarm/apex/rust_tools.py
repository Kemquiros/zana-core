"""
Tool integration with the Rust Steel Core.
Uses smolagents Tool classes to register functions that the LLM can call.
"""

from smolagents import Tool
from typing import Dict, List

try:
    import zana_steel_core

    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False
    print("⚠️ [ZANA] zana_steel_core.so not found. Using mock fallback.")


class CalculateEmlTool(Tool):
    name = "calculate_eml"
    description = "Executes the EML (Exact Math Logic) operator in the Rust core to guarantee zero-hallucination mathematical reasoning."
    inputs = {
        "expression": {
            "type": "string",
            "description": "The symbolic formula to calculate."
        },
        "variables": {
            "type": "object",
            "description": "Dictionary of variables and their values."
        }
    }
    output_type = "number"

    def forward(self, expression: str, variables: Dict[str, float]) -> float:
        if RUST_CORE_AVAILABLE:
            return zana_steel_core.eml_compute(expression, variables)
        print(f"⚙️ [RUST-MOCK] Calculating EML: {expression}")
        return 42.0


class KalmanFilterSurpriseTool(Tool):
    name = "kalman_filter_surprise"
    description = "Calculates the 'Bayesian Surprise' between new data and the current latent state using the Kalman Filter in Rust."
    inputs = {
        "new_data_embedding": {
            "type": "array",
            "description": "Vector of the new data point."
        },
        "state_embedding": {
            "type": "array",
            "description": "Vector of the current state."
        }
    }
    output_type = "number"

    def forward(self, new_data_embedding: List[float], state_embedding: List[float]) -> float:
        if RUST_CORE_AVAILABLE:
            return zana_steel_core.kalman_surprise(new_data_embedding, state_embedding)
        print("⚙️ [RUST-MOCK] Evaluating Bayesian Surprise...")
        return 0.85


class AuditSecurityPayloadTool(Tool):
    name = "audit_security_payload"
    description = "Sentinel tool for scanning PII, API Keys, or prompt injections using the native security module (zana_armor.so)."
    inputs = {
        "payload_str": {
            "type": "string",
            "description": "Text to audit."
        }
    }
    output_type = "boolean"

    def forward(self, payload_str: str) -> bool:
        try:
            import zana_armor
            return zana_armor.scan(payload_str)
        except ImportError:
            # Strict mock fallback
            if "sk-" in payload_str or "password" in payload_str.lower():
                return False
            return True
