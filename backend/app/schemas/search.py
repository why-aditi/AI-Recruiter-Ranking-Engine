from pydantic import BaseModel, Field

from app.schemas.profiles import JobProfile, SignalWeights


class SearchRequest(BaseModel):
    job_text: str = Field(..., min_length=50)
    job_id: str | None = None
    location_filter: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    signal_weights: SignalWeights | None = None


class FeatureContribution(BaseModel):
    feature: str
    value: float
    shap_value: float


class RankedCandidate(BaseModel):
    candidate_id: str
    rank: int
    name: str | None
    title: str | None
    score: float
    llm_score: float | None = None
    rationale: str | None = None
    shap_contributions: list[FeatureContribution] = Field(default_factory=list)
    profile_summary: dict = Field(default_factory=dict)
    missed_by_keyword: bool = False


class BaselineRanking(BaseModel):
    keyword: list[str] = Field(default_factory=list)
    embedding: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    search_id: str
    job_profile: JobProfile
    results: list[RankedCandidate]
    baseline: BaselineRanking
    latency_ms: dict[str, float]
    model_version: str
    degraded: bool = False


class FeedbackRequest(BaseModel):
    candidate_id: str
    is_positive: bool
    search_id: str | None = None
    job_id: str | None = None


class CandidateDetail(BaseModel):
    id: str
    name: str | None
    title: str | None
    location: str | None
    profile: dict
    data_source: str
    career_metadata: dict | None = None
    behavioral: dict | None = None
