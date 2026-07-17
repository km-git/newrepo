import { describe, it, expect, beforeEach } from "vitest";
import { matchEvidenceToStandards } from "./evidence-matcher";
import {
  buildGapReport,
  credentialStatus,
  computeReadinessScore,
} from "./gap-report";
import { PRACTICE_STANDARDS } from "./practice-standards";
import {
  resetStore,
  listChecklist,
  listCredentials,
  generateReport,
  addEvidence,
  getReportText,
} from "./store";
import type { ChecklistEntry } from "./types";

describe("evidence-matcher", () => {
  it("matches privacy policy to standard 1.2", () => {
    const ids = matchEvidenceToStandards({
      title: "Privacy and Confidentiality Policy",
      documentRef: "POL-PRIV",
    });
    expect(ids).toContain("1.2");
  });

  it("matches risk register to standard 2.2", () => {
    const ids = matchEvidenceToStandards({
      title: "Risk Register Q2",
      documentRef: "RISK-REG",
    });
    expect(ids).toContain("2.2");
  });
});

describe("gap-report", () => {
  it("computes readiness score", () => {
    const entries: ChecklistEntry[] = PRACTICE_STANDARDS.map((s, i) => ({
      standardId: s.id,
      status: i < 5 ? "complete" : "gap",
      evidenceIds: i < 5 ? ["ev-1"] : [],
      notes: "",
      updatedAt: new Date().toISOString(),
    }));
    expect(computeReadinessScore(entries)).toBe(56);
  });

  it("flags expiring credentials", () => {
    expect(credentialStatus("2020-01-01")).toBe("expired");
    const soon = new Date();
    soon.setDate(soon.getDate() + 10);
    expect(credentialStatus(soon.toISOString().slice(0, 10))).toBe("expiring_soon");
  });

  it("builds gap report with disclaimer", () => {
    const report = buildGapReport("Test Provider", [], []);
    expect(report.disclaimer).toContain("not compliance");
    expect(report.gaps.length).toBe(PRACTICE_STANDARDS.length);
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("loads demo checklist and credentials", () => {
    const checklist = listChecklist();
    expect(checklist.length).toBe(PRACTICE_STANDARDS.length);
    const creds = listCredentials();
    expect(creds.length).toBe(3);
  });

  it("auto-matches evidence on upload", () => {
    const ev = addEvidence("Incident Management Procedure", "POL-INC");
    expect(ev.matchedStandardIds).toContain("4.2");
  });

  it("generates downloadable gap report text", () => {
    generateReport();
    const text = getReportText();
    expect(text).toContain("AUDIT READINESS GAP REPORT");
    expect(text).toContain("Demo Care Supports");
  });
});
