"use client";

import { useCallback, useEffect, useState } from "react";
import type { ComplianceDocument, Subcontractor } from "@/lib/types";
import { DOC_LABELS } from "@/lib/types";

const complianceStyle: Record<string, string> = {
  compliant: "bg-green-100 text-green-800",
  expiring: "bg-amber-100 text-amber-800",
  non_compliant: "bg-red-100 text-red-800",
};

export function ComplianceDashboard() {
  const [builderName, setBuilderName] = useState("");
  const [subbies, setSubbies] = useState<Subcontractor[]>([]);
  const [pending, setPending] = useState<ComplianceDocument[]>([]);
  const [summary, setSummary] = useState({ total: 0, compliant: 0, expiring: 0, nonCompliant: 0 });
  const [selectedDoc, setSelectedDoc] = useState<ComplianceDocument | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/board");
    const data = await res.json();
    setBuilderName(data.builderName);
    setSubbies(data.subbies);
    setPending(data.pending);
    setSummary(data.summary);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function confirmDoc(docId: string) {
    await fetch("/api/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "confirm", docId }),
    });
    setSelectedDoc(null);
    await refresh();
  }

  async function rejectDoc(docId: string) {
    await fetch("/api/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", docId }),
    });
    setSelectedDoc(null);
    await refresh();
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Subcontractors" value={String(summary.total)} />
        <Stat label="Compliant" value={String(summary.compliant)} />
        <Stat label="Expiring soon" value={String(summary.expiring)} />
        <Stat label="Non-compliant" value={String(summary.nonCompliant)} />
      </div>

      {pending.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="text-lg font-semibold">Pending review ({pending.length})</h2>
          <p className="mt-1 text-sm text-slate-600">
            Parsed fields require human confirmation before counting toward compliance.
          </p>
          <div className="mt-4 space-y-3">
            {pending.map((doc) => {
              const subbie = subbies.find((s) => s.id === doc.subbieId);
              return (
                <div key={doc.id} className="rounded-lg border bg-white p-4">
                  <p className="font-medium">{doc.fileName}</p>
                  <p className="text-sm text-slate-500">
                    {subbie?.companyName} · {DOC_LABELS[doc.documentType]}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    Expiry: {doc.parsed.expiryDate || "unknown"} · Confidence: {doc.parsed.confidence}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedDoc(doc)}
                      className="text-sm text-slate-600 hover:underline"
                    >
                      Review
                    </button>
                    <button
                      type="button"
                      onClick={() => confirmDoc(doc.id)}
                      className="rounded-lg bg-teal-600 px-3 py-1.5 text-sm font-medium text-white"
                    >
                      Confirm
                    </button>
                    <button
                      type="button"
                      onClick={() => rejectDoc(doc.id)}
                      className="rounded-lg border px-3 py-1.5 text-sm text-slate-600"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {selectedDoc && (
        <section className="rounded-xl border border-teal-200 bg-teal-50/50 p-6">
          <h2 className="font-semibold">Document review</h2>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Field label="Type" value={DOC_LABELS[selectedDoc.documentType]} />
            <Field label="Expiry" value={selectedDoc.parsed.expiryDate || "—"} />
            <Field label="Insurer" value={selectedDoc.parsed.insurer || "—"} />
            <Field label="Policy" value={selectedDoc.parsed.policyNumber || "—"} />
            <Field label="Coverage" value={selectedDoc.parsed.coverageAmount || "—"} />
            <Field label="Licence" value={selectedDoc.parsed.licenceNumber || "—"} />
          </dl>
          <button
            type="button"
            onClick={() => setSelectedDoc(null)}
            className="mt-4 text-sm text-slate-500 hover:underline"
          >
            Close
          </button>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Compliance board</h2>
        <p className="mt-1 text-sm text-slate-500">{builderName}</p>
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="pb-2">Company</th>
              <th className="pb-2">Trade</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Issues</th>
              <th className="pb-2">Portal</th>
            </tr>
          </thead>
          <tbody>
            {subbies.map((s) => (
              <tr key={s.id} className="border-b border-slate-100">
                <td className="py-3 font-medium">{s.companyName}</td>
                <td className="py-3">{s.trade}</td>
                <td className="py-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${complianceStyle[s.compliance]}`}>
                    {s.compliance.replace("_", " ")}
                  </span>
                </td>
                <td className="py-3 text-xs text-slate-600">
                  {[...s.missingDocs.map((d) => `Missing: ${DOC_LABELS[d]}`), ...s.expiringDocs].join("; ") || "—"}
                </td>
                <td className="py-3">
                  <a href={`/portal/${s.id}`} className="text-teal-700 hover:underline">
                    Upload
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
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

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
