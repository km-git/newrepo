"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  ChecklistEntry,
  EvidenceItem,
  StaffCredential,
  GapReport,
  PracticeStandard,
} from "@/lib/types";

const statusStyle: Record<string, string> = {
  complete: "bg-green-100 text-green-800",
  in_progress: "bg-blue-100 text-blue-800",
  gap: "bg-red-100 text-red-800",
  not_started: "bg-slate-100 text-slate-600",
};

const credStyle: Record<string, string> = {
  valid: "text-green-700",
  expiring_soon: "text-amber-700 font-semibold",
  expired: "text-red-700 font-semibold",
};

export function AuditDashboard() {
  const [standards, setStandards] = useState<PracticeStandard[]>([]);
  const [checklist, setChecklist] = useState<ChecklistEntry[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [credentials, setCredentials] = useState<StaffCredential[]>([]);
  const [providerName, setProviderName] = useState("");
  const [report, setReport] = useState<GapReport | null>(null);
  const [reportText, setReportText] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newRef, setNewRef] = useState("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/audit");
    const data = await res.json();
    setStandards(data.standards);
    setChecklist(data.checklist);
    setEvidence(data.evidence);
    setCredentials(data.credentials);
    setProviderName(data.providerName);
    if (data.lastReport) setReport(data.lastReport);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function generateReport() {
    const res = await fetch("/api/audit", { method: "POST" });
    const data = await res.json();
    setReport(data.report);
    setReportText(data.text);
  }

  async function addEvidence() {
    if (!newTitle || !newRef) return;
    await fetch("/api/evidence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "add_evidence",
        title: newTitle,
        documentRef: newRef,
      }),
    });
    setNewTitle("");
    setNewRef("");
    await refresh();
  }

  function downloadReport() {
    const blob = new Blob([reportText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gap-report-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const complete = checklist.filter((c) => c.status === "complete").length;
  const readiness = standards.length
    ? Math.round((complete / standards.length) * 100)
    : 0;

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Readiness" value={`${readiness}%`} />
        <Stat label="Indicators" value={`${complete}/${standards.length}`} />
        <Stat label="Evidence items" value={String(evidence.length)} />
        <Stat
          label="Credential alerts"
          value={String(credentials.filter((c) => c.status !== "valid").length)}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Practice standards checklist</h2>
          <button
            type="button"
            onClick={generateReport}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
          >
            Generate gap report
          </button>
        </div>
        <p className="mt-1 text-sm text-slate-500">{providerName}</p>
        <div className="mt-4 space-y-2">
          {standards.map((std) => {
            const entry = checklist.find((c) => c.standardId === std.id);
            return (
              <div
                key={std.id}
                className="rounded-lg border border-slate-200 p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase text-violet-600">
                      {std.id} · {std.module}
                    </p>
                    <p className="font-medium text-slate-900">{std.outcome}</p>
                    <p className="mt-1 text-sm text-slate-600">{std.indicator}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      Evidence: {std.evidenceHint}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusStyle[entry?.status ?? "not_started"]}`}
                  >
                    {entry?.status?.replace("_", " ") ?? "not started"}
                  </span>
                </div>
                {entry && entry.evidenceIds.length > 0 && (
                  <p className="mt-2 text-xs text-green-700">
                    Linked: {entry.evidenceIds.length} item(s)
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Evidence library</h2>
          <ul className="mt-4 space-y-2">
            {evidence.map((ev) => (
              <li key={ev.id} className="rounded-lg bg-slate-50 p-3 text-sm">
                <p className="font-medium">{ev.title}</p>
                <p className="text-slate-500">{ev.documentRef}</p>
                {ev.matchedStandardIds.length > 0 && (
                  <p className="mt-1 text-xs text-violet-600">
                    → {ev.matchedStandardIds.join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-4 space-y-2 border-t pt-4">
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              placeholder="Document title"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
            />
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              placeholder="Reference code"
              value={newRef}
              onChange={(e) => setNewRef(e.target.value)}
            />
            <button
              type="button"
              onClick={addEvidence}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white"
            >
              Add evidence
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Staff credentials</h2>
          <p className="mt-1 text-xs text-slate-500">
            Dates and document refs only — no participant data.
          </p>
          <table className="mt-4 w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="pb-2">Staff</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Expires</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {credentials.map((c) => (
                <tr key={c.id} className="border-b border-slate-100">
                  <td className="py-2">{c.staffName}</td>
                  <td className="py-2">{c.credentialType}</td>
                  <td className="py-2">{c.expiryDate}</td>
                  <td className={`py-2 ${credStyle[c.status]}`}>
                    {c.status.replace("_", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      {report && (
        <section className="rounded-xl border border-violet-200 bg-violet-50/40 p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Gap report</h2>
            <button
              type="button"
              onClick={downloadReport}
              className="text-sm font-medium text-violet-700 hover:underline"
            >
              Download .txt
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-700">{report.summary}</p>
          <p className="mt-4 text-xs text-amber-800">{report.disclaimer}</p>
          {reportText && (
            <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-4 text-xs">
              {reportText}
            </pre>
          )}
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}
