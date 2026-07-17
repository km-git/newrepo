"use client";

import { useCallback, useEffect, useState } from "react";
import type { InboundEmail, JobCard } from "@/lib/types";

const urgencyStyle: Record<string, string> = {
  emergency: "bg-red-100 text-red-800",
  soon: "bg-amber-100 text-amber-800",
  routine: "bg-slate-100 text-slate-700",
};

export function InboxDashboard() {
  const [emails, setEmails] = useState<InboundEmail[]>([]);
  const [jobs, setJobs] = useState<JobCard[]>([]);
  const [mockMode, setMockMode] = useState(true);
  const [selectedJob, setSelectedJob] = useState<JobCard | null>(null);
  const [pushResult, setPushResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/inbox");
    const data = await res.json();
    setEmails(data.emails);
    setJobs(data.jobs);
    setMockMode(data.mockMode);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function processEmail(emailId: string) {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "process", emailId }),
    });
    const data = await res.json();
    setSelectedJob(data.job);
    await refresh();
  }

  async function confirmPush(jobId: string, platform: "servicem8" | "tradify") {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "confirm", jobId, platform }),
    });
    const data = await res.json();
    setPushResult(data.push?.message ?? "Done");
    setSelectedJob(data.job);
    await refresh();
  }

  async function reject(jobId: string) {
    await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", jobId }),
    });
    setSelectedJob(null);
    await refresh();
  }

  const pending = jobs.filter((j) => j.status === "pending_review");

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Inbox" value={String(emails.length)} />
        <Stat label="Pending review" value={String(pending.length)} />
        <Stat label="Mode" value={mockMode ? "Mock APIs" : "Live"} />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Inbox</h2>
        <p className="mt-1 text-sm text-slate-500">
          Parse enquiry emails into structured job cards — confirm before pushing to ServiceM8.
        </p>
        <div className="mt-4 space-y-3">
          {emails.map((em) => {
            const hasJob = jobs.some((j) => j.emailId === em.id);
            return (
              <div
                key={em.id}
                className="flex items-start justify-between rounded-lg border border-slate-200 p-4"
              >
                <div>
                  <p className="font-medium text-slate-900">{em.subject}</p>
                  <p className="text-sm text-slate-500">{em.from}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600">{em.body}</p>
                </div>
                {!hasJob ? (
                  <button
                    type="button"
                    onClick={() => processEmail(em.id)}
                    className="shrink-0 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
                  >
                    Extract job
                  </button>
                ) : (
                  <span className="shrink-0 text-xs font-medium text-green-700">
                    Processed
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {selectedJob && (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-6">
          <h2 className="text-lg font-semibold">Job card preview</h2>
          {selectedJob.ambiguities.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm text-amber-700">
              {selectedJob.ambiguities.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <Field label="Customer" value={selectedJob.data.customerName} />
            <Field label="Phone" value={selectedJob.data.customerPhone ?? "—"} />
            <Field label="Address" value={selectedJob.data.siteAddress} />
            <Field label="Suburb" value={selectedJob.data.suburb ?? "—"} />
            <Field label="Job type" value={selectedJob.data.jobType} />
            <Field label="Urgency" value={selectedJob.data.urgency} badge />
            <Field label="Description" value={selectedJob.data.description} wide />
          </dl>
          {selectedJob.status === "pending_review" && (
            <div className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => confirmPush(selectedJob.id, "servicem8")}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
              >
                Confirm → ServiceM8
              </button>
              <button
                type="button"
                onClick={() => confirmPush(selectedJob.id, "tradify")}
                className="rounded-lg border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
              >
                Confirm → Tradify
              </button>
              <button
                type="button"
                onClick={() => reject(selectedJob.id)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600"
              >
                Reject
              </button>
            </div>
          )}
          {selectedJob.status === "pushed" && (
            <p className="mt-4 text-sm font-medium text-green-700">
              Pushed to {selectedJob.pushPlatform}: {selectedJob.externalJobId}
            </p>
          )}
          {pushResult && (
            <p className="mt-2 text-sm text-slate-600">{pushResult}</p>
          )}
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Job history</h2>
        {jobs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No jobs yet.</p>
        ) : (
          <table className="mt-4 w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="pb-2">Customer</th>
                <th className="pb-2">Job</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Platform</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-b border-slate-100">
                  <td className="py-2">{j.data.customerName}</td>
                  <td className="py-2">{j.data.jobType}</td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${urgencyStyle[j.data.urgency]}`}
                    >
                      {j.status}
                    </span>
                  </td>
                  <td className="py-2 text-slate-500">
                    {j.externalJobId ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

function Field({
  label,
  value,
  wide,
  badge,
}: {
  label: string;
  value: string;
  wide?: boolean;
  badge?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <dt className="font-medium text-slate-500">{label}</dt>
      <dd className={badge ? `mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${urgencyStyle[value] ?? ""}` : "text-slate-900"}>
        {value}
      </dd>
    </div>
  );
}
