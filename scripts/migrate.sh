#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! bash scripts/check-db.sh; then
  exit 1
fi

PY="$ROOT/.venv/Scripts/python.exe"
if [[ ! -x "$PY" ]]; then
  PY="$ROOT/.venv/bin/python"
fi
cd backend
"$PY" -m alembic upgrade head
echo "Migrations complete."
