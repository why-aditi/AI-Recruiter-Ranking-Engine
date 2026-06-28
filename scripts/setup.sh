# Windows / Git Bash setup (replaces `make` on systems without it)
# Usage from repo root:
#   bash scripts/setup.sh          # Git Bash
#   powershell -File scripts/setup.ps1   # PowerShell

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"
VENV=".venv"

echo "==> Python: $($PYTHON --version)"

if [ ! -d "$VENV" ]; then
  echo "==> Creating venv..."
  "$PYTHON" -m venv "$VENV"
fi

# Always use the venv interpreter directly (avoids Windows pip.exe lock issues)
PY="$VENV/Scripts/python.exe"

echo "==> Upgrading pip..."
"$PY" -m pip install --upgrade pip wheel 2>/dev/null || echo "WARN: pip upgrade skipped (already OK)"

echo "==> Installing core dependencies..."
"$PY" -m pip install -r requirements-core.txt

echo "==> Installing ML dependencies..."
"$PY" -m pip install -r requirements-ml.txt || echo "WARN: Some ML packages failed (training may be limited)"

echo ""
echo "==> Done. Activate with: source .venv/Scripts/activate"
echo ""
echo "Next steps:"
echo "  1. Install Docker Desktop, then: bash scripts/up.sh"
echo "  2. bash scripts/migrate.sh"
echo "  3. python scripts/seed_db.py"
echo "  4. python scripts/prepare_data.py --seed-only"
echo "  5. python -m ml.ingestion --seed-only"
echo "  6. bash scripts/backend.sh"
