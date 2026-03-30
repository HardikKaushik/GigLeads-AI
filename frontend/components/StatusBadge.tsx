"use client";

const COLORS: Record<string, string> = {
  // Leads
  new: "bg-blue-100 text-blue-700",
  contacted: "bg-yellow-100 text-yellow-700",
  replied: "bg-green-100 text-green-700",
  qualified: "bg-emerald-100 text-emerald-700",
  converted: "bg-purple-100 text-purple-700",
  lost: "bg-red-100 text-red-700",
  // Gigs
  discovered: "bg-blue-100 text-blue-700",
  applied: "bg-yellow-100 text-yellow-700",
  interviewing: "bg-orange-100 text-orange-700",
  won: "bg-green-100 text-green-700",
  skipped: "bg-gray-100 text-gray-500",
  // Proposals
  draft: "bg-gray-100 text-gray-600",
  reviewed: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
  // Invoices
  paid: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-gray-100 text-gray-500",
  // Pipeline
  pending: "bg-gray-100 text-gray-600",
  planning: "bg-blue-100 text-blue-700",
  finding_leads: "bg-indigo-100 text-indigo-700",
  finding_gigs: "bg-indigo-100 text-indigo-700",
  generating_proposals: "bg-purple-100 text-purple-700",
  reviewing: "bg-yellow-100 text-yellow-700",
  sending: "bg-orange-100 text-orange-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: string }) {
  const color = COLORS[status] || "bg-gray-100 text-gray-600";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${color}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
