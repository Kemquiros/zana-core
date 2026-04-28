#!/bin/bash
# ZANA Core Setup Script

set -e

echo "🧠 ZANA Core Initialization"
echo "==========================="

# Check dependencies
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' is not installed. Please install it: https://github.com/astral-sh/uv"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Error: 'docker' is not installed."
    exit 1
fi

# Setup .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  ACTION REQUIRED: Please edit '.env' and set your 'VAULT_PATH'."
else
    echo "✅ .env already exists."
fi

# Initialize virtual environments
echo "📦 Setting up Python virtual environments via 'uv'..."
for dir in embedder mcp/zana-memory episodic mcp/zana-episodic orchestrator; do
    echo "  -> Processing $dir..."
    cd $dir
    uv venv >/dev/null 2>&1
    uv sync >/dev/null 2>&1
    cd - >/dev/null
done

# Build Rust Steel Core components
echo "⚙️  Forging The Steel Core (Rust)..."
# Build zana_steel_core
cd rust_core && RUSTFLAGS="-C target-cpu=native" cargo build --release --features python && cp target/release/libzana_steel_core.so ../zana_steel_core.so && cd ..
# Build zana_audio_dsp
cd audio_dsp && RUSTFLAGS="-C target-cpu=native" cargo build --release && cp target/release/libzana_audio_dsp.so ../zana_audio_dsp.so && cd ..
# Build zana_armor
cd armor && RUSTFLAGS="-C target-cpu=native" cargo build --release && cp target/release/libzana_armor.so ../zana_armor.so && cd ..

echo "🐳 Booting ZANA Core Services (Docker)..."
docker compose up -d

echo ""
echo "✨ ZANA Core is ready!"
echo ""
echo "Next Steps:"
echo "1. Ensure 'VAULT_PATH' in your '.env' points to your Obsidian Vault."
echo "2. Run the embedding pipeline: cd embedder && uv run python main.py --reset"
echo "3. Initialize Episodic DB: cd episodic && uv run python init_db.py"
echo "4. Start Episodic Service: cd episodic && uv run python main.py &"
echo "5. Add MCP servers to your agent CLI (Gemini/Claude):"
echo "   - ZANA Memory: $(pwd)/mcp/zana-memory/.venv/bin/python $(pwd)/mcp/zana-memory/server.py"
echo "   - ZANA Episodic: $(pwd)/mcp/zana-episodic/.venv/bin/python $(pwd)/mcp/zana-episodic/server.py"
echo ""
