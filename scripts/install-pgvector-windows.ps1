# Install pgvector for PostgreSQL 18 on Windows (prebuilt binaries)
# MUST run PowerShell AS ADMINISTRATOR (right-click -> Run as administrator)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host ""
    Write-Host "ERROR: This script must run in an elevated (Administrator) PowerShell." -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix:"
    Write-Host "  1. Close this window"
    Write-Host "  2. Start menu -> type 'PowerShell'"
    Write-Host "  3. Right-click 'Windows PowerShell' -> Run as administrator"
    Write-Host "  4. cd `"D:\Projects\AI Recruiter Ranking Engine`""
    Write-Host "  5. Set-ExecutionPolicy -Scope Process Bypass"
    Write-Host "  6. .\scripts\install-pgvector-windows.ps1"
    Write-Host ""
    exit 1
}

$PgRoot = "C:\Program Files\PostgreSQL\18"
if (-not (Test-Path $PgRoot)) {
    # Fallback for older local installs
    $PgRoot = "C:\Program Files\PostgreSQL\16"
}
if (-not (Test-Path $PgRoot)) {
    Write-Error "PostgreSQL 18 (or 16) not found under C:\Program Files\PostgreSQL\"
}

$PgMajor = Split-Path $PgRoot -Leaf
$ReleaseTag = if ($PgMajor -eq "18") { "0.8.3_18.4" } else { "0.8.3_16.14" }
$ZipName = if ($PgMajor -eq "18") { "vector.v0.8.3-pg18.zip" } else { "vector.v0.8.3-pg16.zip" }
$ReleaseUrl = "https://github.com/andreiramani/pgvector_pgsql_windows/releases/download/$ReleaseTag/$ZipName"
$TempZip = Join-Path $env:TEMP $ZipName
$TempDir = Join-Path $env:TEMP "vector-pg$PgMajor-install"

Write-Host "Downloading pgvector for PostgreSQL $PgMajor..."
Invoke-WebRequest -Uri $ReleaseUrl -OutFile $TempZip
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
Expand-Archive -Path $TempZip -DestinationPath $TempDir -Force

Write-Host "Stopping PostgreSQL services..."
$pgServices = Get-Service | Where-Object { $_.Name -like "*postgres*" -or $_.DisplayName -like "*PostgreSQL*" }
if (-not $pgServices) {
    Write-Warning "No PostgreSQL Windows service found; continuing anyway."
} else {
    foreach ($svc in $pgServices) {
        if ($svc.Status -eq "Running") {
            Write-Host "  Stopping $($svc.Name)..."
            Stop-Service $svc.Name -Force -ErrorAction Stop
        }
    }
    Start-Sleep -Seconds 3
    Get-Process postgres -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "Installing files to $PgRoot ..."
try {
    Copy-Item -Path "$TempDir\lib\*" -Destination "$PgRoot\lib" -Force
    Copy-Item -Path "$TempDir\share\*" -Destination "$PgRoot\share" -Recurse -Force
    if (Test-Path "$TempDir\include") {
        Copy-Item -Path "$TempDir\include\*" -Destination "$PgRoot\include" -Recurse -Force
    }
} catch {
    Write-Host ""
    Write-Host "Copy failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual install (with Postgres stopped via services.msc):"
    Write-Host "  1. Win+R -> services.msc -> stop postgresql-x64-$PgMajor"
    Write-Host "  2. Extract: $TempZip"
    Write-Host "  3. Copy extracted lib\vector.dll     -> $PgRoot\lib\"
    Write-Host "  4. Copy extracted share\extension\* -> $PgRoot\share\extension\"
    Write-Host "  5. Start the PostgreSQL service again"
    Write-Host "  6. psql -U postgres -d recruiter_ranking -c `"CREATE EXTENSION vector;`""
    exit 1
}

Write-Host "Starting PostgreSQL service..."
foreach ($svc in $pgServices) {
    Start-Service $svc.Name -ErrorAction SilentlyContinue
}

$Psql = Join-Path $PgRoot "bin\psql.exe"
Write-Host "Enabling extension in recruiter_ranking (enter postgres password if prompted)..."
& $Psql -U postgres -d recruiter_ranking -c "CREATE EXTENSION IF NOT EXISTS vector;"
& $Psql -U postgres -d recruiter_ranking -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

Write-Host "`nVerifying..."
& $Psql -U postgres -d recruiter_ranking -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector','uuid-ossp');"

Write-Host "`nDone. Next in Git Bash: bash scripts/migrate.sh"
