"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type PipelineRun } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

// Steps per module — only show relevant steps for the running pipeline
const MODULE_STEPS: Record<string, { key: string; label: string }[]> = {
  leads: [
    { key: "planning", label: "Strategy Planning" },
    { key: "finding_leads", label: "Finding B2B Leads" },
    { key: "generating_proposals", label: "Generating Proposals" },
    { key: "reviewing", label: "Reviewing Quality" },
    { key: "sending", label: "Sending Outreach" },
  ],
  gigs: [
    { key: "planning", label: "Strategy Planning" },
    { key: "finding_gigs", label: "Finding Freelance Gigs" },
    { key: "generating_proposals", label: "Generating Proposals" },
    { key: "reviewing", label: "Reviewing Quality" },
    { key: "sending", label: "Sending Proposals" },
  ],
  jobs: [
    { key: "planning", label: "Strategy Planning" },
    { key: "finding_jobs", label: "Finding Jobs" },
    { key: "generating_cover_letters", label: "Generating Cover Letters" },
    { key: "reviewing", label: "Reviewing Quality" },
    { key: "sending", label: "Applying to Jobs" },
  ],
  all: [
    { key: "planning", label: "Strategy Planning" },
    { key: "finding_leads", label: "Finding B2B Leads" },
    { key: "finding_gigs", label: "Finding Gigs" },
    { key: "finding_jobs", label: "Finding Jobs" },
    { key: "generating_proposals", label: "Generating Proposals" },
    { key: "generating_cover_letters", label: "Generating Cover Letters" },
    { key: "reviewing", label: "Reviewing Quality" },
    { key: "sending", label: "Sending & Applying" },
  ],
};

function getSteps(pipelineType: string | null, selectedModules: string[]) {
  if (pipelineType && MODULE_STEPS[pipelineType]) {
    return MODULE_STEPS[pipelineType];
  }
  // Multi-module: filter "all" steps to only selected modules
  return MODULE_STEPS.all.filter((s) => {
    if (s.key === "finding_leads") return selectedModules.includes("leads");
    if (s.key === "finding_gigs") return selectedModules.includes("gigs");
    if (s.key === "finding_jobs") return selectedModules.includes("jobs");
    if (s.key === "generating_cover_letters") return selectedModules.includes("jobs");
    if (s.key === "generating_proposals") return selectedModules.includes("leads") || selectedModules.includes("gigs");
    return true;
  });
}

function stepIndex(status: string, steps: { key: string }[]) {
  const idx = steps.findIndex((s) => s.key === status);
  if (status === "completed") return steps.length;
  if (status === "failed") return -1;
  return idx;
}

