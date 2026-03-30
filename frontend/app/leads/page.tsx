"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Lead } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";

const STATUSES = ["all", "new", "contacted", "replied", "qualified", "converted", "lost"];

export default function LeadsPage() {
  const { user } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    api
      .getLeads({ status: filter === "all" ? undefined : filter })
      .then(setLeads)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, filter]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (leadId: string, status: string) => {
    try { await api.updateLeadStatus(leadId, status); load(); } catch {}
  };

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
        {!loading && leads.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-blue-600 px-3 py-1 text-sm font-semibold text-white">
            {leads.length} found
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-500">Potential clients discovered by AI agents</p>

      <div className="mt-4 flex gap-2">
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
              filter === s ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}>
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="mt-8 animate-pulse text-gray-400">Loading leads...</div>
      ) : leads.length === 0 ? (
        <div className="mt-8 text-center text-gray-400">No leads yet. Run the pipeline to discover leads.</div>
      ) : (
        <div className="mt-4 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{lead.name}</td>
                  <td className="px-4 py-3 text-gray-600">{lead.company || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{lead.role || "—"}</td>
                  <td className="px-4 py-3"><ScoreBadge score={lead.score} /></td>
                  <td className="px-4 py-3"><StatusBadge status={lead.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {lead.email && <a href={`mailto:${lead.email}`} className="text-blue-600 hover:underline text-xs" title={lead.email}>Email</a>}
                      {lead.linkedin_url && <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs">LinkedIn</a>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <select value={lead.status} onChange={(e) => updateStatus(lead.id, e.target.value)}
                      className="rounded border border-gray-200 px-2 py-1 text-xs">
                      {STATUSES.filter((s) => s !== "all").map((s) => (<option key={s} value={s}>{s}</option>))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
