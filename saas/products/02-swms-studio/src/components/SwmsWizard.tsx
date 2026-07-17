"use client";

import { useState } from "react";
import type { SwmsDocument, Trade } from "@/lib/types";

const TRADES: Trade[] = ["electrical", "plumbing", "carpentry", "general"];

export function SwmsWizard() {
  const [form, setForm] = useState({
    businessName: "",
    siteAddress: "",
    trade: "electrical" as Trade,
    jobDescription: "",
    tasks: "",
    siteConditions: "",
    supervisor: "",
    workers: "",
    emergencyContact: "000",
  });
  const [doc, setDoc] = useState<SwmsDocument | null>(null);
  const [loading, setLoading] = useState(false);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch("/api/swms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        tasks: form.tasks.split("\n").filter(Boolean),
        siteConditions: form.siteConditions.split("\n").filter(Boolean),
      }),
    });
    const data = (await res.json()) as { document: SwmsDocument };
    setDoc(data.document);
    setLoading(false);
  }

  function download() {
    if (!doc) return;
    const blob = new Blob([doc.bodyText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `swms-draft-${doc.id.slice(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <form onSubmit={generate} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Guided SWMS builder</h2>
        {(
          [
            ["businessName", "Business name", "text"],
            ["siteAddress", "Site address", "text"],
            ["supervisor", "Supervisor", "text"],
            ["workers", "Workers on site", "text"],
            ["emergencyContact", "Emergency contact", "text"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="block text-sm">
            <span className="font-medium text-slate-700">{label}</span>
            <input
              required={key === "businessName"}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form[key]}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ))}
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Trade</span>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.trade}
            onChange={(e) => setForm({ ...form, trade: e.target.value as Trade })}
          >
            {TRADES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Job description</span>
          <textarea
            required
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.jobDescription}
            onChange={(e) => setForm({ ...form, jobDescription: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Tasks (one per line)</span>
          <textarea
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.tasks}
            onChange={(e) => setForm({ ...form, tasks: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Site conditions (one per line)</span>
          <textarea
            rows={2}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.siteConditions}
            onChange={(e) => setForm({ ...form, siteConditions: e.target.value })}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-amber-600 py-2.5 font-semibold text-white hover:bg-amber-500 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate SWMS draft"}
        </button>
      </form>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Preview</h2>
          {doc && (
            <button
              type="button"
              onClick={download}
              className="text-sm font-medium text-amber-700 hover:underline"
            >
              Download .txt
            </button>
          )}
        </div>
        {doc ? (
          <pre className="mt-4 max-h-[600px] overflow-auto whitespace-pre-wrap rounded-lg bg-white p-4 text-xs text-slate-800">
            {doc.bodyText}
          </pre>
        ) : (
          <p className="mt-4 text-sm text-slate-500">
            Fill the form and generate a draft SWMS with hazards, controls, and
            sign-off blocks.
          </p>
        )}
      </div>
    </div>
  );
}
