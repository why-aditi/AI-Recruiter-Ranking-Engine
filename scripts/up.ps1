$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ComposeFile = Join-Path $Root "infra\docker-compose.yml"

if (-not (Test-Path $ComposeFile)) {
    Write-Error "Compose file not found: $ComposeFile"
}

$Docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $Docker)) { $Docker = "docker" }

if (-not (Get-Command $Docker -ErrorAction SilentlyContinue) -and -not (Test-Path $Docker)) {
    Write-Host ""
    Write-Host "ERROR: Docker is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    Write-Host ""
    Write-Host "Or continue with local PostgreSQL on port 5432 (no Docker needed):"
    Write-Host "  .\scripts\install-pgvector-windows.ps1"
    Write-Host "  bash scripts/migrate.sh"
    exit 1
}

Write-Host "Starting Postgres 18 + pgvector (port 5434), Redis, MLflow..."
& $Docker compose -f $ComposeFile up -d postgres redis mlflow
Write-Host "Done. Update .env to use port 5434, then run: bash scripts/migrate.sh"
