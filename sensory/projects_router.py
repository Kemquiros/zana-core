import os
import asyncpg # type: ignore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import sys
from pathlib import Path
try:
    # Add root to pythonpath for rust module
    sys.path.append(str(Path(__file__).parent.parent))
    import zana_steel_core
except ImportError:
    zana_steel_core = None

router = APIRouter(prefix="/projects", tags=["projects"])

DB_NAME = os.getenv("POSTGRES_DB", "zana")
DB_USER = os.getenv("POSTGRES_USER", "zana")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "zana_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "55433") # Default local proxy port

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

@router.post("")
async def create_project(project: ProjectCreate):
    if zana_steel_core:
        processor = zana_steel_core.PyProjectProcessor("default")
        try:
            # High performance validation
            project_hash = processor.validate_and_hash(project.name, 0)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    elif not project.name.strip():
        raise HTTPException(status_code=422, detail="Project name cannot be empty")
        
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        row = await conn.fetchrow(
            "INSERT INTO projects (name, description) VALUES ($1, $2) RETURNING id, name",
            project.name, project.description
        )
        await conn.close()
        return {"status": "success", "project_id": str(row["id"]), "name": row["name"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def list_projects():
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        rows = await conn.fetch("SELECT id, name, description FROM projects")
        await conn.close()
        return {"projects": [{"id": str(r["id"]), "name": r["name"], "description": r["description"]} for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))