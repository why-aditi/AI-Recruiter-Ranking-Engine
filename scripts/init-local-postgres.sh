#!/usr/bin/env bash
# Initialize local PostgreSQL for this project (Windows-friendly)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

find_psql() {
  if command -v psql >/dev/null 2>&1; then
    command -v psql
    return
  fi
  for ver in 18 17 16 15 14 13; do
    win="/c/Program Files/PostgreSQL/$ver/bin/psql.exe"
    if [ -x "$win" ]; then
      echo "$win"
      return
    fi
    win="/c/Program Files/PostgreSQL/$ver/bin/psql"
    if [ -x "$win" ]; then
      echo "$win"
      return
    fi
  done
  return 1
}

PSQL=$(find_psql) || {
  echo "ERROR: psql not found."
  echo "Install PostgreSQL from https://www.postgresql.org/download/windows/"
  echo "Or use Docker: bash scripts/up.sh (then set .env port to 5434)"
  exit 1
}

echo "Using: $PSQL"
echo "You will be prompted for the postgres superuser password."
echo ""

# Create user + database (ignore if already exists)
"$PSQL" -U postgres -v ON_ERROR_STOP=0 <<'SQL'
DO $$ BEGIN
  CREATE USER recruiter WITH PASSWORD 'recruiter';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

SELECT 'CREATE DATABASE recruiter_ranking OWNER recruiter'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'recruiter_ranking')\gexec

GRANT ALL PRIVILEGES ON DATABASE recruiter_ranking TO recruiter;
SQL

echo ""
echo "Creating extensions (requires pgvector installed)..."
if ! "$PSQL" -U postgres -d recruiter_ranking -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null; then
  echo ""
  echo "WARN: pgvector not installed. Run as Administrator (PowerShell):"
  echo "  powershell -ExecutionPolicy Bypass -File scripts/install-pgvector-windows.ps1"
  echo ""
  echo "Or use Docker instead: bash scripts/up.sh (set .env port to 5434)"
  exit 1
fi

echo ""
echo "Done. Ensure .env uses port 5432:"
echo "  DATABASE_URL=postgresql+asyncpg://recruiter:recruiter@localhost:5432/recruiter_ranking"
echo "  DATABASE_URL_SYNC=postgresql://recruiter:recruiter@localhost:5432/recruiter_ranking"
echo ""
echo "Next: bash scripts/check-db.sh && bash scripts/migrate.sh"
