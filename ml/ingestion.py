"""Candidate and JD ingestion pipeline."""

import argparse
import csv
import re
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.schemas.profiles import CandidateProfile, CareerMetadata, WorkHistoryEntry
from app.services.embeddings import embed_text
from ml.behavioral import generate_behavioral

DATA_ROOT = Path(__file__).parent.parent / "data" / "raw"
RESUMES_DIR = DATA_ROOT / "resumes"
JDS_DIR = DATA_ROOT / "jobs"
DEFAULT_TENANT = settings.default_tenant_id

# Column mapping for JD CSV (introspecting loader)
JD_TEXT_COLUMNS = ["Job Description", "job_description", "description", "Description", "Job_Description", "JobDescription"]
JD_TITLE_COLUMNS = ["Job Title", "job_title", "title", "Title", "Job_Title"]
JD_COMPANY_COLUMNS = ["Company Name", "company_name", "company", "Company", "Company_Name"]
JD_LOCATION_COLUMNS = ["Location", "location", "Job Location"]
JD_CATEGORY_COLUMNS = ["Category", "category", "Role", "role", "Job Category"]
JD_QUAL_COLUMNS = ["Qualification", "qualification", "Education"]


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    for col in df.columns:
        for cand in candidates:
            if cand.lower() in col.lower():
                return col
    return None


def parse_resume_text(text: str, external_id: str) -> CandidateProfile:
    """Heuristic resume parser — extracts skills, title, experience."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    name = lines[0].split("-")[0].strip() if lines else f"Candidate {external_id}"
    title = ""
    if "-" in lines[0]:
        title = lines[0].split("-", 1)[1].strip()

    skills = []
    skill_match = re.search(r"[Ss]kills?[:\s]+(.+)", text)
    if skill_match:
        skills = [s.strip() for s in re.split(r"[,;|]", skill_match.group(1)) if s.strip()]

    exp_match = re.search(r"(\d+)\+?\s*years?", text, re.I)
    years = float(exp_match.group(1)) if exp_match else 3.0

    seniority = "senior" if years >= 5 else "mid" if years >= 2 else "junior"
    if "staff" in text.lower() or "principal" in text.lower():
        seniority = "staff"

    work_history = []
    if "startup" in text.lower() or "series" in text.lower():
        work_history.append(WorkHistoryEntry(title=title or "Engineer", company="Startup", duration_months=24, company_stage="Series B", industry="fintech"))

    career = CareerMetadata(
        work_history=work_history,
        total_years_experience=years,
        promotion_velocity=min(1.0, years / 10),
        tenure_stability=0.7,
        industry_switches=1,
        company_stages=["Series B startup"] if "startup" in text.lower() else ["Enterprise"],
    )

    behavioral = generate_behavioral(skills, seed=hash(external_id) % 2**31)

    return CandidateProfile(
        name=name,
        title=title,
        skills=skills,
        seniority_level=seniority,
        career=career,
        behavioral=behavioral,
        summary=text[:500],
    )


def extract_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore")


def load_resumes(session: Session, limit: int | None = None) -> int:
    count = 0
    files = list(RESUMES_DIR.glob("**/*.pdf")) + list(RESUMES_DIR.glob("**/*.txt"))
    if limit:
        files = files[:limit]

    for fpath in files:
        external_id = fpath.stem
        if fpath.suffix == ".pdf":
            raw = extract_pdf_text(fpath)
            source = "kaggle"
        else:
            raw = fpath.read_text(encoding="utf-8", errors="ignore")
            source = "synthetic" if external_id.startswith("syn_") else "kaggle"

        if len(raw.strip()) < 20:
            continue

        profile = parse_resume_text(raw, external_id)
        embedding = embed_text(raw)
        emb_str = "[" + ",".join(str(x) for x in embedding) + "]"

        session.execute(
            text("""
                INSERT INTO candidates (id, tenant_id, external_id, name, title, raw_text, profile,
                    embedding, skills, years_experience, seniority_level, career_metadata, behavioral, data_source)
                VALUES (CAST(:id AS uuid), CAST(:tenant_id AS uuid), :external_id, :name, :title, :raw_text,
                    CAST(:profile AS jsonb), CAST(:embedding AS vector), CAST(:skills AS jsonb),
                    :years, :seniority, CAST(:career AS jsonb), CAST(:behavioral AS jsonb), :source)
            """),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": DEFAULT_TENANT,
                "external_id": external_id,
                "name": profile.name,
                "title": profile.title,
                "raw_text": raw,
                "profile": profile.model_dump_json(),
                "embedding": emb_str,
                "skills": __import__("json").dumps(profile.skills),
                "years": profile.career.total_years_experience,
                "seniority": profile.seniority_level,
                "career": profile.career.model_dump_json(),
                "behavioral": profile.behavioral.model_dump_json(),
                "source": source,
            },
        )
        count += 1

    session.commit()
    return count


def load_jobs(session: Session, limit: int | None = None) -> int:
    csv_files = list(JDS_DIR.glob("**/*.csv"))
    if not csv_files:
        print("No JD CSV files found in", JDS_DIR)
        return 0

    count = 0
    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        print(f"JD CSV columns ({csv_path.name}): {list(df.columns)}")

        text_col = _find_column(df, JD_TEXT_COLUMNS)
        title_col = _find_column(df, JD_TITLE_COLUMNS)
        company_col = _find_column(df, JD_COMPANY_COLUMNS)
        location_col = _find_column(df, JD_LOCATION_COLUMNS)
        category_col = _find_column(df, JD_CATEGORY_COLUMNS)

        if not text_col:
            # Use first long text column
            for col in df.columns:
                if df[col].dtype == object and df[col].str.len().mean() > 100:
                    text_col = col
                    break

        if not text_col:
            print(f"Skipping {csv_path}: no description column found")
            continue

        rows = df.head(limit) if limit else df
        for _, row in rows.iterrows():
            raw = str(row.get(text_col, ""))
            if len(raw.strip()) < 50:
                continue
            title = str(row.get(title_col, "Job Opening")) if title_col else "Job Opening"
            company = str(row.get(company_col, "")) if company_col else None
            location = str(row.get(location_col, "")) if location_col else None
            category = str(row.get(category_col, "tech")) if category_col else "tech"

            embedding = embed_text(raw)
            emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
            jd_hash = __import__("hashlib").sha256(raw.encode()).hexdigest()

            session.execute(
                text("""
                    INSERT INTO jobs (id, tenant_id, title, company, location, category, raw_text, jd_hash, embedding)
                    VALUES (CAST(:id AS uuid), CAST(:tenant_id AS uuid), :title, :company, :location, :category,
                        :raw_text, :jd_hash, CAST(:embedding AS vector))
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": DEFAULT_TENANT,
                    "title": title,
                    "company": company,
                    "location": location,
                    "category": category,
                    "raw_text": raw,
                    "jd_hash": jd_hash,
                    "embedding": emb_str,
                },
            )
            count += 1

    session.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--resumes-only", action="store_true")
    parser.add_argument("--jobs-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.seed_only:
        from scripts.prepare_data import create_synthetic_seed
        create_synthetic_seed()

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        if not args.jobs_only:
            n = load_resumes(session, args.limit)
            print(f"Ingested {n} candidates")
        if not args.resumes_only:
            n = load_jobs(session, args.limit)
            print(f"Ingested {n} jobs")


if __name__ == "__main__":
    main()
