#!/usr/bin/env bash
set -e
source .venv/bin/activate 2>/dev/null || true
export PYTHONPATH=.
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
