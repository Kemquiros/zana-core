import os
import sys
import httpx
import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Add project root to sys.path to find episodic modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from episodic.kalman import CognitiveKalmanFilter

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

EPISODIC_API_URL = os.getenv("EPISODIC_API_URL", "http://localhost:8002")

mcp = FastMCP("zana-episodic")

# In-memory Kalman Filter for the current session
_kalman_filter = None

def get_kalman():
    global _kalman_filter
    if _kalman_filter is None:
        _kalman_filter = CognitiveKalmanFilter(dim=384) # Standard embedding dim
    return _kalman_filter

@mcp.tool()
def calculate_session_surprise(embedding_values: List[float]) -> str:
    """
    Calculate the Bayesian Surprise for a given state embedding.
    Uses an Adaptive Kalman Filter to manage intra-episodic memory.
    
    Args:
        embedding_values: The embedding vector of the current context.
    """
    try:
        obs = np.array(embedding_values)
        kf = get_kalman()
        surprise = kf.update(obs)
        uncertainty = kf.get_uncertainty_score()
        
        status = "ESTABLE"
        if surprise > 2.0:
            status = "SORPRESA (Posible cambio de contexto)"
            
        return json.dumps({
            "surprise": surprise,
            "uncertainty": uncertainty,
            "status": status
        })
    except Exception as e:
        return f"❌ Error calculating surprise: {str(e)}"

@mcp.tool()
async def store_episode(
    subject: str, 
    outcome: str, 
    event_type: str = "task", 
    outcome_type: str = "success",
    project: Optional[str] = None,
    context: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    session_id: str = "default"
) -> str:
    """
    Store a new episode (event/task/decision) in ZANA's episodic memory.
    
    Args:
        subject: Description of the task or event.
        outcome: The result or what happened.
        event_type: Type of event (task, insight, error, decision, conversation).
        outcome_type: Outcome status (success, failure, partial, pending).
        project: Project name (e.g., 'VECANOVA', 'ZANA').
        context: Optional dictionary with state/context.
        tags: List of tags.
        session_id: Current session identifier.
    """
    payload = {
        "session_id": session_id,
        "event_type": event_type,
        "subject": subject,
        "context": context or {},
        "outcome": outcome,
        "outcome_type": outcome_type,
        "tags": tags or [],
        "project": project
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{EPISODIC_API_URL}/episodes", json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return f"✅ Episode stored with ID: {data['id']}"
        except Exception as e:
            return f"❌ Error storing episode: {str(e)}"

@mcp.tool()
async def recall_similar(query: str, project: Optional[str] = None, limit: int = 3) -> str:
    """
    Recall similar past episodes from memory using semantic search.
    
    Args:
        query: Search query (e.g., 'how did we fix the docker port issue?').
        project: Filter by project.
        limit: Max number of episodes to return.
    """
    params = {"query": query, "limit": limit}
    if project:
        params["project"] = project
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{EPISODIC_API_URL}/episodes/similar", params=params, timeout=10.0)
            response.raise_for_status()
            episodes = response.json()
            
            if not episodes:
                return "No similar episodes found."
                
            formatted = []
            for ep in episodes:
                ts = ep['timestamp'][:16].replace('T', ' ')
                entry = (
                    f"--- Episode [{ep['outcome_type'].upper()}] ({ts}) ---\n"
                    f"Subject: {ep['subject']}\n"
                    f"Outcome: {ep['outcome']}\n"
                    f"Project: {ep['project'] or 'N/A'}\n"
                )
                formatted.append(entry)
            return "\n".join(formatted)
        except Exception as e:
            return f"❌ Error recalling episodes: {str(e)}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
