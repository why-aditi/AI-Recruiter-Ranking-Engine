#!/usr/bin/env bash
# Start Postgres + Redis (requires Docker Desktop)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/docker-env.sh"
COMPOSE_FILE="$ROOT/infra/docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE"
  exit 1
fi
docker compose -f "$COMPOSE_FILE" up -d postgres redis mlflow
