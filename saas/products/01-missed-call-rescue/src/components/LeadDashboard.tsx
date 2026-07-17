"use client";

import { useCallback, useEffect, useState } from "react";
import type { LeadCard } from "@/lib/types";
import { LeadCardView } from "./LeadCard";

export function LeadDashboard() {
  const [leads, setLeads] = useState<LeadCard[]>([]);
  const [simLog, setSimLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/leads");
    const data = (await res.json()) as { leads: LeadCard[] };
    setLeads(data.leads);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function runSimulation() {
    const phone = "+61400999888";
    const steps = [
      { action: "missed_call" as const },
      { action: "sms_reply" as const, message: "Blocked kitchen drain" },
      { action: "sms_reply" as const, message: "Parramatta" },
      { action: "sms_reply" as const, message: "soon" },
      { action: "sms_reply" as const, message: "Under sink access easy" },
    ];

    const log: string[] = [];
    for (const step of steps) {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...step, phone }),
      });
      const data = await res.json();
      if (data.outbound) log.push(`→ ${data.outbound}`);
      if (data.reply) log.push(`← ${data.reply}`);
      if (data.lead) log.push(`✓ Lead: ${data.lead.summary}`);
    }
    setSimLog(log);
    await refresh();
  }

  async function onStatusChange(id: string, status: LeadCard["status"]) {
    await fetch("/api/leads", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    });
    await refresh();
  }

  if (loading) {
    return <p className="text-slate-500">Loading leads…</p>;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-dashed border-blue-300 bg-blue-50/50 p-4">
        <h2 className="font-semibold text-slate-900">Demo simulator</h2>
        <p className="mt-1 text-sm text-slate-600">
          Run a full missed-call → SMS qualification flow without Twilio credentials.
        </p>
        <button
          type="button"
          onClick={runSimulation}
          className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Simulate missed call + SMS thread
        </button>
        {simLog.length > 0 && (
          <pre className="mt-3 overflow-x-auto rounded-lg bg-white p-3 text-xs text-slate-700">
            {simLog.join("\n")}
          </pre>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">
          Lead cards ({leads.length})
        </h2>
        {leads.length === 0 ? (
          <p className="text-slate-500">No leads yet. Run the simulator above.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {leads.map((lead) => (
              <LeadCardView
                key={lead.id}
                lead={lead}
                onStatusChange={onStatusChange}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
