# Sovereign Memory Engine v2 (Rust) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ChromaDB with a native Rust vector index (`zana_steel_core.PyVectorIndex`) for instant, lightweight semantic search.

**Architecture:** We will move from a networked database (ChromaDB) to a local, binary-persisted vector index managed by Rust. The `embedder` will write directly to a shared index file (`data/memory.index`), and the `zana-memory` MCP server will read from it. This eliminates the need for the `chromadb` Docker service.

**Tech Stack:** Rust (PyO3), Python 3.12, sentence-transformers, Docker Compose.

---

### Task 1: Build and Link Rust Steel Core

**Files:**
- Modify: `rust_core/Cargo.toml` (verify python feature)
- Action: Build `.so` file

- [ ] **Step 1: Build the Rust extension**
```bash
cd rust_core
RUSTFLAGS="-C target-cpu=native" cargo build --release --features python
cp target/release/libzana_steel_core.so ../zana_steel_core.so
```

- [ ] **Step 2: Verify import**
```bash
python3 -c "import zana_steel_core; print('Success:', zana_steel_core.PyVectorIndex())"
```

- [ ] **Step 3: Commit**
```bash
git add zana_steel_core.so
git commit -m "chore(rust): build and link native steel core extension"
```

### Task 2: Refactor Embedder for Rust Index

**Files:**
- Modify: `embedder/config.py`
- Modify: `embedder/watcher.py`

- [ ] **Step 1: Update configuration**
In `embedder/config.py`, remove Chroma host/port and add `MEMORY_INDEX_PATH`.

```python
import os
from pathlib import Path

# ... existing VAULT_PATH ...
MEMORY_INDEX_PATH = Path(os.getenv("ZANA_CORE_DIR", ".")) / "data" / "memory.index"
COLLECTION_NAME = "vault_knowledge"
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
```

- [ ] **Step 2: Update watcher.py logic**
Replace `chromadb` client with `zana_steel_core.PyVectorIndex`.

```python
import zana_steel_core
from config import MEMORY_INDEX_PATH

class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, index, model):
        self.index = index
        self.model = model

    def on_created(self, event):
        # ... logic to chunk and then:
        embedding = self.model.encode(text).tolist()
        self.index.add(id=file_id, embedding=embedding, metadata=json.dumps(metadata))
        self.index.save(str(MEMORY_INDEX_PATH))
```

- [ ] **Step 3: Commit**
```bash
git add embedder/config.py embedder/watcher.py
git commit -m "refactor(embedder): switch from ChromaDB to Rust VectorIndex"
```

### Task 3: Update zana-memory MCP Server

**Files:**
- Modify: `mcp/zana-memory/server.py`
- Modify: `mcp/zana-memory/pyproject.toml`

- [ ] **Step 1: Remove chromadb dependency from pyproject.toml**
- [ ] **Step 2: Update server.py to use `zana_steel_core`**

```python
import zana_steel_core
from pathlib import Path

INDEX_PATH = Path(os.getenv("ZANA_CORE_DIR", ".")) / "data" / "memory.index"

# Load index
index = zana_steel_core.PyVectorIndex.load(str(INDEX_PATH))

# In search tool:
results = index.search(query_embedding, top_k=5)
# results is list of (id, score, metadata_json)
```

- [ ] **Step 3: Commit**
```bash
git add mcp/zana-memory/
git commit -m "refactor(mcp): update memory server to use native Rust index"
```

### Task 4: Infrastructure Cleanup

**Files:**
- Modify: `docker-compose.yml`
- Modify: `cli/cli/commands/status.py`
- Modify: `cli/cli/commands/doctor.py`

- [ ] **Step 1: Remove chromadb from docker-compose.yml**
- [ ] **Step 2: Remove ChromaDB health checks from CLI status/doctor**
- [ ] **Step 3: Commit**
```bash
git add docker-compose.yml cli/
git commit -m "chore(infra): decommission ChromaDB service"
```
