"""NDCG@10 evaluation: Baseline A vs Baseline B vs full pipeline."""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.schemas.profiles import CandidateProfile, JobProfile
from app.services.baseline import embedding_baseline, keyword_baseline
from app.services.features import compute_features, features_to_vector
from app.services.ranker import score_candidates

DATA_DIR = Path(__file__).parent.parent / "data"
LABELS_PATH = DATA_DIR / "labels.csv"
CHART_PATH = DATA_DIR / "ndcg_comparison.png"


def ndcg_at_k(y_true: list, y_score: list, k: int = 10) -> float:
    order = np.argsort(y_score)[::-1][:k]
    gains = [y_true[i] for i in order]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(y_true, reverse=True)[:k]
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate():
    if not LABELS_PATH.exists():
        print("No labels found. Run ml.labeling first.")
        return

    labels_df = pd.read_csv(LABELS_PATH)
    engine = create_engine(settings.database_url_sync)

    baseline_a_ndcg, baseline_b_ndcg, full_ndcg = [], [], []

    with Session(engine) as session:
        for job_id, group in labels_df.groupby("job_id"):
            job_row = session.execute(
                text("SELECT raw_text, job_profile FROM jobs WHERE id = :id"), {"id": job_id}
            ).fetchone()
            if not job_row:
                continue

            job_profile = JobProfile(**job_row.job_profile) if job_row.job_profile else JobProfile(must_have_skills=["python"])
            jd_text = job_row.raw_text

            cands = []
            for _, row in group.iterrows():
                cand_row = session.execute(
                    text("SELECT id, raw_text, profile, embedding FROM candidates WHERE id = :id"),
                    {"id": row["candidate_id"]},
                ).fetchone()
                if cand_row:
                    profile = CandidateProfile(**cand_row.profile) if cand_row.profile else CandidateProfile()
                    cands.append({
                        "id": str(cand_row.id),
                        "raw_text": cand_row.raw_text,
                        "profile": profile,
                        "label": row["label"],
                        "embedding": list(cand_row.embedding) if cand_row.embedding is not None else None,
                    })

            if len(cands) < 2:
                continue

            labels = [c["label"] for c in cands]

            # Baseline A: keyword
            kw_input = [(c["id"], c["raw_text"], c["profile"].skills) for c in cands]
            kw_ranked = keyword_baseline(job_profile, kw_input, len(cands))
            kw_scores = [len(cands) - kw_ranked.index(c["id"]) if c["id"] in kw_ranked else 0 for c in cands]
            baseline_a_ndcg.append(ndcg_at_k(labels, kw_scores))

            # Baseline B: embedding
            emb_input = [(c["id"], c["embedding"]) for c in cands if c["embedding"]]
            if emb_input:
                emb_ranked = embedding_baseline(jd_text, emb_input, len(emb_input))
                emb_scores = [len(cands) - emb_ranked.index(c["id"]) if c["id"] in emb_ranked else 0 for c in cands]
                baseline_b_ndcg.append(ndcg_at_k(labels, emb_scores))

            # Full pipeline
            feat_matrix = []
            for c in cands:
                feats = compute_features(job_profile, c["profile"])
                feat_matrix.append(features_to_vector(feats))
            full_scores = score_candidates(feat_matrix)
            full_ndcg.append(ndcg_at_k(labels, full_scores))

    results = {
        "Baseline A (Keyword)": np.mean(baseline_a_ndcg) if baseline_a_ndcg else 0,
        "Baseline B (Embedding)": np.mean(baseline_b_ndcg) if baseline_b_ndcg else 0,
        "Full Pipeline (LightGBM)": np.mean(full_ndcg) if full_ndcg else 0,
    }

    print("\n=== NDCG@10 Comparison ===")
    for name, score in results.items():
        print(f"  {name}: {score:.4f}")

    # Chart
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    names = list(results.keys())
    scores = list(results.values())
    bars = ax.bar(names, scores, color=["#ef4444", "#f59e0b", "#22c55e"])
    ax.set_ylabel("NDCG@10")
    ax.set_title("Ranking Quality: Baselines vs Full Pipeline")
    ax.set_ylim(0, 1)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{score:.3f}", ha="center")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=150)
    print(f"\nChart saved to {CHART_PATH}")

    pd.DataFrame([results]).to_csv(DATA_DIR / "eval_results.csv", index=False)
    return results


def main():
    evaluate()


if __name__ == "__main__":
    main()
