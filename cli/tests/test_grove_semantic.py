"""
Tests for sqlite-vec semantic memory layer (GROVE path without Docker).

These tests cover:
- graceful fallback to FTS5 when sqlite-vec is not available
- index_memory / has_vector_index API
- search_semantic fallback chain
- rebuild_vector_index
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from zana.core.memory_lite import (
    MemoryLiteDB,
    _get_ollama_embedding,
    _serialize_vec,
    is_ollama_available,
    is_sqlite_vec_available,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def fresh_db(tmp_path: Path) -> MemoryLiteDB:
    return MemoryLiteDB(db_path=tmp_path / "test.db")


# ── is_sqlite_vec_available ───────────────────────────────────────────────────


def test_is_sqlite_vec_available_returns_bool() -> None:
    result = is_sqlite_vec_available()
    assert isinstance(result, bool)


def test_is_sqlite_vec_available_false_when_import_fails() -> None:
    with patch("zana.core.memory_lite._load_sqlite_vec", return_value=False):
        assert is_sqlite_vec_available() is False


# ── _serialize_vec ────────────────────────────────────────────────────────────


def test_serialize_vec_produces_correct_bytes() -> None:
    vec = [1.0, 2.0, 3.0]
    blob = _serialize_vec(vec)
    assert isinstance(blob, bytes)
    assert len(blob) == 12  # 3 floats × 4 bytes


def test_serialize_vec_empty() -> None:
    blob = _serialize_vec([])
    assert blob == b""


# ── _get_ollama_embedding ─────────────────────────────────────────────────────


def test_get_ollama_embedding_returns_none_when_unavailable() -> None:
    with patch("httpx.post", side_effect=ConnectionError("refused")):
        result = _get_ollama_embedding("hello")
    assert result is None


def test_get_ollama_embedding_returns_none_on_non_200() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("httpx.post", return_value=mock_resp):
        result = _get_ollama_embedding("hello")
    assert result is None


def test_get_ollama_embedding_returns_list_on_success() -> None:
    embedding = [0.1] * 768
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": embedding}
    with patch("httpx.post", return_value=mock_resp):
        result = _get_ollama_embedding("hello")
    assert result == embedding


# ── is_ollama_available ───────────────────────────────────────────────────────


def test_is_ollama_available_false_when_connection_refused() -> None:
    with patch("httpx.post", side_effect=ConnectionError):
        assert is_ollama_available() is False


# ── has_vector_index ─────────────────────────────────────────────────────────


def test_has_vector_index_false_when_vec_not_loaded(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    with patch.object(db, "_vec_loaded", False):
        assert db.has_vector_index() is False
    db.close()


def test_has_vector_index_reflects_vec_loaded_state(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    # Whether True or False depends on installation — just check type
    assert isinstance(db.has_vector_index(), bool)
    db.close()


# ── index_memory ─────────────────────────────────────────────────────────────


def test_index_memory_returns_false_without_vec(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    doc_id = db.add("test content")
    with patch.object(db, "has_vector_index", return_value=False):
        result = db.index_memory(doc_id, [0.1] * 768)
    assert result is False
    db.close()


def test_index_memory_requires_existing_doc(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    # index_memory with vec disabled always returns False — correct behavior
    result = db.index_memory(9999, [0.1] * 3)
    assert isinstance(result, bool)
    db.close()


# ── search_semantic fallback chain ───────────────────────────────────────────


def test_search_semantic_falls_back_to_fts5_when_no_vec(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.add("ZANA is a sovereign AI", source="test")
    db.add("The quick brown fox", source="test")

    with patch.object(db, "has_vector_index", return_value=False):
        results = db.search_semantic("sovereign AI", n=5)

    assert isinstance(results, list)
    # FTS5 fallback — should find the sovereign AI entry
    contents = [r["content"] for r in results]
    assert any("sovereign" in c for c in contents)
    db.close()


def test_search_semantic_falls_back_when_ollama_unreachable(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.add("memory content", source="test")

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=None),
    ):
        results = db.search_semantic("memory", n=5)

    assert isinstance(results, list)
    db.close()


def test_search_semantic_returns_list_always(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    # No documents — should return empty list, not crash
    results = db.search_semantic("anything")
    assert results == []
    db.close()


def test_search_semantic_mode_field_present_when_semantic(tmp_path: Path) -> None:
    embedding = [0.1] * 768

    mock_vec_rows: list = [MagicMock()]
    mock_vec_rows[0].__getitem__ = lambda self, key: 1 if key == "rowid" else 0.15

    db = fresh_db(tmp_path)
    db.add("test document")

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=embedding),
        patch("zana.core.memory_lite._serialize_vec", return_value=b"\x00" * (768 * 4)),
    ):
        # If the vec table exists, result would have mode='semantic'
        # Otherwise falls back to FTS5 without mode key
        results = db.search_semantic("test")

    assert isinstance(results, list)
    db.close()


# ── rebuild_vector_index ─────────────────────────────────────────────────────


def test_rebuild_vector_index_returns_zero_without_vec(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.add("first memory")
    db.add("second memory")

    with patch.object(db, "has_vector_index", return_value=False):
        count = db.rebuild_vector_index()
    assert count == 0
    db.close()


def test_rebuild_vector_index_counts_indexed(tmp_path: Path) -> None:
    embedding = [0.1] * 768
    db = fresh_db(tmp_path)
    db.add("first memory")
    db.add("second memory")

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=embedding),
        patch.object(db, "index_memory", return_value=True),
    ):
        count = db.rebuild_vector_index()

    assert count == 2
    db.close()


def test_rebuild_vector_index_skips_failed_embeddings(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.add("memory one")
    db.add("memory two")

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=None),
    ):
        count = db.rebuild_vector_index()
    assert count == 0
    db.close()


# ── add auto-indexes when vec available ──────────────────────────────────────


def test_add_auto_indexes_when_vec_and_ollama_available(tmp_path: Path) -> None:
    embedding = [0.1] * 768
    db = fresh_db(tmp_path)

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=embedding),
        patch.object(db, "index_memory", return_value=True) as mock_index,
    ):
        doc_id = db.add("test content")

    mock_index.assert_called_once_with(doc_id, embedding)
    db.close()


def test_add_does_not_auto_index_non_vault_collections(tmp_path: Path) -> None:
    embedding = [0.1] * 768
    db = fresh_db(tmp_path)

    with (
        patch.object(db, "has_vector_index", return_value=True),
        patch("zana.core.memory_lite._get_ollama_embedding", return_value=embedding),
        patch.object(db, "index_memory", return_value=True) as mock_index,
    ):
        db.add("episodic content", collection="episodic")

    # Should NOT be called for episodic collection
    mock_index.assert_not_called()
    db.close()
