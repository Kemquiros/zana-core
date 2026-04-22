from typing import Any, Dict, List
from pydantic import BaseModel, Field


class AionMessage(BaseModel):
    """
    AION Protocol (Artificial Intelligence Ontological Notation).
    Structured payloads exchanged between sub-agents to prevent
    hallucinations and context loss from plain-text passing.
    """

    intent: str = Field(description="The action or objective required by the message.")
    latent_state: List[float] = Field(
        default_factory=list,
        description="User's vector context (Latent State) extracted by the Kalman Filter.",
    )
    confidence_score: float = Field(
        default=1.0, description="Confidence level of the sending agent (0.0 to 1.0)."
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Structured data to transmit (JSON)."
    )
    history_trace: List[str] = Field(
        default_factory=list,
        description="Trace of agents that have touched this message.",
    )

    def to_json(self) -> str:
        return self.model_dump_json()


class AionResponse(BaseModel):
    status: str = Field(description="'success', 'partial', 'failure', 'blocked'")
    message: str = Field(description="Human-readable or agent-readable response.")
    data: Dict[str, Any] = Field(default_factory=dict, description="Agent output data.")
