#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/Scripts/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