export default function PipelinePage() {
  const { user } = useAuth();
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState("");

  const modules = user?.selected_modules || [];

  const load = useCallback(() => {
    if (!user) return;
    api.getPipelineHistory().then(setRuns).catch(() => {});
  }, [user]);

  useEffect(() => { load(); }, [load]);

  // Poll active run
  useEffect(() => {
    if (!activeRun || activeRun.status === "completed" || activeRun.status === "failed") return;
    const interval = setInterval(async () => {
      try {
        const updated = await api.getPipelineStatus(activeRun.id);
        setActiveRun(updated);
        if (updated.status === "completed" || updated.status === "failed") load();
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [activeRun, load]);

  const startPipeline = async (mods?: string[]) => {
    const key = mods ? mods.join(",") : "all";
    setStarting(key);
    setError("");
    try {
      const run = await api.startPipeline(mods);
      setActiveRun(run);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start pipeline");
    } finally { setStarting(null); }
  };

  const isRunning = activeRun && activeRun.status !== "completed" && activeRun.status !== "failed";

  if (!user) return <p className="text-gray-500">Loading...</p>;

  const pipelineType = activeRun?.pipeline_type || null;
  const visibleSteps = getSteps(pipelineType, modules);
  const currentStep = activeRun ? stepIndex(activeRun.status, visibleSteps) : -2;

  // Extract strategy info
  const strategy = activeRun?.strategy as Record<string, unknown> | null;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
          <p className="mt-1 text-sm text-gray-500">Run AI-powered acquisition pipelines</p>
        </div>
      </div>

      {/* Per-module buttons */}
      <div className="mt-4 flex flex-wrap gap-3">
        {modules.map((mod) => (
          <button key={mod} onClick={() => startPipeline([mod])} disabled={!!isRunning || !!starting}
            className={`rounded-lg border-2 px-5 py-2.5 text-sm font-semibold transition-all disabled:opacity-50 capitalize ${
              mod === "leads" ? "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100" :
              mod === "gigs" ? "border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100" :
              mod === "jobs" ? "border-green-200 bg-green-50 text-green-700 hover:bg-green-100" :
              "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100"
            }`}>
            {starting === mod ? "Starting..." : `Run ${mod.charAt(0).toUpperCase() + mod.slice(1)}`}
          </button>
        ))}
        {modules.length > 1 && (
          <button onClick={() => startPipeline()} disabled={!!isRunning || !!starting}
            className="rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50 transition-colors">
            {starting === "all" ? "Starting..." : "Run All"}
          </button>
        )}
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {/* Active run progress */}
      {activeRun && (
        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">
              Current Run
              {pipelineType && pipelineType !== "all" && (
                <span className={`ml-2 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                  pipelineType === "leads" ? "bg-blue-100 text-blue-700" :
                  pipelineType === "gigs" ? "bg-purple-100 text-purple-700" :
                  pipelineType === "jobs" ? "bg-green-100 text-green-700" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {pipelineType}
                </span>
              )}
            </h2>
            <StatusBadge status={activeRun.status} />
          </div>

          {/* Strategy Preview — show what we're planning */}
          {strategy && (
            <div className="mb-5 rounded-lg bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Strategy</p>
              {strategy.strategy_summary && (
                <p className="text-sm text-gray-700 mb-3">{strategy.strategy_summary as string}</p>
              )}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {strategy.monthly_income_target && (
                  <div className="rounded-md bg-white px-3 py-2 shadow-sm">
                    <p className="text-xs text-gray-400">Target</p>
                    <p className="text-sm font-bold text-gray-900">${(strategy.monthly_income_target as number).toLocaleString()}/mo</p>
                  </div>
                )}
                {(strategy.weekly_targets as Record<string, number>)?.leads_to_find && (
                  <div className="rounded-md bg-white px-3 py-2 shadow-sm">
                    <p className="text-xs text-gray-400">Weekly Leads</p>
                    <p className="text-sm font-bold text-gray-900">{(strategy.weekly_targets as Record<string, number>).leads_to_find}</p>
                  </div>
                )}
                {(strategy.weekly_targets as Record<string, number>)?.proposals_to_send && (
                  <div className="rounded-md bg-white px-3 py-2 shadow-sm">
                    <p className="text-xs text-gray-400">Weekly Proposals</p>
                    <p className="text-sm font-bold text-gray-900">{(strategy.weekly_targets as Record<string, number>).proposals_to_send}</p>
                  </div>
                )}
                {(strategy.pricing_suggestion as Record<string, unknown>)?.hourly_rate_range && (
                  <div className="rounded-md bg-white px-3 py-2 shadow-sm">
                    <p className="text-xs text-gray-400">Rate Range</p>
                    <p className="text-sm font-bold text-gray-900">
                      ${((strategy.pricing_suggestion as Record<string, number[]>).hourly_rate_range)[0]}-${((strategy.pricing_suggestion as Record<string, number[]>).hourly_rate_range)[1]}/hr
                    </p>
                  </div>
                )}
              </div>
              {/* Recommended platforms */}
              {strategy.recommended_platforms && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {(strategy.recommended_platforms as { platform: string; priority: string; reason: string }[]).map((p, i) => (
                    <span key={i} className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                      p.priority === "high" ? "bg-green-100 text-green-700" :
                      p.priority === "medium" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`} title={p.reason}>
                      {p.platform} ({p.priority})
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Steps */}
          <div className="space-y-3">
            {visibleSteps.map((step, i) => {
              let state: "done" | "active" | "pending" = "pending";
              if (activeRun.status === "completed" || i < currentStep) state = "done";
              else if (i === currentStep) state = "active";

              return (
                <div key={step.key} className="flex items-center gap-3">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                    state === "done" ? "bg-green-100 text-green-700"
                      : state === "active" ? "bg-blue-100 text-blue-700 animate-pulse"
                      : "bg-gray-100 text-gray-400"
                  }`}>
                    {state === "done" ? "\u2713" : i + 1}
                  </div>
                  <span className={`text-sm ${
                    state === "done" ? "text-green-700 font-medium"
                      : state === "active" ? "text-blue-700 font-semibold"
                      : "text-gray-400"
                  }`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Completion stats */}
          {activeRun.status === "completed" && (
            <div className="mt-4 grid grid-cols-4 gap-3 rounded-lg bg-gray-50 p-3 text-center text-sm">
              {(pipelineType === "leads" || !pipelineType || pipelineType === "all") && modules.includes("leads") && (
                <div><p className="font-bold text-gray-900">{activeRun.leads_found}</p><p className="text-gray-500">Leads</p></div>
              )}
              {(pipelineType === "gigs" || !pipelineType || pipelineType === "all") && modules.includes("gigs") && (
                <div><p className="font-bold text-gray-900">{activeRun.gigs_found}</p><p className="text-gray-500">Gigs</p></div>
              )}
              {(pipelineType === "jobs" || !pipelineType || pipelineType === "all") && modules.includes("jobs") && (
                <div><p className="font-bold text-gray-900">{activeRun.jobs_found}</p><p className="text-gray-500">Jobs</p></div>
              )}
              <div><p className="font-bold text-gray-900">{activeRun.proposals_sent}</p><p className="text-gray-500">Sent</p></div>
            </div>
          )}
          {activeRun.error_message && (
            <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{activeRun.error_message}</div>
          )}
        </div>
      )}

      {/* History */}
      {runs.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900">Run History</h2>
          <div className="mt-3 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Leads</th>
                  <th className="px-4 py-3">Gigs</th>
                  <th className="px-4 py-3">Jobs</th>
                  <th className="px-4 py-3">Sent</th>
                  <th className="px-4 py-3">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setActiveRun(r)}>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        r.pipeline_type === "leads" ? "bg-blue-100 text-blue-700" :
                        r.pipeline_type === "gigs" ? "bg-purple-100 text-purple-700" :
                        r.pipeline_type === "jobs" ? "bg-green-100 text-green-700" :
                        "bg-gray-100 text-gray-600"
                      }`}>{r.pipeline_type || "all"}</span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3">{r.leads_found}</td>
                    <td className="px-4 py-3">{r.gigs_found}</td>
                    <td className="px-4 py-3">{r.jobs_found}</td>
                    <td className="px-4 py-3">{r.proposals_sent}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(r.started_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
