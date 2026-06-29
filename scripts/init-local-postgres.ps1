$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$psql = $null
if (Get-Command psql -ErrorAction SilentlyContinue) {
    $psql = "psql"
} else {
    foreach ($ver in 18, 17, 16, 15, 14, 13) {
        $candidate = "C:\Program Files\PostgreSQL\$ver\bin\psql.exe"
        if (Test-Path $candidate) {
            $psql = $candidate
            break
        }
    }
}

if (-not $psql) {
    Write-Error "psql not found. Install PostgreSQL or use Docker (scripts/up.ps1)"
}

Write-Host "Using: $psql"
Write-Host "Enter postgres superuser password when prompted.`n"

$sql = @"
DO `$`$ BEGIN
  CREATE USER recruiter WITH PASSWORD 'recruiter';
EXCEPTION WHEN duplicate_object THEN NULL;
END `$`$;

SELECT 'CREATE DATABASE recruiter_ranking OWNER recruiter'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'recruiter_ranking')\gexec

GRANT ALL PRIVILEGES ON DATABASE recruiter_ranking TO recruiter;
"@

$sql | & $psql -U postgres -v ON_ERROR_STOP=0

& $psql -U postgres -d recruiter_ranking -c "CREATE EXTENSION IF NOT EXISTS vector;"
& $psql -U postgres -d recruiter_ranking -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

Write-Host "`nDone. Run: .\scripts\check-db.sh or bash scripts/migrate.sh"
