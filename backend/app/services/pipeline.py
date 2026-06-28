import hashlib
import time
import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AuditRecord
from app.schemas.profiles import CandidateProfile, JobProfile, SignalWeights
from app.schemas.search import BaselineRanking, FeatureContribution, RankedCandidate, SearchResponse
from app.services.baseline import embedding_baseline, keyword_baseline
from app.services.embeddings import embed_text
from app.services.explain import compute_shap
from app.services.features import compute_features, features_to_vector
from app.services.job_understanding import parse_job_description
from app.services.ranker import get_model_version, score_candidates
from app.services.rerank import rerank_and_explain
from app.services.retrieval import retrieve_candidates

logger = structlog.get_logger()


@dataclass
class PipelineContext:
    search_id: str = field(default_factory=lambda: hashlib.sha256(str(time.time()).encode()).hexdigest()[:16])
    latency_ms: dict[str, float] = field(default_factory=dict)
    degraded: bool = False


async def run_search_pipeline(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    job_text: str,
    location_filter: str | None = None,
    top_k: int | None = None,
    signal_weights: SignalWeights | None = None,
    user_id: uuid.UUID | None = None,
) -> SearchResponse:
    top_k = top_k or settings.final_top_k
    ctx = PipelineContext()
    t0 = time.perf_counter()

    # Stage 1: Job Understanding
    t1 = time.perf_counter()
    job_profile = await parse_job_description(job_text)
    ctx.latency_ms["stage1_jd_parse"] = (time.perf_counter() - t1) * 1000

    # Embed JD
    t2 = time.perf_counter()
    jd_embedding = embed_text(job_text)
    ctx.latency_ms["jd_embedding"] = (time.perf_counter() - t2) * 1000

    # Stage 3: Retrieval
    t3 = time.perf_counter()
    retrieved = await retrieve_candidates(
        session, tenant_id, jd_embedding, job_profile, location_filter
    )
    ctx.latency_ms["stage3_retrieval"] = (time.perf_counter() - t3) * 1000

    # Stage 4 + 5: Features + Ranking
    t4 = time.perf_counter()
    scored_items: list[tuple[str, CandidateProfile, float, dict, list[float]]] = []
    all_for_baseline: list[tuple[str, str, list[str]]] = []
    all_embeddings: list[tuple[str, list[float]]] = []

    for item in retrieved:
        c = item.candidate
        profile_data = c.profile or {}
        cand_profile = CandidateProfile(**profile_data) if profile_data else CandidateProfile(
            name=c.name or "", title=c.title or "", skills=c.skills or []
        )
        features = compute_features(job_profile, cand_profile, item.semantic_score, signal_weights)
        feat_vec = features_to_vector(features)
        scored_items.append((str(c.id), cand_profile, 0.0, features, feat_vec))
        all_for_baseline.append((str(c.id), c.raw_text, cand_profile.skills))
        if c.embedding is not None:
            all_embeddings.append((str(c.id), list(c.embedding)))

    feature_matrix = [item[4] for item in scored_items]
    scores = score_candidates(feature_matrix)
    scored_items = [
        (cid, prof, score, feats, vec)
        for (cid, prof, _, feats, vec), score in zip(scored_items, scores)
    ]
    scored_items.sort(key=lambda x: x[2], reverse=True)
    ctx.latency_ms["stage4_5_features_rank"] = (time.perf_counter() - t4) * 1000

    # Stage 6: LLM Re-rank top-20
    t5 = time.perf_counter()
    top_for_rerank = scored_items[: settings.rerank_top_k]
    rerank_input = [(cid, prof, score, feats) for cid, prof, score, feats, _ in top_for_rerank]
    try:
        reranked = await rerank_and_explain(job_profile, rerank_input, top_k)
    except Exception as e:
        logger.warning("Re-rank degraded", error=str(e))
        ctx.degraded = True
        reranked = [
            {"candidate_id": cid, "rank": i + 1, "score": score, "rationale": None}
            for i, (cid, _, score, _) in enumerate(rerank_input[:top_k])
        ]
    ctx.latency_ms["stage6_rerank"] = (time.perf_counter() - t5) * 1000

    # Build results with SHAP
    t6 = time.perf_counter()
    score_map = {cid: (prof, score, feats, vec) for cid, prof, score, feats, vec in scored_items}
    keyword_top = keyword_baseline(job_profile, all_for_baseline, top_k)
    embedding_top = embedding_baseline(job_text, all_embeddings, top_k) if all_embeddings else []

    results: list[RankedCandidate] = []
    for entry in reranked:
        cid = entry["candidate_id"]
        if cid not in score_map:
            continue
        prof, ml_score, feats, vec = score_map[cid]
        shap = compute_shap(feats, vec)
        results.append(
            RankedCandidate(
                candidate_id=cid,
                rank=entry.get("rank", len(results) + 1),
                name=prof.name,
                title=prof.title,
                score=entry.get("score", ml_score),
                llm_score=entry.get("score"),
                rationale=entry.get("rationale"),
                shap_contributions=[FeatureContribution(**s) for s in shap],
                profile_summary={"skills": prof.skills[:8], "seniority": prof.seniority_level},
                missed_by_keyword=cid not in keyword_top[:5] and entry.get("rank", 99) <= 3,
            )
        )
    ctx.latency_ms["explain"] = (time.perf_counter() - t6) * 1000
    ctx.latency_ms["total"] = (time.perf_counter() - t0) * 1000

    model_version = get_model_version()
    response = SearchResponse(
        search_id=ctx.search_id,
        job_profile=job_profile,
        results=results,
        baseline=BaselineRanking(keyword=keyword_top, embedding=embedding_top),
        latency_ms=ctx.latency_ms,
        model_version=model_version,
        degraded=ctx.degraded,
    )

    # Audit record
    audit = AuditRecord(
        tenant_id=tenant_id,
        user_id=user_id,
        search_id=ctx.search_id,
        job_text_hash=hashlib.sha256(job_text.encode()).hexdigest(),
        job_profile=job_profile.model_dump(),
        model_version=model_version,
        input_summary={"candidate_pool": len(retrieved), "location_filter": location_filter},
        results=[r.model_dump() for r in results],
        latency_ms=ctx.latency_ms,
    )
    session.add(audit)
    await session.flush()

    return response
