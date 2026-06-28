from typing import Literal

from pydantic import BaseModel, Field


class JobProfile(BaseModel):
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    implied_skills: list[str] = Field(default_factory=list)
    seniority_level: Literal["junior", "mid", "senior", "staff", "principal"] = "mid"
    years_experience_range: tuple[int, int] = (2, 8)
    domain_context: str = ""
    soft_requirements: list[str] = Field(default_factory=list)
    deal_breakers: list[str] = Field(default_factory=list)
    culture_signals: list[str] = Field(default_factory=list)
    location: str | None = None
    work_authorization: str | None = None


class WorkHistoryEntry(BaseModel):
    title: str = ""
    company: str = ""
    duration_months: int = 0
    company_stage: str | None = None
    industry: str | None = None


class CareerMetadata(BaseModel):
    work_history: list[WorkHistoryEntry] = Field(default_factory=list)
    total_years_experience: float = 0.0
    promotion_velocity: float = 0.0
    tenure_stability: float = 0.0
    industry_switches: int = 0
    employment_gaps_months: int = 0
    company_stages: list[str] = Field(default_factory=list)


class BehavioralSignals(BaseModel):
    code_activity_recency_days: int | None = None
    primary_languages: list[str] = Field(default_factory=list)
    outreach_response_rate: float | None = None
    profile_update_recency_days: int | None = None
    application_to_offer_ratio: float | None = None
    endorsement_growth: float | None = None
    is_simulated: bool = True


class CandidateProfile(BaseModel):
    name: str = ""
    title: str = ""
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    seniority_level: Literal["junior", "mid", "senior", "staff", "principal"] = "mid"
    location: str | None = None
    career: CareerMetadata = Field(default_factory=CareerMetadata)
    behavioral: BehavioralSignals = Field(default_factory=BehavioralSignals)
    summary: str = ""


class SignalWeights(BaseModel):
    profile: float = 1.0
    career: float = 1.0
    behavioral: float = 1.0
