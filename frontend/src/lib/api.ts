const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface JobProfile {
  must_have_skills: string[];
  nice_to_have_skills: string[];
  implied_skills: string[];
  seniority_level: string;
  years_experience_range: [number, number];
  domain_context: string;
  soft_requirements: string[];
  deal_breakers: string[];
  culture_signals: string[];
}

export interface RankedCandidate {
  candidate_id: string;
  rank: number;
  name: string | null;
  title: string | null;
  score: number;
  rationale: string | null;
  shap_contributions: { feature: string; value: number; shap_value: number }[];
  profile_summary: { skills?: string[]; seniority?: string };
  missed_by_keyword: boolean;
}

export interface SearchResponse {
  search_id: string;
  job_profile: JobProfile;
  results: RankedCandidate[];
  baseline: { keyword: string[]; embedding: string[] };
  latency_ms: Record<string, number>;
  model_version: string;
  degraded: boolean;
}

export interface JobListing {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  category: string | null;
  raw_text: string;
}

export async function searchCandidates(
  jobText: string,
  weights?: { profile: number; career: number; behavioral: number }
): Promise<SearchResponse> {
  const res = await fetch(`${API}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_text: jobText,
      signal_weights: weights,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJobs(): Promise<JobListing[]> {
  const res = await fetch(`${API}/api/v1/jobs`);
  if (!res.ok) return [];
  return res.json();
}

export async function submitFeedback(
  candidateId: string,
  isPositive: boolean,
  searchId?: string
) {
  await fetch(`${API}/api/v1/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId, is_positive: isPositive, search_id: searchId }),
  });
}
