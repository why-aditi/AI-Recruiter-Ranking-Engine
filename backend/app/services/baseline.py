"""Baseline A (keyword) and Baseline B (embedding cosine) rankings."""

import re

from app.schemas.profiles import JobProfile
from app.services.embeddings import cosine_similarity, embed_text


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z+#.]{2,}", text.lower()))


def keyword_baseline(
    job_profile: JobProfile,
    candidates: list[tuple[str, str, list[str]]],
    top_k: int = 10,
) -> list[str]:
    """Baseline A: pure keyword/ATS-style filter match."""
    keywords = set()
    for skills in [job_profile.must_have_skills, job_profile.nice_to_have_skills]:
        for s in skills:
            keywords.update(_tokenize(s))
    keywords.update(_tokenize(job_profile.domain_context))

    scored = []
    for cid, raw_text, skills in candidates:
        cand_tokens = _tokenize(raw_text) | {_tokenize(s) for s in skills}
        flat_tokens = set()
        for t in cand_tokens:
            if isinstance(t, set):
                flat_tokens |= t
            else:
                flat_tokens.add(t)
        overlap = len(keywords & flat_tokens)
        scored.append((cid, overlap))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored[:top_k]]


def embedding_baseline(
    jd_text: str,
    candidates: list[tuple[str, list[float]]],
    top_k: int = 10,
) -> list[str]:
    """Baseline B: pure embedding cosine similarity."""
    jd_emb = embed_text(jd_text)
    scored = [(cid, cosine_similarity(jd_emb, emb)) for cid, emb in candidates if emb]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored[:top_k]]
