"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api, type Analytics } from "@/lib/api";
import StatCard from "@/components/StatCard";

export default function Dashboard() {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  const modules = user?.selected_modules || [];

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    api
      .getAnalytics()
      .then(setAnalytics)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  if (loading) {
    return <div className="animate-pulse text-gray-400">Loading dashboard...</div>;
  }

  const a = analytics;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Your freelance acquisition overview</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {modules.includes("leads") && (
          <StatCard title="Total Leads" value={a?.total_leads ?? 0} color="blue" />
        )}
        {modules.includes("gigs") && (
          <StatCard title="Gigs Found" value={a?.total_gigs ?? 0} color="purple" />
        )}
        {modules.includes("jobs") && (
          <StatCard title="Jobs Found" value={a?.total_jobs ?? 0} color="green" />
        )}
        <StatCard title="Proposals Sent" value={a?.proposals_sent ?? 0} color="orange" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Proposals" value={a?.total_proposals ?? 0} color="purple" />
        <StatCard
          title="Response Rate"
          value={`${a?.response_rate ?? 0}%`}
          color="green"
        />
        <StatCard
          title="Revenue"
          value={`$${(a?.total_revenue ?? 0).toLocaleString()}`}
          color="orange"
        />
        <StatCard title="Pipeline Runs" value={a?.pipeline_runs ?? 0} color="blue" />
      </div>

      {a?.best_platforms && a.best_platforms.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900">Top Platforms</h2>
          <div className="mt-3 flex gap-3">
            {a.best_platforms.map((p) => (
              <div
                key={p.platform}
                className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm"
              >
                <p className="text-sm font-medium capitalize text-gray-700">{p.platform}</p>
                <p className="text-xl font-bold text-gray-900">{p.gig_count} gigs</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
