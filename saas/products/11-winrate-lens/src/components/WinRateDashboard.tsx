"use client";

import { useCallback, useEffect, useState } from "react";
import type { MonthlyInsight, WinRateMetrics, WinRateSlice } from "@/lib/types";

function SliceTable({ title, slices }: { title: string; slices: WinRateSlice[] }) {
  return (
    <section className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="pb-2 font-medium">Segment</th>
            <th className="pb-2 font-medium">Won</th>
            <th className="pb-2 font-medium">Lost</th>
            <th className="pb-2 font-medium">Win rate</th>
          </tr>
        </thead>
        <tbody>
          {slices.map((s) => (
            <tr key={s.key} className="border-b last:border-0">
              <td className="py-2 font-medium">{s.label}</td>
              <td className="py-2">{s.won}</td>
              <td className="py-2">{s.lost}</td>
              <td className="py-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    s.winRate >= 60
                      ? "bg-emerald-100 text-emerald-800"
                      : s.winRate >= 40
                        ? "bg-amber-100 text-amber-800"
                        : "bg-red-100 text-red-800"
                  }`}
                >
                  {s.winRate}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function WinRateDashboard() {
  const [metrics, setMetrics] = useState<WinRateMetrics | null>(null);
  const [insight, setInsight] = useState<MonthlyInsight | null>(null);
  const [mockMode, setMockMode] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/metrics");
    const data = await res.json();
    setMetrics(data.metrics);
    setInsight(data.insight);
    setMockMode(data.mockMode);
    setLastSync(data.lastSyncAt ?? null);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSync() {
    setSyncing(true);
    await fetch("/api/sync", { method: "POST" });
    await refresh();
    setSyncing(false);
  }

  if (!metrics || !insight) {
    return <p className="text-sm text-slate-500">Loading metrics…</p>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="text-sm text-slate-500">
          {metrics.period}
          {lastSync && (
            <span> · Last sync {new Date(lastSync).toLocaleString()}</span>
          )}
          {mockMode && <span className="ml-2 text-violet-600"> · Mock ServiceM8</span>}
        </div>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncing}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {syncing ? "Syncing…" : "Sync quotes"}
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm text-slate-500">Win rate</p>
          <p className="mt-1 text-3xl font-bold text-violet-700">{metrics.overall.winRate}%</p>
          <p className="mt-1 text-xs text-slate-400">
            {metrics.overall.won} won · {metrics.overall.lost} lost · {metrics.overall.open} open
          </p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm text-slate-500">Value won</p>
          <p className="mt-1 text-3xl font-bold">${metrics.overall.totalValueWon.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm text-slate-500">Avg response</p>
          <p className="mt-1 text-3xl font-bold">{metrics.avgResponseHours}h</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm text-slate-500">Total quoted</p>
          <p className="mt-1 text-3xl font-bold">${metrics.totalQuoted.toLocaleString()}</p>
        </div>
      </div>

      <section className="rounded-xl border border-violet-200 bg-violet-50 p-6">
        <h2 className="text-lg font-semibold text-violet-900">Monthly insight</h2>
        <p className="mt-2 font-medium text-violet-800">{insight.headline}</p>
        <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-violet-900/90">
          {insight.bullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <p className="rounded-lg bg-white/70 p-3 text-sm">
            <span className="font-medium text-emerald-700">Opportunity:</span> {insight.topOpportunity}
          </p>
          <p className="rounded-lg bg-white/70 p-3 text-sm">
            <span className="font-medium text-amber-700">Watch:</span> {insight.caution}
          </p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <SliceTable title="By job type" slices={metrics.byJobType} />
        <SliceTable title="By suburb" slices={metrics.bySuburb} />
        <SliceTable title="By price band" slices={metrics.byPriceBand} />
        <SliceTable title="By response time" slices={metrics.byResponseTime} />
      </div>
    </div>
  );
}
