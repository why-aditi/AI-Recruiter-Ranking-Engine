#!/usr/bin/env bash
# Test database connectivity and print fix hints
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY=".venv/Scripts/python.exe"

"$PY" - <<'PY'
import os
import sys
from pathlib import Path

# Load .env manually for diagnostic
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

url = os.environ.get("DATABASE_URL_SYNC", "postgresql://recruiter:recruiter@localhost:5432/recruiter_ranking")
print(f"Testing: {url.split('@')[-1]}")  # hide password in output

try:
    import psycopg2
    conn = psycopg2.connect(url)
    conn.close()
    print("OK: Database connection successful")
    sys.exit(0)
except Exception as e:
    print(f"FAIL: {e}")
    print()
    print("Common fixes:")
    print("  A) Use Docker Postgres (recommended):")
    print("     - Install Docker Desktop")
    print("     - bash scripts/up.sh")
    print("     - Set in .env: DATABASE_URL_SYNC=postgresql://recruiter:recruiter@localhost:5433/recruiter_ranking")
    print("       (and same host/port for DATABASE_URL with +asyncpg)")
    print("  B) Use your existing local Postgres on port 5432:")
    print("     - psql -U postgres -f scripts/init-local-postgres.sql")
    print("     - Requires pgvector extension installed locally")
    print("  C) Update .env with your actual postgres user/password/database")
    sys.exit(1)
PY
