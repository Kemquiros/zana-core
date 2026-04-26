from typing import Any, Dict, List, Optional
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


class AeonDelegationRequest(BaseModel):
    """
    Cross-Aeon Protocol:
    Schema used by ZANA to dispatch autonomous tasks to other Aeons (e.g., KoruOS).
    """
    source_aeon: str = Field(description="ID of the calling Aeon (e.g., 'zana-core', 'vecanova-factory').")
    target_aeon: str = Field(description="ID of the target Aeon (e.g., 'koru-os-orchestrator', 'ragnarok-npc').")
    task_id: str = Field(description="Unique identifier for this delegation task.")
    objective: str = Field(description="The primary goal or instruction for the sub-agent.")
    context_payload: AionMessage = Field(description="The contextual AION message containing the latent state and history.")
    constraints: List[str] = Field(default_factory=list, description="Strict rules the sub-agent must follow.")
    timeout_ms: int = Field(default=30000, description="Maximum allowed time in milliseconds for the sub-agent to respond.")


class AeonDelegationResponse(BaseModel):
    """
    Cross-Aeon Protocol:
    Schema returned by sub-agents (e.g., KoruOS NPCs) back to the orchestrator.
    """
    task_id: str = Field(description="The task ID this response corresponds to.")
    status: str = Field(description="'completed', 'failed', 'needs_context', 'blocked'")
    result_payload: Dict[str, Any] = Field(default_factory=dict, description="Structured output from the sub-agent.")
    error_trace: Optional[str] = Field(default=None, description="Detailed error trace if status is 'failed' or 'blocked'.")
    innovation_score: float = Field(default=1.0, description="Metric of how much the sub-agent state changed.")
