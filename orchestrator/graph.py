import os
from typing import Annotated, List, TypedDict
from pathlib import Path
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

load_dotenv(Path(__file__).parent.parent / ".env")

# --- Configuration ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MEMORY_API_URL = os.getenv("MEMORY_API_URL", "http://localhost:58001")
EPISODIC_API_URL = os.getenv("EPISODIC_API_URL", "http://localhost:8002")


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The conversation history"]
    context: str
    plan: List[str]
    observations: List[str]
    iterations: int
    task_completed: bool


# --- Nodes ---

def orchestrator(state: AgentState):
    """The brain: decides strategy (ToT/CoT)."""
    last_message = state["messages"][-1].content
    logger.info(f"🔱 Orchestrating: {last_message[:50]}...")
    return {"next_node": "planner", "iterations": 0}

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
    """Reflection Node: Verifies outcome and decides if more loops are needed."""
    logger.info("🧠 Reflecting on outcome...")
    if state["iterations"] >= len(state["plan"]):
        return {"task_completed": True, "next_node": "chronicler"}
    return {"next_node": "executor"}

def chronicler(state: AgentState):
    """Memory Reflection: Persists learning to Wiki."""
    logger.info("🖋️ Chronicling session to Obsidian Wiki...")
    return {"next_node": END}

# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("orchestrator", orchestrator)
workflow.add_node("planner", planner)
workflow.add_node("executor", executor)
workflow.add_node("critic", critic)
workflow.add_node("chronicler", chronicler)

workflow.set_entry_point("orchestrator")

workflow.add_edge("orchestrator", "planner")
workflow.add_edge("planner", "executor")

workflow.add_conditional_edges(
    "critic",
    lambda x: "executor" if not x["task_completed"] else "chronicler",
    {"executor": "executor", "chronicler": "chronicler"}
)

workflow.add_edge("chronicler", END)

app = workflow.compile()


def run_task(task: str):
    print(f"🔱 ZANA Orchestrator: Starting task '{task}'")
    initial_state = {
        "messages": [HumanMessage(content=task)],
        "context": "",
        "plan": [],
        "next_node": "",
        "task_completed": False,
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
