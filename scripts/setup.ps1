$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Python: $(python --version)"

if (-not (Test-Path ".venv")) {
    Write-Host "==> Creating venv..."
    python -m venv .venv
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "==> Upgrading pip..."
try {
    & $Py -m pip install --upgrade pip wheel
} catch {
    Write-Host "WARN: pip upgrade skipped (already OK)"
}

& $Py -m pip install -r requirements-core.txt
& $Py -m pip install -r requirements-ml.txt

Write-Host "`n==> Done. Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host @"

Next steps:
  1. Install Docker Desktop, then: .\scripts\up.ps1
  2. .\scripts\migrate.ps1
  3. python scripts\seed_db.py
  4. python scripts\prepare_data.py --seed-only
  5. python -m ml.ingestion --seed-only
  6. .\scripts\backend.ps1
"@
