import type {
  ComplianceDocument,
  ComplianceLevel,
  DocumentType,
  Subcontractor,
} from "./types";
import { REQUIRED_DOCS, DOC_LABELS } from "./types";
import { expiryStatus } from "./cert-parser";

export function computeSubbieCompliance(
  subbieId: string,
  docs: ComplianceDocument[],
): Pick<Subcontractor, "compliance" | "missingDocs" | "expiringDocs"> {
  const confirmed = docs.filter(
    (d) => d.subbieId === subbieId && d.status === "confirmed",
  );

  const missingDocs: DocumentType[] = [];
  const expiringDocs: string[] = [];

  for (const req of REQUIRED_DOCS) {
    const doc = confirmed.find((d) => d.documentType === req);
    if (!doc) {
      missingDocs.push(req);
      continue;
    }
    const status = expiryStatus(doc.parsed.expiryDate);
    if (status === "expired") {
      expiringDocs.push(`${DOC_LABELS[req]} (expired)`);
    } else if (status === "expiring") {
      expiringDocs.push(`${DOC_LABELS[req]} (expires ${doc.parsed.expiryDate})`);
    }
  }

  let compliance: ComplianceLevel = "compliant";
  if (missingDocs.length > 0 || expiringDocs.some((e) => e.includes("expired"))) {
    compliance = "non_compliant";
  } else if (expiringDocs.length > 0) {
    compliance = "expiring";
  }

  return { compliance, missingDocs, expiringDocs };
}

export function boardSummary(subbies: Subcontractor[]) {
  return {
    total: subbies.length,
    compliant: subbies.filter((s) => s.compliance === "compliant").length,
    expiring: subbies.filter((s) => s.compliance === "expiring").length,
    nonCompliant: subbies.filter((s) => s.compliance === "non_compliant").length,
  };
}
