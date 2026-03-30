"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Job } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";

const PLATFORMS = ["all", "linkedin", "indeed", "naukri", "internshala", "glassdoor"];
const JOB_TYPES = ["all", "full-time", "part-time", "contract", "internship"];
const STATUSES = ["discovered", "bookmarked", "applied", "interviewing", "offered", "accepted", "rejected", "skipped"];

export default function JobsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [platform, setPlatform] = useState("all");
  const [jobType, setJobType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    api.getJobs({
      platform: platform === "all" ? undefined : platform,
      job_type: jobType === "all" ? undefined : jobType,
    }).then(setJobs).catch(() => {}).finally(() => setLoading(false));
  }, [user, platform, jobType]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (jobId: string, status: string) => {
    try { await api.updateJobStatus(jobId, status); load(); } catch {}
  };

  const formatSalary = (min: number | null, max: number | null) => {
    if (!min && !max) return null;
    const fmt = (n: number) => `$${Math.round(n / 1000)}k`;
    if (min && max) return `${fmt(min)} - ${fmt(max)}`;
    if (min) return `${fmt(min)}+`;
    return `Up to ${fmt(max!)}`;
  };

  // Extract skills from job description (simple keyword extraction)
  const extractSkills = (desc: string | null): string[] => {
    if (!desc) return [];
    const knownSkills = [
      "Python", "JavaScript", "TypeScript", "React", "Node.js", "Next.js", "Vue",
      "Angular", "Django", "FastAPI", "Flask", "Express", "Spring", "Java", "Go",
      "Rust", "C++", "C#", ".NET", "Ruby", "Rails", "PHP", "Laravel", "Swift",
      "Kotlin", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
      "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL", "REST", "API",
      "Machine Learning", "AI", "ML", "NLP", "Deep Learning", "TensorFlow",
      "PyTorch", "Pandas", "NumPy", "SQL", "NoSQL", "Git", "CI/CD", "DevOps",
      "Linux", "Agile", "Scrum", "HTML", "CSS", "Tailwind", "Figma",
      "Blockchain", "Solidity", "Web3", "React Native", "Flutter", "Dart",
      "Shopify", "WordPress", "SEO", "ETL", "Kafka", "Spark", "Airflow",
      "Snowflake", "dbt", "Power BI", "Tableau", "Excel", "Selenium",
      "Playwright", "Jest", "Cypress", "Microservices", "Serverless",
    ];
    const descLower = desc.toLowerCase();
    return knownSkills.filter((s) => descLower.includes(s.toLowerCase()));
  };

  const toggle = (id: string) => setExpandedId(expandedId === id ? null : id);

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
        {!loading && jobs.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-blue-600 px-3 py-1 text-sm font-semibold text-white">
            {jobs.length} found
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-500">Employment opportunities matched by AI</p>

      <div className="mt-4 flex flex-wrap gap-4">
        <div className="flex gap-2">
          {PLATFORMS.map((p) => (
            <button key={p} onClick={() => setPlatform(p)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                platform === p ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}>{p}</button>
          ))}
        </div>
        <div className="flex gap-2">
          {JOB_TYPES.map((t) => (
            <button key={t} onClick={() => setJobType(t)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                jobType === t ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}>{t}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="mt-8 animate-pulse text-gray-400">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="mt-8 text-center text-gray-400">No jobs yet. Run the pipeline to discover jobs.</div>
      ) : (
        <div className="mt-4 grid gap-4">
          {jobs.map((job) => {
            const skills = extractSkills(job.description);
            const isExpanded = expandedId === job.id;

            return (
              <div key={job.id}
                className="rounded-xl border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => toggle(job.id)}>
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{job.title}</h3>
                        <ScoreBadge score={job.match_score} />
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                        {job.company && <span className="font-medium text-gray-700">{job.company}</span>}
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                          job.platform === "linkedin" ? "bg-blue-100 text-blue-700" :
                          job.platform === "indeed" ? "bg-purple-100 text-purple-700" :
                          job.platform === "naukri" ? "bg-indigo-100 text-indigo-700" :
                          job.platform === "internshala" ? "bg-cyan-100 text-cyan-700" :
                          job.platform === "glassdoor" ? "bg-emerald-100 text-emerald-700" :
                          "bg-gray-100 text-gray-600"
                        }`}>{job.platform}</span>
                        {job.job_type && (
                          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs capitalize">{job.job_type}</span>
                        )}
                        {job.remote && (
                          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">Remote</span>
                        )}
                        {job.location && <span>{job.location}</span>}
                        {formatSalary(job.salary_min, job.salary_max) && (
                          <span className="font-medium text-gray-700">{formatSalary(job.salary_min, job.salary_max)}</span>
                        )}
                        <StatusBadge status={job.status} />
                      </div>

                      {/* Required Skills */}
                      {skills.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {skills.slice(0, 8).map((skill) => (
                            <span key={skill}
                              className="inline-flex items-center rounded-md bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 ring-1 ring-inset ring-orange-200">
                              {skill}
                            </span>
                          ))}
                          {skills.length > 8 && (
                            <span className="text-xs text-gray-400">+{skills.length - 8} more</span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="ml-4 flex flex-col items-end gap-2" onClick={(e) => e.stopPropagation()}>
                      {job.url && (
                        <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                          View Posting
                        </a>
                      )}
                      <select value={job.status} onChange={(e) => updateStatus(job.id, e.target.value)}
                        className="rounded border border-gray-200 px-2 py-1 text-xs">
                        {STATUSES.map((s) => (<option key={s} value={s}>{s}</option>))}
                      </select>
                      {job.cover_letter && (
                        <button onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : job.id); }}
                          className="rounded-lg bg-purple-100 px-3 py-1.5 text-xs font-medium text-purple-700 hover:bg-purple-200 transition-colors">
                          {isExpanded ? "Hide" : "View"} Cover Letter
                        </button>
                      )}
                      <svg className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Expanded: Description + Cover Letter */}
                {isExpanded && (
                  <div className="border-t border-gray-100">
                    {job.description && (
                      <div className="px-5 py-4">
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-400">Description</p>
                        <p className="text-sm leading-relaxed text-gray-700 whitespace-pre-line">
                          {job.description.length > 600 ? job.description.slice(0, 600) + "..." : job.description}
                        </p>
                      </div>
                    )}
                    {job.cover_letter && (
                      <div className="border-t border-gray-100 px-5 py-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-purple-600">AI-Generated Cover Letter</p>
                        <pre className="whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm text-gray-800">
                          {job.cover_letter}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
