"""
The Central Orchestrator (The Apex Quintet in Action).
Manages communication between the 5 sub-agents using the AION Protocol.
"""

from .aion import AionMessage
from .agents import (
    archivist_agent,
    herald_agent,
    operator_agent,
    analyst_agent,
    sentinel_agent,
    ARCHIVIST_PROMPT,
    HERALD_PROMPT,
    OPERATOR_PROMPT,
    ANALYST_PROMPT,
    SENTINEL_PROMPT,
)
from autonomy.resonance_engine import ResonanceEngine


class ApexOrchestrator:
    def __init__(self):
        self.state = {}
        self.resonance_engine = ResonanceEngine()

    def _get_resonance(self) -> str:
        return self.resonance_engine.get_system_directive()

    def process_request(self, user_prompt: str, context_vector: list = None) -> str:
        """
        Executes the full lifecycle of a complex request through the Apex Quintet.
        """
        print(f"🌀 [ORCHESTRATOR] Incoming request: '{user_prompt}'")
        res_dir = self._get_resonance()

        # 1. SENTINEL: Input audit (Security)
        print("🛡️ [1/6] SENTINEL auditing prompt...")
        sentinel_query = SENTINEL_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Audit this user prompt: {user_prompt}"
        )
        sentinel_audit = sentinel_agent.run(sentinel_query)
        if (
            "BLOQUEADO" in str(sentinel_audit).upper()
            or "UNSAFE" in str(sentinel_audit).upper()
            or "❌" in str(sentinel_audit)
        ):
            return str(sentinel_audit)

        # 2. ARCHIVIST: Retrieve necessary context (Memory)
        print("📚 [2/6] ARCHIVIST searching context in Vault...")
        archivist_query = ARCHIVIST_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Find relevant context to answer this request: {user_prompt}"
        )
        archivist_context = archivist_agent.run(archivist_query)

        # 3. ANALYST: Reasoning and deduction (Logic)
        print("🔬 [3/6] ANALYST performing reasoning...")
        analyst_query = ANALYST_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Reason about the following query using the retrieved context.\nQUERY: {user_prompt}\nCONTEXT: {archivist_context}"
        )
        deduction = analyst_agent.run(analyst_query)

        # 4. OPERATOR: Action execution (Tools)
        print("⚙️ [4/6] OPERATOR executing tools...")
        operator_query = OPERATOR_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Execute any necessary tools based on the deduction.\nDEDUCTION: {deduction}"
        )
        operation_result = operator_agent.run(operator_query)

        # 5. HERALD: Final synthesis (Synthesis)
        print("📢 [5/6] HERALD synthesizing final response...")
        herald_query = HERALD_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Synthesize the final answer for the user.\nORIGINAL_PROMPT: {user_prompt}\nANALYSIS: {deduction}\nOP_RESULT: {operation_result}"
        )
        final_response = herald_agent.run(herald_query)

        # 6. SENTINEL: Output audit (Safety)
        print("🛡️ [6/6] SENTINEL auditing output...")
        final_audit_query = SENTINEL_PROMPT.replace("{resonance_directive}", res_dir).format(
            query=f"Audit this final response for safety: {final_response}"
        )
        final_audit = sentinel_agent.run(final_audit_query)

        return str(final_audit)
