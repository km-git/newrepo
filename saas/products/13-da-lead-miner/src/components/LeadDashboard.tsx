"use client";

import { useCallback, useEffect, useState } from "react";
import type { Council, DevelopmentApplication, UserProfile, WeeklyDigest } from "@/lib/types";

function scoreBadge(score: number) {
  if (score >= 75) return "bg-orange-100 text-orange-800";
  if (score >= 55) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export function LeadDashboard() {
  const [leads, setLeads] = useState<DevelopmentApplication[]>([]);
  const [councils, setCouncils] = useState<Council[]>([]);
  const [digest, setDigest] = useState<WeeklyDigest | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [mockMode, setMockMode] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filter, setFilter] = useState<"all" | "new" | "saved">("all");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/leads");
    const data = await res.json();
    setLeads(data.leads);
    setCouncils(data.councils);
    setDigest(data.digest);
    setProfile(data.profile);
    setMockMode(data.mockMode);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSync() {
    setSyncing(true);
    await fetch("/api/sync", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    await refresh();
    setSyncing(false);
  }

  async function updateStatus(leadId: string, status: DevelopmentApplication["status"]) {
    await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update_status", leadId, status }),
    });
    await refresh();
  }

  const visible = leads.filter((l) => {
    if (filter === "all") return l.status !== "dismissed";
    return l.status === filter;
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="text-sm text-slate-500">
          {profile && (
            <span>
              {profile.businessName} · {profile.tradeFocus.replace("_", " ")} focus
            </span>
          )}
          {mockMode && <span className="ml-2 text-orange-600">· Mock DA feeds</span>}
        </div>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncing}
          className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-medium text-white hover:bg-orange-500 disabled:opacity-50"
        >
          {syncing ? "Syncing…" : "Sync councils"}
        </button>
      </div>

      {digest && (
        <section className="rounded-xl border border-orange-200 bg-orange-50 p-6">
          <h2 className="text-lg font-semibold text-orange-900">Weekly digest</h2>
          <p className="mt-1 text-xs text-orange-700">{digest.periodLabel}</p>
          <p className="mt-3 text-sm text-orange-900">{digest.summary}</p>
          <p className="mt-2 text-sm font-medium text-orange-800">{digest.leadCount} leads this week</p>
        </section>
      )}

      <div className="flex gap-2 text-sm">
        {(["all", "new", "saved"] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 capitalize ${filter === f ? "bg-orange-600 text-white" : "bg-white border"}`}
          >
            {f}
          </button>
        ))}
        <span className="ml-auto text-slate-500">{councils.length} councils monitored</span>
      </div>

      <div className="space-y-3">
        {visible.map((lead) => (
          <article key={lead.id} className="rounded-xl border bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold">{lead.address}, {lead.suburb}</p>
                <p className="text-xs text-slate-500">
                  {lead.daNumber} · {councils.find((c) => c.id === lead.councilId)?.name}
                </p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${scoreBadge(lead.leadScore)}`}>
                {lead.leadScore} score
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{lead.description}</p>
            <p className="mt-2 text-sm italic text-orange-800">{lead.leadReason}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {lead.workTypes.map((w) => (
                <span key={w} className="rounded bg-slate-100 px-2 py-0.5 text-xs capitalize">{w}</span>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <button type="button" onClick={() => updateStatus(lead.id, "saved")} className="text-sm text-orange-600 hover:underline">Save</button>
              <button type="button" onClick={() => updateStatus(lead.id, "reviewed")} className="text-sm text-slate-600 hover:underline">Mark reviewed</button>
              <button type="button" onClick={() => updateStatus(lead.id, "dismissed")} className="text-sm text-slate-400 hover:underline">Dismiss</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
