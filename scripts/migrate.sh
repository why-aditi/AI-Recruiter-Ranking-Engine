#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! bash scripts/check-db.sh; then
  exit 1
fi

source .venv/Scripts/activate
cd backend
python -m alembic upgrade head
echo "Migrations complete."
