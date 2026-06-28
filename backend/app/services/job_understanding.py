import json

from app.schemas.profiles import JobProfile
from app.services.llm_gateway import llm_gateway

JD_PARSE_SYSTEM = """You are an expert technical recruiter. Parse the job description into structured JSON.
Capture explicit requirements AND implied/inferred signals (e.g., "thrives in ambiguity" implies early-stage startup experience).
Return JSON with keys: must_have_skills, nice_to_have_skills, implied_skills, seniority_level (junior|mid|senior|staff|principal),
years_experience_range [min, max], domain_context, soft_requirements, deal_breakers, culture_signals, location, work_authorization."""


async def parse_job_description(jd_text: str) -> JobProfile:
    jd_hash = llm_gateway.jd_hash(jd_text)
    cache_key = f"parse:{jd_hash}"
    raw = await llm_gateway.chat_json(
        system=JD_PARSE_SYSTEM,
        user=f"Job Description:\n\n{jd_text}",
        cache_key=cache_key,
    )
    years = raw.get("years_experience_range", [2, 8])
    if isinstance(years, list) and len(years) >= 2:
        years_tuple = (int(years[0]), int(years[1]))
    else:
        years_tuple = (2, 8)

    seniority = raw.get("seniority_level", "mid")
    if seniority not in ("junior", "mid", "senior", "staff", "principal"):
        seniority = "mid"

    return JobProfile(
        must_have_skills=raw.get("must_have_skills", []),
        nice_to_have_skills=raw.get("nice_to_have_skills", []),
        implied_skills=raw.get("implied_skills", []),
        seniority_level=seniority,
        years_experience_range=years_tuple,
        domain_context=raw.get("domain_context", ""),
        soft_requirements=raw.get("soft_requirements", []),
        deal_breakers=raw.get("deal_breakers", []),
        culture_signals=raw.get("culture_signals", []),
        location=raw.get("location"),
        work_authorization=raw.get("work_authorization"),
    )
