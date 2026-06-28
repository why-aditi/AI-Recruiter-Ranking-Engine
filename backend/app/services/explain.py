import logging

import numpy as np

from app.services.features import FEATURE_NAMES
from app.services.ranker import load_ranker, heuristic_score

logger = logging.getLogger(__name__)


def compute_shap(features: dict[str, float], feature_vector: list[float] | None = None) -> list[dict]:
    """Compute SHAP attributions; falls back to proportional heuristic."""
    model = load_ranker()
    vec = feature_vector or [features.get(n, 0.0) for n in FEATURE_NAMES]

    if model is not None:
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(np.array([vec]))
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            sv = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            contributions = [
                {"feature": name, "value": float(vec[i]), "shap_value": float(sv[i])}
                for i, name in enumerate(FEATURE_NAMES)
            ]
            contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            return contributions[:8]
        except Exception as e:
            logger.warning("SHAP computation failed: %s", e)

    # Heuristic attribution: weight * value
    total = heuristic_score(features) or 1e-9
    weights = {
        "skill_overlap_must_have": 0.25,
        "skill_overlap_nice_to_have": 0.10,
        "semantic_similarity_score": 0.15,
        "years_experience_delta": 0.10,
        "seniority_match": 0.08,
        "domain_experience_match": 0.08,
        "career_trajectory_score": 0.06,
        "culture_fit_proxy": 0.03,
    }
    contributions = []
    for name in FEATURE_NAMES:
        w = weights.get(name, 0.02)
        val = features.get(name, 0.0)
        contributions.append({"feature": name, "value": val, "shap_value": w * val})
    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return contributions[:8]
