"use client";

import { useState } from "react";
import type { FieldReport, TradeTemplate } from "@/lib/types";

const TRADES: TradeTemplate[] = ["electrical", "pest", "solar", "maintenance"];

export function CaptureWizard() {
  const [trade, setTrade] = useState<TradeTemplate>("electrical");
  const [jobRef, setJobRef] = useState("");
  const [siteAddress, setSiteAddress] = useState("");
  const [clientName, setClientName] = useState("");
  const [technician, setTechnician] = useState("");
  const [photoLabels, setPhotoLabels] = useState("");
  const [voiceTranscripts, setVoiceTranscripts] = useState("");
  const [report, setReport] = useState<FieldReport | null>(null);
  const [loading, setLoading] = useState(false);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch("/api/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "create",
        input: {
          trade,
          jobRef,
          siteAddress,
          clientName,
          technician,
          photoLabels: photoLabels.split("\n").map((s) => s.trim()).filter(Boolean),
          voiceTranscripts: voiceTranscripts.split("\n").map((s) => s.trim()).filter(Boolean),
        },
      }),
    });
    const data = await res.json();
    setReport(data.report);
    setLoading(false);
  }

  function download() {
    if (!report) return;
    const blob = new Blob([report.bodyText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${report.jobRef}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <form onSubmit={generate} className="space-y-4 rounded-xl border bg-white p-6">
        <h2 className="text-lg font-semibold">Site capture</h2>
        <p className="text-sm text-slate-500">
          Demo mode — enter photo labels and voice note transcripts (speech-to-text mock).
        </p>
        <label className="block text-sm">
          <span className="font-medium">Trade template</span>
          <select
            className="mt-1 w-full rounded-lg border px-3 py-2"
            value={trade}
            onChange={(e) => setTrade(e.target.value as TradeTemplate)}
          >
            {TRADES.map((t) => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium">Job reference</span>
          <input required className="mt-1 w-full rounded-lg border px-3 py-2" value={jobRef} onChange={(e) => setJobRef(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Site address</span>
          <input className="mt-1 w-full rounded-lg border px-3 py-2" value={siteAddress} onChange={(e) => setSiteAddress(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Client name</span>
          <input className="mt-1 w-full rounded-lg border px-3 py-2" value={clientName} onChange={(e) => setClientName(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Technician</span>
          <input className="mt-1 w-full rounded-lg border px-3 py-2" value={technician} onChange={(e) => setTechnician(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Photo labels (one per line)</span>
          <textarea rows={3} className="mt-1 w-full rounded-lg border px-3 py-2 font-mono text-xs" value={photoLabels} onChange={(e) => setPhotoLabels(e.target.value)} placeholder="Switchboard before&#10;Switchboard after" />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Voice notes (one per line)</span>
          <textarea rows={3} className="mt-1 w-full rounded-lg border px-3 py-2 font-mono text-xs" value={voiceTranscripts} onChange={(e) => setVoiceTranscripts(e.target.value)} />
        </label>
        <button type="submit" disabled={loading} className="w-full rounded-lg bg-orange-600 py-2.5 font-semibold text-white hover:bg-orange-500 disabled:opacity-50">
          {loading ? "Generating…" : "Generate report"}
        </button>
      </form>

      <div className="rounded-xl border bg-slate-50 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Report preview</h2>
          {report && (
            <button type="button" onClick={download} className="text-sm font-medium text-orange-700 hover:underline">
              Download .txt
            </button>
          )}
        </div>
        {report ? (
          <pre className="mt-4 max-h-[600px] overflow-auto whitespace-pre-wrap rounded-lg bg-white p-4 text-xs text-slate-800">
            {report.bodyText}
          </pre>
        ) : (
          <p className="mt-4 text-sm text-slate-500">Complete the capture form to generate a completion report.</p>
        )}
      </div>
    </div>
  );
}
