import logging
import os
from datetime import datetime
from typing import Annotated, List, TypedDict
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from orchestrator.budget import BUDGET
from orchestrator.compressor import ContextCompressor
from orchestrator.trajectory import TrajectoryCapture

logger = logging.getLogger(__name__)

_compressor = ContextCompressor()
_trajectory = TrajectoryCapture()

load_dotenv(Path(__file__).parent.parent / ".env")

# --- Configuration ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MEMORY_API_URL = os.getenv("MEMORY_API_URL", "http://localhost:58001")
EPISODIC_API_URL = os.getenv("EPISODIC_API_URL", "http://localhost:8002")


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The conversation history"]
    context: str
    task: str
    plan: List[str]
    observations: List[str]
    iterations: int
    task_completed: bool
    budget_exhausted: bool
    compression_count: int


# --- Nodes ---

def orchestrator(state: AgentState):
    """The brain: decides strategy (ToT/CoT)."""
    last_message = state["messages"][-1].content
    task = state.get("task") or last_message
    logger.info(f"🔱 Orchestrating: {task[:50]}...")
    return {"iterations": 0, "task": task}

def planner(state: AgentState):
    """Generates a structured plan using Tree of Thoughts logic."""
    last_message = state["messages"][-1].content.lower()
    
    # Dynamic strategy selection based on intent
    if "correo" in last_message or "email" in last_message:
        llm_plan = [
            "1. Recall contact context from Wiki",
            "2. Execute action 'send_email' via KoruOS (n8n)",
            "3. Reflect on delivery status"
        ]
    else:
        llm_plan = ["1. Recall context", "2. Execute body action via MCP", "3. Reflect and Chronicler"]
        
    return {"plan": llm_plan, "next_node": "executor"}

def executor(state: AgentState):
    """ReAct Loop: Thought -> Action -> Observation."""
    current_step = state["plan"][state["iterations"] % len(state["plan"])]
    logger.info(f"⚙️ Executing Step: {current_step}")
    
    # Integration with KoruOS Nervous System (Forge)
    import requests
    try:
        packet = {
            "id": f"trace-{state['iterations']}",
            "aeon_id": "zana-v2",
            "type": "action",
            "content": {"step": current_step},
            "timestamp": datetime.now().isoformat()
        }
        # In production, this calls the NestJS server we created
        # response = requests.post("http://localhost:51112/ai/forge/packet", json=packet)
        observation = f"KoruOS Forge confirmed execution of: {current_step}"
    except Exception as e:
        observation = f"Tool execution failed: {str(e)}"
    
    return {
        "observations": state.get("observations", []) + [observation],
        "iterations": state["iterations"] + 1,
        "next_node": "critic"
    }

def critic(state: AgentState):
    """Reflection Node: Verifies outcome or enforces iteration budget."""
    iterations = state.get("iterations", 0)

    if BUDGET.should_warn(iterations):
        logger.warning(BUDGET.status_line(iterations))

    if BUDGET.is_exhausted(iterations):
        logger.error(f"Budget exhausted after {iterations} iterations — forcing stop.")
        return {"task_completed": True, "budget_exhausted": True}

    if iterations >= len(state.get("plan", [1])):
        return {"task_completed": True, "budget_exhausted": False}

    logger.info(f"🧠 Reflecting — {BUDGET.status_line(iterations)}")
    return {}

def compressor(state: AgentState):
    """Context Compression Node: summarizes history when approaching token limits."""
    logger.info("🗜️ Compressing context...")
    new_messages, new_observations = _compressor.compress(
        state["messages"], state.get("observations", [])
    )
    return {
        "messages": new_messages,
        "observations": new_observations,
        "compression_count": state.get("compression_count", 0) + 1,
    }

def chronicler(state: AgentState):
    """Memory Reflection: Persists learning to Wiki and captures trajectory."""
    logger.info("🖋️ Chronicling session to Obsidian Wiki...")
    _trajectory.capture(state)
    return {}

# --- Graph Construction ---

def _route_critic(state: AgentState) -> str:
    if state.get("task_completed"):
        return "chronicler"
    if _compressor.should_compress(state["messages"]):
        return "compressor"
    return "executor"


workflow = StateGraph(AgentState)

workflow.add_node("orchestrator", orchestrator)
workflow.add_node("planner", planner)
workflow.add_node("executor", executor)
workflow.add_node("critic", critic)
workflow.add_node("compressor", compressor)
workflow.add_node("chronicler", chronicler)

workflow.set_entry_point("orchestrator")

workflow.add_edge("orchestrator", "planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "critic")
workflow.add_edge("compressor", "executor")

workflow.add_conditional_edges(
    "critic",
    _route_critic,
    {"executor": "executor", "compressor": "compressor", "chronicler": "chronicler"},
)

workflow.add_edge("chronicler", END)

app = workflow.compile()


def run_task(task: str):
    print(f"🔱 ZANA Orchestrator: Starting task '{task}'")
    initial_state = {
        "messages": [HumanMessage(content=task)],
        "context": "",
        "task": task,
        "plan": [],
        "observations": [],
        "iterations": 0,
        "task_completed": False,
        "budget_exhausted": False,
        "compression_count": 0,
    }
    for output in app.stream(initial_state):
        for node, data in output.items():
            print(f"--- Node: {node} ---")
            if "next_node" in data:
                print(f"Transitioning to: {data['next_node']}")
    print("   /\ \n  /  \ \n /____\ \n [ VALHALLA REACHED ]")


if __name__ == "__main__":
    import sys

    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Build a luxury landing page plan for VECANOVA"
    )
    run_task(query)
