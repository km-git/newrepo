"use client";

import { useCallback, useEffect, useState } from "react";
import type { FollowUpDraft, Quote } from "@/lib/types";

const statusStyle: Record<string, string> = {
  stale: "bg-amber-100 text-amber-800",
  sent: "bg-slate-100 text-slate-700",
  won: "bg-green-100 text-green-800",
  lost: "bg-red-100 text-red-800",
};

export function ChaseDashboard() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [stale, setStale] = useState<Quote[]>([]);
  const [drafts, setDrafts] = useState<FollowUpDraft[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [mockMode, setMockMode] = useState(true);
  const [selected, setSelected] = useState<Quote | null>(null);
  const [draft, setDraft] = useState<FollowUpDraft | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [sendMsg, setSendMsg] = useState("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/quotes");
    const data = await res.json();
    setQuotes(data.quotes);
    setStale(data.stale);
    setDrafts(data.drafts);
    setPendingCount(data.pendingCount);
    setMockMode(data.mockMode);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function createDraft(quoteId: string) {
    const res = await fetch("/api/followups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "draft", quoteId }),
    });
    const data = await res.json();
    if (data.draft) {
      setDraft(data.draft);
      setEditSubject(data.draft.subject);
      setEditBody(data.draft.body);
      const quote = quotes.find((q) => q.id === quoteId);
      if (quote) setSelected(quote);
    }
    await refresh();
  }

  async function approve() {
    if (!draft) return;
    await fetch("/api/followups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "update",
        draftId: draft.id,
        subject: editSubject,
        body: editBody,
      }),
    });
    const res = await fetch("/api/followups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve", draftId: draft.id }),
    });
    const data = await res.json();
    setSendMsg(data.result?.message ?? "Sent");
    setDraft(null);
    setSelected(null);
    await refresh();
  }

  async function reject() {
    if (!draft) return;
    await fetch("/api/followups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", draftId: draft.id }),
    });
    setDraft(null);
    await refresh();
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap gap-3 text-sm text-slate-500">
        <span>{stale.length} stale quotes</span>
        <span>·</span>
        <span>{pendingCount} drafts pending</span>
        {mockMode && <span className="text-teal-600">· Mock email</span>}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Quote inbox</h2>
          <div className="mt-4 space-y-3">
            {quotes.map((q) => (
              <div
                key={q.id}
                className={`rounded-lg border p-4 ${selected?.id === q.id ? "border-teal-400 bg-teal-50/30" : ""}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{q.contactName}</p>
                    <p className="text-xs text-slate-500">
                      {q.quoteNumber} · ${q.amountAud.toLocaleString()} · {q.daysSinceSent}d ago
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle[q.status] ?? "bg-slate-100"}`}>
                    {q.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{q.jobDescription}</p>
                {needsFollowUpButton(q) && (
                  <button
                    type="button"
                    onClick={() => createDraft(q.id)}
                    className="mt-2 text-sm font-medium text-teal-600 hover:underline"
                  >
                    Draft follow-up
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Follow-up editor</h2>
          {!draft ? (
            <p className="mt-4 text-sm text-slate-500">Select a stale quote to draft a follow-up.</p>
          ) : (
            <div className="mt-4 space-y-4">
              <p className="text-xs text-slate-500">
                Stage {draft.stage} · {draft.tone} tone
              </p>
              <input
                type="text"
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
              />
              <textarea
                rows={6}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={approve}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500"
                >
                  Approve &amp; send
                </button>
                <button
                  type="button"
                  onClick={reject}
                  className="rounded-lg border px-4 py-2 text-sm text-slate-600"
                >
                  Reject
                </button>
              </div>
              {sendMsg && <p className="text-sm text-green-700">{sendMsg}</p>}
            </div>
          )}
        </section>
      </div>

      {drafts.length > 0 && (
        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Recent drafts</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {drafts.slice(0, 5).map((d) => (
              <li key={d.id} className="flex justify-between text-slate-600">
                <span>{d.subject}</span>
                <span className="text-xs uppercase">{d.status}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function needsFollowUpButton(q: Quote): boolean {
  return q.threadState === "awaiting_reply" && q.status !== "won" && q.status !== "lost" && q.daysSinceSent >= 3;
}
