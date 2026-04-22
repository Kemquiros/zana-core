import os
import httpx
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ZANA-KoruOS Symbiosis Protocol (MCP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In a real environment, this URL points to the World Model or Episodic Memory
EPISODIC_API_URL = os.getenv("EPISODIC_API_URL", "http://localhost:8002")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("🔗 [MCP SOCKET] KoruOS Client (Aeon) connected.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("🔗 [MCP SOCKET] KoruOS Client (Aeon) disconnected.")

    async def broadcast_event(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

# ==========================================
# 1. PULL FLOW (Immortal Memory)
# KoruOS (the Aeon) requests context from ZANA before responding to the user.
# ==========================================


class ContextRequest(BaseModel):
    query: str
    session_id: str
    limit: int = 5


@app.post("/mcp/context")
async def get_context(request: ContextRequest):
    """
    PULL route: KoruOS calls here when the user asks a verbal question.
    ZANA queries episodic/semantic memory and returns the enriched context.
    """
    print(f"🧠 [MCP PULL] KoruOS requested context for: '{request.query}'")

    # In production, query ChromaDB and Neo4j.
    # Simulate a call to the Episodic Memory API (port 8002).
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(
                f"{EPISODIC_API_URL}/episodes/similar",
                params={"query": request.query, "limit": request.limit},
                timeout=5.0,
            )
            if res.status_code == 200:
                episodes = res.json()
                context_str = "\n".join(
                    [
                        f"- {ep.get('subject', '')}: {ep.get('outcome', '')}"
                        for ep in episodes
                    ]
                )
                return {
                    "status": "success",
                    "context": context_str,
                    "source": "episodic_memory",
                }
        except Exception as e:
            print(f"⚠️ Error connecting to Cortex (8002): {e}")

    # Fallback / Mock
    return {
        "status": "partial",
        "context": "The user has been working on the ZANA project for the last 2 hours. Current cognitive state: flow.",
        "source": "local_mock",
    }


# ==========================================
# 2. PUSH FLOW (Asymmetric Empathy)
# ZANA proactively interrupts KoruOS using WebSockets.
# ==========================================


class PushEvent(BaseModel):
    intent: str
    emotion: str
    message: str
    data: Optional[Dict[str, Any]] = None


@app.post("/mcp/intervene")
async def trigger_intervention(event: PushEvent):
    """
    PUSH IN route: The Shadow Observer (Rust) or Kalman Filter (Python) call
    this route when a critical event is detected (frustration, repeated error).
    """
    print(f"⚡ [MCP PUSH TRIGGER] ZANA detected: {event.intent} ({event.emotion})")

    payload = {
        "type": "intervention",
        "intent": event.intent,
        "emotion": event.emotion,
        "message": event.message,
        "data": event.data or {},
    }

    # ZANA pushes the event to all connected KoruOS clients via WebSocket
    await manager.broadcast_event(payload)
    return {"status": "success", "pushed_to_aeons": len(manager.active_connections)}


@app.websocket("/ws/mcp")
async def mcp_websocket(websocket: WebSocket):
    """
    PUSH OUT route: KoruOS (Frontend) keeps this socket open 24/7.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive waiting for pings (heartbeats) from KoruOS
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    # Run the Symbiosis server on port 4444 (as defined by the protocol)
    uvicorn.run(app, host="0.0.0.0", port=4444)
