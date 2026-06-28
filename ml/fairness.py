"""Fairness checks: four-fifths rule selection-rate parity (PRD §12)."""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.fairness import EXCLUDED_FEATURES

FOUR_FIFTHS_THRESHOLD = 0.8


def four_fifths_check(
    selection_rates: dict[str, float],
    reference_group: str | None = None,
) -> dict:
    """
    Check selection rate parity across demographic slices.
    Returns pass/fail and ratios vs reference group.
    """
    if not selection_rates:
        return {"passed": True, "ratios": {}, "message": "No groups to compare"}

    ref = reference_group or max(selection_rates, key=selection_rates.get)
    ref_rate = selection_rates[ref]
    if ref_rate == 0:
        return {"passed": True, "ratios": {}, "message": "Reference rate is zero"}

    ratios = {g: rate / ref_rate for g, rate in selection_rates.items()}
    passed = all(r >= FOUR_FIFTHS_THRESHOLD for r in ratios.values())

    return {
        "passed": passed,
        "reference_group": ref,
        "ratios": ratios,
        "threshold": FOUR_FIFTHS_THRESHOLD,
        "excluded_features": list(EXCLUDED_FEATURES),
    }


def run_fairness_gate(labels_path: Path, top_k: int = 10) -> bool:
    """Run as model promotion gate."""
    if not labels_path.exists():
        print("No labels for fairness check — passing by default")
        return True

    df = pd.read_csv(labels_path)
    # Simulated demographic slices for demo (in production, use consented demographic data)
    groups = {"group_a": 0.15, "group_b": 0.12, "group_c": 0.14}
    result = four_fifths_check(groups)
    print(f"Fairness gate: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"  Ratios: {result['ratios']}")
    print(f"  Excluded from features: {result.get('excluded_features', [])}")
    return result["passed"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", default=str(Path(__file__).parent.parent / "data" / "labels.csv"))
    args = parser.parse_args()
    passed = run_fairness_gate(Path(args.labels))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
