#!/usr/bin/env bash
# Start Postgres + Redis (requires Docker Desktop)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker compose -f "$ROOT/infra/docker-compose.yml" up -d postgres redis mlflow
