"""Quick verification script — runs without Docker."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
checks = []


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    checks.append(ok)
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


print("\n=== AI Recruiter Ranking Engine — Verification ===\n")

# Structure
required = [
    "backend/app/main.py",
    "backend/app/services/pipeline.py",
    "backend/app/services/llm_gateway.py",
    "ml/ingestion.py",
    "ml/training.py",
    "ml/evaluation.py",
    "frontend/src/app/page.tsx",
    "infra/docker-compose.yml",
    "scripts/prepare_data.py",
    "docs/runbooks.md",
]
for f in required:
    check(f"File: {f}", (ROOT / f).exists())

# Synthetic data
check("Synthetic seed data", (ROOT / "data/raw/resumes").exists() and any((ROOT / "data/raw/resumes").glob("*.txt")))

# Unit tests
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no"],
    cwd=ROOT / "backend",
    capture_output=True,
    text=True,
)
check("Unit tests", result.returncode == 0, f"{result.stdout.count('PASSED')} passed")

print(f"\n{'All checks passed!' if all(checks) else f'{sum(checks)}/{len(checks)} checks passed'}")
print("\nNext steps (requires Docker):")
print("  1. make up && make migrate")
print("  2. python scripts/seed_db.py")
print("  3. python -m ml.ingestion --seed-only")
print("  4. cd backend && uvicorn app.main:app --reload")
print("  5. cd frontend && npm run dev")
sys.exit(0 if all(checks) else 1)
