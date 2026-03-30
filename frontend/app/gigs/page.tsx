"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Gig } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";

const PLATFORMS = ["all", "linkedin", "indeed", "upwork", "freelancer"];

export default function GigsPage() {
  const { user } = useAuth();
  const [gigs, setGigs] = useState<Gig[]>([]);
  const [platform, setPlatform] = useState("all");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    api.getGigs({ platform: platform === "all" ? undefined : platform })
      .then(setGigs).catch(() => {}).finally(() => setLoading(false));
  }, [user, platform]);

  useEffect(() => { load(); }, [load]);

  const generateProposal = async (gigId: string) => {
    setGenerating(gigId);
    try {
      await api.generateProposal({ gig_id: gigId });
      alert("Proposal generated! Check the Proposals page.");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to generate proposal");
    } finally { setGenerating(null); }
  };

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Gigs</h1>
        {!loading && gigs.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-blue-600 px-3 py-1 text-sm font-semibold text-white">
            {gigs.length} found
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-500">Freelance gigs ranked by AI match score</p>

      <div className="mt-4 flex gap-2">
        {PLATFORMS.map((p) => (
          <button key={p} onClick={() => setPlatform(p)}
            className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
              platform === p ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}>{p}</button>
        ))}
      </div>

      {loading ? (
        <div className="mt-8 animate-pulse text-gray-400">Loading gigs...</div>
      ) : gigs.length === 0 ? (
        <div className="mt-8 text-center text-gray-400">No gigs yet. Run the pipeline to discover gigs.</div>
      ) : (
        <div className="mt-4 grid gap-4">
          {gigs.map((gig) => (
            <div key={gig.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{gig.title}</h3>
                    <ScoreBadge score={gig.match_score} />
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
                    <span className="capitalize">{gig.platform}</span>
                    {gig.budget && <span>${gig.budget.toLocaleString()}</span>}
                    <StatusBadge status={gig.status} />
                  </div>
                  {gig.description && <p className="mt-2 text-sm text-gray-600 line-clamp-2">{gig.description}</p>}
                </div>
                <div className="ml-4 flex flex-col items-end gap-2">
                  {gig.url && <a href={gig.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">View Posting</a>}
                  <button onClick={() => generateProposal(gig.id)} disabled={generating === gig.id}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
                    {generating === gig.id ? "Generating..." : "Write Proposal"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
