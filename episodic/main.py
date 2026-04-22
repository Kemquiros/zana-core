import os
import sys
import uuid
import psycopg
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

sys.path.append(os.path.abspath(".."))
from kalman import CognitiveKalmanFilter

load_dotenv(Path(__file__).parent.parent / ".env")

DB_NAME = os.getenv("POSTGRES_DB", "zana")
DB_USER = os.getenv("POSTGRES_USER", "zana")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "zana_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "55433")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

CONN_STR = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

app = FastAPI(title="ZANA Episodic Memory API (CRISOL-APEX)")

# Lazy load model
_model = None

# Global dictionary for Session Kalman Filters
# In production, this should be stored in Redis or similar
_kalman_filters: Dict[str, CognitiveKalmanFilter] = {}
SURPRISE_THRESHOLD = 1.5  # Tunable parameter for Bayesian Surprise


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL, device="cpu")
    return _model


def get_kalman_filter(session_id: str) -> CognitiveKalmanFilter:
    if session_id not in _kalman_filters:
        # MiniLM-L6-v2 output dimension is 384
        _kalman_filters[session_id] = CognitiveKalmanFilter(dim=384)
    return _kalman_filters[session_id]


class EpisodeBase(BaseModel):
    session_id: str
    event_type: str
    subject: str
    context: Optional[dict] = None
    outcome: Optional[str] = None
    outcome_type: Optional[str] = None
    tags: Optional[List[str]] = None
    project: Optional[str] = None


class EpisodeCreate(EpisodeBase):
    pass


class Episode(EpisodeBase):
    id: uuid.UUID
    timestamp: datetime
    surprise: Optional[float] = None
    discarded: bool = False


@app.post("/episodes", response_model=Episode)
async def create_episode(episode: EpisodeCreate):
    model = get_model()

    # Create embedding from subject + outcome
    text_to_embed = f"{episode.subject}\n\n{episode.outcome or ''}"
    if episode.context and "full_text" in episode.context:
        text_to_embed += f"\n{episode.context['full_text']}"

    embedding = model.encode(text_to_embed)

    # 🧠 THE CORTEX: Bayesian Surprise Calculation
    kf = get_kalman_filter(episode.session_id)
    surprise = kf.update(embedding)

    # Check if the information is surprising enough to remember
    # Always remember 'FOCUS' events to build a timeline, but filter 'CLIPBOARD' or others
    is_surprise = surprise > SURPRISE_THRESHOLD

    if not is_surprise and episode.event_type != "FOCUS":
        # Discard noise
        return Episode(
            id=uuid.uuid4(),  # Dummy UUID
            timestamp=datetime.now(),
            surprise=surprise,
            discarded=True,
            **episode.model_dump(),
        )

    # Persist the surprising event
    embedding_list = embedding.tolist()
    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO episodes (session_id, event_type, subject, context, outcome, outcome_type, tags, project, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, timestamp;
            """,
                (
                    episode.session_id,
                    episode.event_type,
                    episode.subject,
                    psycopg.types.json.Jsonb(episode.context),
                    episode.outcome,
                    episode.outcome_type,
                    episode.tags,
                    episode.project,
                    embedding_list,
                ),
            )
            res = cur.fetchone()
            if not res:
                raise HTTPException(status_code=500, detail="Failed to insert episode")

            return Episode(
                id=res[0],
                timestamp=res[1],
                surprise=surprise,
                discarded=False,
                **episode.model_dump(),
            )


@app.get("/episodes/similar", response_model=List[Episode])
async def search_episodes(query: str, limit: int = 5, project: Optional[str] = None):
    model = get_model()
    embedding = model.encode(query).tolist()

    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            vector_str = "[" + ",".join(map(str, embedding)) + "]"

            sql = """
                SELECT id, session_id, timestamp, event_type, subject, context, outcome, outcome_type, tags, project
                FROM episodes
                WHERE 1=1
            """
            params = []
            if project:
                sql += " AND project = %s"
                params.append(project)

            sql += " ORDER BY embedding <=> %s::vector LIMIT %s;"
            params.extend([vector_str, limit])

            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append(
                    Episode(
                        id=row[0],
                        session_id=row[1],
                        timestamp=row[2],
                        event_type=row[3],
                        subject=row[4],
                        context=row[5],
                        outcome=row[6],
                        outcome_type=row[7],
                        tags=row[8],
                        project=row[9],
                        surprise=None,
                        discarded=False,
                    )
                )
            return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=58002)
