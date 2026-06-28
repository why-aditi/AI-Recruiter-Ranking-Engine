"use client";

import { useState } from "react";
import type { JobProfile, RankedCandidate, SearchResponse } from "@/lib/api";
import { searchCandidates, submitFeedback } from "@/lib/api";

const SAMPLE_JD = `Senior Backend Engineer — FinStart Inc (Series B Fintech)

We're a fast-paced fintech startup building next-gen payment infrastructure.
Must thrive in ambiguity and lead small teams.

Requirements:
- 5+ years Python, PostgreSQL, AWS
- Experience with high-throughput payment systems
- Kubernetes and Redis nice-to-have

Culture: high ownership, fast-paced, collaborative. Series B-D startup experience strongly preferred.`;

export default function HomePage() {
  const [jd, setJd] = useState(SAMPLE_JD);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [selected, setSelected] = useState<RankedCandidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [weights, setWeights] = useState({ profile: 1, career: 1, behavioral: 1 });
  const [elapsed, setElapsed] = useState(0);

  async function handleSearch() {
    setLoading(true);
    setError(null);
    setSelected(null);
    const t0 = Date.now();
    const timer = setInterval(() => setElapsed(Date.now() - t0), 50);
    try {
      const data = await searchCandidates(jd, weights);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      clearInterval(timer);
      setElapsed(Date.now() - t0);
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      {/* Left: JD Input */}
      <div className="lg:col-span-5 space-y-4">
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Job Description
          </h2>
          <textarea
            className="h-64 w-full resize-none rounded-lg border border-neutral-200 p-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste your job description..."
          />
          <div className="mt-4 space-y-3">
            <WeightSlider label="Profile signals" value={weights.profile} onChange={(v) => setWeights({ ...weights, profile: v })} />
            <WeightSlider label="Career metadata" value={weights.career} onChange={(v) => setWeights({ ...weights, career: v })} />
            <WeightSlider label="Behavioral signals" value={weights.behavioral} onChange={(v) => setWeights({ ...weights, behavioral: v })} />
          </div>
          <button className="btn-primary mt-4 w-full" onClick={handleSearch} disabled={loading || jd.length < 50}>
            {loading ? `Searching... ${elapsed}ms` : "Rank Candidates"}
          </button>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>

        {result && (
          <JobProfileCard profile={result.job_profile} latency={result.latency_ms} model={result.model_version} degraded={result.degraded} />
        )}
      </div>

      {/* Center: Results */}
      <div className="lg:col-span-4">
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
              Ranked Shortlist
            </h2>
            {result && (
              <span className="text-xs text-neutral-400">
                {(result.latency_ms.total ?? elapsed).toFixed(0)}ms total
              </span>
            )}
          </div>
          {!result && !loading && (
            <p className="py-12 text-center text-sm text-neutral-400">
              Paste a JD and click Rank to see your top-10 shortlist
            </p>
          )}
          {loading && (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg bg-neutral-100" />
              ))}
            </div>
          )}
          {result && (
            <ul className="space-y-2">
              {result.results.map((c) => (
                <li
                  key={c.candidate_id}
                  className={`cursor-pointer rounded-lg border p-3 transition hover:border-brand-500 ${
                    selected?.candidate_id === c.candidate_id ? "border-brand-500 bg-brand-50" : "border-neutral-100"
                  }`}
                  onClick={() => setSelected(c)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="mr-2 text-xs font-bold text-brand-600">#{c.rank}</span>
                      <span className="font-medium">{c.name || "Candidate"}</span>
                      {c.missed_by_keyword && (
                        <span className="ml-2 badge bg-emerald-100 text-emerald-700">Missed gem</span>
                      )}
                      <p className="text-xs text-neutral-500">{c.title}</p>
                    </div>
                    <span className="text-sm font-mono text-brand-600">{(c.score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="mt-2 flex gap-1">
                    <FeedbackBtn positive onClick={() => submitFeedback(c.candidate_id, true, result.search_id)} />
                    <FeedbackBtn positive={false} onClick={() => submitFeedback(c.candidate_id, false, result.search_id)} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Right: Detail + Baseline */}
      <div className="lg:col-span-3 space-y-4">
        {selected && <CandidateDetail candidate={selected} />}
        {result && <BaselinePanel result={result} />}
      </div>
    </div>
  );
}

function WeightSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-neutral-500">
        <span>{label}</span>
        <span>{value.toFixed(1)}x</span>
      </div>
      <input type="range" min={0} max={2} step={0.1} value={value} onChange={(e) => onChange(+e.target.value)} className="w-full" />
    </div>
  );
}

function JobProfileCard({ profile, latency, model, degraded }: { profile: JobProfile; latency: Record<string, number>; model: string; degraded: boolean }) {
  return (
    <div className="card">
      <h3 className="mb-2 text-sm font-semibold">Extracted JobProfile</h3>
      {degraded && <p className="mb-2 text-xs text-amber-600">LLM degraded — Stage-5 ranking used</p>}
      <div className="space-y-2 text-xs">
        <TagRow label="Must-have" tags={profile.must_have_skills} color="red" />
        <TagRow label="Nice-to-have" tags={profile.nice_to_have_skills} color="blue" />
        <TagRow label="Implied" tags={profile.implied_skills} color="purple" />
        <p><span className="text-neutral-500">Seniority:</span> {profile.seniority_level}</p>
        <p><span className="text-neutral-500">Experience:</span> {profile.years_experience_range[0]}-{profile.years_experience_range[1]} yrs</p>
        <TagRow label="Culture" tags={profile.culture_signals} color="green" />
      </div>
      <div className="mt-3 border-t pt-2 text-[10px] text-neutral-400">
        Model: {model} | Stages: {Object.entries(latency).map(([k, v]) => `${k.replace("stage", "S")}:${v.toFixed(0)}ms`).join(" ")}
      </div>
    </div>
  );
}

function TagRow({ label, tags, color }: { label: string; tags: string[]; color: string }) {
  const colors: Record<string, string> = {
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
    purple: "bg-purple-100 text-purple-700",
    green: "bg-green-100 text-green-700",
  };
  return (
    <div>
      <span className="text-neutral-500">{label}: </span>
      {tags.slice(0, 6).map((t) => (
        <span key={t} className={`badge mr-1 ${colors[color]}`}>{t}</span>
      ))}
    </div>
  );
}

function CandidateDetail({ candidate }: { candidate: RankedCandidate }) {
  const maxShap = Math.max(...candidate.shap_contributions.map((s) => Math.abs(s.shap_value)), 0.01);
  return (
    <div className="card">
      <h3 className="mb-2 font-semibold">{candidate.name}</h3>
      <p className="mb-3 text-xs text-neutral-500">{candidate.rationale}</p>
      <h4 className="mb-2 text-xs font-semibold uppercase text-neutral-400">SHAP Attribution</h4>
      <div className="space-y-1.5">
        {candidate.shap_contributions.map((s) => (
          <div key={s.feature} className="flex items-center gap-2 text-xs">
            <span className="w-32 truncate text-neutral-500">{s.feature.replace(/_/g, " ")}</span>
            <div className="h-2 flex-1 rounded bg-neutral-100">
              <div
                className={`h-2 rounded ${s.shap_value >= 0 ? "bg-emerald-500" : "bg-red-400"}`}
                style={{ width: `${(Math.abs(s.shap_value) / maxShap) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BaselinePanel({ result }: { result: SearchResponse }) {
  const ourTop = result.results.slice(0, 5).map((r) => r.candidate_id);
  const kwTop = result.baseline.keyword.slice(0, 5);
  const gems = result.results.filter((r) => r.missed_by_keyword && r.rank <= 3);

  return (
    <div className="card">
      <h3 className="mb-2 text-sm font-semibold">Baseline Comparison</h3>
      <div className="space-y-3 text-xs">
        <div>
          <p className="mb-1 font-medium text-brand-600">Our Ranking (top 5)</p>
          {ourTop.map((id, i) => {
            const c = result.results.find((r) => r.candidate_id === id);
            return <p key={id}>#{i + 1} {c?.name || id.slice(0, 8)}</p>;
          })}
        </div>
        <div>
          <p className="mb-1 font-medium text-red-500">Keyword Baseline (top 5)</p>
          {kwTop.map((id, i) => {
            const c = result.results.find((r) => r.candidate_id === id);
            return <p key={id}>#{i + 1} {c?.name || id.slice(0, 8)}</p>;
          })}
        </div>
        {gems.length > 0 && (
          <div className="rounded-lg bg-emerald-50 p-2">
            <p className="font-medium text-emerald-700">Missed by keyword filter:</p>
            {gems.map((g) => (
              <p key={g.candidate_id}>{g.name} — #{g.rank}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FeedbackBtn({ positive, onClick }: { positive: boolean; onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={`rounded px-2 py-0.5 text-xs ${positive ? "hover:bg-green-100" : "hover:bg-red-100"}`}
      title={positive ? "Good match" : "Poor match"}
    >
      {positive ? "👍" : "👎"}
    </button>
  );
}
