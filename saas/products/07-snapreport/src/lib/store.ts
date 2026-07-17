import type { CaptureInput, FieldReport } from "./types";
import { assembleReport } from "./report-assembler";

const globalStore = globalThis as typeof globalThis & {
  __srStore?: {
    businessName: string;
    reports: Map<string, FieldReport>;
  };
};

function store() {
  if (!globalStore.__srStore) {
    globalStore.__srStore = {
      businessName: "Demo Spark Electrical",
      reports: new Map(),
    };
  }
  return globalStore.__srStore;
}

export function getBusinessName(): string {
  return store().businessName;
}

export function listReports(): FieldReport[] {
  return [...store().reports.values()].sort(
    (a, b) => new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime(),
  );
}

export function getReport(id: string): FieldReport | undefined {
  return store().reports.get(id);
}

export function createReport(input: CaptureInput): FieldReport {
  const report = assembleReport(input);
  store().reports.set(report.id, report);
  return report;
}

export function markReportReady(id: string): FieldReport | null {
  const report = store().reports.get(id);
  if (!report) return null;
  report.status = "ready";
  return report;
}

export function seedDemoReport(): FieldReport {
  return createReport({
    trade: "electrical",
    jobRef: "JOB-2847",
    siteAddress: "18 River Road, Penrith NSW 2750",
    clientName: "James & Sarah Wilson",
    technician: "Tom Bradley",
    photoLabels: ["Switchboard before", "Switchboard after", "RCD test reading"],
    voiceTranscripts: [
      "Replaced main switchboard and installed new RCD protection. All circuits tested and passed compliance.",
      "Recommend annual RCD test and consider surge protection upgrade within 12 months.",
    ],
  });
}

export function resetStore(): void {
  globalStore.__srStore = undefined;
}
