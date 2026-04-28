import pytest
import psycopg
import os
import sys
from pathlib import Path

# Add parent to path to import init_db
sys.path.append(str(Path(__file__).parent.parent))

from init_db import CONN_STR, init_db

def test_projects_tables_exist():
    init_db()
    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.projects');")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.project_tasks');")
            assert cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('public.project_files');")
            assert cur.fetchone()[0] is not None