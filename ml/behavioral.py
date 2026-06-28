"""Simulated behavioral signals — clearly labeled as synthetic (PRD §6)."""

import random
from typing import Any

SKILL_LANGUAGES = {
    "python": ["Python"],
    "react": ["JavaScript", "TypeScript"],
    "vue": ["JavaScript", "Vue"],
    "java": ["Java"],
    "aws": ["Python", "YAML"],
    "kubernetes": ["Go", "YAML"],
    "sql": ["SQL", "Python"],
    "typescript": ["TypeScript"],
    "node": ["JavaScript", "TypeScript"],
}


def generate_behavioral(skills: list[str], seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    primary_langs = []
    for s in skills:
        for key, langs in SKILL_LANGUAGES.items():
            if key in s.lower():
                primary_langs.extend(langs)
    primary_langs = list(dict.fromkeys(primary_langs))[:5] or ["Python"]

    return {
        "code_activity_recency_days": rng.randint(1, 90),
        "primary_languages": primary_langs,
        "outreach_response_rate": round(rng.uniform(0.3, 0.95), 2),
        "profile_update_recency_days": rng.randint(7, 180),
        "application_to_offer_ratio": round(rng.uniform(0.05, 0.4), 2),
        "endorsement_growth": round(rng.uniform(0.0, 0.3), 2),
        "is_simulated": True,
    }
