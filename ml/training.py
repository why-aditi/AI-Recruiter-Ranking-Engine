"""LightGBM LambdaMART training with MLflow registry and promotion gate."""

import argparse
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

try:
    import mlflow
    import mlflow.lightgbm

    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.schemas.profiles import CandidateProfile, JobProfile
from app.services.features import FEATURE_NAMES, compute_features, features_to_vector

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
LABELS_PATH = DATA_DIR / "labels.csv"
CHAMPION_NDCG = 0.0


def ndcg_at_k(y_true: list, y_score: list, k: int = 10) -> float:
    order = np.argsort(y_score)[::-1][:k]
    gains = [y_true[i] for i in order]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(y_true, reverse=True)[:k]
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def build_training_data(session: Session, labels_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X, y, groups = [], [], []
    job_cache = {}
    cand_cache = {}

    for job_id, group in labels_df.groupby("job_id"):
        job_row = session.execute(text("SELECT raw_text, job_profile FROM jobs WHERE id = :id"), {"id": job_id}).fetchone()
        if not job_row:
            continue
        if job_id not in job_cache:
            if job_row.job_profile:
                job_cache[job_id] = JobProfile(**job_row.job_profile)
            else:
                job_cache[job_id] = JobProfile(must_have_skills=["python"], domain_context="tech")

        group_size = 0
        for _, row in group.iterrows():
            cid = row["candidate_id"]
            if cid not in cand_cache:
                cand_row = session.execute(text("SELECT profile FROM candidates WHERE id = :id"), {"id": cid}).fetchone()
                if cand_row and cand_row.profile:
                    cand_cache[cid] = CandidateProfile(**cand_row.profile)
                else:
                    continue
            features = compute_features(job_cache[job_id], cand_cache[cid])
            X.append(features_to_vector(features))
            y.append(row["label"])
            group_size += 1
        if group_size > 0:
            groups.append(group_size)

    return np.array(X), np.array(y), np.array(groups)


def train(max_rounds: int = 100) -> str:
    if not LABELS_PATH.exists():
        print(f"No labels at {LABELS_PATH}. Run ml.labeling first.")
        return ""

    labels_df = pd.read_csv(LABELS_PATH)
    engine = create_engine(settings.database_url_sync)

    with Session(engine) as session:
        X, y, groups = build_training_data(session, labels_df)

    if len(X) < 10:
        print("Insufficient training data. Generating synthetic labels...")
        _generate_synthetic_labels()
        labels_df = pd.read_csv(LABELS_PATH)
        with Session(engine) as session:
            X, y, groups = build_training_data(session, labels_df)

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    job_ids = labels_df.groupby("job_id").size().index.tolist()
    train_jobs, test_jobs = next(gss.split(job_ids, groups=job_ids))

    train_mask = labels_df["job_id"].isin([job_ids[i] for i in train_jobs])
    test_mask = labels_df["job_id"].isin([job_ids[i] for i in test_jobs])

    if HAS_MLFLOW:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    def _train_body():
        train_data = lgb.Dataset(X[train_mask.values if hasattr(train_mask, 'values') else train_mask], label=y[train_mask.values if hasattr(train_mask, 'values') else train_mask])
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [10],
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 5,
            "verbose": -1,
        }
        model = lgb.train(params, train_data, num_boost_round=max_rounds)

        test_X = X[test_mask.values if hasattr(test_mask, 'values') else test_mask]
        test_y = y[test_mask.values if hasattr(test_mask, 'values') else test_mask]
        preds = model.predict(test_X)

        ndcg_scores = []
        test_df = labels_df[test_mask]
        for jid, grp in test_df.groupby("job_id"):
            idx = grp.index.tolist()
            local_preds = [preds[list(test_df.index).index(i)] for i in idx if i in test_df.index]
            local_labels = grp["label"].tolist()
            if local_labels:
                ndcg_scores.append(ndcg_at_k(local_labels, local_preds))

        avg_ndcg = np.mean(ndcg_scores) if ndcg_scores else 0.0
        if HAS_MLFLOW:
            mlflow.log_metric("ndcg_at_10", avg_ndcg)
            mlflow.log_param("num_features", len(FEATURE_NAMES))
            mlflow.log_param("train_samples", len(X))

        model_path = MODEL_DIR / "ranker.txt"
        model.save_model(str(model_path))
        if HAS_MLFLOW:
            mlflow.lightgbm.log_model(model, "model")

        champion_path = MODEL_DIR / "champion_ndcg.txt"
        champion_ndcg = float(champion_path.read_text()) if champion_path.exists() else 0.0
        if avg_ndcg >= champion_ndcg:
            champion_path.write_text(str(avg_ndcg))
            print(f"Model PROMOTED: NDCG@10={avg_ndcg:.4f} (champion was {champion_ndcg:.4f})")
        else:
            print(f"Model NOT promoted: NDCG@10={avg_ndcg:.4f} < champion {champion_ndcg:.4f}")

        print(f"Model saved to {model_path}")
        return str(model_path)

    if HAS_MLFLOW:
        with mlflow.start_run(run_name="lambdamart_ranker"):
            return _train_body()
    print("MLflow not installed — training without experiment tracking")
    return _train_body()


def _generate_synthetic_labels():
    """Create minimal synthetic labels for cold start."""
    rows = []
    for i in range(5):
        for j in range(10):
            rows.append({"job_id": f"job_{i}", "candidate_id": f"cand_{j}", "label": (i + j) % 4, "reason": "synthetic"})
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(LABELS_PATH, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=100)
    train(args.rounds)


if __name__ == "__main__":
    main()
