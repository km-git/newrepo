"use client";

import type { LeadCard } from "@/lib/types";

const urgencyColors: Record<string, string> = {
  emergency: "bg-red-100 text-red-800 border-red-200",
  soon: "bg-amber-100 text-amber-800 border-amber-200",
  routine: "bg-slate-100 text-slate-700 border-slate-200",
};

export function LeadCardView({
  lead,
  onStatusChange,
}: {
  lead: LeadCard;
  onStatusChange?: (id: string, status: LeadCard["status"]) => void;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {lead.trade} · {lead.status}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">
            {lead.jobType}
          </h3>
          <p className="text-sm text-slate-600">{lead.suburb}</p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${urgencyColors[lead.urgency]}`}
        >
          {lead.urgency}
        </span>
      </div>

      <dl className="mt-4 grid gap-2 text-sm">
        <div className="flex gap-2">
          <dt className="font-medium text-slate-500">Phone</dt>
          <dd>
            <a href={`tel:${lead.phone}`} className="text-blue-600 hover:underline">
              {lead.phone}
            </a>
          </dd>
        </div>
        {lead.notes && (
          <div className="flex gap-2">
            <dt className="font-medium text-slate-500">Notes</dt>
            <dd className="text-slate-700">{lead.notes}</dd>
          </div>
        )}
        <div className="flex gap-2">
          <dt className="font-medium text-slate-500">Summary</dt>
          <dd className="text-slate-700">{lead.summary}</dd>
        </div>
      </dl>

      {onStatusChange && lead.status === "ready" && (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => onStatusChange(lead.id, "called")}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            Mark called
          </button>
          <button
            type="button"
            onClick={() => onStatusChange(lead.id, "won")}
            className="rounded-lg border border-green-600 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50"
          >
            Won
          </button>
          <button
            type="button"
            onClick={() => onStatusChange(lead.id, "lost")}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Lost
          </button>
        </div>
      )}
    </article>
  );
}
