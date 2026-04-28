# Ars Magna 2.0 (Refinamiento Recursivo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Ars Magna 2.0 reasoning cycle (Actor-Critic-Defender) with recursive refinement, triggered by high Kalman surprise or user demand.

**Architecture:** We will enhance the `ApexOrchestrator` to support a non-linear reasoning path. When the "Ars Magna" trigger is active, the orchestrator will enter a loop: (1) Actor proposes a response, (2) Critic evaluates against sovereign principles and provides a "Resonance Score", (3) If score < 0.8, the loop repeats with the criticism as context (max 3 iterations). (4) Defender performs the final audit.

**Tech Stack:** Python 3.12, Pydantic, litellm, asyncio.

---

### Task 1: Define Ars Magna Schemas & Logic

**Files:**
- Create: `swarm/apex/ars_magna.py`
- Modify: `swarm/apex/orchestrator.py`

- [ ] **Step 1: Create Pydantic models for the Critic's feedback**
Define how the Critic should communicate its evaluation.

```python
from pydantic import BaseModel, Field
from typing import List

class CriticFeedback(BaseModel):
    resonance_score: float = Field(..., description="0.0 to 1.0 score of how well the response aligns with sovereign principles.")
    critique: str = Field(..., description="Detailed feedback on what is missing or wrong.")
    suggestions: List[str] = Field(default_factory=list, description="Specific actions to improve the response.")
    is_sufficient: bool = Field(..., description="True if resonance_score >= 0.8")
```

- [ ] **Step 2: Implement the recursive loop core**
Create a function in `ars_magna.py` that manages the Actor-Critic interaction.

```python
async def run_ars_magna_cycle(user_prompt: str, context: str, initial_response: str, max_rounds: int = 3):
    # Logic to call Critic -> if fail -> call Actor with critique -> repeat
    pass
```

- [ ] **Step 3: Commit**
```bash
git add swarm/apex/ars_magna.py
git commit -m "feat(apex): define schemas and shell for Ars Magna 2.0 cycle"
```

### Task 2: Implement the Critic Agent

**Files:**
- Modify: `swarm/apex/agents.py`
- Create: `swarm/apex/prompts_ars_magna.py`

- [ ] **Step 1: Define CRITIC_PROMPT**
The prompt should instruct the model to act as a rigorous evaluator of sovereignty, checking for bias, dependency on external cloud concepts, and alignment with the user's specific "Resonance Profile".

- [ ] **Step 2: Add CRITIC agent to `agents.py`**
Initialize the agent using `litellm` or the existing agent wrapper.

- [ ] **Step 3: Commit**
```bash
git add swarm/apex/agents.py swarm/apex/prompts_ars_magna.py
git commit -m "feat(apex): implement Critic agent and prompts"
```

### Task 3: Integrate with ApexOrchestrator & Kalman Trigger

**Files:**
- Modify: `swarm/apex/orchestrator.py`
- Modify: `sensory/multimodal_gateway.py`

- [ ] **Step 1: Update `process_request` to detect triggers**
Check for `kalman_surprise > 0.7` or manual keywords in the prompt.

- [ ] **Step 2: Invoke Ars Magna cycle**
If triggered, replace the standard `HERALD` synthesis with the recursive loop.

- [ ] **Step 3: Update Gateway to pass Kalman Surprise to Orchestrator**
Ensure the `kalman_surprise` calculated in the WebSocket reaches the Apex engine.

- [ ] **Step 4: Commit**
```bash
git add swarm/apex/orchestrator.py sensory/multimodal_gateway.py
git commit -m "feat(apex): integrate Ars Magna cycle with Kalman triggers"
```

### Task 4: UI Feedback for Deliberation

**Files:**
- Modify: `aria-ui/components/ChatInterface.tsx`
- Modify: `aria-ui/lib/zana-stream.ts`

- [ ] **Step 1: Add "Deliberating" state to the UI**
Show a special animation (perhaps the particles moving in a more intense pattern) when Ars Magna is active.

- [ ] **Step 2: Send "thought" events through WebSocket**
The Gateway should stream the Critic's feedback (hidden or partially visible) to let the user know ZANA is performing a "Deep Think".

- [ ] **Step 3: Commit**
```bash
git add aria-ui/ components/
git commit -m "feat(ui): visualize Ars Magna deliberation state"
```
