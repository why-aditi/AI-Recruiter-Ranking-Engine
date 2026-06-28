"""Kaggle data preparation for resumes and job descriptions."""

import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path

DATA_ROOT = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_ROOT / "raw"
RESUMES_DIR = RAW_DIR / "resumes"
JDS_DIR = RAW_DIR / "jobs"

RESUME_DATASET = "hadikp/resume-data-pdf"
JD_DATASET = "adityarajsrv/job-descriptions-2025-tech-and-non-tech-roles"


def download_kaggle(dataset: str, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset, "-p", str(dest), "--unzip"],
            check=True,
            capture_output=True,
        )
        print(f"Downloaded {dataset} -> {dest}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Kaggle download failed for {dataset}: {e}")
        return False


def extract_zip(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for zf in src.glob("*.zip"):
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(dest)
        print(f"Extracted {zf} -> {dest}")


def create_synthetic_seed() -> None:
    """Create minimal synthetic data when Kaggle datasets are unavailable."""
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    JDS_DIR.mkdir(parents=True, exist_ok=True)

    synthetic_resumes = [
        {
            "id": "syn_001",
            "name": "Alex Chen",
            "title": "Senior Backend Engineer",
            "text": """Alex Chen - Senior Backend Engineer
Skills: Python, FastAPI, PostgreSQL, AWS, Kubernetes, Docker, Redis
Experience: 6 years building fintech payment systems at Series B startup.
Previously at early-stage startup handling high-throughput transaction processing.
Led team of 4 engineers. Strong in ambiguous, fast-paced environments.""",
            "category": "tech",
        },
        {
            "id": "syn_002",
            "name": "Jordan Rivera",
            "title": "Full Stack Developer",
            "text": """Jordan Rivera - Full Stack Developer
Skills: Vue.js, React, Node.js, TypeScript, GraphQL, MongoDB
Experience: 5 years. Deep Vue.js expertise with adjacent React exposure.
Built e-commerce platforms. Comfortable ramping quickly on new frameworks.""",
            "category": "tech",
        },
        {
            "id": "syn_003",
            "name": "Sam Patel",
            "title": "Data Engineer",
            "text": """Sam Patel - Data Engineer
Skills: Python, Spark, Airflow, SQL, AWS, Kafka, dbt
Experience: 7 years in data pipeline engineering for healthcare analytics.
Strong SQL and Python. Experience with regulated data environments.""",
            "category": "tech",
        },
        {
            "id": "syn_004",
            "name": "Taylor Kim",
            "title": "DevOps Engineer",
            "text": """Taylor Kim - DevOps Engineer
Skills: Kubernetes, Terraform, AWS, CI/CD, Python, Prometheus, Grafana
Experience: 4 years automating infrastructure at growth-stage SaaS company.
Built deployment pipelines reducing release time by 60%.""",
            "category": "tech",
        },
        {
            "id": "syn_005",
            "name": "Morgan Lee",
            "title": "Frontend Engineer",
            "text": """Morgan Lee - Frontend Engineer
Skills: React, TypeScript, Next.js, Tailwind CSS, Webpack, Jest
Experience: 3 years building recruiter-facing dashboards and data visualization tools.
Strong UX sensibility and performance optimization.""",
            "category": "tech",
        },
    ]

    for r in synthetic_resumes:
        path = RESUMES_DIR / f"{r['id']}.txt"
        if not path.exists():
            path.write_text(r["text"], encoding="utf-8")

    import csv

    jd_path = JDS_DIR / "synthetic_jobs.csv"
    if not jd_path.exists():
        rows = [
            {
                "Job Title": "Senior Backend Engineer",
                "Role": "Engineering",
                "Company Name": "FinStart Inc",
                "Location": "San Francisco, CA",
                "Qualification": "B.Tech",
                "Category": "tech",
                "Job Description": """We are a fast-paced fintech startup seeking a Senior Backend Engineer.
Must have: Python, PostgreSQL, AWS, 5+ years experience.
Nice to have: Kubernetes, Redis, payment systems experience.
Must thrive in ambiguity and lead small teams. Series B-D startup experience preferred.
Culture: high ownership, fast-paced, collaborative.""",
            },
            {
                "Job Title": "React Frontend Developer",
                "Role": "Engineering",
                "Company Name": "TechCorp",
                "Location": "Remote",
                "Qualification": "B.S. Computer Science",
                "Category": "tech",
                "Job Description": """Looking for a React developer with 3+ years experience.
Required: React, TypeScript, CSS. Nice: Next.js, GraphQL.
Must be comfortable with Vue.js developers transitioning to React stack.""",
            },
            {
                "Job Title": "Data Engineer",
                "Role": "Data",
                "Company Name": "HealthAnalytics",
                "Location": "Boston, MA",
                "Qualification": "M.Tech",
                "Category": "tech",
                "Job Description": """Data Engineer for healthcare analytics platform.
Must have: Python, Spark, SQL, Airflow. 4-7 years experience.
Experience with regulated/healthcare data is a plus.""",
            },
        ]
        with open(jd_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"Synthetic seed created in {RAW_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Prepare Kaggle datasets")
    parser.add_argument("--seed-only", action="store_true", help="Only create synthetic seed data")
    parser.add_argument("--resumes-only", action="store_true")
    parser.add_argument("--jobs-only", action="store_true")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if args.seed_only:
        create_synthetic_seed()
        return

    create_synthetic_seed()

    if not args.jobs_only:
        RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        if not any(RESUMES_DIR.iterdir()) if RESUMES_DIR.exists() else True:
            download_kaggle(RESUME_DATASET, RESUMES_DIR)

    if not args.resumes_only:
        JDS_DIR.mkdir(parents=True, exist_ok=True)
        if not any(JDS_DIR.glob("*.csv")):
            download_kaggle(JD_DATASET, JDS_DIR)

    print("Data preparation complete.")
    print(f"  Resumes: {RESUMES_DIR}")
    print(f"  Jobs:    {JDS_DIR}")


if __name__ == "__main__":
    main()
