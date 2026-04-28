import pytest
import psycopg
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from init_db import CONN_STR, init_db

def test_episodic_memory_table_exists(monkeypatch):
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = [True]
    monkeypatch.setattr(psycopg, "connect", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=mock_conn))))
    
    init_db()
    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.episodic_memory');")
            assert cur.fetchone()[0] is not None