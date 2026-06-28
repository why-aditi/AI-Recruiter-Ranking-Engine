"""LLM-as-judge label generation for (JD, candidate) pairs."""

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.services.llm_gateway import llm_gateway

JUDGE_SYSTEM = """You are an expert recruiter evaluating candidate-job fit.
Score the candidate's relevance to the job on a 0-3 scale:
0 = not relevant, 1 = weak fit, 2 = good fit, 3 = excellent fit.
Return JSON: {"score": N, "reason": "brief explanation"}"""

HAND_LABELS_PATH = Path(__file__).parent.parent / "data" / "hand_labels.csv"


async def judge_pair(jd_text: str, candidate_text: str) -> dict:
    user = f"Job Description:\n{jd_text[:2000]}\n\nCandidate Resume:\n{candidate_text[:2000]}"
    try:
        result = await llm_gateway.chat_json(system=JUDGE_SYSTEM, user=user)
        return {"score": int(result.get("score", 1)), "reason": result.get("reason", "")}
    except Exception:
        # Heuristic fallback
        jd_tokens = set(jd_text.lower().split())
        cand_tokens = set(candidate_text.lower().split())
        overlap = len(jd_tokens & cand_tokens) / max(len(jd_tokens), 1)
        score = min(3, int(overlap * 10))
        return {"score": score, "reason": "heuristic overlap"}


async def generate_labels(session: Session, max_pairs: int = 200) -> pd.DataFrame:
    jobs = session.execute(text("SELECT id, raw_text FROM jobs LIMIT 20")).fetchall()
    candidates = session.execute(text("SELECT id, raw_text FROM candidates LIMIT 50")).fetchall()

    if not jobs or not candidates:
        print("Need jobs and candidates in DB first. Run ingestion.")
        return pd.DataFrame()

    pairs = []
    for job in jobs:
        for cand in random.sample(candidates, min(10, len(candidates))):
            pairs.append((str(job.id), job.raw_text, str(cand.id), cand.raw_text))

    random.shuffle(pairs)
    pairs = pairs[:max_pairs]

    labels = []
    for i, (jid, jd, cid, ct) in enumerate(pairs):
        result = await judge_pair(jd, ct)
        labels.append({
            "job_id": jid,
            "candidate_id": cid,
            "label": result["score"],
            "reason": result["reason"],
        })
        if (i + 1) % 10 == 0:
            print(f"Labeled {i + 1}/{len(pairs)} pairs")

    df = pd.DataFrame(labels)
    out = Path(__file__).parent.parent / "data" / "labels.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} labels to {out}")
    return df


def create_hand_labels_template():
    HAND_LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HAND_LABELS_PATH.exists():
        pd.DataFrame(columns=["job_id", "candidate_id", "label", "annotator"]).to_csv(HAND_LABELS_PATH, index=False)
        print(f"Created hand labels template at {HAND_LABELS_PATH}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pairs", type=int, default=100)
    args = parser.parse_args()

    create_hand_labels_template()
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        await generate_labels(session, args.max_pairs)


if __name__ == "__main__":
    asyncio.run(main())
