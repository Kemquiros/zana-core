#!/usr/bin/env bash
# XANA Multimodal Sensory Gateway — launcher
# Usage: ./sensory/run.sh [--reload]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

cd "$SCRIPT_DIR"
# Ensure uv env is up to date
uv sync -q

# Make Rust .so modules visible
export PYTHONPATH="$ROOT:$PYTHONPATH"

exec uv run uvicorn \
    sensory.multimodal_gateway:app \
    --host 0.0.0.0 \
    --port "${GATEWAY_PORT:-54446}" \
    --log-level info \
    "$@"
