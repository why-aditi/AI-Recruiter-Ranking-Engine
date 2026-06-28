import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.profiles import CandidateProfile, CareerMetadata, JobProfile
from app.services.features import compute_features, FEATURE_NAMES
from app.services.fairness import EXCLUDED_FEATURES


def test_feature_computation():
    job = JobProfile(
        must_have_skills=["Python", "PostgreSQL", "AWS"],
        nice_to_have_skills=["Kubernetes"],
        seniority_level="senior",
        years_experience_range=(4, 7),
        domain_context="fintech",
        culture_signals=["fast-paced", "startup"],
    )
    candidate = CandidateProfile(
        name="Test",
        skills=["Python", "PostgreSQL", "AWS", "Docker"],
        seniority_level="senior",
        career=CareerMetadata(total_years_experience=6, company_stages=["Series B startup"]),
    )
    features = compute_features(job, candidate, semantic_score=0.8)
    assert "skill_overlap_must_have" in features
    assert features["skill_overlap_must_have"] > 0.5
    assert features["semantic_similarity_score"] == 0.8


def test_excluded_features_not_in_vector():
    for name in FEATURE_NAMES:
        assert name not in EXCLUDED_FEATURES


def test_feature_names_count():
    assert len(FEATURE_NAMES) >= 10
