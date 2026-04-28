# Gateway Asynchronous Resilience & Testing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the FastAPI Gateway to handle LLM streaming and TTS synthesis asynchronously without blocking the main event loop, and introduce comprehensive integration/stress testing.

**Architecture:** We will decouple the `multimodal_gateway.py` monolithic file by introducing proper FastAPI background tasks and asyncio concurrency for LLM generation and Text-to-Speech in the WebSocket endpoints. We will also implement a rigorous test suite using `pytest` and `httpx` to simulate concurrent connections and ensure the WebSocket doesn't drop connections under heavy load.

**Tech Stack:** Python 3.12, FastAPI, WebSockets, asyncio, pytest, httpx.

---

### Task 1: Create Gateway Test Suite Foundation

**Files:**
- Create: `tests/test_multimodal_gateway.py`
- Modify: `pyproject.toml` (if needed to add test deps)

- [ ] **Step 1: Write the failing test**
Create a test file that attempts to connect to the `/sense/stream` websocket and send a simple message.

```python
import pytest
from fastapi.testclient import TestClient
from sensory.multimodal_gateway import app

client = TestClient(app)

def test_websocket_stream_basic():
    with client.websocket_connect("/sense/stream") as websocket:
        websocket.send_json({"type": "text", "data": "Hello Aeon", "session_id": "test_1"})
        
        # We expect a chunk response
        response = websocket.receive_json()
        assert response["type"] in ["chunk", "end", "error"]
```

- [ ] **Step 2: Run test to verify it works (or fails if dependencies are missing)**
Run: `uv run pytest tests/test_multimodal_gateway.py -v`
Note: It might pass if the current blocking implementation works for 1 connection, but it sets up our harness.

- [ ] **Step 3: Commit**
```bash
git add tests/test_multimodal_gateway.py
git commit -m "test(gateway): add basic websocket test harness"
```

### Task 2: Implement Asyncio TaskGroup for Non-Blocking WebSockets

**Files:**
- Modify: `sensory/multimodal_gateway.py`

- [ ] **Step 1: Write the stress test**
Add a stress test in `test_multimodal_gateway.py` to ensure the server can handle multiple rapid messages without closing the connection.

```python
def test_websocket_stream_stress():
    with client.websocket_connect("/sense/stream") as websocket:
        # Send 10 messages rapidly
        for i in range(10):
            websocket.send_json({"type": "text", "data": f"Stress {i}", "session_id": f"stress_{i}"})
        
        responses = []
        for _ in range(10):
            responses.append(websocket.receive_json())
            
        assert len(responses) > 0
```

- [ ] **Step 2: Run test**
Run: `uv run pytest tests/test_multimodal_gateway.py::test_websocket_stream_stress -v`

- [ ] **Step 3: Refactor WebSocket endpoint to use `asyncio.create_task` or `to_thread`**
Modify `sense_stream` in `multimodal_gateway.py`. The LLM generator is a synchronous generator (`yield`). We need to ensure it doesn't block. FastAPI WebSockets run in the async event loop. Since `get_local_llm().generate_stream` does network I/O synchronously (via litellm without async), it blocks the whole server.

```python
import asyncio

# Inside sense_stream websocket endpoint:
            if msg_type == "text":
                # ... armor check ...
                
                async def _process_llm():
                    llm = get_local_llm()
                    # Run the synchronous generator in a thread pool
                    def _get_chunks():
                        return list(llm.generate_stream(data, context=ctx, session_id=session_id or ""))
                        
                    chunks = await asyncio.to_thread(_get_chunks)
                    for chunk in chunks:
                        await ws.send_json({"type": "chunk", "content": chunk})
                    await ws.send_json({"type": "end"})
                
                # Fire and forget (or await it depending on how we want to block the user)
                # To stream properly without blocking the receive loop, we create a task:
                asyncio.create_task(_process_llm())
```
*Correction*: If we use `to_thread` on the generator list, we lose the streaming effect (it buffers everything). A better approach is to make the litellm call async using `acompletion`.

- [ ] **Step 4: Update `local_llm.py` to support `generate_stream_async`**
Modify `sensory/local_llm.py`:

```python
    async def generate_stream_async(self, user_input: str, context: str = "", session_id: str = ""):
        messages = [{"role": "system", "content": _ZANA_SYSTEM}]
        if context:
            messages.append({"role": "system", "content": f"[MEMORY CONTEXT]\n{context}"})
        messages.append({"role": "user", "content": user_input})

        try:
            response = await litellm.acompletion(
                model=self.primary_model,
                messages=messages,
                temperature=0.7,
                max_tokens=512,
                stream=True
            )
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"❌ [LLM STREAM] Error: {e}")
            yield f"[Inference Stream Error] {e}"
```

- [ ] **Step 5: Apply async generator in `multimodal_gateway.py`**
```python
                # In sense_stream:
                llm = get_local_llm()
                async for chunk in llm.generate_stream_async(data, context=ctx, session_id=session_id or ""):
                    await ws.send_json({"type": "chunk", "content": chunk})
                await ws.send_json({"type": "end"})
```

- [ ] **Step 6: Run tests**
Run: `uv run pytest tests/test_multimodal_gateway.py -v`
Expected: PASS and no event loop blockage.

- [ ] **Step 7: Commit**
```bash
git add sensory/multimodal_gateway.py sensory/local_llm.py tests/test_multimodal_gateway.py
git commit -m "refactor(gateway): implement async litellm streaming to prevent event loop blocking"
```
