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
    next_node: str
    task_completed: bool


# --- Nodes ---


def orchestrator(state: AgentState):
    """The brain: scans input and decides initial path."""
    last_message = state["messages"][-1].content
    # Simple logic to decide if we need memory retrieval
    if "recuerda" in last_message.lower() or "busca" in last_message.lower():
        return {"next_node": "recall"}
    return {"next_node": "planner"}


def recall(state: AgentState):
    """Retrieves semantic and episodic memory."""
    state["messages"][-1].content
    # In a real scenario, this would call semantic_search and recall_similar APIs
    # For now, we mock the retrieval for the demo
    retrieved_context = (
        "[MOCK MEMORY]: VECANOVA focuses on AI agents and 'Empire of One'."
    )
    return {"context": retrieved_context, "next_node": "planner"}


def planner(state: AgentState):
    """Generates a multi-step plan (ToT)."""
    if not ANTHROPIC_API_KEY:
        print("[WARN]: ANTHROPIC_API_KEY not found. Using MOCK PLAN.")
        return {
            "plan": [
                "1. Research target audience",
                "2. Design glassmorphism hero",
                "3. Implement async capture",
            ],
            "next_node": "executor",
        }

    # Use LLM to generate plan
    llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=ANTHROPIC_API_KEY)
    prompt = f"Context: {state.get('context', '')}\nTask: {state['messages'][-1].content}\nGenerate a 3-step execution plan."
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"plan": [response.content], "next_node": "executor"}


def executor(state: AgentState):
    """Executes the plan using tools (ReAct)."""
    # In Phase 3, this node would iterate through the plan calling tools
    return {
        "messages": state["messages"]
        + [AIMessage(content="[EXECUTOR]: Task executed according to plan.")],
        "next_node": "critic",
    }


def critic(state: AgentState):
    """Reflects on the outcome."""
    return {"task_completed": True, "next_node": END}


# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("orchestrator", orchestrator)
workflow.add_node("recall", recall)
workflow.add_node("planner", planner)
workflow.add_node("executor", executor)
workflow.add_node("critic", critic)

workflow.set_entry_point("orchestrator")

workflow.add_conditional_edges(
    "orchestrator", lambda x: x["next_node"], {"recall": "recall", "planner": "planner"}
)

workflow.add_edge("recall", "planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "critic")
workflow.add_edge("critic", END)

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
