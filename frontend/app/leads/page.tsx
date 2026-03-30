"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Lead } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";

const STATUSES = ["all", "new", "contacted", "replied", "qualified", "converted", "lost"];

function formatFunding(amount: number | null): string | null {
  if (!amount) return null;
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount}`;
}

export default function LeadsPage() {
  const { user } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
        <h1 className="text-2xl font-bold text-gray-900">B2B Leads</h1>
        {!loading && leads.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-blue-600 px-3 py-1 text-sm font-semibold text-white">
            {leads.length} found
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-500">Potential clients who need your services — enriched with Crunchbase data</p>

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
        <div className="mt-8 text-center text-gray-400">No leads yet. Run the pipeline to discover B2B leads.</div>
      ) : (
        <div className="mt-4 grid gap-4">
          {leads.map((lead) => {
            const isExpanded = expandedId === lead.id;
            const funding = formatFunding(lead.funding_usd);

            return (
              <div key={lead.id}
                className="rounded-xl border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : lead.id)}>
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Company Name + Score */}
                      <div className="flex items-center gap-2">
                        {lead.company_logo && (
                          <img src={lead.company_logo} alt="" className="h-8 w-8 rounded-md object-contain bg-gray-50" />
                        )}
                        <h3 className="font-semibold text-gray-900">{lead.company || lead.name}</h3>
                        <ScoreBadge score={lead.score} />
                        {funding && (
                          <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                            {funding} funded
                          </span>
                        )}
                      </div>

                      {/* Signal + Location */}
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                        <span className="text-gray-700">{lead.role || "Potential client"}</span>
                        {lead.location && <span>· {lead.location}</span>}
                        <StatusBadge status={lead.status} />
                      </div>

                      {/* Industries */}
                      {lead.industries && lead.industries.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {lead.industries.slice(0, 5).map((ind) => (
                            <span key={ind}
                              className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-200">
                              {ind}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Service Opportunity */}
                      {lead.service_opportunity && (
                        <p className="mt-2 text-sm text-green-700">
                          <span className="font-medium">Opportunity:</span> {lead.service_opportunity}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="ml-4 flex flex-col items-end gap-2" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2">
                        {lead.linkedin_url && (
                          <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer"
                            className="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors">
                            LinkedIn
                          </a>
                        )}
                        {lead.company_website && (
                          <a href={lead.company_website.startsWith("http") ? lead.company_website : `https://${lead.company_website}`}
                            target="_blank" rel="noopener noreferrer"
                            className="rounded-md bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 transition-colors">
                            Website
                          </a>
                        )}
                        {lead.job_url && (
                          <a href={lead.job_url} target="_blank" rel="noopener noreferrer"
                            className="rounded-md bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100 transition-colors">
                            Job Post
                          </a>
                        )}
                        {lead.email && (
                          <a href={`mailto:${lead.email}`}
                            className="rounded-md bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-100 transition-colors">
                            Email
                          </a>
                        )}
                      </div>
                      <select value={lead.status} onChange={(e) => updateStatus(lead.id, e.target.value)}
                        className="rounded border border-gray-200 px-2 py-1 text-xs">
                        {STATUSES.filter((s) => s !== "all").map((s) => (<option key={s} value={s}>{s}</option>))}
                      </select>
                      <svg className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Expanded: Founders + Notes */}
                {isExpanded && (
                  <div className="border-t border-gray-100 px-5 py-4 space-y-3">
                    {/* Founders / Decision Makers */}
                    {lead.founders && lead.founders.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Decision Makers (Founders)</p>
                        <div className="grid grid-cols-2 gap-2">
                          {lead.founders.map((founder, i) => (
                            <div key={i} className="flex items-center gap-2 rounded-lg bg-gray-50 px-3 py-2">
                              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-700">
                                {founder.name?.charAt(0) || "?"}
                              </div>
                              <div>
                                <p className="text-sm font-medium text-gray-900">{founder.name}</p>
                                <p className="text-xs text-gray-500">{founder.title}</p>
                              </div>
                              {founder.linkedin && (
                                <a href={founder.linkedin} target="_blank" rel="noopener noreferrer"
                                  className="ml-auto text-xs text-blue-600 hover:underline"
                                  onClick={(e) => e.stopPropagation()}>
                                  Profile
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Notes / AI Reasoning */}
                    {lead.notes && (
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">AI Analysis</p>
                        <p className="text-sm text-gray-700">{lead.notes}</p>
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
