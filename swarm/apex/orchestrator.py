"""
The Central Orchestrator (The Apex Quintet in Action).
Manages communication between the 5 sub-agents using the AION Protocol.
"""
from .aion import AionMessage, AionResponse
from .agents import (
    archivist_agent, herald_agent, operator_agent, analyst_agent, sentinel_agent,
    ARCHIVIST_PROMPT, HERALD_PROMPT, OPERATOR_PROMPT, ANALYST_PROMPT, SENTINEL_PROMPT
)
import json

class ApexOrchestrator:
    def __init__(self):
        self.state = {}

    def process_request(self, user_prompt: str, context_vector: list = None) -> str:
        """
        Executes the full lifecycle of a complex request through the Apex Quintet.
        """
        print(f"🌀 [ORCHESTRATOR] Incoming request: '{user_prompt}'")

        # 1. SENTINEL: Input audit (Security)
        print("🛡️ [1/6] SENTINEL auditing prompt...")
        sentinel_query = SENTINEL_PROMPT.format(query=f"Audit this user prompt: {user_prompt}")
        sentinel_audit = sentinel_agent.run(sentinel_query)
        if "BLOQUEADO" in str(sentinel_audit).upper() or "UNSAFE" in str(sentinel_audit).upper() or "❌" in str(sentinel_audit):
            return str(sentinel_audit)

        # 2. ARCHIVIST: Retrieve necessary context (Memory)
        print("📚 [2/6] ARCHIVIST searching context in Vault...")
        archivist_query = ARCHIVIST_PROMPT.format(query=f"Find relevant context to answer this request: {user_prompt}")
        archivist_context = archivist_agent.run(archivist_query)

        # Build AionMessage to pass to Analyst and Operator
        aion_msg = AionMessage(
            intent="Process User Request",
            payload={"user_prompt": user_prompt, "context": archivist_context},
            history_trace=["Sentinel", "Archivist"]
        )

        # 3. ANALYST: Process if logic or numbers are required
        print("🧠 [3/6] ANALYST calculating and reasoning strategy...")
        analyst_query = ANALYST_PROMPT.format(query=f"Analyze the following payload and run calculations if necessary: {aion_msg.to_json()}")
        analysis_result = analyst_agent.run(analyst_query)

        aion_msg.payload["analysis"] = analysis_result
        aion_msg.history_trace.append("Analyst")

        # 4. OPERATOR: Execute external actions if required
        print("⚙️ [4/6] OPERATOR evaluating if external action is needed...")
        operator_query = OPERATOR_PROMPT.format(query=f"If the request requires browsing the internet or executing code, do it. Data: {aion_msg.to_json()}")
        operator_result = operator_agent.run(operator_query)

        aion_msg.payload["execution_data"] = operator_result
        aion_msg.history_trace.append("Operator")

        # 5. HERALD: Draft the final polished response
        print("✍️ [5/6] HERALD drafting final report...")
        herald_query = HERALD_PROMPT.format(query=f"Write a final response to the user based on this data. Tone: Formal, Direct. Data: {aion_msg.to_json()}")
        final_draft = herald_agent.run(herald_query)

        # 6. SENTINEL: Output audit
        print("🛡️ [6/6] SENTINEL auditing outgoing response...")
        sentinel_out_query = SENTINEL_PROMPT.format(query=f"Audit this response to ensure no secrets are leaked. If there are secrets, redact them: {final_draft}")
        sentinel_out_audit = sentinel_agent.run(sentinel_out_query)

        print("✅ [ORCHESTRATOR] Cycle completed successfully.")
        return sentinel_out_audit

# Usage example:
if __name__ == "__main__":
    import asyncio
    orchestrator = ApexOrchestrator()
    res = orchestrator.process_request("Find my expenses this month in Obsidian, sum them, and send me a summary by email.")
    print("\n--- FINAL RESPONSE ---")
    print(res)
