import json
import logging

from app.schemas.profiles import CandidateProfile, JobProfile
from app.services.llm_gateway import llm_gateway

logger = logging.getLogger(__name__)

RERANK_SYSTEM = """You are a senior technical recruiter performing final candidate ranking.
Given a job profile and top candidates with their ML scores and feature summaries,
re-rank them and provide a specific, feature-grounded justification for each (2-3 sentences).
Return JSON: {"rankings": [{"candidate_id": "...", "rank": 1, "score": 0.95, "rationale": "..."}]}"""


async def rerank_and_explain(
    job_profile: JobProfile,
    candidates: list[tuple[str, CandidateProfile, float, dict]],
    top_k: int = 10,
) -> list[dict]:
    if not candidates:
        return []

    payload = {
        "job_profile": job_profile.model_dump(),
        "candidates": [
            {
                "candidate_id": cid,
                "name": profile.name,
                "title": profile.title,
                "skills": profile.skills[:10],
                "ml_score": score,
                "features": {k: round(v, 3) for k, v in list(features.items())[:8]},
            }
            for cid, profile, score, features in candidates
        ],
    }

    try:
        result = await llm_gateway.chat_json(
            system=RERANK_SYSTEM,
            user=json.dumps(payload, indent=2),
        )
        rankings = result.get("rankings", [])
        if rankings:
            return rankings[:top_k]
    except Exception as e:
        logger.warning("LLM re-rank failed, using Stage-5 order: %s", e)

    # Fallback: keep Stage-5 order with template rationale
    return [
        {
            "candidate_id": cid,
            "rank": i + 1,
            "score": score,
            "rationale": _template_rationale(profile, job_profile, features),
        }
        for i, (cid, profile, score, features) in enumerate(candidates[:top_k])
    ]


def _template_rationale(profile: CandidateProfile, job: JobProfile, features: dict) -> str:
    top_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:3]
    feat_str = ", ".join(f"{k.replace('_', ' ')} ({v:.0%})" for k, v in top_features)
    return (
        f"{profile.name or 'Candidate'} ranked highly due to strong alignment on {feat_str}. "
        f"Skills include {', '.join(profile.skills[:5]) or 'relevant experience'} "
        f"matching the {job.seniority_level} {job.domain_context or 'role'} requirements."
    )
