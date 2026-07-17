import { describe, it, expect, beforeEach } from "vitest";
import {
  parseCertificate,
  detectDocumentType,
  expiryStatus,
  daysUntilExpiry,
} from "./cert-parser";
import { computeSubbieCompliance, boardSummary } from "./compliance-board";
import {
  resetStore,
  listSubbies,
  uploadDocument,
  confirmDocument,
  listPendingDocuments,
} from "./store";
import type { ComplianceDocument } from "./types";
import { DOC_LABELS } from "./types";

describe("cert-parser", () => {
  it("parses public liability certificate fields", () => {
    const parsed = parseCertificate(
      "PLI_2026.pdf",
      "Public Liability Insurance. Insurer: QBE Insurance. Policy: PL-8844221. Coverage $20 million. Expiry: 15/08/2026",
    );
    expect(parsed.expiryDate).toBe("2026-08-15");
    expect(parsed.policyNumber).toBe("PL-8844221");
    expect(parsed.coverageAmount).toContain("$20");
    expect(parsed.confidence).toBe("high");
  });

  it("detects document type from filename", () => {
    expect(detectDocumentType("White_Card_John.pdf", "")).toBe("white_card");
    expect(detectDocumentType("Workers_Comp_Cert.pdf", "workcover")).toBe("workers_comp");
  });

  it("flags expiring and expired dates", () => {
    expect(expiryStatus("2020-01-01")).toBe("expired");
    const soon = new Date();
    soon.setDate(soon.getDate() + 14);
    expect(expiryStatus(soon.toISOString().slice(0, 10))).toBe("expiring");
    expect(daysUntilExpiry("2099-12-31")).toBeGreaterThan(1000);
  });
});

describe("compliance-board", () => {
  it("marks subbie non-compliant when required doc missing", () => {
    const docs: ComplianceDocument[] = [
      {
        id: "1",
        subbieId: "s1",
        documentType: "public_liability",
        fileName: "pli.pdf",
        uploadedAt: new Date().toISOString(),
        parsed: { expiryDate: "2027-01-01", confidence: "high" },
        status: "confirmed",
      },
    ];
    const result = computeSubbieCompliance("s1", docs);
    expect(result.compliance).toBe("non_compliant");
    expect(result.missingDocs).toContain("workers_comp");
  });

  it("summarises board counts", () => {
    const summary = boardSummary([
      { id: "1", companyName: "A", contactName: "", contactEmail: "", trade: "", compliance: "compliant", missingDocs: [], expiringDocs: [] },
      { id: "2", companyName: "B", contactName: "", contactEmail: "", trade: "", compliance: "non_compliant", missingDocs: ["white_card"], expiringDocs: [] },
    ]);
    expect(summary.compliant).toBe(1);
    expect(summary.nonCompliant).toBe(1);
  });
});

describe("store workflow", () => {
  beforeEach(() => resetStore());

  it("loads demo subbies", () => {
    expect(listSubbies().length).toBe(3);
  });

  it("uploads and confirms document", () => {
    const doc = uploadDocument(
      "sub-003",
      "White_Card_Dave.pdf",
      "Construction induction white card. Expiry: 2028-06-01",
    );
    expect(doc).toBeDefined();
    expect(doc!.documentType).toBe("white_card");
    expect(listPendingDocuments().some((d) => d.id === doc!.id)).toBe(true);

    const confirmed = confirmDocument(doc!.id)!;
    expect(confirmed.status).toBe("confirmed");
    expect(DOC_LABELS[confirmed.documentType]).toContain("White Card");
  });
});
