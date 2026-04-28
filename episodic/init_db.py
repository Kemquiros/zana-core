import os
import psycopg
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_NAME = os.getenv("POSTGRES_DB", "zana")
DB_USER = os.getenv("POSTGRES_USER", "zana")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "zana_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")

CONN_STR = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def init_db():
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            # Enable pgvector
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Create episodes table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id   TEXT NOT NULL,
                timestamp    TIMESTAMPTZ NOT NULL DEFAULT now(),
                event_type   TEXT NOT NULL,   -- 'task', 'insight', 'error', 'decision', 'conversation'
                subject      TEXT NOT NULL,   -- one line description
                context      JSONB,           -- state relevant at the moment
                outcome      TEXT,            -- what happened
                outcome_type TEXT,            -- 'success', 'failure', 'partial', 'pending'
                embedding    vector(384),     -- for similarity search (all-MiniLM-L6-v2)
                tags         TEXT[],
                project      TEXT             -- 'VECANOVA', 'ZANA', etc.
            );
            """)

            cur.execute(
                "CREATE INDEX IF NOT EXISTS episodes_embedding_idx ON episodes USING hnsw (embedding vector_cosine_ops);"
            )

            # Create episodic_memory table for memory_router
            cur.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id      TEXT NOT NULL,
                project_id      TEXT,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                modality        TEXT DEFAULT 'text',
                emotion         TEXT,
                kalman_surprise FLOAT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """)

            # Create projects table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name         TEXT NOT NULL UNIQUE,
                description  TEXT,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """)

            # Create project_tasks table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS project_tasks (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title        TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'todo',
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """)

            # Create project_files table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS project_files (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                file_path    TEXT NOT NULL,
                file_hash    TEXT NOT NULL,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """)

            conn.commit()
            print("✅ Database initialized successfully.")


if __name__ == "__main__":
    init_db()
