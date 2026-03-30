"use client";

export default function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return <span className="text-sm text-gray-400">--</span>;
  }
  let color = "bg-red-100 text-red-700";
  if (score >= 80) color = "bg-green-100 text-green-700";
  else if (score >= 60) color = "bg-yellow-100 text-yellow-700";
  else if (score >= 40) color = "bg-orange-100 text-orange-700";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${color}`}
    >
      {score}
    </span>
  );
}
