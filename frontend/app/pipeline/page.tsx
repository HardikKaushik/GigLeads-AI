"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type PipelineRun } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

const STEPS = [
  { key: "planning", label: "Strategy Planning" },
  { key: "finding_leads", label: "Finding Leads", module: "leads" },
  { key: "finding_gigs", label: "Finding Gigs", module: "gigs" },
  { key: "finding_jobs", label: "Finding Jobs", module: "jobs" },
  { key: "generating_proposals", label: "Generating Proposals" },
  { key: "generating_cover_letters", label: "Generating Cover Letters", module: "jobs" },
  { key: "reviewing", label: "Reviewing Quality" },
  { key: "sending", label: "Sending & Applying" },
];

function stepIndex(status: string, modules: string[]) {
  const visible = STEPS.filter(s => !s.module || modules.includes(s.module));
  const idx = visible.findIndex((s) => s.key === status);
  if (status === "completed") return visible.length;
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

  const visibleSteps = STEPS.filter(s => !s.module || modules.includes(s.module));
  const currentStep = activeRun ? stepIndex(activeRun.status, modules) : -2;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
          <p className="mt-1 text-sm text-gray-500">Run AI-powered acquisition pipelines</p>
        </div>
        <button onClick={() => startPipeline()} disabled={!!isRunning || !!starting}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {starting === "all" ? "Starting..." : "Run All"}
        </button>
      </div>

      {/* Per-module buttons */}
      <div className="mt-4 flex gap-3">
        {modules.map((mod) => (
          <button key={mod} onClick={() => startPipeline([mod])} disabled={!!isRunning || !!starting}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors capitalize">
            {starting === mod ? "Starting..." : `Run ${mod}`}
          </button>
        ))}
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {/* Active run progress */}
      {activeRun && (
        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Current Run</h2>
            <div className="flex items-center gap-2">
              {activeRun.pipeline_type && (
                <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600">
                  {activeRun.pipeline_type}
                </span>
              )}
              <StatusBadge status={activeRun.status} />
            </div>
          </div>
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
          {activeRun.status === "completed" && (
            <div className="mt-4 grid grid-cols-4 gap-3 rounded-lg bg-gray-50 p-3 text-center text-sm">
              {modules.includes("leads") && <div><p className="font-bold text-gray-900">{activeRun.leads_found}</p><p className="text-gray-500">Leads</p></div>}
              {modules.includes("gigs") && <div><p className="font-bold text-gray-900">{activeRun.gigs_found}</p><p className="text-gray-500">Gigs</p></div>}
              {modules.includes("jobs") && <div><p className="font-bold text-gray-900">{activeRun.jobs_found}</p><p className="text-gray-500">Jobs</p></div>}
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
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 capitalize text-gray-600">{r.pipeline_type || "all"}</td>
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
