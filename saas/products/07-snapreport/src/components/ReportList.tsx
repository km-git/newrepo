"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { FieldReport } from "@/lib/types";

export function ReportList() {
  const [reports, setReports] = useState<FieldReport[]>([]);
  const [businessName, setBusinessName] = useState("");

  useEffect(() => {
    fetch("/api/reports")
      .then((r) => r.json())
      .then((d) => {
        setReports(d.reports);
        setBusinessName(d.businessName);
      });
  }, []);

  return (
    <div>
      <p className="text-sm text-slate-500">{businessName}</p>
      <div className="mt-4 space-y-3">
        {reports.map((r) => (
          <div key={r.id} className="rounded-lg border bg-white p-4">
            <p className="font-medium">{r.jobRef} — {r.clientName}</p>
            <p className="text-sm text-slate-500">{r.siteAddress} · {r.trade}</p>
            <p className="mt-1 text-xs text-slate-400">
              {r.photos.length} photos · {r.voiceNotes.length} voice notes · {r.status}
            </p>
          </div>
        ))}
      </div>
      <Link href="/capture" className="mt-6 inline-block rounded-lg bg-orange-600 px-4 py-2 text-sm font-medium text-white">
        New capture
      </Link>
    </div>
  );
}
