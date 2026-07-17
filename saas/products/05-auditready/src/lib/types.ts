export type ChecklistStatus = "not_started" | "in_progress" | "complete" | "gap";

export type CredentialStatus = "valid" | "expiring_soon" | "expired";

export interface PracticeStandard {
  id: string;
  module: string;
  outcome: string;
  indicator: string;
  evidenceHint: string;
}

export interface ChecklistEntry {
  standardId: string;
  status: ChecklistStatus;
  evidenceIds: string[];
  notes: string;
  updatedAt: string;
}

export interface EvidenceItem {
  id: string;
  title: string;
  documentRef: string;
  uploadedAt: string;
  matchedStandardIds: string[];
}

export interface StaffCredential {
  id: string;
  staffName: string;
  credentialType: string;
  expiryDate: string;
  documentRef: string;
  status: CredentialStatus;
}

export interface GapItem {
  standardId: string;
  module: string;
  outcome: string;
  indicator: string;
  status: ChecklistStatus;
  missingEvidence: boolean;
  notes: string;
}

export interface GapReport {
  id: string;
  generatedAt: string;
  providerName: string;
  readinessScore: number;
  gaps: GapItem[];
  expiringCredentials: StaffCredential[];
  summary: string;
  disclaimer: string;
}
