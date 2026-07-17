export type DocumentType =
  | "public_liability"
  | "workers_comp"
  | "trade_licence"
  | "white_card"
  | "swms_acknowledgement";

export type DocStatus = "pending_review" | "confirmed" | "rejected" | "expired";

export type ComplianceLevel = "compliant" | "expiring" | "non_compliant";

export interface ParsedFields {
  insurer?: string;
  policyNumber?: string;
  coverageAmount?: string;
  licenceNumber?: string;
  expiryDate: string;
  confidence: "high" | "medium" | "low";
}

export interface ComplianceDocument {
  id: string;
  subbieId: string;
  documentType: DocumentType;
  fileName: string;
  uploadedAt: string;
  parsed: ParsedFields;
  status: DocStatus;
  confirmedAt?: string;
}

export interface Subcontractor {
  id: string;
  companyName: string;
  contactName: string;
  contactEmail: string;
  trade: string;
  compliance: ComplianceLevel;
  missingDocs: DocumentType[];
  expiringDocs: string[];
}

export const REQUIRED_DOCS: DocumentType[] = [
  "public_liability",
  "workers_comp",
  "trade_licence",
  "white_card",
];

export const DOC_LABELS: Record<DocumentType, string> = {
  public_liability: "Public Liability Insurance",
  workers_comp: "Workers Compensation",
  trade_licence: "Trade Licence",
  white_card: "White Card",
  swms_acknowledgement: "SWMS Acknowledgement",
};
