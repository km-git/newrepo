import { randomUUID } from "crypto";
import type {
  ChecklistEntry,
  ChecklistStatus,
  GapItem,
  GapReport,
  StaffCredential,
  CredentialStatus,
} from "./types";
import { PRACTICE_STANDARDS, getStandard } from "./practice-standards";

const EXPIRY_WARNING_DAYS = 30;

export function credentialStatus(expiryDate: string, now = new Date()): CredentialStatus {
  const expiry = new Date(expiryDate);
  const days = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  if (days < 0) return "expired";
  if (days <= EXPIRY_WARNING_DAYS) return "expiring_soon";
  return "valid";
}

export function computeReadinessScore(entries: ChecklistEntry[]): number {
  if (entries.length === 0) return 0;
  const complete = entries.filter((e) => e.status === "complete").length;
  return Math.round((complete / entries.length) * 100);
}

export function buildGapReport(
  providerName: string,
  entries: ChecklistEntry[],
  credentials: StaffCredential[],
): GapReport {
  const gaps: GapItem[] = [];

  for (const std of PRACTICE_STANDARDS) {
    const entry = entries.find((e) => e.standardId === std.id);
    const status: ChecklistStatus = entry?.status ?? "not_started";
    const missingEvidence =
      !entry || entry.evidenceIds.length === 0 || status === "gap";

    if (status !== "complete" || missingEvidence) {
      gaps.push({
        standardId: std.id,
        module: std.module,
        outcome: std.outcome,
        indicator: std.indicator,
        status: missingEvidence && status !== "gap" ? "gap" : status,
        missingEvidence,
        notes: entry?.notes ?? "",
      });
    }
  }

  const expiringCredentials = credentials.filter(
    (c) => c.status === "expiring_soon" || c.status === "expired",
  );

  const readinessScore = computeReadinessScore(entries);
  const gapCount = gaps.length;

  const summary =
    gapCount === 0
      ? `${providerName} appears audit-ready across ${PRACTICE_STANDARDS.length} mapped indicators. Review expiring credentials before the audit.`
      : `${providerName} has ${gapCount} gap(s) across ${PRACTICE_STANDARDS.length} indicators (${readinessScore}% readiness). Address missing evidence and credential expiries before the auditor arrives.`;

  return {
    id: randomUUID(),
    generatedAt: new Date().toISOString(),
    providerName,
    readinessScore,
    gaps,
    expiringCredentials,
    summary,
    disclaimer:
      "INFORMATIONAL ONLY — This gap report is an organisation tool, not compliance or legal advice. " +
      "Validate all indicators against current NDIS Practice Standards and seek qualified advice.",
  };
}

export function formatGapReportText(report: GapReport): string {
  const lines = [
    `AUDIT READINESS GAP REPORT (DRAFT)`,
    `Provider: ${report.providerName}`,
    `Generated: ${report.generatedAt}`,
    `Readiness score: ${report.readinessScore}%`,
    ``,
    `SUMMARY`,
    report.summary,
    ``,
    `GAPS (${report.gaps.length})`,
    ...report.gaps.map(
      (g, i) =>
        `${i + 1}. [${g.standardId}] ${g.module} — ${g.outcome}\n` +
        `   Indicator: ${g.indicator}\n` +
        `   Status: ${g.status}${g.missingEvidence ? " (missing evidence)" : ""}\n` +
        (g.notes ? `   Notes: ${g.notes}\n` : ""),
    ),
    ``,
    `CREDENTIAL ALERTS (${report.expiringCredentials.length})`,
    ...report.expiringCredentials.map(
      (c) =>
        `- ${c.staffName}: ${c.credentialType} expires ${c.expiryDate} [${c.status}]`,
    ),
    ``,
    report.disclaimer,
  ];
  return lines.join("\n");
}

export function deriveChecklistStatus(
  evidenceCount: number,
  notes: string,
): ChecklistStatus {
  if (evidenceCount >= 2) return "complete";
  if (evidenceCount === 1) return "in_progress";
  if (notes) return "in_progress";
  return "not_started";
}

export function updateEntryFromEvidence(
  entry: ChecklistEntry,
  evidenceCount: number,
): ChecklistEntry {
  const status = deriveChecklistStatus(evidenceCount, entry.notes);
  return {
    ...entry,
    status: status === "not_started" && evidenceCount === 0 ? "gap" : status,
    updatedAt: new Date().toISOString(),
  };
}

export { getStandard };
