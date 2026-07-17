import { randomUUID } from "crypto";
import type {
  ChecklistEntry,
  EvidenceItem,
  StaffCredential,
  GapReport,
} from "./types";
import { PRACTICE_STANDARDS } from "./practice-standards";
import { matchEvidenceToStandards } from "./evidence-matcher";
import {
  buildGapReport,
  credentialStatus,
  formatGapReportText,
  updateEntryFromEvidence,
} from "./gap-report";

const globalStore = globalThis as typeof globalThis & {
  __arStore?: {
    providerName: string;
    checklist: Map<string, ChecklistEntry>;
    evidence: Map<string, EvidenceItem>;
    credentials: Map<string, StaffCredential>;
    lastReport?: GapReport;
  };
};

function initChecklist(): Map<string, ChecklistEntry> {
  const map = new Map<string, ChecklistEntry>();
  const now = new Date().toISOString();
  for (const std of PRACTICE_STANDARDS) {
    map.set(std.id, {
      standardId: std.id,
      status: "not_started",
      evidenceIds: [],
      notes: "",
      updatedAt: now,
    });
  }
  return map;
}

function store() {
  if (!globalStore.__arStore) {
    const checklist = initChecklist();
    const evidence = new Map<string, EvidenceItem>();
    const credentials = new Map<string, StaffCredential>();

    const demoEvidence: EvidenceItem[] = [
      {
        id: "ev-001",
        title: "Privacy and Confidentiality Policy v3",
        documentRef: "POL-PRIV-2025",
        uploadedAt: new Date().toISOString(),
        matchedStandardIds: [],
      },
      {
        id: "ev-002",
        title: "Risk Register Q2 2026",
        documentRef: "RISK-REG-Q2",
        uploadedAt: new Date().toISOString(),
        matchedStandardIds: [],
      },
      {
        id: "ev-003",
        title: "Staff Training Competency Matrix",
        documentRef: "HR-COMP-MATRIX",
        uploadedAt: new Date().toISOString(),
        matchedStandardIds: [],
      },
    ];

    for (const ev of demoEvidence) {
      ev.matchedStandardIds = matchEvidenceToStandards(ev);
      evidence.set(ev.id, ev);
    }

    linkEvidenceToChecklist(checklist, evidence);

    const demoCreds: Omit<StaffCredential, "status">[] = [
      {
        id: "cr-001",
        staffName: "Alex Nguyen",
        credentialType: "NDIS Worker Screening",
        expiryDate: "2026-09-15",
        documentRef: "NDS-AN-2024",
      },
      {
        id: "cr-002",
        staffName: "Jordan Lee",
        credentialType: "Working With Children Check",
        expiryDate: "2026-08-01",
        documentRef: "WWCC-JL-2023",
      },
      {
        id: "cr-003",
        staffName: "Sam Patel",
        credentialType: "First Aid Certificate",
        expiryDate: "2026-06-20",
        documentRef: "FA-SP-2025",
      },
    ];

    for (const c of demoCreds) {
      credentials.set(c.id, {
        ...c,
        status: credentialStatus(c.expiryDate),
      });
    }

    globalStore.__arStore = {
      providerName: "Demo Care Supports Pty Ltd",
      checklist,
      evidence,
      credentials,
    };
  }
  return globalStore.__arStore;
}

function linkEvidenceToChecklist(
  checklist: Map<string, ChecklistEntry>,
  evidence: Map<string, EvidenceItem>,
) {
  for (const entry of checklist.values()) {
    entry.evidenceIds = [];
  }
  for (const ev of evidence.values()) {
    for (const stdId of ev.matchedStandardIds) {
      const entry = checklist.get(stdId);
      if (entry && !entry.evidenceIds.includes(ev.id)) {
        entry.evidenceIds.push(ev.id);
      }
    }
  }
  for (const entry of checklist.values()) {
    const updated = updateEntryFromEvidence(entry, entry.evidenceIds.length);
    checklist.set(entry.standardId, updated);
  }
}

export function getProviderName(): string {
  return store().providerName;
}

export function listChecklist(): ChecklistEntry[] {
  return PRACTICE_STANDARDS.map(
    (s) => store().checklist.get(s.id)!,
  );
}

export function listEvidence(): EvidenceItem[] {
  return [...store().evidence.values()];
}

export function listCredentials(): StaffCredential[] {
  return [...store().credentials.values()].sort((a, b) =>
    a.expiryDate.localeCompare(b.expiryDate),
  );
}

export function addEvidence(
  title: string,
  documentRef: string,
): EvidenceItem {
  const ev: EvidenceItem = {
    id: randomUUID(),
    title,
    documentRef,
    uploadedAt: new Date().toISOString(),
    matchedStandardIds: matchEvidenceToStandards({ title, documentRef }),
  };
  store().evidence.set(ev.id, ev);
  linkEvidenceToChecklist(store().checklist, store().evidence);
  return ev;
}

export function updateChecklistNotes(
  standardId: string,
  notes: string,
): ChecklistEntry | null {
  const entry = store().checklist.get(standardId);
  if (!entry) return null;
  entry.notes = notes;
  const updated = updateEntryFromEvidence(entry, entry.evidenceIds.length);
  store().checklist.set(standardId, updated);
  return updated;
}

export function generateReport(): GapReport {
  const report = buildGapReport(
    store().providerName,
    listChecklist(),
    listCredentials(),
  );
  store().lastReport = report;
  return report;
}

export function getLastReport(): GapReport | undefined {
  return store().lastReport;
}

export function getReportText(): string {
  const report = store().lastReport ?? generateReport();
  return formatGapReportText(report);
}

export function resetStore(): void {
  globalStore.__arStore = undefined;
}
