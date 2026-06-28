"""Feature engineering for (JobProfile, CandidateProfile) pairs — PRD §3.7."""

from app.schemas.profiles import CandidateProfile, JobProfile, SignalWeights
from app.services.fairness import EXCLUDED_FEATURES

SENIORITY_ORDER = {"junior": 0, "mid": 1, "senior": 2, "staff": 3, "principal": 4}

FEATURE_NAMES = [
    "skill_overlap_must_have",
    "skill_overlap_nice_to_have",
    "skill_overlap_implied",
    "semantic_similarity_score",
    "years_experience_delta",
    "seniority_match",
    "domain_experience_match",
    "career_trajectory_score",
    "activity_recency_score",
    "response_likelihood_score",
    "culture_fit_proxy",
    "tenure_stability",
    "promotion_velocity",
    "industry_switches_norm",
    "education_match",
]


def _normalize_skill(s: str) -> str:
    return s.lower().strip().replace(".", "").replace("-", " ")


def _skill_overlap(candidate_skills: list[str], required: list[str]) -> float:
    if not required:
        return 0.0
    cand_set = {_normalize_skill(s) for s in candidate_skills}
    req_set = {_normalize_skill(s) for s in required}
    # Partial match: check if any word in req appears in any cand skill
    matches = 0
    for req in req_set:
        for cs in cand_set:
            if req in cs or cs in req or any(w in cs for w in req.split()):
                matches += 1
                break
    return matches / len(req_set)


def _years_experience_delta(years: float, exp_range: tuple[int, int]) -> float:
    lo, hi = exp_range
    if lo <= years <= hi:
        return 1.0
    if years < lo:
        return max(0.0, 1.0 - (lo - years) / max(lo, 1))
    return max(0.0, 1.0 - (years - hi) / max(hi, 1))


def _seniority_match(cand_level: str, jd_level: str) -> float:
    c = SENIORITY_ORDER.get(cand_level, 1)
    j = SENIORITY_ORDER.get(jd_level, 1)
    diff = abs(c - j)
    return max(0.0, 1.0 - diff * 0.3)


def _domain_match(career_stages: list[str], domain: str, culture_signals: list[str]) -> float:
    domain_lower = domain.lower()
    score = 0.0
    for stage in career_stages:
        if any(d in stage.lower() for d in domain_lower.split(",")):
            score += 0.5
    for signal in culture_signals:
        if any(s in signal.lower() for s in ["startup", "early", "fast"]):
            if any("startup" in s.lower() or "seed" in s.lower() for s in career_stages):
                score += 0.3
    return min(1.0, score)


def _career_trajectory(career) -> float:
    promo = career.promotion_velocity if career else 0.0
    tenure = career.tenure_stability if career else 0.5
    return min(1.0, (promo * 0.5 + tenure * 0.5))


def _activity_recency(behavioral) -> float:
    if behavioral is None or behavioral.code_activity_recency_days is None:
        return 0.5  # neutral when unavailable (PRD §13)
    days = behavioral.code_activity_recency_days
    return max(0.0, 1.0 - days / 365)


def _response_likelihood(behavioral) -> float:
    if behavioral is None or behavioral.outreach_response_rate is None:
        return 0.5
    return behavioral.outreach_response_rate


def _culture_fit(career_stages: list[str], culture_signals: list[str]) -> float:
    if not culture_signals:
        return 0.5
    matches = 0
    for signal in culture_signals:
        sig = signal.lower()
        for stage in career_stages:
            if sig in stage.lower() or ("startup" in sig and "startup" in stage.lower()):
                matches += 1
                break
    return matches / len(culture_signals)


def compute_features(
    job: JobProfile,
    candidate: CandidateProfile,
    semantic_score: float = 0.0,
    weights: SignalWeights | None = None,
) -> dict[str, float]:
    weights = weights or SignalWeights()
    career = candidate.career
    behavioral = candidate.behavioral

    profile_features = {
        "skill_overlap_must_have": _skill_overlap(candidate.skills, job.must_have_skills),
        "skill_overlap_nice_to_have": _skill_overlap(candidate.skills, job.nice_to_have_skills),
        "skill_overlap_implied": _skill_overlap(candidate.skills, job.implied_skills),
        "semantic_similarity_score": semantic_score,
        "years_experience_delta": _years_experience_delta(career.total_years_experience, job.years_experience_range),
        "seniority_match": _seniority_match(candidate.seniority_level, job.seniority_level),
        "domain_experience_match": _domain_match(career.company_stages, job.domain_context, job.culture_signals),
        "education_match": 0.5,
    }

    career_features = {
        "career_trajectory_score": _career_trajectory(career),
        "tenure_stability": career.tenure_stability,
        "promotion_velocity": min(1.0, career.promotion_velocity),
        "industry_switches_norm": max(0.0, 1.0 - career.industry_switches / 5),
    }

    behavioral_features = {
        "activity_recency_score": _activity_recency(behavioral),
        "response_likelihood_score": _response_likelihood(behavioral),
        "culture_fit_proxy": _culture_fit(career.company_stages, job.culture_signals),
    }

    all_features = {**profile_features, **career_features, **behavioral_features}

    # Apply signal-family weights
    for k in profile_features:
        all_features[k] *= weights.profile
    for k in career_features:
        all_features[k] *= weights.career
    for k in behavioral_features:
        all_features[k] *= weights.behavioral

    # Ensure excluded features never appear
    return {k: v for k, v in all_features.items() if k not in EXCLUDED_FEATURES}


def features_to_vector(features: dict[str, float]) -> list[float]:
    return [features.get(name, 0.0) for name in FEATURE_NAMES]
