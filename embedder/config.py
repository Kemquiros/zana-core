import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

vault_env = os.getenv("VAULT_PATH")
if not vault_env:
    raise ValueError(
        "VAULT_PATH is not set in .env. Please configure your Obsidian Vault path."
    )

VAULT_PATH = Path(vault_env)

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_URL = f"http://{CHROMA_HOST}:{CHROMA_PORT}"

COLLECTION_NAME = "vault_knowledge"
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# Folders to skip (binary files, git internals, etc.)
SKIP_FOLDERS = {".obsidian", ".git", ".trash", ".space", ".makemd", "images", "assets"}
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".svg", ".webp"}

# Chunking
MIN_CHUNK_CHARS = 80  # shorter chunks discarded
MAX_CHUNK_CHARS = 2000  # split chunks that exceed this
