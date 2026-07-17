"use client";

import { useCallback, useEffect, useState } from "react";
import type { AreaPage, SuburbData } from "@/lib/types";

export function PageStudio() {
  const [suburbs, setSuburbs] = useState<SuburbData[]>([]);
  const [pages, setPages] = useState<AreaPage[]>([]);
  const [selected, setSelected] = useState<AreaPage | null>(null);
  const [publishMsg, setPublishMsg] = useState("");
  const [businessName, setBusinessName] = useState("Ace Plumbing Sydney");
  const [service, setService] = useState("Emergency Plumber");
  const [trade] = useState("Plumber");
  const [suburbSlug, setSuburbSlug] = useState("parramatta");
  const [jobRefs, setJobRefs] = useState("blocked drain on Macquarie St");
  const [phone] = useState("1300 000 111");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/pages");
    const data = await res.json();
    setSuburbs(data.suburbs);
    setPages(data.pages);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function generatePage(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "create",
        input: {
          businessName,
          service,
          trade,
          suburbSlug,
          phone,
          jobReferences: jobRefs.split("\n").map((s) => s.trim()).filter(Boolean),
        },
      }),
    });
    const data = await res.json();
    setSelected(data.page);
    await refresh();
  }

  async function approve(id: string) {
    await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve", pageId: id }),
    });
    await refresh();
    const res = await fetch(`/api/generate?id=${id}`);
    const data = await res.json();
    setSelected(data.page);
  }

  async function publish(id: string) {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "publish", pageId: id }),
    });
    const data = await res.json();
    setPublishMsg(data.result?.message ?? "Done");
    setSelected(data.page);
    await refresh();
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <form onSubmit={generatePage} className="space-y-4 rounded-xl border bg-white p-6">
        <h2 className="text-lg font-semibold">Generate suburb page</h2>
        <label className="block text-sm">
          <span className="font-medium">Business name</span>
          <input className="mt-1 w-full rounded-lg border px-3 py-2" value={businessName} onChange={(e) => setBusinessName(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Service</span>
          <input className="mt-1 w-full rounded-lg border px-3 py-2" value={service} onChange={(e) => setService(e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Suburb</span>
          <select className="mt-1 w-full rounded-lg border px-3 py-2" value={suburbSlug} onChange={(e) => setSuburbSlug(e.target.value)}>
            {suburbs.map((s) => (
              <option key={s.slug} value={s.slug}>{s.name} ({s.postcode})</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium">Local job references (one per line)</span>
          <textarea rows={2} className="mt-1 w-full rounded-lg border px-3 py-2 text-xs" value={jobRefs} onChange={(e) => setJobRefs(e.target.value)} />
        </label>
        <button type="submit" className="w-full rounded-lg bg-sky-600 py-2.5 font-semibold text-white hover:bg-sky-500">
          Generate page
        </button>
      </form>

      <div className="space-y-6">
        {selected && (
          <section className="rounded-xl border border-sky-200 bg-sky-50/50 p-6">
            <h2 className="font-semibold">{selected.title}</h2>
            <p className="mt-1 text-xs text-slate-500">{selected.metaDescription}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Score label="Overall" value={selected.quality.overall} />
              <Score label="Local" value={selected.quality.localGrounding} />
              <Score label="Unique" value={selected.quality.uniqueness} />
            </div>
            {selected.quality.warnings.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-xs text-amber-700">
                {selected.quality.warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            )}
            <pre className="mt-4 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-white p-3 text-xs">{selected.bodyText}</pre>
            <div className="mt-4 flex gap-2">
              {selected.status !== "approved" && selected.status !== "published" && (
                <button type="button" onClick={() => approve(selected.id)} className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white">Approve</button>
              )}
              {selected.status === "approved" && (
                <button type="button" onClick={() => publish(selected.id)} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white">Publish to WordPress</button>
              )}
            </div>
            {publishMsg && <p className="mt-2 text-sm text-green-700">{publishMsg}</p>}
          </section>
        )}

        <section className="rounded-xl border bg-white p-6">
          <h2 className="font-semibold">Pages ({pages.length})</h2>
          <ul className="mt-3 space-y-2">
            {pages.map((p) => (
              <li key={p.id}>
                <button type="button" onClick={() => setSelected(p)} className="w-full rounded-lg border p-3 text-left text-sm hover:bg-slate-50">
                  <span className="font-medium">{p.suburb.name} — {p.input.service}</span>
                  <span className="ml-2 text-xs text-slate-500">{p.status} · score {p.quality.overall}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium">
      {label}: {value}
    </span>
  );
}
