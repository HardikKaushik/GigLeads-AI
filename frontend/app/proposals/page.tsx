"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Proposal } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";

export default function ProposalsPage() {
  const { user } = useAuth();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sending, setSending] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    api.getProposals().then(setProposals).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const sendProposal = async (id: string) => {
    setSending(id);
    try { await api.sendProposal(id); load(); }
    catch (e: unknown) { alert(e instanceof Error ? e.message : "Failed to send"); }
    finally { setSending(null); }
  };

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Proposals</h1>
      <p className="mt-1 text-sm text-gray-500">AI-generated proposals with quality scores</p>

      {loading ? (
        <div className="mt-8 animate-pulse text-gray-400">Loading proposals...</div>
      ) : proposals.length === 0 ? (
        <div className="mt-8 text-center text-gray-400">No proposals yet. Generate them from the Gigs or Leads pages.</div>
      ) : (
        <div className="mt-6 space-y-4">
          {proposals.map((p) => (
            <div key={p.id} className="rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-3">
                  <ScoreBadge score={p.review_score} />
                  <StatusBadge status={p.status} />
                  <span className="text-sm text-gray-500">{new Date(p.created_at).toLocaleDateString()}</span>
                  {p.sent_at && <span className="text-xs text-gray-400">Sent {new Date(p.sent_at).toLocaleDateString()}</span>}
                </div>
                <div className="flex items-center gap-2">
                  {p.status === "approved" && (
                    <button onClick={() => sendProposal(p.id)} disabled={sending === p.id}
                      className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors">
                      {sending === p.id ? "Sending..." : "Send"}
                    </button>
                  )}
                  <button onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                    className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200 transition-colors">
                    {expanded === p.id ? "Collapse" : "View"}
                  </button>
                </div>
              </div>
              {expanded === p.id && (
                <div className="border-t border-gray-100 px-5 py-4">
                  <pre className="whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm text-gray-800">{p.content}</pre>
                  {p.review_feedback && (
                    <div className="mt-3 rounded-lg bg-yellow-50 p-3">
                      <p className="text-xs font-medium text-yellow-800">Review Feedback</p>
                      <p className="mt-1 text-sm text-yellow-700">{p.review_feedback}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
