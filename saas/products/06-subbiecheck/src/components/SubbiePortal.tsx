"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Subcontractor } from "@/lib/types";
import { DOC_LABELS } from "@/lib/types";

export function SubbiePortal({ subbieId }: { subbieId: string }) {
  const [subbie, setSubbie] = useState<Subcontractor | null>(null);
  const [fileName, setFileName] = useState("");
  const [rawText, setRawText] = useState("");
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/documents?subbieId=${subbieId}`)
      .then((r) => r.json())
      .then((d) => setSubbie(d.subbie));
  }, [subbieId]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "upload", subbieId, fileName, rawText }),
    });
    const data = await res.json();
    if (data.document) {
      setResult(
        `Uploaded as ${DOC_LABELS[data.document.documentType as keyof typeof DOC_LABELS]} — pending builder review`,
      );
      setFileName("");
      setRawText("");
    }
  }

  if (!subbie) return <p className="text-slate-500">Loading…</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold">{subbie.companyName}</h1>
      <p className="text-slate-600">Upload your compliance documents for {subbie.trade}</p>

      <form onSubmit={upload} className="mt-8 space-y-4 rounded-xl border bg-white p-6">
        <label className="block text-sm">
          <span className="font-medium">File name</span>
          <input
            required
            className="mt-1 w-full rounded-lg border px-3 py-2"
            placeholder="e.g. Public_Liability_2026.pdf"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Paste certificate text (demo — no file upload in MVP)</span>
          <textarea
            required
            rows={5}
            className="mt-1 w-full rounded-lg border px-3 py-2 font-mono text-xs"
            placeholder="Paste the text from your insurance certificate or licence..."
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
          />
        </label>
        <button
          type="submit"
          className="rounded-lg bg-teal-600 px-6 py-2.5 font-medium text-white hover:bg-teal-500"
        >
          Upload for review
        </button>
        {result && <p className="text-sm text-green-700">{result}</p>}
      </form>

      <p className="mt-6 text-xs text-slate-500">
        Documents are parsed for expiry dates and policy fields. Your builder confirms all details.
      </p>
      <Link href="/dashboard" className="mt-4 inline-block text-sm text-teal-700 hover:underline">
        ← Back to compliance board
      </Link>
    </div>
  );
}
