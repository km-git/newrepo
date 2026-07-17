"use client";

import { useCallback, useEffect, useState } from "react";
import type { Invoice, ReminderDraft } from "@/lib/types";

const toneBadge: Record<string, string> = {
  friendly: "bg-green-100 text-green-800",
  firm: "bg-amber-100 text-amber-800",
  final: "bg-red-100 text-red-800",
};

export function ChaseDashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [drafts, setDrafts] = useState<ReminderDraft[]>([]);
  const [mockMode, setMockMode] = useState(true);
  const [selectedDraft, setSelectedDraft] = useState<ReminderDraft | null>(null);
  const [replyText, setReplyText] = useState("");
  const [replyResult, setReplyResult] = useState<string | null>(null);
  const [testInvoiceId, setTestInvoiceId] = useState<string>("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/invoices");
    const data = await res.json();
    setInvoices(data.invoices);
    setDrafts(data.pendingDrafts);
    setMockMode(data.mockMode);
    if (data.invoices.length && !testInvoiceId) {
      setTestInvoiceId(data.invoices[0].id);
    }
  }, [testInvoiceId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function generateDraft(invoiceId: string) {
    await fetch("/api/chase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "generate", invoiceId }),
    });
    await refresh();
  }

  async function approve(draftId: string) {
    await fetch("/api/chase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve", draftId }),
    });
    setSelectedDraft(null);
    await refresh();
  }

  async function reject(draftId: string) {
    await fetch("/api/chase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", draftId }),
    });
    setSelectedDraft(null);
    await refresh();
  }

  async function testReply() {
    const res = await fetch("/api/chase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "classify_reply",
        invoiceId: testInvoiceId,
        replyText: replyText,
      }),
    });
    const data = await res.json();
    setReplyResult(
      `${data.classification.intent} (${data.classification.confidence}): ${data.classification.suggestedAction}`,
    );
    await refresh();
  }

  const totalOverdue = invoices.reduce((s, i) => s + i.amountDue, 0);

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Overdue invoices" value={String(invoices.length)} />
        <Stat label="Total outstanding" value={`$${totalOverdue.toLocaleString()}`} />
        <Stat label="Mode" value={mockMode ? "Mock Xero" : "Live Xero"} />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Aged receivables</h2>
        <p className="mt-1 text-sm text-slate-500">
          Invoice metadata only — reminders require your approval before sending.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="pb-2 pr-4">Invoice</th>
                <th className="pb-2 pr-4">Contact</th>
                <th className="pb-2 pr-4">Amount</th>
                <th className="pb-2 pr-4">Days overdue</th>
                <th className="pb-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-b border-slate-100">
                  <td className="py-3 pr-4 font-medium">{inv.invoiceNumber}</td>
                  <td className="py-3 pr-4">{inv.contactName}</td>
                  <td className="py-3 pr-4">${inv.amountDue.toLocaleString()}</td>
                  <td className="py-3 pr-4">
                    <span
                      className={
                        inv.daysOverdue > 30
                          ? "font-semibold text-red-600"
                          : inv.daysOverdue > 14
                            ? "text-amber-600"
                            : ""
                      }
                    >
                      {inv.daysOverdue}d
                    </span>
                  </td>
                  <td className="py-3">
                    <button
                      type="button"
                      onClick={() => generateDraft(inv.id)}
                      className="text-sm font-medium text-emerald-700 hover:underline"
                    >
                      Draft reminder
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">
          Approval queue ({drafts.length})
        </h2>
        {drafts.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            No drafts pending. Click &quot;Draft reminder&quot; on an overdue invoice.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {drafts.map((d) => {
              const inv = invoices.find((i) => i.id === d.invoiceId);
              return (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-4"
                >
                  <div>
                    <p className="font-medium">
                      {inv?.invoiceNumber} — {inv?.contactName}
                    </p>
                    <p className="text-sm text-slate-500">{d.subject}</p>
                    <span
                      className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${toneBadge[d.tone]}`}
                    >
                      {d.tone}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedDraft(d)}
                      className="text-sm text-slate-600 hover:underline"
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      onClick={() => approve(d.id)}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
                    >
                      Approve &amp; send
                    </button>
                    <button
                      type="button"
                      onClick={() => reject(d.id)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {selectedDraft && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Reminder preview</h2>
            <button
              type="button"
              onClick={() => setSelectedDraft(null)}
              className="text-sm text-slate-500 hover:underline"
            >
              Close
            </button>
          </div>
          <p className="mt-2 text-sm font-medium">{selectedDraft.subject}</p>
          <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-white p-4 text-sm text-slate-800">
            {selectedDraft.body}
          </pre>
        </section>
      )}

      <section className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6">
        <h2 className="font-semibold">Reply classifier demo</h2>
        <p className="mt-1 text-sm text-slate-500">
          Test how debtor replies are classified (paid / dispute / promise / opt-out).
        </p>
        <textarea
          className="mt-3 w-full rounded-lg border border-slate-300 p-3 text-sm"
          rows={2}
          placeholder="e.g. Payment sent yesterday via EFT"
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
        />
        <button
          type="button"
          onClick={testReply}
          className="mt-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white"
        >
          Classify reply
        </button>
        {replyResult && (
          <p className="mt-2 text-sm text-emerald-700">{replyResult}</p>
        )}
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
