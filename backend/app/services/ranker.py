import logging
import os
from pathlib import Path

import lightgbm as lgb
import numpy as np

from app.config import settings
from app.services.features import FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_PATHS = [
    Path("data/models/ranker.txt"),
    Path("/app/data/models/ranker.txt"),
    Path(__file__).parent.parent.parent.parent / "data" / "models" / "ranker.txt",
]

_model: lgb.Booster | None = None
MODEL_VERSION = "stub-v0"


def _find_model_path() -> Path | None:
    for p in MODEL_PATHS:
        if p.exists():
            return p
    return None


def load_ranker() -> lgb.Booster | None:
    global _model, MODEL_VERSION
    if _model is not None:
        return _model
    path = _find_model_path()
    if path:
        _model = lgb.Booster(model_file=str(path))
        MODEL_VERSION = path.stem + "-trained"
        logger.info("Loaded ranker from %s", path)
        return _model
    logger.warning("No trained ranker found; using heuristic scoring")
    return None


def heuristic_score(features: dict[str, float]) -> float:
    """Fallback when no trained model is available."""
    weights = {
        "skill_overlap_must_have": 0.25,
        "skill_overlap_nice_to_have": 0.10,
        "skill_overlap_implied": 0.08,
        "semantic_similarity_score": 0.15,
        "years_experience_delta": 0.10,
        "seniority_match": 0.08,
        "domain_experience_match": 0.08,
        "career_trajectory_score": 0.06,
        "activity_recency_score": 0.04,
        "response_likelihood_score": 0.03,
        "culture_fit_proxy": 0.03,
    }
    return sum(features.get(k, 0.0) * w for k, w in weights.items())


def score_candidates(feature_matrix: list[list[float]]) -> list[float]:
    model = load_ranker()
    if model is not None:
        X = np.array(feature_matrix)
        return model.predict(X).tolist()
    return [heuristic_score(dict(zip(FEATURE_NAMES, row))) for row in feature_matrix]


def get_model_version() -> str:
    load_ranker()
    return MODEL_VERSION
