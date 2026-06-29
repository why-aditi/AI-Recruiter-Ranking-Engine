#!/usr/bin/env bash
# Reset Docker Postgres — works in Git Bash (finds docker.exe automatically)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=docker-env.sh
source "$ROOT/scripts/docker-env.sh"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker Desktop and ensure it is running."
  exit 1
fi

echo "Using: $(command -v docker)"
echo "Stopping and removing container..."
docker rm -f recruiter-ranking-db 2>/dev/null || true

echo "Removing project volumes..."
docker volume rm recruiter-ranking-pgdata 2>/dev/null || true

echo "Pulling pgvector/pgvector:pg18 (if needed)..."
docker pull pgvector/pgvector:pg18

echo "Starting fresh pgvector/pgvector:pg18 on port ${DOCKER_PG_HOST_PORT}..."
docker run -d \
  --name recruiter-ranking-db \
  -e POSTGRES_USER=recruiter \
  -e POSTGRES_PASSWORD=recruiter \
  -e POSTGRES_DB=recruiter_ranking \
  -p "${DOCKER_PG_HOST_PORT}:5432" \
  -v recruiter-ranking-pgdata:/var/lib/postgresql \
  pgvector/pgvector:pg18

echo "Waiting 8s for init..."
sleep 8

echo ""
echo "=== Internal test (must succeed) ==="
docker exec recruiter-ranking-db psql -U recruiter -d recruiter_ranking -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT 1 AS ok;"

echo ""
echo "=== Next: test from host ==="
echo 'PGPASSWORD=recruiter "/c/Program Files/PostgreSQL/16/bin/psql.exe" -h 127.0.0.1 -p '"${DOCKER_PG_HOST_PORT}"' -U recruiter -d recruiter_ranking -c "SELECT 1;"'
echo "bash scripts/check-db.sh && bash scripts/migrate.sh"
