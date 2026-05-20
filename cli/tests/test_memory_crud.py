"""
test_memory_crud.py — Sprint 9 · P0

Coverage for Sprint 8 APIs:
  MemoryLiteDB.delete / clear / export_docs / import_docs
  CLI commands: cmd_memory_delete / cmd_memory_clear / cmd_memory_export / cmd_memory_import

All tests use isolated tmp_path DBs — no shared state.
Resolves: https://github.com/Kemquiros/zana-core/issues/3
"""

import csv
import json

import pytest
from zana.core.memory_lite import MemoryLiteDB, get_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Isolated MemoryLiteDB backed by a temp directory."""
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    instance = get_db()
    yield instance
    instance.close()


@pytest.fixture()
def populated_db(db):
    """DB with 3 docs in zana_vault and 2 in episodic."""
    db.add("Alpha document about astronomy", source="test", collection="zana_vault")
    db.add("Beta document about biology", source="test", collection="zana_vault")
    db.add("Gamma document about geology", source="test", collection="zana_vault")
    db.add_episodic("user", "Hello Aeon")
    db.add_episodic("assistant", "Hello John, ready to build empires")
    return db


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


def test_delete_existing_id_returns_true(db):
    doc_id = db.add("Document to delete", collection="zana_vault")
    assert db.delete(doc_id) is True


def test_delete_removes_document_from_db(db):
    doc_id = db.add("Ephemeral content", collection="zana_vault")
    db.delete(doc_id)
    results = db.search("Ephemeral content", collection="zana_vault")
    assert results == []


def test_delete_nonexistent_id_returns_false(db):
    assert db.delete(999999) is False


def test_delete_does_not_affect_other_documents(populated_db):
    docs_before = populated_db.export_docs(collection="zana_vault")
    target_id = docs_before[0]["id"]
    remaining_before = [d for d in docs_before if d["id"] != target_id]

    populated_db.delete(target_id)

    docs_after = populated_db.export_docs(collection="zana_vault")
    assert len(docs_after) == len(remaining_before)
    remaining_ids = {d["id"] for d in docs_after}
    assert target_id not in remaining_ids


def test_delete_twice_same_id(db):
    doc_id = db.add("Delete me twice", collection="zana_vault")
    assert db.delete(doc_id) is True
    assert db.delete(doc_id) is False


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def test_clear_collection_returns_correct_count(populated_db):
    deleted = populated_db.clear(collection="zana_vault")
    assert deleted == 3


def test_clear_collection_leaves_other_collections_intact(populated_db):
    populated_db.clear(collection="zana_vault")
    episodic = populated_db.export_docs(collection="episodic")
    assert len(episodic) == 2


def test_clear_all_removes_every_document(populated_db):
    deleted = populated_db.clear()
    assert deleted == 5
    assert populated_db.export_docs() == []


def test_clear_returns_zero_on_empty_collection(db):
    deleted = db.clear(collection="nonexistent_collection")
    assert deleted == 0


def test_clear_fts5_index_usable_after_clear(populated_db):
    populated_db.clear(collection="zana_vault")
    # Insert new document after clear — FTS5 must still index it
    populated_db.add("Post-clear searchable document", collection="zana_vault")
    results = populated_db.search("Post-clear", collection="zana_vault")
    assert len(results) == 1
    assert "Post-clear" in results[0]["content"]


def test_clear_stats_reflect_deletion(populated_db):
    populated_db.clear(collection="zana_vault")
    stats = populated_db.stats()
    assert stats["collections"].get("zana_vault", 0) == 0
    assert stats["collections"].get("episodic", 0) == 2


# ---------------------------------------------------------------------------
# export_docs()
# ---------------------------------------------------------------------------


def test_export_docs_returns_all_documents(populated_db):
    docs = populated_db.export_docs()
    assert len(docs) == 5


def test_export_docs_with_collection_filter(populated_db):
    docs = populated_db.export_docs(collection="zana_vault")
    assert len(docs) == 3
    assert all(d["collection"] == "zana_vault" for d in docs)


def test_export_docs_keys_are_complete(populated_db):
    docs = populated_db.export_docs(collection="zana_vault")
    required_keys = {"id", "collection", "source", "content", "metadata", "created_at"}
    for doc in docs:
        assert required_keys.issubset(doc.keys())


def test_export_docs_content_matches(db):
    db.add("Unique export content XYZ", source="src1", collection="zana_vault")
    docs = db.export_docs(collection="zana_vault")
    assert any("Unique export content XYZ" in d["content"] for d in docs)


def test_export_docs_empty_collection_returns_empty_list(db):
    assert db.export_docs(collection="nonexistent") == []


# ---------------------------------------------------------------------------
# import_docs()
# ---------------------------------------------------------------------------


def test_import_docs_returns_correct_count(db):
    docs = [
        {"content": "Imported alpha", "collection": "zana_vault"},
        {"content": "Imported beta", "collection": "zana_vault"},
        {"content": "Imported gamma", "collection": "episodic", "source": "user"},
    ]
    assert db.import_docs(docs) == 3


def test_import_docs_skips_empty_content(db):
    docs = [
        {"content": "Valid document"},
        {"content": ""},
        {"source": "no-content-key"},
    ]
    count = db.import_docs(docs)
    assert count == 1


def test_import_docs_are_searchable_after_import(db):
    db.import_docs(
        [{"content": "Quantum sovereign inference", "collection": "zana_vault"}]
    )
    results = db.search("Quantum sovereign", collection="zana_vault")
    assert len(results) >= 1
    assert "Quantum sovereign inference" in results[0]["content"]


def test_import_docs_preserves_collection_field(db):
    db.import_docs(
        [{"content": "Episodic import", "collection": "episodic", "source": "user"}]
    )
    docs = db.export_docs(collection="episodic")
    assert any(d["content"] == "Episodic import" for d in docs)


# ---------------------------------------------------------------------------
# Round-trip: add → export → clear → import → search
# ---------------------------------------------------------------------------


def test_roundtrip_export_clear_import_search(db):
    originals = [
        "ZANA sovereign memory architecture",
        "Offline inference without Docker",
        "Z-Protocol open stack",
    ]
    for text in originals:
        db.add(text, collection="zana_vault")

    # Export
    exported = db.export_docs(collection="zana_vault")
    assert len(exported) == 3

    # Clear
    db.clear(collection="zana_vault")
    assert db.export_docs(collection="zana_vault") == []

    # Re-import
    imported = db.import_docs(exported)
    assert imported == 3

    # Search — all originals must be findable
    for text in originals:
        keyword = text.split()[0]
        results = db.search(keyword, collection="zana_vault")
        assert len(results) >= 1, f"'{text}' not found after round-trip"


# ---------------------------------------------------------------------------
# CLI command wrappers (integration)
# ---------------------------------------------------------------------------


def test_cmd_delete_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    db = get_db()
    doc_id = db.add("CLI delete test", collection="zana_vault")
    db.close()

    from zana.commands.memory import cmd_memory_delete

    cmd_memory_delete(doc_id)  # should not raise

    db2 = get_db()
    assert db2.export_docs(collection="zana_vault") == []
    db2.close()


def test_cmd_clear_with_yes_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    db = get_db()
    db.add("Will be cleared", collection="zana_vault")
    db.close()

    from zana.commands.memory import cmd_memory_clear

    cmd_memory_clear(collection="zana_vault")  # should not raise

    db2 = get_db()
    assert db2.export_docs(collection="zana_vault") == []
    db2.close()


def test_cmd_export_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    db = get_db()
    db.add("Export JSON test", collection="zana_vault")
    db.close()

    output_file = tmp_path / "export.json"
    from zana.commands.memory import cmd_memory_export

    cmd_memory_export(collection="zana_vault", fmt="json", output=str(output_file))

    data = json.loads(output_file.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["content"] == "Export JSON test"


def test_cmd_export_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    db = get_db()
    db.add("Export CSV test", collection="zana_vault")
    db.close()

    output_file = tmp_path / "export.csv"
    from zana.commands.memory import cmd_memory_export

    cmd_memory_export(collection="zana_vault", fmt="csv", output=str(output_file))

    with output_file.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["content"] == "Export CSV test"


def test_cmd_import_from_json_file(tmp_path, monkeypatch):
    monkeypatch.setattr(MemoryLiteDB, "DB_PATH", tmp_path / "memory_lite.db")
    import_data = [
        {"content": "Imported from file A", "collection": "zana_vault"},
        {"content": "Imported from file B", "collection": "zana_vault"},
    ]
    import_file = tmp_path / "import.json"
    import_file.write_text(json.dumps(import_data))

    from zana.commands.memory import cmd_memory_import

    cmd_memory_import(str(import_file))

    db = get_db()
    docs = db.export_docs(collection="zana_vault")
    db.close()
    assert len(docs) == 2
