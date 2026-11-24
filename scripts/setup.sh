#!/usr/bin/env bash
set -euo pipefail

echo "=== LocalHarvey Setup ==="

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional: install Playwright browsers only if you plan online enrichment
# playwright install chromium || true

if ! command -v ollama &> /dev/null; then
  echo ""
  echo "Ollama is not installed."
  echo "Install from https://ollama.com then re-run this script or pull models manually."
else
  echo "Ollama found. Pulling permissive-licence models only..."
  # Apache-2.0 / MIT models only
  ollama pull qwen2.5:7b-instruct || true
  ollama pull phi3:mini || true
  # Optional larger models if hardware allows:
  # ollama pull qwen2.5:14b-instruct || true
fi

echo ""
echo "Setup complete."
echo "Start with:"
echo "  source .venv/bin/activate"
echo "  export PROFILE=standard   # or high / minimal / auto"
echo "  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Then open http://localhost:8000"
