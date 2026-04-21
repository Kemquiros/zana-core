#!/bin/bash
# XANA Core Setup Script

set -e

echo "🧠 XANA Core Initialization"
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
for dir in embedder mcp/xana-memory episodic mcp/xana-episodic orchestrator; do
    echo "  -> Processing $dir..."
    cd $dir
    uv venv >/dev/null 2>&1
    uv sync >/dev/null 2>&1
    cd - >/dev/null
done

echo "🐳 Booting XANA Core Services (Docker)..."
docker compose up -d

echo ""
echo "✨ XANA Core is ready!"
echo ""
echo "Next Steps:"
echo "1. Ensure 'VAULT_PATH' in your '.env' points to your Obsidian Vault."
echo "2. Run the embedding pipeline: cd embedder && uv run python main.py --reset"
echo "3. Initialize Episodic DB: cd episodic && uv run python init_db.py"
echo "4. Start Episodic Service: cd episodic && uv run python main.py &"
echo "5. Add MCP servers to your agent CLI (Gemini/Claude):"
echo "   - XANA Memory: $(pwd)/mcp/xana-memory/.venv/bin/python $(pwd)/mcp/xana-memory/server.py"
echo "   - XANA Episodic: $(pwd)/mcp/xana-episodic/.venv/bin/python $(pwd)/mcp/xana-episodic/server.py"
echo ""
